"""
Strategic Sourcing & Multi-Supplier Allocation Enterprise Platform
Synthetic Data Generation Script (Updated Industrial Specification)

Generates 13 relational, fully consistent CSV datasets across Master, Supplier,
Demand, Logistics, and Output layers matching the updated business flow spec.
"""

import os
import math
import random
import pandas as pd
import numpy as np

# Set deterministic random seed
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MASTER_DIR = os.path.join(DATA_DIR, "master")
SUPPLIER_DIR = os.path.join(DATA_DIR, "suppliers")
DEMAND_DIR = os.path.join(DATA_DIR, "demand")
LOGISTICS_DIR = os.path.join(DATA_DIR, "logistics")
OUTPUT_DIR = os.path.join(DATA_DIR, "outputs")

for d in [MASTER_DIR, SUPPLIER_DIR, DEMAND_DIR, LOGISTICS_DIR, OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

print(f"[DATA GENERATOR] Generating updated synthetic industrial datasets in {DATA_DIR}...")

# -------------------------------------------------------------------------
# 1. Master Data Layer
# -------------------------------------------------------------------------

# 1.1 Material Master (40 Materials across 8 Industrial Categories)
categories_config = {
    "Structural Steel": ("kg", 8.50, 24.00, [
        "High-Tensile Structural Steel I-Beam",
        "Cold-Rolled Carbon Steel Sheet 2mm",
        "Austenitic Stainless Steel 316L Plate",
        "Galvanized Structural Angle Steel",
        "Hardox 450 Wear-Resistant Steel"
    ]),
    "Aluminum Alloys": ("kg", 14.00, 48.00, [
        "Aerospace Grade 7075-T6 Billet",
        "Structural Aluminum 6061-T6 Extrusion",
        "Marine Grade 5083-H116 Plate",
        "Die-Cast Aluminum A380 Ingot",
        "Alloy 2024-T3 Precision Sheet"
    ]),
    "Polymers & Resins": ("kg", 6.00, 32.00, [
        "Engineered Polyamide PA66-GF30 Resin",
        "High-Density Polyethylene HDPE Copolymer",
        "Polycarbonate Optical-Grade Pellets",
        "Polyether Ether Ketone PEEK Polymer",
        "Thermoplastic Polyurethane TPU Elastomer"
    ]),
    "Electronic Subassemblies": ("units", 45.00, 380.00, [
        "Quad-Core Embedded Controller SoC",
        "Industrial Power Management Module",
        "Multi-Layer High-Frequency PCB Array",
        "Precision MEMS IMU Sensor Package",
        "Fiber-Optic Gigabit Transceiver Subassembly"
    ]),
    "Precision Bearings": ("units", 18.00, 145.00, [
        "Angular Contact Spindle Bearing 7008",
        "Double-Row Tapered Roller Bearing",
        "Deep-Groove Ceramic Hybrid Bearing",
        "Sealed Spherical Roller Bearing 22210",
        "High-Speed Miniature Precision Bearing"
    ]),
    "Hydraulics": ("units", 65.00, 450.00, [
        "Proportional Electro-Hydraulic Valve",
        "Double-Acting Heavy Cylinder 3000 PSI",
        "Variable Displacement Piston Pump Core",
        "Reinforced High-Pressure Flex Hose Assembly",
        "Servo-Controlled Hydraulic Actuator"
    ]),
    "High-Tensile Fasteners": ("units", 1.20, 18.50, [
        "Grade 12.9 Structural Flange Hex Bolt",
        "Aerospace Grade Titanium Locknut",
        "Stainless Steel A4-80 Socket Cap Screw",
        "Hardened Belleville Spring Washers",
        "Structural Monobolt Blind Rivet Pack"
    ]),
    "Industrial Composites": ("meters", 35.00, 220.00, [
        "Toray Carbon Fiber Prepreg 3K Twill",
        "Structural S-Glass Woven Roving Mat",
        "Nomex Honeycomb Structural Core 1/8",
        "Basalt Fiber High-Temp Insulation Roll",
        "High-Modulus Epoxy Resin Infusion Matrix"
    ])
}

materials_list = []
mat_idx = 1
for cat, (uom, min_cost, max_cost, names) in categories_config.items():
    for name in names:
        mat_id = f"MAT_{mat_idx:03d}"
        std_cost = round(random.uniform(min_cost, max_cost), 2)
        criticality = "HIGH" if cat in ["Electronic Subassemblies", "Hydraulics", "Industrial Composites"] and mat_idx % 2 == 0 else ("MEDIUM" if mat_idx % 3 != 0 else "LOW")
        materials_list.append({
            "material_id": mat_id,
            "material_name": name,
            "category": cat,
            "unit_of_measure": uom,
            "standard_cost_usd": std_cost,
            "criticality": criticality
        })
        mat_idx += 1

df_material_master = pd.DataFrame(materials_list)
df_material_master.to_csv(os.path.join(MASTER_DIR, "material_master.csv"), index=False)
print(f"  [OK] Created material_master.csv ({len(df_material_master)} rows)")

# 1.2 Supplier Master (12 Global Industrial Suppliers)
suppliers_data = [
    {"supplier_id": "SUP_001", "supplier_name": "Apex Precision Metals GmbH", "country": "Germany", "tier": "Tier-1", "base_financial_risk_score": 1.2, "iso_certified": True},
    {"supplier_id": "SUP_002", "supplier_name": "Vanguard Industrial Dynamics", "country": "USA", "tier": "Tier-1", "base_financial_risk_score": 1.4, "iso_certified": True},
    {"supplier_id": "SUP_003", "supplier_name": "Nippon Advanced Metallurgy", "country": "Japan", "tier": "Tier-1", "base_financial_risk_score": 1.1, "iso_certified": True},
    {"supplier_id": "SUP_004", "supplier_name": "Hansol High-Tech Components", "country": "South Korea", "tier": "Tier-1", "base_financial_risk_score": 1.8, "iso_certified": True},
    {"supplier_id": "SUP_005", "supplier_name": "MexSteel & Polymer Fabrica", "country": "Mexico", "tier": "Tier-2", "base_financial_risk_score": 2.6, "iso_certified": True},
    {"supplier_id": "SUP_006", "supplier_name": "Saigon Composite Solutions", "country": "Vietnam", "tier": "Tier-2", "base_financial_risk_score": 3.1, "iso_certified": False},
    {"supplier_id": "SUP_007", "supplier_name": "Bharat Precision Engineering", "country": "India", "tier": "Tier-2", "base_financial_risk_score": 2.4, "iso_certified": True},
    {"supplier_id": "SUP_008", "supplier_name": "Taiwan Micro-Silicon Ltd", "country": "Taiwan", "tier": "Tier-1", "base_financial_risk_score": 1.5, "iso_certified": True},
    {"supplier_id": "SUP_009", "supplier_name": "EuroHydraulics SpA", "country": "Germany", "tier": "Tier-1", "base_financial_risk_score": 1.9, "iso_certified": True},
    {"supplier_id": "SUP_010", "supplier_name": "Detroit Fastener Alliance", "country": "USA", "tier": "Tier-2", "base_financial_risk_score": 2.2, "iso_certified": True},
    {"supplier_id": "SUP_011", "supplier_name": "Shinshu Bearing & Motion Systems", "country": "Japan", "tier": "Tier-1", "base_financial_risk_score": 1.3, "iso_certified": True},
    {"supplier_id": "SUP_012", "supplier_name": "Monterrey Die & Mold S.A.", "country": "Mexico", "tier": "Tier-2", "base_financial_risk_score": 3.4, "iso_certified": False}
]
df_supplier_master = pd.DataFrame(suppliers_data)
df_supplier_master.to_csv(os.path.join(MASTER_DIR, "supplier_master.csv"), index=False)
print(f"  [OK] Created supplier_master.csv ({len(df_supplier_master)} rows)")

# 1.3 Plant Master (5 Assembly Plants)
plants_data = [
    {"plant_id": "PLANT_01", "plant_name": "Detroit Advanced Assembly Hub", "location": "Detroit", "weekly_assembly_capacity_units": 15000},
    {"plant_id": "PLANT_02", "plant_name": "Munich Engineering Works", "location": "Munich", "weekly_assembly_capacity_units": 12000},
    {"plant_id": "PLANT_03", "plant_name": "Monterrey Global Production Hub", "location": "Monterrey", "weekly_assembly_capacity_units": 20000},
    {"plant_id": "PLANT_04", "plant_name": "Tokyo Precision Facility", "location": "Tokyo", "weekly_assembly_capacity_units": 10000},
    {"plant_id": "PLANT_05", "plant_name": "Chennai Industrial Complex", "location": "Chennai", "weekly_assembly_capacity_units": 18000}
]
df_plant_master = pd.DataFrame(plants_data)
df_plant_master.to_csv(os.path.join(MASTER_DIR, "plant_master.csv"), index=False)
print(f"  [OK] Created plant_master.csv ({len(df_plant_master)} rows)")

# 1.4 BOM Direct Materials (30 SKUs x 4 Materials on average = 120 BOM mappings)
bom_records = []
for sku_idx in range(1, 31):
    sku_id = f"SKU_{sku_idx:03d}"
    selected_mats = [
        f"MAT_{( (sku_idx * 3 + offset) % 40 ) + 1:03d}"
        for offset in range(4)
    ]
    for mat_id in selected_mats:
        usage = round(random.uniform(1.2, 8.5), 2)
        scrap = round(random.uniform(0.02, 0.08), 3)
        bom_records.append({
            "sku_id": sku_id,
            "material_id": mat_id,
            "usage_qty_per_unit": usage,
            "scrap_allowance_pct": scrap
        })

df_bom = pd.DataFrame(bom_records)
df_bom.to_csv(os.path.join(MASTER_DIR, "bom_direct_materials.csv"), index=False)
print(f"  [OK] Created bom_direct_materials.csv ({len(df_bom)} rows)")


# -------------------------------------------------------------------------
# 2. Sourcing Terms & Performance Layer (Certified Compatibility Matrix)
# -------------------------------------------------------------------------

# Supplier Certified Capability Matrix (Exactly 3-4 approved suppliers per category, 8-12 materials per supplier)
supplier_specialization = {
    "Structural Steel": ["SUP_001", "SUP_002", "SUP_005", "SUP_007"],
    "Aluminum Alloys": ["SUP_001", "SUP_003", "SUP_005", "SUP_012"],
    "Polymers & Resins": ["SUP_002", "SUP_004", "SUP_005", "SUP_006"],
    "Electronic Subassemblies": ["SUP_003", "SUP_004", "SUP_008"],
    "Precision Bearings": ["SUP_003", "SUP_011", "SUP_004"],
    "Hydraulics": ["SUP_001", "SUP_009", "SUP_007"],
    "High-Tensile Fasteners": ["SUP_002", "SUP_007", "SUP_010"],
    "Industrial Composites": ["SUP_003", "SUP_006", "SUP_008"]
}

pricing_records = []
contract_records = []

for _, mat in df_material_master.iterrows():
    mat_id = mat["material_id"]
    category = mat["category"]
    std_cost = mat["standard_cost_usd"]
    approved_sups = supplier_specialization.get(category, ["SUP_001", "SUP_002", "SUP_003"])
    
    for s_idx, sup_id in enumerate(approved_sups):
        price_factor = 1.0 + (s_idx * 0.04) - 0.04 + random.uniform(-0.03, 0.03)
        unit_price = round(std_cost * price_factor, 2)
        moq = random.choice([250, 500, 750, 1000, 1200])
        lead_time = random.choice([2, 3, 4, 5, 6])
        
        pricing_records.append({
            "supplier_id": sup_id,
            "material_id": mat_id,
            "unit_price_usd": unit_price,
            "moq_units": moq,
            "standard_lead_time_weeks": lead_time
        })
        
        min_share = round(random.uniform(0.10, 0.20), 2)
        max_share = round(random.uniform(0.55, 0.70), 2)
        contract_records.append({
            "supplier_id": sup_id,
            "material_id": mat_id,
            "min_guaranteed_share_pct": min_share,
            "max_allocation_cap_pct": max_share
        })

df_pricing = pd.DataFrame(pricing_records)
df_pricing.to_csv(os.path.join(SUPPLIER_DIR, "supplier_material_pricing.csv"), index=False)
print(f"  [OK] Created supplier_material_pricing.csv ({len(df_pricing)} rows)")

df_contracts = pd.DataFrame(contract_records)
df_contracts.to_csv(os.path.join(SUPPLIER_DIR, "contract_commitments.csv"), index=False)
print(f"  [OK] Created contract_commitments.csv ({len(df_contracts)} rows)")

# 2.3 Supplier Weekly Capacity Limits (1,440 rows for 12 weeks)
capacity_records = []
weeks = [f"W{w:02d}" for w in range(1, 13)]

for _, pr in df_pricing.iterrows():
    sup_id = pr["supplier_id"]
    mat_id = pr["material_id"]
    base_cap = random.randint(5000, 14000)
    for w in weeks:
        cap_val = int(base_cap * random.uniform(0.92, 1.08))
        capacity_records.append({
            "supplier_id": sup_id,
            "material_id": mat_id,
            "period_week": w,
            "max_weekly_capacity_units": cap_val
        })

df_capacity = pd.DataFrame(capacity_records)
df_capacity.to_csv(os.path.join(SUPPLIER_DIR, "supplier_capacity_limits.csv"), index=False)
print(f"  [OK] Created supplier_capacity_limits.csv ({len(df_capacity)} rows)")

# 2.4 Supplier Scorecards (12 Suppliers)
scorecards = [
    {"supplier_id": "SUP_001", "historical_otd_pct": 97.5, "defect_ppm": 65,  "quality_audit_score": 96, "lead_time_variance_days": 0.8, "reliability_rating": "EXCELLENT"},
    {"supplier_id": "SUP_002", "historical_otd_pct": 95.0, "defect_ppm": 120, "quality_audit_score": 92, "lead_time_variance_days": 1.4, "reliability_rating": "EXCELLENT"},
    {"supplier_id": "SUP_003", "historical_otd_pct": 98.2, "defect_ppm": 45,  "quality_audit_score": 98, "lead_time_variance_days": 0.6, "reliability_rating": "EXCELLENT"},
    {"supplier_id": "SUP_004", "historical_otd_pct": 94.2, "defect_ppm": 160, "quality_audit_score": 89, "lead_time_variance_days": 1.8, "reliability_rating": "GOOD"},
    {"supplier_id": "SUP_005", "historical_otd_pct": 89.5, "defect_ppm": 340, "quality_audit_score": 79, "lead_time_variance_days": 3.2, "reliability_rating": "MARGINAL"},
    {"supplier_id": "SUP_006", "historical_otd_pct": 81.0, "defect_ppm": 720, "quality_audit_score": 68, "lead_time_variance_days": 5.8, "reliability_rating": "HIGH_RISK"},
    {"supplier_id": "SUP_007", "historical_otd_pct": 91.0, "defect_ppm": 240, "quality_audit_score": 83, "lead_time_variance_days": 2.5, "reliability_rating": "GOOD"},
    {"supplier_id": "SUP_008", "historical_otd_pct": 96.8, "defect_ppm": 85,  "quality_audit_score": 95, "lead_time_variance_days": 1.1, "reliability_rating": "EXCELLENT"},
    {"supplier_id": "SUP_009", "historical_otd_pct": 93.5, "defect_ppm": 190, "quality_audit_score": 87, "lead_time_variance_days": 2.1, "reliability_rating": "GOOD"},
    {"supplier_id": "SUP_010", "historical_otd_pct": 92.0, "defect_ppm": 210, "quality_audit_score": 85, "lead_time_variance_days": 2.3, "reliability_rating": "GOOD"},
    {"supplier_id": "SUP_011", "historical_otd_pct": 97.0, "defect_ppm": 75,  "quality_audit_score": 94, "lead_time_variance_days": 0.9, "reliability_rating": "EXCELLENT"},
    {"supplier_id": "SUP_012", "historical_otd_pct": 79.5, "defect_ppm": 820, "quality_audit_score": 62, "lead_time_variance_days": 6.1, "reliability_rating": "HIGH_RISK"}
]
df_scorecards = pd.DataFrame(scorecards)
df_scorecards.to_csv(os.path.join(SUPPLIER_DIR, "supplier_scorecards.csv"), index=False)
print(f"  [OK] Created supplier_scorecards.csv ({len(df_scorecards)} rows)")


# -------------------------------------------------------------------------
# 3. Demand & Logistics Layer
# -------------------------------------------------------------------------

# 3.1 Plant Material Demand (40 Materials x 5 Plants x 12 Weeks = 2,400 rows)
demand_records = []
for mat in df_material_master["material_id"]:
    for plant in df_plant_master["plant_id"]:
        base_demand = random.randint(600, 2400)
        for w_idx, w in enumerate(weeks):
            trend = 1.0 + (w_idx * 0.012) + random.uniform(-0.08, 0.08)
            demand_val = int(base_demand * trend)
            demand_records.append({
                "material_id": mat,
                "plant_id": plant,
                "period_week": w,
                "forecasted_demand_units": demand_val
            })

df_demand = pd.DataFrame(demand_records)
df_demand.to_csv(os.path.join(DEMAND_DIR, "plant_material_demand.csv"), index=False)
print(f"  [OK] Created plant_material_demand.csv ({len(df_demand)} rows)")

# 3.2 Current Inventory & Safety Stock (40 Materials x 5 Plants = 200 rows)
inventory_records = []
for mat in df_material_master["material_id"]:
    for plant in df_plant_master["plant_id"]:
        safety_stock = random.randint(300, 1000)
        on_hand = int(safety_stock * random.uniform(0.70, 1.30))
        inventory_records.append({
            "material_id": mat,
            "plant_id": plant,
            "available_on_hand_units": on_hand,
            "safety_stock_threshold_units": safety_stock
        })

df_inventory = pd.DataFrame(inventory_records)
df_inventory.to_csv(os.path.join(DEMAND_DIR, "current_inventory.csv"), index=False)
print(f"  [OK] Created current_inventory.csv ({len(df_inventory)} rows)")

# 3.3 Freight Lane Matrix (12 Suppliers x 5 Plants = 60 rows)
freight_matrix = {
    ("Germany", "Munich"): (2, 0.45, 99.0),
    ("Germany", "Detroit"): (14, 3.40, 94.0),
    ("Germany", "Monterrey"): (18, 4.80, 91.0),
    ("Germany", "Tokyo"): (24, 7.60, 89.0),
    ("Germany", "Chennai"): (20, 5.10, 90.0),

    ("USA", "Detroit"): (2, 0.50, 98.5),
    ("USA", "Munich"): (15, 3.50, 93.5),
    ("USA", "Monterrey"): (5, 1.60, 96.0),
    ("USA", "Tokyo"): (22, 6.20, 91.0),
    ("USA", "Chennai"): (24, 6.40, 89.5),

    ("Japan", "Tokyo"): (1, 0.45, 99.5),
    ("Japan", "Detroit"): (21, 5.10, 92.5),
    ("Japan", "Munich"): (24, 6.50, 90.0),
    ("Japan", "Monterrey"): (22, 5.30, 91.0),
    ("Japan", "Chennai"): (16, 3.60, 93.0),

    ("South Korea", "Tokyo"): (3, 0.85, 98.0),
    ("South Korea", "Detroit"): (22, 5.15, 92.0),
    ("South Korea", "Munich"): (24, 6.55, 89.5),
    ("South Korea", "Monterrey"): (23, 5.35, 90.5),
    ("South Korea", "Chennai"): (15, 3.55, 93.5),

    ("Mexico", "Monterrey"): (1, 0.45, 98.0),
    ("Mexico", "Detroit"): (6, 1.70, 95.0),
    ("Mexico", "Munich"): (19, 4.90, 90.0),
    ("Mexico", "Tokyo"): (24, 6.45, 89.0),
    ("Mexico", "Chennai"): (24, 7.65, 88.0),

    ("Vietnam", "Tokyo"): (8, 1.85, 92.0),
    ("Vietnam", "Detroit"): (24, 6.50, 87.0),
    ("Vietnam", "Munich"): (24, 7.70, 86.0),
    ("Vietnam", "Monterrey"): (24, 6.60, 86.5),
    ("Vietnam", "Chennai"): (9, 2.10, 93.0),

    ("India", "Chennai"): (1, 0.45, 98.5),
    ("India", "Detroit"): (24, 6.55, 88.0),
    ("India", "Munich"): (21, 5.05, 91.0),
    ("India", "Monterrey"): (24, 6.75, 87.0),
    ("India", "Tokyo"): (16, 3.65, 92.5),

    ("Taiwan", "Tokyo"): (4, 0.90, 98.0),
    ("Taiwan", "Detroit"): (22, 5.20, 91.5),
    ("Taiwan", "Munich"): (24, 6.50, 89.5),
    ("Taiwan", "Monterrey"): (23, 5.40, 90.0),
    ("Taiwan", "Chennai"): (14, 3.45, 93.0)
}

freight_records = []
for _, sup in df_supplier_master.iterrows():
    s_id = sup["supplier_id"]
    s_country = sup["country"]
    for _, plt in df_plant_master.iterrows():
        p_id = plt["plant_id"]
        p_loc = plt["location"]
        
        lookup_key = (s_country, p_loc)
        if lookup_key in freight_matrix:
            transit, cost, rel = freight_matrix[lookup_key]
        else:
            transit = 20
            cost = 5.00
            rel = 90.0
            
        freight_records.append({
            "supplier_id": s_id,
            "plant_id": p_id,
            "transit_time_days": transit,
            "freight_cost_per_unit_usd": cost,
            "lane_reliability_pct": rel
        })

df_freight = pd.DataFrame(freight_records)
df_freight.to_csv(os.path.join(LOGISTICS_DIR, "freight_lane_matrix.csv"), index=False)
print(f"  [OK] Created freight_lane_matrix.csv ({len(df_freight)} rows)")


# -------------------------------------------------------------------------
# 4. Initial Outputs & Decision Ledger Seeds
# -------------------------------------------------------------------------

initial_decisions = [
    {
        "cycle_id": "CYC-2026-Q3",
        "stage": "STAGE_1_DEMAND_AGGREGATION",
        "owner_role": "plant_buyer",
        "decision": "Global 12-Week Plant Demand Master Schedule aggregated and locked across 5 assembly hubs.",
        "financial_impact": 0.0,
        "risk_impact": 0.0,
        "status": "APPROVED",
        "approved_by": "David Miller (Plant Buyer Lead)",
        "timestamp": "2026-08-01 09:30:00"
    },
    {
        "cycle_id": "CYC-2026-Q3",
        "stage": "STAGE_2_SUPPLIER_SCORECARD",
        "owner_role": "quality_lead",
        "decision": "Supplier OTD telemetry and PPM defect audits completed. 10 approved vendors certified, 2 marked High Risk.",
        "financial_impact": 0.0,
        "risk_impact": -14.2,
        "status": "APPROVED",
        "approved_by": "Dr. Aris Thorne (Quality Assurance Lead)",
        "timestamp": "2026-08-03 14:15:00"
    },
    {
        "cycle_id": "CYC-2026-Q3",
        "stage": "STAGE_3_MILP_OPTIMIZATION",
        "owner_role": "sourcing_lead",
        "decision": "PuLP MILP Sourcing Solver executed with dual-sourcing bounds (15% min / 60% max cap) and MOQ adherence.",
        "financial_impact": -482350.00,
        "risk_impact": -22.5,
        "status": "APPROVED",
        "approved_by": "Marcus Vance (Category Sourcing Lead)",
        "timestamp": "2026-08-05 11:00:00"
    },
    {
        "cycle_id": "CYC-2026-Q3",
        "stage": "STAGE_4_PREDICTIVE_DELAY_REVIEW",
        "owner_role": "sourcing_lead",
        "decision": "Pre-PO predictive transit delay audit completed. High-risk maritime lanes rebalanced with nearshore suppliers.",
        "financial_impact": 18200.00,
        "risk_impact": -35.8,
        "status": "APPROVED",
        "approved_by": "Marcus Vance (Category Sourcing Lead)",
        "timestamp": "2026-08-07 16:45:00"
    },
    {
        "cycle_id": "CYC-2026-Q3",
        "stage": "STAGE_5_EXECUTIVE_AWARD",
        "owner_role": "executive",
        "decision": "Executive Sourcing Committee final award ratified. $4.85M quarterly PO releases approved for SAP ERP dispatch.",
        "financial_impact": -512000.00,
        "risk_impact": -28.0,
        "status": "PENDING_FINAL_SIGN_OFF",
        "approved_by": "Robert Sterling (Chief Procurement Officer)",
        "timestamp": "2026-08-10 10:00:00"
    }
]

df_decisions = pd.DataFrame(initial_decisions)
df_decisions.to_csv(os.path.join(OUTPUT_DIR, "sourcing_decisions.csv"), index=False)
print(f"  [OK] Created sourcing_decisions.csv ({len(df_decisions)} rows)")

print("\n[DATA GENERATOR] All 13 updated relational datasets successfully generated in data/!")
