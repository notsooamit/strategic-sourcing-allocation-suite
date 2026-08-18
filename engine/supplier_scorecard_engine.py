"""
Supplier Performance & Risk Scorecard Engine

Computes multi-dimensional supplier reliability indices balancing On-Time Delivery (OTD),
quality defect PPM, lead-time variance, and geopolitical/financial risk.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from .data_loader import DataLoader

class ScorecardEngine:
    """Evaluates supplier scorecards, quality PPM, delivery reliability, and composite risk."""
    
    def __init__(self, data_loader: DataLoader, weights: Dict[str, float] = None):
        self.loader = data_loader
        self.weights = weights or {
            "w_otd": 0.40,
            "w_var": 0.35,
            "w_geo": 0.25
        }

    def compute_scorecards(self) -> pd.DataFrame:
        """
        Calculates composite risk score R_s and normalized performance ratings:
        S_Qual = 0.50 * (1 - DefectPPM / 1,000,000) + 0.50 * (AuditScore / 100)
        R_s = 0.40*(1 - OTD) + 0.35*(VarianceDays/7) + 0.25*(FinancialRisk/5)
        """
        df_sups = self.loader.supplier_master
        df_scores = self.loader.scorecards
        
        merged = df_sups.merge(df_scores, on="supplier_id", how="left")
        
        w_otd = self.weights["w_otd"]
        w_var = self.weights["w_var"]
        w_geo = self.weights["w_geo"]
        
        results = []
        for _, row in merged.iterrows():
            otd_pct = float(row["historical_otd_pct"])
            ppm = float(row["defect_ppm"])
            audit = float(row["quality_audit_score"])
            var_days = float(row["lead_time_variance_days"])
            fin_risk = float(row["base_financial_risk_score"])
            
            # S_Qual formulation from docs
            s_qual = 0.50 * (1.0 - (ppm / 1000000.0)) + 0.50 * (audit / 100.0)
            
            # Composite risk index from docs (scaled to 100 for continuity)
            risk_raw = (
                w_otd * (1.0 - (otd_pct / 100.0)) +
                w_var * (var_days / 7.0) +
                w_geo * (fin_risk / 5.0)
            )
            # risk_raw is typically 0 to 1, we multiply by 100 to get a 0-100 scale for UI
            risk_index = round(max(0.0, min(100.0, risk_raw * 100.0)), 2)
            
            # Tier classification
            if risk_index < 15.0:
                tier_rating = "EXCELLENT"
                risk_badge = "LOW"
            elif risk_index < 25.0:
                tier_rating = "GOOD"
                risk_badge = "MODERATE"
            elif risk_index < 40.0:
                tier_rating = "MARGINAL"
                risk_badge = "ELEVATED"
            else:
                tier_rating = "HIGH_RISK"
                risk_badge = "CRITICAL"
                
            # Eligibility check (Aligned with optimizer rules)
            # Note: PPM is intentionally excluded here so the MILP can handle it as a weighted portfolio constraint.
            eligible = (otd_pct >= 80.0) and (int(row["quality_audit_score"]) >= 85)
            
            results.append({
                "supplier_id": row["supplier_id"],
                "supplier_name": row["supplier_name"],
                "country": row["country"],
                "tier": row["tier"],
                "iso_certified": bool(row["iso_certified"]),
                "historical_otd_pct": otd_pct,
                "defect_ppm": int(ppm),
                "quality_score": round(s_qual, 1),
                "quality_audit_score": int(row["quality_audit_score"]),
                "lead_time_variance_days": var_days,
                "base_financial_risk_score": fin_risk,
                "composite_risk_index": risk_index,
                "reliability_rating": tier_rating,
                "risk_badge": risk_badge,
                "is_eligible": bool(eligible)
            })
            
        df_res = pd.DataFrame(results).sort_values(by="composite_risk_index").reset_index(drop=True)
        return df_res

    def get_scorecard_dict(self) -> Dict[str, Dict[str, Any]]:
        """Returns a dictionary keyed by supplier_id for fast lookup in solver."""
        df = self.compute_scorecards()
        return df.set_index("supplier_id").to_dict(orient="index")
