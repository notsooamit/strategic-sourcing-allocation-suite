"""
SQLite Database Migration Script

Reads all existing CSV flat files and migrates them into a unified SQLite database.
"""

import os
import sqlite3
import pandas as pd

def migrate_to_sqlite():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    
    db_path = os.path.join(data_dir, "sourcing_platform.db")
    
    print(f"Creating SQLite database at: {db_path}")
    conn = sqlite3.connect(db_path)
    
    # Mapping of table names to their CSV file paths
    csv_files = {
        "material_master": os.path.join(data_dir, "master", "material_master.csv"),
        "supplier_master": os.path.join(data_dir, "master", "supplier_master.csv"),
        "plant_master": os.path.join(data_dir, "master", "plant_master.csv"),
        "bom_direct_materials": os.path.join(data_dir, "master", "bom_direct_materials.csv"),
        
        "supplier_material_pricing": os.path.join(data_dir, "suppliers", "supplier_material_pricing.csv"),
        "supplier_capacity_limits": os.path.join(data_dir, "suppliers", "supplier_capacity_limits.csv"),
        "supplier_scorecards": os.path.join(data_dir, "suppliers", "supplier_scorecards.csv"),
        "contract_commitments": os.path.join(data_dir, "suppliers", "contract_commitments.csv"),
        
        "plant_material_demand": os.path.join(data_dir, "demand", "plant_material_demand.csv"),
        "current_inventory": os.path.join(data_dir, "demand", "current_inventory.csv"),
        
        "freight_lane_matrix": os.path.join(data_dir, "logistics", "freight_lane_matrix.csv"),
        
        "optimized_sourcing_plan": os.path.join(data_dir, "outputs", "optimized_sourcing_plan.csv"),
        "sourcing_decisions": os.path.join(data_dir, "outputs", "sourcing_decisions.csv"),
        "predictive_delay_alerts": os.path.join(data_dir, "outputs", "predictive_delay_alerts.csv")
    }
    
    for table_name, csv_path in csv_files.items():
        if os.path.exists(csv_path):
            print(f"Migrating {table_name}...")
            df = pd.read_csv(csv_path)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
        else:
            print(f"Warning: CSV file not found for {table_name}: {csv_path}")
            
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate_to_sqlite()
