"""
Spend Analytics & Concentration Risk Engine

Calculates total procurement spend, landed cost waterfalls, savings realized,
and supplier market concentration (Herfindahl-Hirschman Index - HHI).
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from .data_loader import DataLoader
from .supplier_scorecard_engine import ScorecardEngine

class SpendEngine:
    """Computes procurement spend breakdowns, cost waterfalls, and vendor concentration indices."""
    
    def __init__(self, data_loader: DataLoader):
        self.loader = data_loader
        self.scorecards = ScorecardEngine(data_loader)

    def analyze_spend(self, allocations_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Comprehensive spend analysis on solved procurement allocations.
        """
        if allocations_df.empty:
            return {
                "total_spend_usd": 0.0,
                "base_material_spend_usd": 0.0,
                "freight_spend_usd": 0.0,
                "savings_usd": 0.0,
                "savings_pct": 0.0,
                "hhi_index": 0.0,
                "hhi_status": "DIVERSIFIED",
                "weighted_otd_pct": 0.0,
                "weighted_ppm": 0.0,
                "by_supplier": [],
                "by_category": [],
                "by_plant": []
            }
            
        materials_df = self.loader.material_master
        scorecards_dict = self.scorecards.get_scorecard_dict()
        
        # Merge material categories
        merged = allocations_df.merge(
            materials_df[["material_id", "category"]],
            on="material_id",
            how="left"
        )
        
        # Cost components
        base_material_spend = sum(
            r["allocated_units"] * r["unit_price_usd"]
            for _, r in merged.iterrows()
        )
        freight_spend = sum(
            r["allocated_units"] * r["freight_cost_per_unit_usd"]
            for _, r in merged.iterrows()
        )
        total_landed_spend = float(merged["landed_cost_usd"].sum())
        
        baseline_standard_spend = sum(
            r["allocated_units"] * r["standard_cost_usd"]
            for _, r in merged.iterrows()
        )
        savings_usd = round(baseline_standard_spend - total_landed_spend, 2)
        savings_pct = round((savings_usd / max(1.0, baseline_standard_spend)) * 100.0, 2)
        
        # Supplier distribution and HHI
        sup_spend = merged.groupby(["supplier_id", "supplier_name"]).agg(
            total_spend_usd=("landed_cost_usd", "sum"),
            allocated_units=("allocated_units", "sum")
        ).reset_index()
        
        total_units = merged["allocated_units"].sum()
        sup_spend["spend_share_pct"] = round((sup_spend["total_spend_usd"] / max(1.0, total_landed_spend)) * 100.0, 2)
        sup_spend["volume_share_pct"] = round((sup_spend["allocated_units"] / max(1.0, total_units)) * 100.0, 2)
        
        # Herfindahl-Hirschman Index (HHI) based on spend shares
        # HHI = sum( (s_i * 100)^2 ) where s_i is fractional share, so (share_pct)^2
        hhi_val = round(sum(sup_spend["spend_share_pct"] ** 2), 1)
        if hhi_val < 1500:
            hhi_status = "HEALTHY_DIVERSIFIED"
            hhi_desc = "Low Concentration Risk (<1,500)"
        elif hhi_val <= 2500:
            hhi_status = "MODERATELY_CONCENTRATED"
            hhi_desc = "Moderate Concentration (1,500 - 2,500)"
        else:
            hhi_status = "HIGHLY_CONCENTRATED"
            hhi_desc = "High Vendor Lock-in Risk (>2,500)"
            
        # Category breakdown
        cat_spend = merged.groupby("category").agg(
            total_spend_usd=("landed_cost_usd", "sum"),
            allocated_units=("allocated_units", "sum")
        ).reset_index()
        cat_spend["spend_share_pct"] = round((cat_spend["total_spend_usd"] / max(1.0, total_landed_spend)) * 100.0, 2)
        
        # Plant breakdown
        plant_spend = merged.groupby(["plant_id", "plant_name"]).agg(
            total_spend_usd=("landed_cost_usd", "sum"),
            allocated_units=("allocated_units", "sum")
        ).reset_index()
        plant_spend["spend_share_pct"] = round((plant_spend["total_spend_usd"] / max(1.0, total_landed_spend)) * 100.0, 2)

        # Weighted metrics
        total_vol = max(1.0, float(merged["allocated_units"].sum()))
        weighted_otd = sum(
            float(r["allocated_units"]) * float(scorecards_dict.get(r["supplier_id"], {}).get("historical_otd_pct", 90.0))
            for _, r in merged.iterrows()
        ) / total_vol
        
        weighted_ppm = sum(
            float(r["allocated_units"]) * float(scorecards_dict.get(r["supplier_id"], {}).get("defect_ppm", 150.0))
            for _, r in merged.iterrows()
        ) / total_vol
        
        weighted_risk = sum(
            float(r["allocated_units"]) * float(scorecards_dict.get(r["supplier_id"], {}).get("composite_risk_index", 20.0))
            for _, r in merged.iterrows()
        ) / total_vol

        return {
            "total_spend_usd": round(total_landed_spend, 2),
            "base_material_spend_usd": round(base_material_spend, 2),
            "freight_spend_usd": round(freight_spend, 2),
            "baseline_standard_spend_usd": round(baseline_standard_spend, 2),
            "savings_usd": savings_usd,
            "savings_pct": savings_pct,
            "hhi_index": hhi_val,
            "hhi_status": hhi_status,
            "hhi_description": hhi_desc,
            "weighted_otd_pct": round(weighted_otd, 2),
            "weighted_ppm": round(weighted_ppm, 1),
            "weighted_risk_index": round(weighted_risk, 2),
            "by_supplier": sup_spend.sort_values(by="total_spend_usd", ascending=False).to_dict(orient="records"),
            "by_category": cat_spend.sort_values(by="total_spend_usd", ascending=False).to_dict(orient="records"),
            "by_plant": plant_spend.sort_values(by="total_spend_usd", ascending=False).to_dict(orient="records")
        }
