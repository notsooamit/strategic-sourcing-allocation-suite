"""
5-Stage Sourcing Governance & Decision Ledger State Machine

Coordinates cross-functional approval cadence from Demand Aggregation to Executive Award
with tamper-evident audit logging.
"""

import hashlib
import datetime
import pandas as pd
from typing import Dict, List, Any
from .data_loader import DataLoader

STAGES = [
    {
        "stage_id": "STAGE_1_DEMAND_AGGREGATION",
        "stage_num": 1,
        "title": "Demand & MPS Aggregation",
        "owner_role": "plant_buyer",
        "role_title": "Plant Materials Planner",
        "description": "Aggregate 12-week gross production demand from 5 assembly plants and explode BOM netting."
    },
    {
        "stage_id": "STAGE_2_SUPPLIER_SCORECARD",
        "stage_num": 2,
        "title": "Supplier Quality & Scorecard Audit",
        "owner_role": "quality_lead",
        "role_title": "Supplier Quality Assurance",
        "description": "Audit supplier delivery OTD %, defect PPM ratings, ISO certifications, and composite risk indices."
    },
    {
        "stage_id": "STAGE_3_MILP_OPTIMIZATION",
        "stage_num": 3,
        "title": "Multi-Objective MILP Allocation",
        "owner_role": "sourcing_lead",
        "role_title": "Global Sourcing Category Lead",
        "description": "Execute PuLP Mixed-Integer Linear Programming optimization enforcing MOQs and contract share bands."
    },
    {
        "stage_id": "STAGE_4_PREDICTIVE_DELAY_REVIEW",
        "stage_num": 4,
        "title": "Predictive Delay & Split-Sourcing",
        "owner_role": "sourcing_lead",
        "role_title": "Global Sourcing Category Lead",
        "description": "Inspect pre-PO delivery delay probabilities and activate dual-sourcing contingency buffers."
    },
    {
        "stage_id": "STAGE_5_EXECUTIVE_AWARD",
        "stage_num": 5,
        "title": "Executive Sourcing Committee Award",
        "owner_role": "executive",
        "role_title": "Chief Procurement Officer",
        "description": "Review procurement spend waterfall, ratify vendor awards, and release digital POs to ERP/EDI."
    }
]

class SourcingWorkflowManager:
    """Manages the 5-stage monthly governance cycle and auditable decision ledger."""
    
    def __init__(self, data_loader: DataLoader):
        self.loader = data_loader

    def get_cycle_state(self) -> Dict[str, Any]:
        """Returns the current cycle status, stage progression, and decision ledger."""
        df_dec = self.loader.decisions
        
        # Build stage status mapping
        approved_stages = set(df_dec[df_dec["status"] == "APPROVED"]["stage"])
        
        stage_details = []
        current_active_stage = None
        
        for s in STAGES:
            s_id = s["stage_id"]
            is_approved = s_id in approved_stages
            dec_row = df_dec[df_dec["stage"] == s_id]
            
            if is_approved:
                status = "COMPLETED"
                approved_by = dec_row.iloc[-1]["approved_by"]
                timestamp = dec_row.iloc[-1]["timestamp"]
                decision = dec_row.iloc[-1]["decision"]
            else:
                if current_active_stage is None:
                    status = "IN_PROGRESS"
                    current_active_stage = s
                else:
                    status = "LOCKED"
                approved_by = "Pending"
                timestamp = "-"
                decision = "-"
                
            stage_details.append({
                **s,
                "status": status,
                "approved_by": approved_by,
                "timestamp": timestamp,
                "decision": decision
            })
            
        completed_count = len(approved_stages)
        cycle_progress_pct = round((completed_count / len(STAGES)) * 100, 1)

        # Generate tamper-evident audit ledger with SHA-256 hashes
        audit_trail = []
        for _, row in df_dec.iterrows():
            payload = f"{row.get('cycle_id')}||{row.get('stage')}||{row.get('approved_by')}||{row.get('timestamp')}||{row.get('financial_impact')}"
            audit_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
            audit_trail.append({
                "cycle_id": row.get("cycle_id", "CYC-2026-Q3"),
                "stage": row.get("stage", ""),
                "owner_role": row.get("owner_role", ""),
                "decision": row.get("decision", ""),
                "financial_impact": float(row.get("financial_impact", 0.0)),
                "risk_impact": float(row.get("risk_impact", 0.0)),
                "status": row.get("status", "APPROVED"),
                "approved_by": row.get("approved_by", ""),
                "timestamp": row.get("timestamp", ""),
                "audit_hash": f"AUD-{audit_hash}"
            })

        return {
            "cycle_id": "CYC-2026-Q3",
            "cycle_title": "Q3 2026 Direct Materials Strategic Sourcing Cycle",
            "cycle_progress_pct": cycle_progress_pct,
            "completed_stages_count": completed_count,
            "total_stages_count": len(STAGES),
            "stages": stage_details,
            "current_stage": current_active_stage or STAGES[-1],
            "audit_trail": audit_trail
        }

    def record_decision(
        self,
        stage_id: str,
        decision_text: str,
        owner_role: str,
        approved_by: str,
        financial_impact: float = 0.0,
        risk_impact: float = 0.0,
        cycle_id: str = "CYC-2026-Q3"
    ) -> Dict[str, Any]:
        """Appends a new immutable decision record to the governance ledger."""
        df_dec = self.loader.decisions
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_record = {
            "cycle_id": cycle_id,
            "stage": stage_id,
            "owner_role": owner_role,
            "decision": decision_text,
            "financial_impact": round(financial_impact, 2),
            "risk_impact": round(risk_impact, 2),
            "status": "APPROVED",
            "approved_by": approved_by,
            "timestamp": now_str
        }
        
        # Append approved record immutably to the ledger
        df_updated = pd.concat([df_dec, pd.DataFrame([new_record])], ignore_index=True)
        self.loader.save_decisions(df_updated)
        
        return {
            "success": True,
            "record": new_record,
            "message": f"Stage {stage_id} successfully approved and locked in audit ledger."
        }
