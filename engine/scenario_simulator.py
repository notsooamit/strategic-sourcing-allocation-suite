"""
What-If Strategy & Disruption Scenario Simulator

Simulates parametric stress-tests including supplier outages, demand surges,
logistics lead-time delays, and quality threshold tightenings.
"""

import copy
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from .data_loader import DataLoader
from .optimizer import SourcingOptimizer
from .spend_analytics_engine import SpendEngine

class ScenarioSimulator:
    """Parametric What-If scenario simulation and stress-testing engine."""
    
    def __init__(self, data_loader: DataLoader, optimizer: SourcingOptimizer):
        self.loader = data_loader
        self.optimizer = optimizer
        self.spend_engine = SpendEngine(data_loader)

    def run_scenario(
        self,
        scenario_name: str,
        supplier_capacity_cuts: Dict[str, float] = None, # e.g. {"SUP_003": 0.0} (0% remaining)
        demand_surge_pct: float = 0.0, # e.g. +45.0%
        target_plants: List[str] = None, # e.g. ["PLANT_01"] or None for all
        lead_time_delay_weeks: int = 0, # e.g. +3 weeks
        max_ppm_threshold: Optional[float] = 150.0 # e.g. Quality Purge
    ) -> Dict[str, Any]:
        """
        Executes a What-If scenario and calculates exact deltas against the baseline plan.
        """
        # 1. Obtain baseline plan
        baseline_res = self.optimizer.optimize_sourcing()
        baseline_spend = self.spend_engine.analyze_spend(baseline_res["allocations_df"])
        
        # 2. Prepare scenario parameters
        # Demand modification
        demand_df = self.loader.demand.copy()
        if demand_surge_pct != 0.0:
            surge_mult = 1.0 + (demand_surge_pct / 100.0)
            if target_plants:
                mask = demand_df["plant_id"].isin(target_plants)
                demand_df.loc[mask, "forecasted_demand_units"] = (
                    demand_df.loc[mask, "forecasted_demand_units"] * surge_mult
                ).astype(int)
            else:
                demand_df["forecasted_demand_units"] = (
                    demand_df["forecasted_demand_units"] * surge_mult
                ).astype(int)

        # Capacity cuts
        cap_mult = supplier_capacity_cuts or {}
        
        # Banned suppliers based on PPM threshold
        banned = []
        if max_ppm_threshold is not None:
            scorecards = self.loader.scorecards
            banned = scorecards[scorecards["defect_ppm"] > max_ppm_threshold]["supplier_id"].tolist()

        # 3. Solve scenario MILP
        scenario_res = self.optimizer.optimize_sourcing(
            demand_override_df=demand_df,
            capacity_multiplier=cap_mult,
            lead_time_delay_weeks=lead_time_delay_weeks,
            banned_suppliers=banned
        )
        scenario_spend = self.spend_engine.analyze_spend(scenario_res["allocations_df"])

        # 4. Calculate Deltas
        base_cost = baseline_res["total_landed_cost_usd"]
        scen_cost = scenario_res["total_landed_cost_usd"]
        cost_delta_usd = round(scen_cost - base_cost, 2)
        cost_delta_pct = round((cost_delta_usd / max(1.0, base_cost)) * 100.0, 2)
        
        base_fill = baseline_res["service_level_pct"]
        scen_fill = scenario_res["service_level_pct"]
        fill_delta_pct = round(scen_fill - base_fill, 2)
        
        unmet_delta = scenario_res["unmet_demand_units"] - baseline_res["unmet_demand_units"]

        # 5. Generate Contingency Recommendations
        recommendations = []
        if unmet_delta > 0:
            recommendations.append(f"⚠️ Critical Capacity Deficit: {unmet_delta:,} units unmet. Immediately authorize secondary contract volume expansions.")
        if cost_delta_pct > 10.0:
            recommendations.append(f"💰 Landed Cost Surge: +{cost_delta_pct}% (+${cost_delta_usd:,.2f}). Trigger emergency freight subsidy approval.")
        if lead_time_delay_weeks > 0:
            recommendations.append(f"⏱️ Transit Delay: PO release windows advanced by {lead_time_delay_weeks} weeks to maintain on-time plant deliveries.")
        if not recommendations:
            recommendations.append("✅ Robust Network Resilience: Network successfully absorbed stress within standard operating buffers.")

        return {
            "scenario_name": scenario_name,
            "parameters": {
                "capacity_cuts": cap_mult,
                "demand_surge_pct": demand_surge_pct,
                "target_plants": target_plants or "ALL",
                "lead_time_delay_weeks": lead_time_delay_weeks,
                "banned_suppliers_count": len(banned)
            },
            "baseline": {
                "total_landed_cost_usd": base_cost,
                "service_level_pct": base_fill,
                "unmet_demand_units": baseline_res["unmet_demand_units"],
                "hhi_index": baseline_spend["hhi_index"],
                "weighted_otd_pct": baseline_spend["weighted_otd_pct"]
            },
            "scenario": {
                "total_landed_cost_usd": scen_cost,
                "service_level_pct": scen_fill,
                "unmet_demand_units": scenario_res["unmet_demand_units"],
                "hhi_index": scenario_spend["hhi_index"],
                "weighted_otd_pct": scenario_spend["weighted_otd_pct"]
            },
            "deltas": {
                "cost_delta_usd": cost_delta_usd,
                "cost_delta_pct": cost_delta_pct,
                "service_level_delta_pct": fill_delta_pct,
                "unmet_demand_delta_units": unmet_delta
            },
            "recommendations": recommendations,
            "scenario_allocations_count": scenario_res["allocation_count"]
        }
