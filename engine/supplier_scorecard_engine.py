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
            "w_otd": 0.35,
            "w_qual": 0.30,
            "w_var": 0.20,
            "w_geo": 0.15
        }

    def compute_scorecards(self) -> pd.DataFrame:
        """
        Calculates composite risk score R_s and normalized performance ratings:
        S_OTD = Historical OTD %
        S_Qual = max(0, 100 - PPM / 50)
        R_s = w1*(100 - S_OTD) + w2*(100 - S_Qual) + w3*(VarianceDays * 5) + w4*(FinancialRisk * 20)
        """
        df_sups = self.loader.supplier_master
        df_scores = self.loader.scorecards
        
        merged = df_sups.merge(df_scores, on="supplier_id", how="left")
        
        w1 = self.weights["w_otd"]
        w2 = self.weights["w_qual"]
        w3 = self.weights["w_var"]
        w4 = self.weights["w_geo"]
        
        results = []
        for _, row in merged.iterrows():
            otd = float(row["historical_otd_pct"])
            ppm = float(row["defect_ppm"])
            var_days = float(row["lead_time_variance_days"])
            fin_risk = float(row["base_financial_risk_score"])
            
            s_otd = otd
            s_qual = max(0.0, 100.0 - (ppm / 50.0))
            
            # Composite risk index (0 to 100 scale, lower is better)
            risk_index = (
                w1 * (100.0 - s_otd) +
                w2 * (100.0 - s_qual) +
                w3 * min(100.0, var_days * 5.0 * 2.0) +
                w4 * min(100.0, fin_risk * 20.0)
            )
            risk_index = round(max(0.0, min(100.0, risk_index)), 2)
            
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
                
            # Eligibility check
            eligible = (otd >= 80.0) and (ppm <= 850) and (row["iso_certified"] or fin_risk <= 3.2)
            
            results.append({
                "supplier_id": row["supplier_id"],
                "supplier_name": row["supplier_name"],
                "country": row["country"],
                "tier": row["tier"],
                "iso_certified": bool(row["iso_certified"]),
                "historical_otd_pct": otd,
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
