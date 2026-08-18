"""
    Prototype Predictive Delay Engine
    
    Evaluates risk of supply chain delivery delays exceeding 3 days using a calibrated logistic model.
    Note: The coefficients used here are prototype/calibrated values for the demonstration, 
    not generated from a historical machine learning training pipeline.
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
        self.active_disruption = False
        self.expedited_pos = set()

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
        # Build pricing and freight lookups
        df_pricing = self.loader.pricing
        df_freight = self.loader.freight
        
        moq_lookup = {}
        for _, r in df_pricing.iterrows():
            moq_lookup[(r["supplier_id"], r["material_id"])] = float(r["moq_units"])
            
        freight_lookup = {}
        for _, r in df_freight.iterrows():
            freight_lookup[(r["supplier_id"], r["plant_id"])] = {
                "transit_days": int(r["transit_time_days"]),
                "lane_reliability": float(r.get("lane_reliability_pct", 95.0))
            }
            
        results = []
        for _, row in allocations_df.iterrows():
            s_id = row["supplier_id"]
            m_id = row["material_id"]
            p_id = row["plant_id"]
            week = row["period_week"]
            alloc_qty = float(row["allocated_units"])
            sup_info = scorecards_dict.get(s_id, {})
            otd = float(sup_info.get("historical_otd_pct", 95.0))
            var_days = float(sup_info.get("lead_time_variance_days", 1.5))
            geo_risk = float(sup_info.get("base_financial_risk_score", 1.5))
            
            f_info = freight_lookup.get((s_id, p_id), {"transit_days": 7, "lane_reliability": 95.0})
            transit_days = f_info["transit_days"]
            lane_rel = f_info["lane_reliability"]
            
            po_id = f"PO-{s_id}-{m_id}-{week}"
            if po_id in self.expedited_pos:
                transit_days = max(1, transit_days - 5)
                lane_rel = min(100.0, lane_rel + 5.0)
            
            # Calculate utilization just for reporting to frontend
            max_cap = cap_lookup.get((s_id, m_id, week), 10000.0)
            util_ratio = min(1.20, alloc_qty / max(100.0, max_cap))
            
            moq_val = moq_lookup.get((s_id, m_id), 500.0)
            order_ratio = min(2.5, alloc_qty / max(100.0, moq_val))
            
            # Disruption Simulation Logic
            if self.active_disruption and s_id.endswith(('001', '003', '005', '007')):
                transit_days += 14
                lane_rel -= 30.0
                geo_risk += 2.0
                
            # Logistic logit from spec: z = b0 + b1*(1-OTD) + b2*Var + b3*Transit + b4*(1-LaneRel) + b5*(Order/MOQ)
            # These are manually configured prototype coefficients calibrated to represent business risk.
            z = (
                self.b0 +
                1.5 * (1.0 - (otd / 100.0)) +
                self.b_var * var_days +
                0.05 * transit_days +
                2.0 * (1.0 - (lane_rel / 100.0)) +
                self.b_size * order_ratio
            )
            
            p_delay_gt_3 = 1.0 / (1.0 + math.exp(-z))
            p_delay_pct = round(p_delay_gt_3 * 100.0, 1)
            
            if p_delay_pct < 25.0:
                risk_tier = "GREEN"
                status_label = "Low Delay Risk (< 25%)"
                recommended_action = "Direct PO Release Approved"
                split_needed = False
            elif p_delay_pct <= 50.0:
                risk_tier = "AMBER"
                status_label = "Moderate Delay Risk (25-50%)"
                recommended_action = "Expedited Transit Buffer Required"
                split_needed = False
            else:
                risk_tier = "RED"
                status_label = "High Delay Risk (> 50%)"
                recommended_action = "Split-Sourcing Contingency Required"
                split_needed = True
                
            results.append({
                "po_id": po_id,
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
        Identifies high-risk orders and formulates a max-allocation cap constraint
        to force the MILP to re-allocate 35% of the volume from high-risk suppliers.
        """
        evaluated = self.evaluate_allocations(allocations_df)
        if evaluated.empty:
            return {"max_allocation_caps": {}, "target_shifts_count": 0, "target_shifted_volume": 0}
            
        caps = {}
        target_shifted_vol = 0
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
                shift_units = int(units * 0.35)
                remain_units = units - shift_units
                target_shifted_vol += shift_units
                shifts_count += 1
                
                key = f"{s_id}_{m_id}_{p_id}_{week}"
                caps[key] = remain_units
                
        return {
            "max_allocation_caps": caps, 
            "target_shifts_count": shifts_count, 
            "target_shifted_volume": target_shifted_vol
        }
