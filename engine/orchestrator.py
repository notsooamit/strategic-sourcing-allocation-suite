"""
Strategic Sourcing Master Orchestrator

Coordinates end-to-end data ingestion, MRP netting, MILP optimization, predictive
delay analysis, spend analytics, and governance lifecycle management.
"""

import copy
import threading
import datetime
import pandas as pd
from typing import Dict, List, Any, Optional

from .data_loader import DataLoader
from .mrp_engine import MRPEngine
from .supplier_scorecard_engine import ScorecardEngine
from .optimizer import SourcingOptimizer
from .predictive_delay_engine import PredictiveDelayEngine
from .spend_analytics_engine import SpendEngine
from .scenario_simulator import ScenarioSimulator
from .sourcing_workflow import SourcingWorkflowManager

class SourcingOrchestrator:
    """Singleton orchestrator managing all platform computational engines and state."""
    
    _instance = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SourcingOrchestrator, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, data_dir: Optional[str] = None):
        with self._lock:
            if getattr(self, "_initialized", False):
                return
            self.data_loader = DataLoader(data_dir)
            self.mrp_engine = MRPEngine(self.data_loader)
            self.scorecard_engine = ScorecardEngine(self.data_loader)
            self.optimizer = SourcingOptimizer(self.data_loader)
            self.predictive_delay_engine = PredictiveDelayEngine(self.data_loader)
            self.spend_engine = SpendEngine(self.data_loader)
            self.scenario_simulator = ScenarioSimulator(self.data_loader, self.optimizer)
            self.workflow_manager = SourcingWorkflowManager(self.data_loader)
            
            # Collaborative event feed
            self.activity_log: List[Dict[str, Any]] = [
                {
                    "id": "EVT-001",
                    "timestamp": "2026-08-10 10:00:00",
                    "user": "Robert Sterling (CPO)",
                    "action": "GOVERNANCE_REVIEW",
                    "details": "Initiated Q3 Strategic Sourcing Review Cycle across 5 manufacturing hubs."
                },
                {
                    "id": "EVT-002",
                    "timestamp": "2026-08-10 10:15:30",
                    "user": "System Solver",
                    "action": "OPTIMIZATION_SOLVED",
                    "details": "PuLP MILP Solver completed 12-week allocation across 12 suppliers and 40 direct materials."
                }
            ]
            
            self._cached_optimization_result = None
            self._cached_spend_result = None
            self._cached_delay_result = None
            
            # Run initial baseline pipeline
            self.run_full_pipeline()
            self._initialized = True

    def log_activity(self, user: str, action: str, details: str):
        """Appends an event to the live activity stream."""
        with self._lock:
            evt_id = f"EVT-{len(self.activity_log) + 1:03d}"
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.activity_log.insert(0, {
                "id": evt_id,
                "timestamp": now_str,
                "user": user,
                "action": action,
                "details": details
            })
            if len(self.activity_log) > 50:
                self.activity_log.pop()

    def run_full_pipeline(self) -> Dict[str, Any]:
        """Executes full optimization, delay prediction, and spend analytics reconciliation."""
        with self._lock:
            # 1. Run MILP Solver
            opt_res = self.optimizer.optimize_sourcing()
            alloc_df = opt_res["allocations_df"]
            self.data_loader.save_optimized_plan(alloc_df)
            self._cached_optimization_result = opt_res
            
            # 2. Run Pre-PO Delay Risk Model
            delay_df = self.predictive_delay_engine.evaluate_allocations(alloc_df)
            self._cached_delay_result = delay_df
            
            # 3. Compute Spend Analytics & Concentration HHI
            spend_res = self.spend_engine.analyze_spend(alloc_df)
            self._cached_spend_result = spend_res
            
            return {
                "status": "SUCCESS",
                "solver_status": opt_res["status"],
                "total_spend_usd": spend_res["total_spend_usd"],
                "cost_savings_usd": spend_res["savings_usd"],
                "cost_savings_pct": spend_res["savings_pct"],
                "service_level_pct": opt_res["service_level_pct"],
                "hhi_index": spend_res["hhi_index"],
                "allocations_count": len(alloc_df),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    def get_dashboard_kpis(self) -> Dict[str, Any]:
        """Returns consolidated executive KPIs for the dashboard."""
        with self._lock:
            if self._cached_spend_result is None or self._cached_optimization_result is None:
                self.run_full_pipeline()
                
            spend = self._cached_spend_result
            opt = self._cached_optimization_result
            cycle = self.workflow_manager.get_cycle_state()
            
            return {
                "total_spend_usd": spend["total_spend_usd"],
                "cost_savings_usd": spend["savings_usd"],
                "cost_savings_pct": spend["savings_pct"],
                "mean_otd_pct": spend["weighted_otd_pct"],
                "ppm_defect_rate": spend["weighted_ppm"],
                "sourcing_risk_index": spend["weighted_risk_index"],
                "hhi_concentration_index": spend["hhi_index"],
                "hhi_status": spend["hhi_status"],
                "hhi_description": spend["hhi_description"],
                "service_level_pct": opt["service_level_pct"],
                "total_allocated_units": opt["total_allocated_units"],
                "cycle_progress_pct": cycle["cycle_progress_pct"],
                "cycle_current_stage": cycle["current_stage"]["title"],
                "total_suppliers_active": len(spend["by_supplier"]),
                "materials_count": len(self.data_loader.material_master),
                "plants_count": len(self.data_loader.plant_master)
            }

    def get_demand_data(self) -> Dict[str, Any]:
        """Returns demand netting and time-phased breakdown."""
        with self._lock:
            summary = self.mrp_engine.get_demand_summary()
            net_df = self.mrp_engine.compute_net_requirements()
            return {
                "summary": summary,
                "net_requirements": net_df.head(100).to_dict(orient="records"),
                "total_rows": len(net_df)
            }

    def get_scorecards_data(self) -> List[Dict[str, Any]]:
        """Returns supplier scorecards and quality audit rankings."""
        with self._lock:
            df = self.scorecard_engine.compute_scorecards()
            return df.to_dict(orient="records")

    def get_procurement_plan(self) -> List[Dict[str, Any]]:
        """Returns the optimal purchase order allocation schedule."""
        with self._lock:
            df = self.data_loader.optimized_plan
            return df.to_dict(orient="records")

    def get_predictive_delays(self) -> Dict[str, Any]:
        """Returns pre-PO predictive delivery delay risk alerts."""
        with self._lock:
            df = self.data_loader.delay_alerts
            if df.empty and not self.data_loader.optimized_plan.empty:
                df = self.predictive_delay_engine.evaluate_allocations(self.data_loader.optimized_plan)
                
            high_risk_count = len(df[df["risk_tier"] == "RED"]) if not df.empty else 0
            mod_risk_count = len(df[df["risk_tier"] == "AMBER"]) if not df.empty else 0
            low_risk_count = len(df[df["risk_tier"] == "GREEN"]) if not df.empty else 0
            
            return {
                "alerts": df.to_dict(orient="records"),
                "summary": {
                    "total_orders_audited": len(df),
                    "high_risk_red_count": high_risk_count,
                    "moderate_risk_amber_count": mod_risk_count,
                    "low_risk_green_count": low_risk_count,
                    "high_risk_pct": round((high_risk_count / max(1, len(df))) * 100, 1)
                }
            }

    def get_spend_analytics_data(self) -> Dict[str, Any]:
        """Returns comprehensive spend analytics and breakdown charts."""
        with self._lock:
            if self._cached_spend_result is None:
                self.run_full_pipeline()
            return self._cached_spend_result

    def get_sourcing_cycle(self) -> Dict[str, Any]:
        """Returns 5-stage governance cycle state and audit ledger."""
        with self._lock:
            return self.workflow_manager.get_cycle_state()

    def get_activity_feed(self) -> List[Dict[str, Any]]:
        """Returns collaborative activity stream."""
        with self._lock:
            return copy.deepcopy(self.activity_log)

    def override_demand(self, material_id: str, plant_id: str, period_week: str, new_demand: int, user: str = "Plant Planner") -> Dict[str, Any]:
        """Overrides demand for a specific SKU/material and re-runs optimization."""
        with self._lock:
            df_dem = self.data_loader.demand
            mask = (
                (df_dem["material_id"] == material_id) &
                (df_dem["plant_id"] == plant_id) &
                (df_dem["period_week"] == period_week)
            )
            if not mask.any():
                return {"success": False, "message": f"Demand record for {material_id}/{plant_id}/{period_week} not found."}
                
            old_val = int(df_dem.loc[mask, "forecasted_demand_units"].values[0])
            df_dem.loc[mask, "forecasted_demand_units"] = new_demand
            self.data_loader.update_demand(df_dem)
            
            # Recalculate pipeline
            pipe_res = self.run_full_pipeline()
            
            self.log_activity(
                user=user,
                action="DEMAND_OVERRIDE",
                details=f"Adjusted demand for {material_id} at {plant_id} ({period_week}): {old_val:,} -> {new_demand:,} units."
            )
            
            return {
                "success": True,
                "message": f"Demand updated from {old_val} to {new_demand} units. Solver re-optimized schedule.",
                "pipeline": pipe_res
            }

    def execute_split_sourcing_contingency(self, user: str = "Sourcing Category Lead") -> Dict[str, Any]:
        """Applies split-sourcing contingency to rebalance high-risk allocations."""
        with self._lock:
            alloc_df = self.data_loader.optimized_plan
            res = self.predictive_delay_engine.get_split_sourcing_contingency(alloc_df)
            
            if res["shifts_count"] > 0:
                self.data_loader.save_optimized_plan(res["rebalanced_allocations_df"])
                self._cached_optimization_result["allocations_df"] = res["rebalanced_allocations_df"]
                self.predictive_delay_engine.evaluate_allocations(res["rebalanced_allocations_df"])
                self._cached_spend_result = self.spend_engine.analyze_spend(res["rebalanced_allocations_df"])
                
                self.log_activity(
                    user=user,
                    action="SPLIT_SOURCING_REBALANCE",
                    details=f"Executed split-sourcing rebalancing: transferred {res['shifted_volume_units']:,} units across {res['shifts_count']} high-risk orders to certified backup suppliers."
                )
                
            return res

    def run_scenario(self, payload: Dict[str, Any], user: str = "Sourcing Lead") -> Dict[str, Any]:
        """Executes a What-If scenario simulation."""
        with self._lock:
            scen_name = payload.get("scenario_name", "What-If Stress Test")
            cap_cuts = payload.get("supplier_capacity_cuts", {})
            demand_surge = float(payload.get("demand_surge_pct", 0.0))
            plants = payload.get("target_plants", None)
            lt_delay = int(payload.get("lead_time_delay_weeks", 0))
            max_ppm = payload.get("max_ppm_threshold", None)
            if max_ppm is not None:
                max_ppm = float(max_ppm)
                
            res = self.scenario_simulator.run_scenario(
                scenario_name=scen_name,
                supplier_capacity_cuts=cap_cuts,
                demand_surge_pct=demand_surge,
                target_plants=plants,
                lead_time_delay_weeks=lt_delay,
                max_ppm_threshold=max_ppm
            )
            
            self.log_activity(
                user=user,
                action="SCENARIO_SIMULATION",
                details=f"Ran scenario '{scen_name}': Cost Delta: {res['deltas']['cost_delta_pct']:+.1f}%, Service Level: {res['scenario']['service_level_pct']}%."
            )
            return res

    def record_decision(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Records a formal governance decision."""
        with self._lock:
            stage_id = payload.get("stage_id")
            decision_text = payload.get("decision_text")
            owner_role = payload.get("owner_role", "executive")
            approved_by = payload.get("approved_by", "Authorized Officer")
            fin_impact = float(payload.get("financial_impact", 0.0))
            risk_impact = float(payload.get("risk_impact", 0.0))
            
            res = self.workflow_manager.record_decision(
                stage_id=stage_id,
                decision_text=decision_text,
                owner_role=owner_role,
                approved_by=approved_by,
                financial_impact=fin_impact,
                risk_impact=risk_impact
            )
            
            self.log_activity(
                user=approved_by,
                action="GOVERNANCE_SIGN_OFF",
                details=f"Approved and signed off Stage: {stage_id}."
            )
            return res
