"""
PuLP Mixed-Integer Linear Programming (MILP) Sourcing Optimization Engine

Solves multi-objective allocation balancing landed procurement costs, freight,
supplier quality PPM, capacity limits, MOQs, and contractual share bands.
"""

import time
import math
import pulp
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from .data_loader import DataLoader
from .mrp_engine import MRPEngine
from .supplier_scorecard_engine import ScorecardEngine

class SourcingOptimizer:
    """Mixed-Integer Linear Programming multi-supplier procurement allocation engine."""
    
    def __init__(self, data_loader: DataLoader, risk_lambda: float = 0.15, max_ppm_target: float = 250.0):
        self.loader = data_loader
        self.mrp = MRPEngine(data_loader)
        self.scorecards_engine = ScorecardEngine(data_loader)
        self.risk_lambda = risk_lambda
        self.max_ppm_target = max_ppm_target

    def optimize_sourcing(
        self,
        demand_override_df: Optional[pd.DataFrame] = None,
        capacity_multiplier: Dict[str, float] = None,
        lead_time_delay_weeks: int = 0,
        banned_suppliers: List[str] = None,
        enforce_moq: bool = True,
        enforce_contract_bands: bool = True,
        manual_tuning_constraints: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Executes the PuLP MILP solver across all materials, plants, and planning weeks.
        
        Args:
            demand_override_df: Optional custom demand table for scenario stress-testing.
            capacity_multiplier: Dictionary of {supplier_id: float} scaling capacities (e.g. 0.0 for shutdown).
            lead_time_delay_weeks: Global transit delay added to delivery schedules.
            banned_suppliers: List of supplier IDs to exclude (e.g. quality purge).
            enforce_moq: Boolean flag to enable/disable MOQ step constraints.
            enforce_contract_bands: Boolean flag to enforce min/max allocation caps.
            
        Returns:
            Dictionary containing optimized plan DataFrame, solve metrics, cost breakdown, and status.
        """
        start_time = time.time()
        
        # 1. Compute Net Requirements
        net_df = self.mrp.compute_net_requirements(demand_override_df)
        
        # 2. Gather Model Parameters
        df_pricing = self.loader.pricing
        df_capacity = self.loader.capacity
        df_contracts = self.loader.contracts
        df_freight = self.loader.freight
        scorecards_dict = self.scorecards_engine.get_scorecard_dict()
        
        banned_sups = set(banned_suppliers or [])
        cap_mult = capacity_multiplier or {}
        
        # Filter active pricing
        pricing_filtered = df_pricing[~df_pricing["supplier_id"].isin(banned_sups)].copy()
        
        # Build lookup dictionaries for sub-millisecond solver coefficient access
        # pricing: (sup, mat) -> {unit_price, moq, lead_time}
        pricing_map = {}
        for _, r in pricing_filtered.iterrows():
            pricing_map[(r["supplier_id"], r["material_id"])] = {
                "price": float(r["unit_price_usd"]),
                "moq": float(r["moq_units"]),
                "lead_time": int(r["standard_lead_time_weeks"])
            }
            
        # freight: (sup, plant) -> {cost, transit_days}
        freight_map = {}
        for _, r in df_freight.iterrows():
            freight_map[(r["supplier_id"], r["plant_id"])] = {
                "cost": float(r["freight_cost_per_unit_usd"]),
                "transit_days": int(r["transit_time_days"])
            }
            
        # contracts: (sup, mat) -> {min_share, max_share}
        contract_map = {}
        for _, r in df_contracts.iterrows():
            contract_map[(r["supplier_id"], r["material_id"])] = {
                "min_share": float(r["min_guaranteed_share_pct"]),
                "max_share": float(r["max_allocation_cap_pct"])
            }
            
        # capacity: (sup, mat, week) -> max_cap
        capacity_map = {}
        for _, r in df_capacity.iterrows():
            sup_id = r["supplier_id"]
            mult = cap_mult.get(sup_id, 1.0)
            capacity_map[(sup_id, r["material_id"], r["period_week"])] = float(r["max_weekly_capacity_units"]) * max(0.0, mult)

        # Standard material costs for savings calculation
        std_cost_map = dict(zip(self.loader.material_master["material_id"], self.loader.material_master["standard_cost_usd"]))

        # Group net requirements by period_week for structured batch solving
        weeks = sorted(net_df["period_week"].unique())
        
        allocation_results = []
        total_objective_val = 0.0
        unmet_demand_total = 0.0
        
        for w in weeks:
            week_net = net_df[net_df["period_week"] == w]
            
            # Setup PuLP Problem for week w
            prob = pulp.LpProblem(f"Sourcing_Optimization_{w}", pulp.LpMinimize)
            
            # Decision Variables
            # x[s, m, p]: volume allocated
            # y[s, m]: binary order indicator
            # slack[m, p]: unmet demand slack variable (penalty $10,000/unit)
            x_vars = {}
            y_vars = {}
            slack_vars = {}
            
            # Identify active (m, p) demands in week w
            demand_tuples = []
            for _, r in week_net.iterrows():
                m = r["material_id"]
                p = r["plant_id"]
                req = float(r["net_requirement_units"])
                if req > 0:
                    demand_tuples.append((m, p, req))
                    slack_vars[(m, p)] = pulp.LpVariable(f"slack_{m}_{p}", lowBound=0)
            
            # Find eligible suppliers for materials needed this week
            needed_materials = set(m for m, p, req in demand_tuples)
            active_sup_mat = []
            for (s, m), p_info in pricing_map.items():
                if m in needed_materials:
                    active_sup_mat.append((s, m))
                    y_vars[(s, m)] = pulp.LpVariable(f"y_{s}_{m}", cat=pulp.LpBinary)
                    for _, p, _ in [dt for dt in demand_tuples if dt[0] == m]:
                        x_vars[(s, m, p)] = pulp.LpVariable(f"x_{s}_{m}_{p}", lowBound=0)
                        
            if not demand_tuples:
                continue

            # Objective terms
            obj_terms = []
            
            # 1. Procurement Landed Cost + Risk Penalty
            for (s, m, p), x_var in x_vars.items():
                unit_p = pricing_map[(s, m)]["price"]
                freight_p = freight_map.get((s, p), {}).get("cost", 1.50)
                risk_score = scorecards_dict.get(s, {}).get("composite_risk_index", 20.0)
                
                # Landed cost coefficient = Base Price + Freight + Risk Penalty
                cost_coeff = unit_p + freight_p + (self.risk_lambda * risk_score)
                obj_terms.append(cost_coeff * x_var)
                
            # 2. Transaction / Order Setup Overhead ($150 per supplier-material batch)
            setup_cost = 150.0
            for (s, m), y_var in y_vars.items():
                obj_terms.append(setup_cost * y_var)
                
            # 3. Unmet demand penalty ($10,000/unit)
            for (m, p), s_var in slack_vars.items():
                obj_terms.append(10000.0 * s_var)
                
            prob += pulp.lpSum(obj_terms), "Total_Landed_Cost_and_Risk"

            # Constraints:
            # 1. Demand Fulfillment per (m, p)
            for m, p, req in demand_tuples:
                sup_for_mat = [s for (s_cand, m_cand) in active_sup_mat if m_cand == m for s in [s_cand] if (s, m, p) in x_vars]
                prob += (
                    pulp.lpSum([x_vars[(s, m, p)] for s in sup_for_mat]) + slack_vars[(m, p)] >= req,
                    f"Demand_{m}_{p}"
                )

            # 2. Supplier Capacity & MOQ per (s, m)
            for (s, m) in active_sup_mat:
                relevant_plants = [p for (s_cand, m_cand, p) in x_vars.keys() if s_cand == s and m_cand == m]
                if not relevant_plants:
                    continue
                
                total_alloc_sm = pulp.lpSum([x_vars[(s, m, p)] for p in relevant_plants])
                max_cap = capacity_map.get((s, m, w), 10000.0)
                moq_val = pricing_map[(s, m)]["moq"] if enforce_moq else 0.0
                
                # Big-M upper bound linking x and y
                prob += total_alloc_sm <= max_cap * y_vars[(s, m)], f"Cap_{s}_{m}"
                
                # MOQ lower bound when y = 1
                if enforce_moq and moq_val > 0:
                    prob += total_alloc_sm >= moq_val * y_vars[(s, m)], f"MOQ_{s}_{m}"

            # 3. Contractual Share Allocation Bands (e.g. Max 60% cap, Min 15% guarantee)
            if enforce_contract_bands:
                for m, p, req in demand_tuples:
                    sup_for_mat = [s for (s_cand, m_cand) in active_sup_mat if m_cand == m for s in [s_cand] if (s, m, p) in x_vars]
                    if len(sup_for_mat) > 1:
                        for s in sup_for_mat:
                            min_share = contract_map.get((s, m), {}).get("min_share", 0.15)
                            max_share = contract_map.get((s, m), {}).get("max_share", 0.65)
                            # x_s <= max_share * req
                            prob += x_vars[(s, m, p)] <= (max_share * req) * y_vars[(s, m)], f"MaxShare_{s}_{m}_{p}"
                            # x_s >= min_share * req * y_s (if selected, must take at least min_share)
                            prob += x_vars[(s, m, p)] >= (min_share * req) * y_vars[(s, m)], f"MinShare_{s}_{m}_{p}"

            # 3.5 Manual Tuning Overrides (from Sourcing Lead)
            if manual_tuning_constraints:
                for (s, m, p), x_var in x_vars.items():
                    key = f"{s}_{m}_{p}_{w}"
                    if key in manual_tuning_constraints:
                        target_pct = manual_tuning_constraints[key] / 100.0
                        # Find req for this m, p
                        req = next((r for m_cand, p_cand, r in demand_tuples if m_cand == m and p_cand == p), 0)
                        if req > 0:
                            target_vol = int(round(target_pct * req))
                            prob += x_var == target_vol, f"ManualTuning_{s}_{m}_{p}"

            # 4. Quality PPM Ceiling Constraint per Material
            for m in needed_materials:
                m_allocs = [(s, p, x_vars[(s, m, p)]) for (s, m_cand, p) in x_vars.keys() if m_cand == m]
                if m_allocs:
                    ppm_terms = [
                        scorecards_dict.get(s, {}).get("defect_ppm", 150) * x_var
                        for s, p, x_var in m_allocs
                    ]
                    vol_terms = [x_var for s, p, x_var in m_allocs]
                    prob += pulp.lpSum(ppm_terms) <= self.max_ppm_target * pulp.lpSum(vol_terms), f"PPM_Ceiling_{m}"

            # Solve with bundled CBC Solver (silent mode)
            solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=10)
            status = prob.solve(solver)
            
            # Extract Results
            for (s, m, p), x_var in x_vars.items():
                alloc_qty = x_var.varValue or 0.0
                if alloc_qty > 0.001:
                    unit_p = pricing_map[(s, m)]["price"]
                    freight_p = freight_map.get((s, p), {}).get("cost", 1.50)
                    landed_cost = (unit_p + freight_p) * alloc_qty
                    moq_req = pricing_map[(s, m)]["moq"]
                    # Exact Lead-Time Backward Scheduling:
                    # OffsetWeeks = ceil((LeadTimeWeeks*7 + TransitDays) / 7) + DelayWeeks
                    lt_m_weeks = pricing_map[(s, m)]["lead_time"]
                    transit_days = freight_map.get((s, p), {}).get("transit_days", 7)
                    total_transit_offset_weeks = int(math.ceil((lt_m_weeks * 7 + transit_days) / 7.0)) + lead_time_delay_weeks
                    w_num = int(w[1:])
                    po_week_num = max(1, w_num - total_transit_offset_weeks)
                    po_week_str = f"W{po_week_num:02d}"
                    
                    moq_status = "COMPLIANT" if alloc_qty >= moq_req else "SUB_MOQ_VIOLATION"
                    
                    allocation_results.append({
                        "material_id": m,
                        "material_name": dict(zip(self.loader.material_master["material_id"], self.loader.material_master["material_name"])).get(m, m),
                        "supplier_id": s,
                        "supplier_name": scorecards_dict.get(s, {}).get("supplier_name", s),
                        "plant_id": p,
                        "plant_name": dict(zip(self.loader.plant_master["plant_id"], self.loader.plant_master["plant_name"])).get(p, p),
                        "period_week": w,
                        "allocated_units": int(round(alloc_qty)),
                        "unit_price_usd": unit_p,
                        "freight_cost_per_unit_usd": freight_p,
                        "landed_cost_usd": round(landed_cost, 2),
                        "standard_cost_usd": std_cost_map.get(m, unit_p),
                        "po_release_week": po_week_str,
                        "expected_delivery_week": w,
                        "lead_time_weeks": total_transit_offset_weeks,
                        "moq_compliance_status": moq_status
                    })
                    
            for (m, p), s_var in slack_vars.items():
                slack_qty = s_var.varValue or 0.0
                if slack_qty > 0.001:
                    unmet_demand_total += slack_qty

        df_alloc = pd.DataFrame(allocation_results)
        solve_duration = round(time.time() - start_time, 3)
        
        # Calculate summary financials
        total_allocated_units = int(df_alloc["allocated_units"].sum()) if not df_alloc.empty else 0
        total_landed_cost = float(df_alloc["landed_cost_usd"].sum()) if not df_alloc.empty else 0.0
        
        # Standard baseline benchmark cost
        baseline_cost = sum(
            r["allocated_units"] * r["standard_cost_usd"]
            for _, r in df_alloc.iterrows()
        ) if not df_alloc.empty else 0.0
        
        savings_usd = round(baseline_cost - total_landed_cost, 2)
        savings_pct = round((savings_usd / max(1.0, baseline_cost)) * 100, 2)
        
        total_demand_req = int(net_df["net_requirement_units"].sum())
        service_level_pct = round((total_allocated_units / max(1, total_demand_req)) * 100, 2)

        # Get actual solver status
        solver_status = pulp.LpStatus[status].upper()
        if solver_status == "OPTIMAL" and unmet_demand_total > 0:
            solver_status = "OPTIMAL_WITH_SHORTAGE"

        return {
            "status": solver_status,
            "solver_name": "PuLP CBC MILP",
            "solve_duration_sec": solve_duration,
            "total_allocated_units": total_allocated_units,
            "total_net_demand_units": total_demand_req,
            "unmet_demand_units": int(unmet_demand_total),
            "service_level_pct": service_level_pct,
            "total_landed_cost_usd": round(total_landed_cost, 2),
            "baseline_standard_cost_usd": round(baseline_cost, 2),
            "cost_savings_realized_usd": savings_usd,
            "cost_savings_pct": savings_pct,
            "allocation_count": len(df_alloc),
            "allocations_df": df_alloc
        }
