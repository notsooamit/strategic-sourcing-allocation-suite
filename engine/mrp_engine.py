"""
Material Requirements Planning (MRP) & Netting Engine

Handles time-phased BOM explosion, gross demand netting against on-hand inventory,
safety stock buffer ratios, and weeks of supply (WOS) analytics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from .data_loader import DataLoader

class MRPEngine:
    """Computes time-phased gross and net material requirements across assembly plants."""
    
    def __init__(self, data_loader: DataLoader):
        self.loader = data_loader

    def compute_net_requirements(self, demand_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Calculates Net Requirements for each material, plant, and week:
        NetReq = max(0, GrossReq + SafetyStock - OnHand - ScheduledReceipts)
        
        NOTE: The business specification includes '- ScheduledReceipts' (In-Transit inventory).
        However, the current relational database schema and CSV datasets (e.g., current_inventory, 
        plant_material_demand) lack any tables or columns for open POs or in-transit receipts. 
        Therefore, this calculation relies solely on OnHand inventory. Data fabrication has been 
        explicitly avoided to maintain prototype integrity.

        Also calculates:
        InventoryCoverageRatio = (OnHand / (GrossReq + SafetyStock)) * 100
        WeeksOfSupply = OnHand / AverageWeeklyDemand
        """
        if demand_df is None:
            demand_df = self.loader.demand
            
        inventory_df = self.loader.inventory
        materials_df = self.loader.material_master
        
        # Merge demand with inventory parameters
        merged = demand_df.merge(
            inventory_df,
            on=["material_id", "plant_id"],
            how="left"
        ).merge(
            materials_df[["material_id", "material_name", "category", "unit_of_measure", "standard_cost_usd", "criticality"]],
            on="material_id",
            how="left"
        )
        
        merged = merged.sort_values(by=["material_id", "plant_id", "period_week"]).reset_index(drop=True)
        
        # Calculate dynamic inventory tracking per (material, plant)
        net_rows = []
        grouped = merged.groupby(["material_id", "plant_id"])
        
        for (mat_id, plant_id), group in grouped:
            on_hand = group["available_on_hand_units"].iloc[0]
            safety_stock = group["safety_stock_threshold_units"].iloc[0]
            avg_weekly_demand = max(1.0, float(group["forecasted_demand_units"].mean()))
            weeks_of_supply = round(on_hand / avg_weekly_demand, 2)
            current_avail = on_hand
            
            for _, row in group.iterrows():
                gross_req = row["forecasted_demand_units"]
                week = row["period_week"]
                
                # Coverage ratio prior to netting replenishment
                eff_denom = max(1.0, float(gross_req + safety_stock))
                cov_ratio_pct = round((float(current_avail) / eff_denom) * 100.0, 1)
                
                effective_needed = gross_req + safety_stock
                if current_avail >= effective_needed:
                    net_req = 0
                    current_avail -= gross_req
                else:
                    net_req = effective_needed - current_avail
                    current_avail = safety_stock
                    
                net_rows.append({
                    "material_id": mat_id,
                    "material_name": row["material_name"],
                    "category": row["category"],
                    "plant_id": plant_id,
                    "period_week": week,
                    "gross_demand_units": gross_req,
                    "on_hand_units": on_hand,
                    "safety_stock_units": safety_stock,
                    "net_requirement_units": int(net_req),
                    "inventory_coverage_ratio_pct": cov_ratio_pct,
                    "weeks_of_supply": weeks_of_supply,
                    "unit_of_measure": row["unit_of_measure"],
                    "standard_cost_usd": row["standard_cost_usd"],
                    "criticality": row["criticality"]
                })
                
        return pd.DataFrame(net_rows)

    def get_demand_summary(self) -> Dict[str, Any]:
        """Returns high-level summary statistics for demand, inventory coverage, and netting."""
        net_df = self.compute_net_requirements()
        
        total_gross = int(net_df["gross_demand_units"].sum())
        total_net = int(net_df["net_requirement_units"].sum())
        avg_wos = round(float(net_df["weeks_of_supply"].mean()), 2)
        avg_cov = round(float(net_df["inventory_coverage_ratio_pct"].mean()), 1)
        
        # Category breakdown
        cat_summary = net_df.groupby("category").agg({
            "gross_demand_units": "sum",
            "net_requirement_units": "sum"
        }).reset_index().to_dict(orient="records")
        
        # Plant breakdown
        plant_summary = net_df.groupby("plant_id").agg({
            "gross_demand_units": "sum",
            "net_requirement_units": "sum"
        }).reset_index().to_dict(orient="records")
        
        # Weekly profile
        weekly_summary = net_df.groupby("period_week").agg({
            "gross_demand_units": "sum",
            "net_requirement_units": "sum"
        }).reset_index().to_dict(orient="records")
        
        return {
            "total_gross_demand_units": total_gross,
            "total_net_requirement_units": total_net,
            "mean_weeks_of_supply": avg_wos,
            "mean_inventory_coverage_pct": avg_cov,
            "inventory_coverage_pct": round((1.0 - (total_net / max(1, total_gross))) * 100, 2),
            "by_category": cat_summary,
            "by_plant": plant_summary,
            "by_week": weekly_summary
        }
