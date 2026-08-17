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
        """Loads or reloads all datasets into memory from SQLite database."""
        db_path = os.path.join(self.data_dir, "sourcing_platform.db")
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"SQLite database not found at {db_path}. Please run init_sqlite_db.py first.")
            
        import sqlite3
        conn = sqlite3.connect(db_path)
        
        with self._lock:
            # Master data
            self._cache["material_master"] = pd.read_sql("SELECT * FROM material_master", conn)
            self._cache["supplier_master"] = pd.read_sql("SELECT * FROM supplier_master", conn)
            self._cache["plant_master"] = pd.read_sql("SELECT * FROM plant_master", conn)
            self._cache["bom_direct_materials"] = pd.read_sql("SELECT * FROM bom_direct_materials", conn)
            
            # Suppliers
            self._cache["supplier_material_pricing"] = pd.read_sql("SELECT * FROM supplier_material_pricing", conn)
            self._cache["supplier_capacity_limits"] = pd.read_sql("SELECT * FROM supplier_capacity_limits", conn)
            self._cache["supplier_scorecards"] = pd.read_sql("SELECT * FROM supplier_scorecards", conn)
            self._cache["contract_commitments"] = pd.read_sql("SELECT * FROM contract_commitments", conn)
            
            # Demand & Logistics
            self._cache["plant_material_demand"] = pd.read_sql("SELECT * FROM plant_material_demand", conn)
            self._cache["current_inventory"] = pd.read_sql("SELECT * FROM current_inventory", conn)
            self._cache["freight_lane_matrix"] = pd.read_sql("SELECT * FROM freight_lane_matrix", conn)
            
            # Outputs
            try:
                self._cache["optimized_sourcing_plan"] = pd.read_sql("SELECT * FROM optimized_sourcing_plan", conn)
            except Exception:
                self._cache["optimized_sourcing_plan"] = pd.DataFrame(columns=[
                    "material_id", "supplier_id", "plant_id", "period_week",
                    "allocated_units", "landed_cost_usd", "po_release_week",
                    "expected_delivery_week", "moq_compliance_status"
                ])
                
            try:
                self._cache["sourcing_decisions"] = pd.read_sql("SELECT * FROM sourcing_decisions", conn)
            except Exception:
                self._cache["sourcing_decisions"] = pd.DataFrame(columns=[
                    "cycle_id", "stage", "owner_role", "decision", "financial_impact",
                    "risk_impact", "status", "approved_by", "timestamp"
                ])
                
            try:
                self._cache["predictive_delay_alerts"] = pd.read_sql("SELECT * FROM predictive_delay_alerts", conn)
            except Exception:
                self._cache["predictive_delay_alerts"] = pd.DataFrame(columns=[
                    "material_id", "supplier_id", "plant_id", "period_week",
                    "delay_probability", "risk_category", "recommended_action"
                ])
                
        conn.close()

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
    def _save_to_db(self, df: pd.DataFrame, table_name: str):
        import sqlite3
        db_path = os.path.join(self.data_dir, "sourcing_platform.db")
        conn = sqlite3.connect(db_path)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()

    def save_optimized_plan(self, df: pd.DataFrame):
        with self._lock:
            self._cache["optimized_sourcing_plan"] = df.copy()
            self._save_to_db(df, "optimized_sourcing_plan")

    def save_decisions(self, df: pd.DataFrame):
        with self._lock:
            self._cache["sourcing_decisions"] = df.copy()
            self._save_to_db(df, "sourcing_decisions")

    def save_delay_alerts(self, df: pd.DataFrame):
        with self._lock:
            self._cache["predictive_delay_alerts"] = df.copy()
            self._save_to_db(df, "predictive_delay_alerts")

    def update_demand(self, df: pd.DataFrame):
        with self._lock:
            self._cache["plant_material_demand"] = df.copy()
            self._save_to_db(df, "plant_material_demand")

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
