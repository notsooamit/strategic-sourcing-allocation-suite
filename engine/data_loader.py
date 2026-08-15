"""
Data Loader & Relational Caching Engine

Manages in-memory caching of all 13 CSV tables, integrity validation,
and persistence.
"""

import os
import threading
import pandas as pd
from typing import Dict, Optional, Any

class DataLoader:
    """Thread-safe data loader and cache manager for the Sourcing Platform."""
    
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.data_dir = os.path.join(base_dir, "data")
        else:
            self.data_dir = data_dir
            
        self.master_dir = os.path.join(self.data_dir, "master")
        self.supplier_dir = os.path.join(self.data_dir, "suppliers")
        self.demand_dir = os.path.join(self.data_dir, "demand")
        self.logistics_dir = os.path.join(self.data_dir, "logistics")
        self.output_dir = os.path.join(self.data_dir, "outputs")
        
        self._lock = threading.RLock()
        self._cache: Dict[str, pd.DataFrame] = {}
        self.reload_all()

    def reload_all(self):
        """Loads or reloads all CSV datasets into memory."""
        with self._lock:
            # Master data
            self._cache["material_master"] = pd.read_csv(os.path.join(self.master_dir, "material_master.csv"))
            self._cache["supplier_master"] = pd.read_csv(os.path.join(self.master_dir, "supplier_master.csv"))
            self._cache["plant_master"] = pd.read_csv(os.path.join(self.master_dir, "plant_master.csv"))
            self._cache["bom_direct_materials"] = pd.read_csv(os.path.join(self.master_dir, "bom_direct_materials.csv"))
            
            # Suppliers
            self._cache["supplier_material_pricing"] = pd.read_csv(os.path.join(self.supplier_dir, "supplier_material_pricing.csv"))
            self._cache["supplier_capacity_limits"] = pd.read_csv(os.path.join(self.supplier_dir, "supplier_capacity_limits.csv"))
            self._cache["supplier_scorecards"] = pd.read_csv(os.path.join(self.supplier_dir, "supplier_scorecards.csv"))
            self._cache["contract_commitments"] = pd.read_csv(os.path.join(self.supplier_dir, "contract_commitments.csv"))
            
            # Demand & Logistics
            self._cache["plant_material_demand"] = pd.read_csv(os.path.join(self.demand_dir, "plant_material_demand.csv"))
            self._cache["current_inventory"] = pd.read_csv(os.path.join(self.demand_dir, "current_inventory.csv"))
            self._cache["freight_lane_matrix"] = pd.read_csv(os.path.join(self.logistics_dir, "freight_lane_matrix.csv"))
            
            # Outputs
            opt_path = os.path.join(self.output_dir, "optimized_sourcing_plan.csv")
            if os.path.exists(opt_path):
                self._cache["optimized_sourcing_plan"] = pd.read_csv(opt_path)
            else:
                self._cache["optimized_sourcing_plan"] = pd.DataFrame(columns=[
                    "material_id", "supplier_id", "plant_id", "period_week",
                    "allocated_units", "landed_cost_usd", "po_release_week",
                    "expected_delivery_week", "moq_compliance_status"
                ])
                
            dec_path = os.path.join(self.output_dir, "sourcing_decisions.csv")
            if os.path.exists(dec_path):
                self._cache["sourcing_decisions"] = pd.read_csv(dec_path)
            else:
                self._cache["sourcing_decisions"] = pd.DataFrame(columns=[
                    "cycle_id", "stage", "owner_role", "decision", "financial_impact",
                    "risk_impact", "status", "approved_by", "timestamp"
                ])
                
            delay_path = os.path.join(self.output_dir, "predictive_delay_alerts.csv")
            if os.path.exists(delay_path):
                self._cache["predictive_delay_alerts"] = pd.read_csv(delay_path)
            else:
                self._cache["predictive_delay_alerts"] = pd.DataFrame(columns=[
                    "material_id", "supplier_id", "plant_id", "period_week",
                    "delay_probability", "risk_category", "recommended_action"
                ])

    # Accessor properties
    @property
    def material_master(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["material_master"].copy()

    @property
    def supplier_master(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["supplier_master"].copy()

    @property
    def plant_master(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["plant_master"].copy()

    @property
    def bom(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["bom_direct_materials"].copy()

    @property
    def pricing(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["supplier_material_pricing"].copy()

    @property
    def capacity(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["supplier_capacity_limits"].copy()

    @property
    def scorecards(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["supplier_scorecards"].copy()

    @property
    def contracts(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["contract_commitments"].copy()

    @property
    def demand(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["plant_material_demand"].copy()

    @property
    def inventory(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["current_inventory"].copy()

    @property
    def freight(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["freight_lane_matrix"].copy()

    @property
    def optimized_plan(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["optimized_sourcing_plan"].copy()

    @property
    def decisions(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["sourcing_decisions"].copy()

    @property
    def delay_alerts(self) -> pd.DataFrame:
        with self._lock:
            return self._cache["predictive_delay_alerts"].copy()

    # Mutation and Persistence
    def save_optimized_plan(self, df: pd.DataFrame):
        with self._lock:
            self._cache["optimized_sourcing_plan"] = df.copy()
            df.to_csv(os.path.join(self.output_dir, "optimized_sourcing_plan.csv"), index=False)

    def save_decisions(self, df: pd.DataFrame):
        with self._lock:
            self._cache["sourcing_decisions"] = df.copy()
            df.to_csv(os.path.join(self.output_dir, "sourcing_decisions.csv"), index=False)

    def save_delay_alerts(self, df: pd.DataFrame):
        with self._lock:
            self._cache["predictive_delay_alerts"] = df.copy()
            df.to_csv(os.path.join(self.output_dir, "predictive_delay_alerts.csv"), index=False)

    def update_demand(self, df: pd.DataFrame):
        with self._lock:
            self._cache["plant_material_demand"] = df.copy()
            df.to_csv(os.path.join(self.demand_dir, "plant_material_demand.csv"), index=False)

    def validate_integrity(self) -> Dict[str, Any]:
        """Validates referential integrity between all relational tables."""
        with self._lock:
            mats = set(self._cache["material_master"]["material_id"])
            sups = set(self._cache["supplier_master"]["supplier_id"])
            plants = set(self._cache["plant_master"]["plant_id"])
            
            pricing_mats = set(self._cache["supplier_material_pricing"]["material_id"])
            pricing_sups = set(self._cache["supplier_material_pricing"]["supplier_id"])
            demand_mats = set(self._cache["plant_material_demand"]["material_id"])
            demand_plants = set(self._cache["plant_material_demand"]["plant_id"])
            
            errors = []
            if not pricing_mats.issubset(mats):
                errors.append(f"Pricing has unknown materials: {pricing_mats - mats}")
            if not pricing_sups.issubset(sups):
                errors.append(f"Pricing has unknown suppliers: {pricing_sups - sups}")
            if not demand_mats.issubset(mats):
                errors.append(f"Demand has unknown materials: {demand_mats - mats}")
            if not demand_plants.issubset(plants):
                errors.append(f"Demand has unknown plants: {demand_plants - plants}")
                
            return {
                "valid": len(errors) == 0,
                "material_count": len(mats),
                "supplier_count": len(sups),
                "plant_count": len(plants),
                "errors": errors
            }
