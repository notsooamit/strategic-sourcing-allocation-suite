"""
Pre-PO Predictive Delivery Delay Probability Engine

Calculates shipment delay probabilities prior to Purchase Order dispatch using
supplier backlog capacity loading, lead-time variance telemetry, and geopolitical risk factors.
Provides automatic split-sourcing contingency recommendations.
"""

import math
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from .data_loader import DataLoader
from .supplier_scorecard_engine import ScorecardEngine

class PredictiveDelayEngine:
    """Predicts pre-release delivery delay probabilities and generates split-sourcing buffers."""
    
    def __init__(
        self,
        data_loader: DataLoader,
        beta_0: float = -4.5,
        beta_util: float = 1.8,
        beta_var: float = 0.35,
        beta_size: float = 0.40,
        beta_geo: float = 0.30
    ):
        self.loader = data_loader
        self.scorecards = ScorecardEngine(data_loader)
        self.b0 = beta_0
        self.b_util = beta_util
        self.b_var = beta_var
        self.b_size = beta_size
        self.b_geo = beta_geo

    def evaluate_allocations(self, allocations_df: pd.DataFrame) -> pd.DataFrame:
        """
        Evaluates P(Delay) for every line-item in the proposed purchase order plan.
        
        P(Delay) = 1 / (1 + exp(-(beta_0 + beta_1*Util + beta_2*Variance + beta_3*OrderRatio + beta_4*GeoRisk)))
        """
        if allocations_df.empty:
            return pd.DataFrame()
            
        scorecards_dict = self.scorecards.get_scorecard_dict()
        df_capacity = self.loader.capacity
        
        # Build capacity & pricing MOQ lookups
        cap_lookup = {}
        for _, r in df_capacity.iterrows():
            cap_lookup[(r["supplier_id"], r["material_id"], r["period_week"])] = float(r["max_weekly_capacity_units"])
            
        df_pricing = self.loader.pricing
        moq_lookup = {}
        for _, r in df_pricing.iterrows():
            moq_lookup[(r["supplier_id"], r["material_id"])] = float(r["moq_units"])

        # Calculate supplier weekly material loading
        weekly_material_load = allocations_df.groupby(["supplier_id", "material_id", "period_week"])["allocated_units"].sum().to_dict()
        
        results = []
        for _, row in allocations_df.iterrows():
            s_id = row["supplier_id"]
            m_id = row["material_id"]
            p_id = row["plant_id"]
            week = row["period_week"]
            alloc_qty = float(row["allocated_units"])
            
            sup_info = scorecards_dict.get(s_id, {})
            var_days = float(sup_info.get("lead_time_variance_days", 1.5))
            geo_risk = float(sup_info.get("base_financial_risk_score", 1.5))
            
            # Supplier utilization & Order/MOQ ratio calculation
            max_cap = cap_lookup.get((s_id, m_id, week), 10000.0)
            moq_val = moq_lookup.get((s_id, m_id), 500.0)
            total_mat_load = weekly_material_load.get((s_id, m_id, week), alloc_qty)
            util_ratio = min(1.20, total_mat_load / max(100.0, max_cap))
            order_ratio = min(2.5, alloc_qty / max(100.0, moq_val))
            
            # Logistic logit: P(Delay > 3d)
            z = (
                self.b0 +
                (self.b_util * util_ratio) +
                (self.b_var * var_days) +
                (self.b_size * order_ratio) +
                (self.b_geo * geo_risk)
            )
            
            p_delay = 1.0 / (1.0 + math.exp(-z))
            p_delay_pct = round(p_delay * 100.0, 1)
            
            # Classification
            if p_delay_pct <= 15.0:
                risk_tier = "GREEN"
                status_label = "Low Delay Risk (<15%)"
                recommended_action = "Direct PO Release Approved"
                split_needed = False
            elif p_delay_pct <= 35.0:
                risk_tier = "AMBER"
                status_label = "Moderate Delay Risk (15-35%)"
                recommended_action = "Expedited Transit Buffer Advised"
                split_needed = False
            else:
                risk_tier = "RED"
                status_label = "High Delay Risk (>35%)"
                recommended_action = "Split-Sourcing Contingency Required"
                split_needed = True
                
            results.append({
                "po_id": f"PO-{s_id}-{m_id}-{week}",
                "material_id": m_id,
                "material_name": row.get("material_name", m_id),
                "supplier_id": s_id,
                "supplier_name": row.get("supplier_name", s_id),
                "plant_id": p_id,
                "plant_name": row.get("plant_name", p_id),
                "period_week": week,
                "allocated_units": int(alloc_qty),
                "utilization_pct": round(util_ratio * 100, 1),
                "lead_time_variance_days": var_days,
                "geo_financial_risk": geo_risk,
                "delay_probability_pct": p_delay_pct,
                "risk_tier": risk_tier,
                "status_label": status_label,
                "recommended_action": recommended_action,
                "split_sourcing_recommended": split_needed
            })
            
        df_delay = pd.DataFrame(results)
        self.loader.save_delay_alerts(df_delay)
        return df_delay

    def get_split_sourcing_contingency(self, allocations_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Identifies high-risk orders and formulates a rebalanced split-sourcing contingency plan.
        Transfers 35% of volume from high-risk suppliers to backup certified suppliers.
        """
        evaluated = self.evaluate_allocations(allocations_df)
        if evaluated.empty:
            return {"rebalanced_allocations": allocations_df, "shifts_count": 0, "shifted_volume": 0}
            
        df_pricing = self.loader.pricing
        scorecards_dict = self.scorecards.get_scorecard_dict()
        
        rebalanced_rows = []
        total_shifted_vol = 0
        shifts_count = 0
        
        for _, row in allocations_df.iterrows():
            m_id = row["material_id"]
            s_id = row["supplier_id"]
            p_id = row["plant_id"]
            week = row["period_week"]
            units = row["allocated_units"]
            
            # Check if this allocation is high risk
            match = evaluated[
                (evaluated["material_id"] == m_id) &
                (evaluated["supplier_id"] == s_id) &
                (evaluated["plant_id"] == p_id) &
                (evaluated["period_week"] == week)
            ]
            
            if not match.empty and match.iloc[0]["risk_tier"] == "RED" and units > 500:
                # Find alternative approved suppliers for this material
                alt_sups = df_pricing[
                    (df_pricing["material_id"] == m_id) &
                    (df_pricing["supplier_id"] != s_id)
                ]["supplier_id"].tolist()
                
                # Pick backup with lowest composite risk
                best_backup = None
                lowest_risk = 999.0
                for alt_s in alt_sups:
                    alt_risk = scorecards_dict.get(alt_s, {}).get("composite_risk_index", 50.0)
                    if alt_risk < lowest_risk:
                        lowest_risk = alt_risk
                        best_backup = alt_s
                        
                if best_backup:
                    shift_units = int(units * 0.35)
                    remain_units = units - shift_units
                    total_shifted_vol += shift_units
                    shifts_count += 1
                    
                    # Primary supplier reduced allocation
                    p1_row = dict(row)
                    p1_row["allocated_units"] = remain_units
                    p1_row["landed_cost_usd"] = round(p1_row["landed_cost_usd"] * (remain_units / units), 2)
                    rebalanced_rows.append(p1_row)
                    
                    # Secondary supplier contingency allocation
                    alt_pricing_row = df_pricing[
                        (df_pricing["material_id"] == m_id) &
                        (df_pricing["supplier_id"] == best_backup)
                    ].iloc[0]
                    alt_unit_price = float(alt_pricing_row["unit_price_usd"])
                    alt_lt = int(alt_pricing_row["standard_lead_time_weeks"])
                    
                    p2_row = dict(row)
                    p2_row["supplier_id"] = best_backup
                    p2_row["supplier_name"] = scorecards_dict.get(best_backup, {}).get("supplier_name", best_backup)
                    p2_row["allocated_units"] = shift_units
                    p2_row["unit_price_usd"] = alt_unit_price
                    p2_row["landed_cost_usd"] = round((alt_unit_price + float(row["freight_cost_per_unit_usd"])) * shift_units, 2)
                    p2_row["lead_time_weeks"] = alt_lt
                    rebalanced_rows.append(p2_row)
                    continue
                    
            rebalanced_rows.append(dict(row))
            
        df_rebalanced = pd.DataFrame(rebalanced_rows)
        return {
            "rebalanced_allocations_df": df_rebalanced,
            "shifts_count": shifts_count,
            "shifted_volume_units": total_shifted_vol,
            "status": "CONTINGENCY_BUFFER_APPLIED"
        }
