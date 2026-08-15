"""
Comprehensive System Health & Mathematical Validation Test Suite

Validates all 13 relational datasets, PuLP MILP solver convergence, constraint adherence,
predictive delay engine, scenario simulator, governance state machine, and REST endpoints.
"""

import os
import sys
import json
import unittest
import threading
import time
import urllib.request

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.data_loader import DataLoader
from engine.mrp_engine import MRPEngine
from engine.supplier_scorecard_engine import ScorecardEngine
from engine.optimizer import SourcingOptimizer
from engine.predictive_delay_engine import PredictiveDelayEngine
from engine.spend_analytics_engine import SpendEngine
from engine.scenario_simulator import ScenarioSimulator
from engine.sourcing_workflow import SourcingWorkflowManager
from engine.orchestrator import SourcingOrchestrator
from server.http_server import ThreadedHTTPServer, SourcingAPIHandler

class TestStrategicSourcingPlatform(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.data_loader = DataLoader()
        cls.mrp_engine = MRPEngine(cls.data_loader)
        cls.scorecard_engine = ScorecardEngine(cls.data_loader)
        cls.optimizer = SourcingOptimizer(cls.data_loader)
        cls.delay_engine = PredictiveDelayEngine(cls.data_loader)
        cls.spend_engine = SpendEngine(cls.data_loader)
        cls.orchestrator = SourcingOrchestrator()
        
        # Start a local test server on a test port
        cls.test_port = 8765
        cls.httpd = ThreadedHTTPServer(("127.0.0.1", cls.test_port), SourcingAPIHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_01_relational_data_integrity(self):
        """Test 1: Verify all 13 CSV tables exist and have valid foreign keys."""
        integrity = self.data_loader.validate_integrity()
        self.assertTrue(integrity["valid"], f"Data integrity errors: {integrity['errors']}")
        self.assertEqual(integrity["material_count"], 40, "Expected 40 materials")
        self.assertEqual(integrity["supplier_count"], 12, "Expected 12 suppliers")
        self.assertEqual(integrity["plant_count"], 5, "Expected 5 plants")
        print("  [PASS] Test 1: Relational Dataset Integrity (40 Materials, 12 Suppliers, 5 Plants)")

    def test_02_mrp_netting_engine(self):
        """Test 2: Verify time-phased MRP gross and net requirement calculations."""
        net_df = self.mrp_engine.compute_net_requirements()
        self.assertFalse(net_df.empty)
        self.assertIn("net_requirement_units", net_df.columns)
        self.assertIn("safety_stock_units", net_df.columns)
        
        summary = self.mrp_engine.get_demand_summary()
        self.assertGreater(summary["total_gross_demand_units"], 0)
        self.assertGreater(summary["total_net_requirement_units"], 0)
        print(f"  [PASS] Test 2: MRP Netting Engine (Gross: {summary['total_gross_demand_units']:,}, Net: {summary['total_net_requirement_units']:,})")

    def test_03_supplier_scorecards_calculation(self):
        """Test 3: Verify composite risk index and reliability classification."""
        scorecards_df = self.scorecard_engine.compute_scorecards()
        self.assertEqual(len(scorecards_df), 12)
        
        for _, row in scorecards_df.iterrows():
            self.assertGreaterEqual(row["composite_risk_index"], 0.0)
            self.assertLessEqual(row["composite_risk_index"], 100.0)
            self.assertIn(row["reliability_rating"], ["EXCELLENT", "GOOD", "MARGINAL", "HIGH_RISK"])
        print("  [PASS] Test 3: Supplier Scorecard & Composite Risk Classification")

    def test_04_pulp_milp_optimization(self):
        """Test 4: Verify PuLP CBC Solver convergence, demand satisfaction, and cost metrics."""
        res = self.optimizer.optimize_sourcing()
        self.assertEqual(res["status"], "OPTIMAL")
        self.assertGreaterEqual(res["service_level_pct"], 99.0, "Service level must be >= 99%")
        self.assertGreater(res["total_allocated_units"], 0)
        self.assertGreater(res["total_landed_cost_usd"], 0.0)
        self.assertLessEqual(res["solve_duration_sec"], 35.0, "Solver should finish in under 35s")
        print(f"  [PASS] Test 4: PuLP MILP Optimization (Status: {res['status']}, Fill: {res['service_level_pct']}%, Cost: ${res['total_landed_cost_usd']:,.2f})")

    def test_05_predictive_delay_engine(self):
        """Test 5: Verify pre-PO delay probability modeling and risk categorization."""
        opt_res = self.optimizer.optimize_sourcing()
        alloc_df = opt_res["allocations_df"]
        delays_df = self.delay_engine.evaluate_allocations(alloc_df)
        
        self.assertFalse(delays_df.empty)
        for _, row in delays_df.iterrows():
            self.assertGreaterEqual(row["delay_probability_pct"], 0.0)
            self.assertLessEqual(row["delay_probability_pct"], 100.0)
            self.assertIn(row["risk_tier"], ["GREEN", "AMBER", "RED"])
        print(f"  [PASS] Test 5: Predictive Pre-PO Delay Engine ({len(delays_df)} line-items evaluated)")

    def test_06_spend_analytics_and_hhi(self):
        """Test 6: Verify spend breakdown and Herfindahl-Hirschman Index (HHI)."""
        opt_res = self.optimizer.optimize_sourcing()
        spend = self.spend_engine.analyze_spend(opt_res["allocations_df"])
        
        self.assertGreater(spend["total_spend_usd"], 0.0)
        self.assertGreater(spend["hhi_index"], 0.0)
        self.assertIn(spend["hhi_status"], ["HEALTHY_DIVERSIFIED", "MODERATELY_CONCENTRATED", "HIGHLY_CONCENTRATED"])
        print(f"  [PASS] Test 6: Spend Analytics & Concentration HHI ({spend['hhi_index']} - {spend['hhi_status']})")

    def test_07_what_if_scenario_simulator(self):
        """Test 7: Verify parametric What-If disruption simulations (Supplier Outage)."""
        sim = ScenarioSimulator(self.data_loader, self.optimizer)
        res = sim.run_scenario(
            scenario_name="Nippon Metallurgy Outage",
            supplier_capacity_cuts={"SUP_003": 0.0},
            demand_surge_pct=0.0
        )
        self.assertIn("baseline", res)
        self.assertIn("scenario", res)
        self.assertIn("deltas", res)
        print(f"  [PASS] Test 7: What-If Disruption Simulator (Cost Delta: {res['deltas']['cost_delta_pct']:+.1f}%)")

    def test_08_governance_state_machine_and_audit(self):
        """Test 8: Verify 5-stage monthly governance cycle and decision signing."""
        workflow = SourcingWorkflowManager(self.data_loader)
        cycle = workflow.get_cycle_state()
        self.assertEqual(len(cycle["stages"]), 5)
        
        sign_res = workflow.record_decision(
            stage_id="STAGE_3_MILP_OPTIMIZATION",
            decision_text="Automated test validation sign-off",
            owner_role="sourcing_lead",
            approved_by="Marcus Vance (Test Lead)",
            financial_impact=-480000.0,
            risk_impact=-22.0
        )
        self.assertTrue(sign_res["success"])
        print("  [PASS] Test 8: 5-Stage Governance State Machine & Decision Ledger")

    def test_09_rest_api_endpoints(self):
        """Test 9: Verify all REST API endpoints over HTTP."""
        base_url = f"http://127.0.0.1:{self.test_port}"
        
        endpoints = [
            "/api/health",
            "/api/dashboard",
            "/api/demand",
            "/api/scorecards",
            "/api/procurement/plan",
            "/api/delays/predictive",
            "/api/spend/analytics",
            "/api/sourcing/cycle",
            "/api/activity/feed",
            "/api/materials",
            "/api/suppliers",
            "/api/plants"
        ]
        
        for ep in endpoints:
            url = f"{base_url}{ep}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                self.assertEqual(response.status, 200, f"Endpoint {ep} failed with status {response.status}")
                data = json.loads(response.read().decode("utf-8"))
                self.assertIsNotNone(data, f"Endpoint {ep} returned empty payload")
                
        # Test POST endpoint
        post_url = f"{base_url}/api/scenario/run"
        post_data = json.dumps({"scenario_name": "API Test", "demand_surge_pct": 10.0}).encode("utf-8")
        post_req = urllib.request.Request(post_url, data=post_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(post_req) as post_res:
            self.assertEqual(post_res.status, 200)
            data = json.loads(post_res.read().decode("utf-8"))
            self.assertIn("deltas", data)
            
        print("  [PASS] Test 9: All 13 REST API Endpoints Verified (HTTP 200 OK)")

if __name__ == "__main__":
    print("\n================================================================================")
    print("   STRATEGIC SOURCING PLATFORM: AUTOMATED SYSTEM VERIFICATION AUDIT")
    print("================================================================================")
    unittest.main(verbosity=2)
