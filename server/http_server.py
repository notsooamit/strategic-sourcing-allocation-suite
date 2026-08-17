"""
Thread-Safe HTTP REST API Gateway & Static File Server

Serves all Sourcing Platform REST APIs and glassmorphic UI static assets.
"""

import os
import sys
import json
import urllib.parse
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Add parent directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.orchestrator import SourcingOrchestrator

WEB_DIR = os.path.join(BASE_DIR, "web")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Thread-per-request HTTP server for concurrent API handling."""
    daemon_threads = True
    allow_reuse_address = True

class SourcingAPIHandler(BaseHTTPRequestHandler):
    """HTTP Request handler for REST endpoints and web assets."""
    
    server_version = "StrategicSourcingGateway/1.0"

    def __init__(self, *args, **kwargs):
        self.orchestrator = SourcingOrchestrator()
        super().__init__(*args, **kwargs)

    def _set_headers(self, status_code: int = 200, content_type: str = "application/json"):
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, HEAD")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self._set_headers(200)

    def do_HEAD(self):
        """Handle HEAD requests (used by health checks and reverse proxies)."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        if path.startswith("/api/"):
            self._set_headers(200, "application/json")
        else:
            self._set_headers(200, "text/html")

    def _send_json(self, data: any, status_code: int = 200):
        try:
            self._set_headers(status_code, "application/json")
            payload = json.dumps(data, indent=2, default=str).encode("utf-8")
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_error(self, message: str, status_code: int = 400):
        try:
            self._send_json({"status": "ERROR", "error": message}, status_code)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _parse_json_body(self) -> dict:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                return {}
            body = self.rfile.read(content_length).decode("utf-8")
            return json.loads(body)
        except Exception:
            return {}

    def do_GET(self):
        """Route GET requests to API handlers or static files."""
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            path = parsed_url.path

            # REST API Routes
            if path == "/api/health":
                integrity = self.orchestrator.data_loader.validate_integrity()
                self._send_json({
                    "status": "HEALTHY",
                    "solver_engine": "PuLP CBC MILP",
                    "data_integrity": integrity,
                    "active_materials": 40,
                    "active_suppliers": 12,
                    "active_plants": 5
                })
            elif path == "/api/dashboard":
                kpis = self.orchestrator.get_dashboard_kpis()
                self._send_json(kpis)
            elif path == "/api/demand":
                demand_data = self.orchestrator.get_demand_data()
                self._send_json(demand_data)
            elif path == "/api/scorecards":
                scorecards = self.orchestrator.get_scorecards_data()
                self._send_json(scorecards)
            elif path == "/api/procurement/plan":
                plan = self.orchestrator.get_procurement_plan()
                self._send_json(plan)
            elif path == "/api/delays/predictive":
                delays = self.orchestrator.get_predictive_delays()
                self._send_json(delays)
            elif path == "/api/spend/analytics":
                spend = self.orchestrator.get_spend_analytics_data()
                self._send_json(spend)
            elif path == "/api/sourcing/cycle":
                cycle = self.orchestrator.get_sourcing_cycle()
                self._send_json(cycle)
            elif path == "/api/activity/feed":
                feed = self.orchestrator.get_activity_feed()
                self._send_json(feed)
            elif path == "/api/materials":
                mats = self.orchestrator.data_loader.material_master.to_dict(orient="records")
                self._send_json(mats)
            elif path == "/api/suppliers":
                sups = self.orchestrator.data_loader.supplier_master.to_dict(orient="records")
                self._send_json(sups)
            elif path == "/api/plants":
                plants = self.orchestrator.data_loader.plant_master.to_dict(orient="records")
                self._send_json(plants)
            elif path == "/api/pricing":
                pricing = self.orchestrator.data_loader.pricing.to_dict(orient="records")
                self._send_json(pricing)
            elif path.startswith("/api/"):
                self._send_error(f"API endpoint '{path}' not found.", 404)
            else:
                # Static Web Assets Serving
                self._serve_static(path)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                self._send_error(f"Internal Server Error: {str(e)}", 500)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_POST(self):
        """Route POST requests for simulations, overrides, and governance."""
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            path = parsed_url.path
            body = self._parse_json_body()

            if path == "/api/demand/override":
                mat_id = body.get("material_id")
                plant_id = body.get("plant_id")
                period_week = body.get("period_week")
                new_demand = int(body.get("new_demand_units", 0))
                user = body.get("user", "Plant Buyer")
                
                if not (mat_id and plant_id and period_week):
                    return self._send_error("Missing required fields: material_id, plant_id, period_week", 400)
                    
                res = self.orchestrator.override_demand(mat_id, plant_id, period_week, new_demand, user)
                self._send_json(res)
                
            elif path == "/api/scenario/run":
                user = body.get("user", "Sourcing Lead")
                res = self.orchestrator.run_scenario(body, user)
                self._send_json(res)
                
            elif path == "/api/sourcing/tune":
                user = body.get("user", "Sourcing Lead")
                res = self.orchestrator.apply_tuning_constraints(body, user)
                self._send_json(res)
                
            elif path == "/api/sourcing/decide":
                stage_id = body.get("stage_id")
                decision_text = body.get("decision_text")
                if not (stage_id and decision_text):
                    return self._send_error("Missing required fields: stage_id, decision_text", 400)
                    
                res = self.orchestrator.record_decision(body)
                self._send_json(res)
                
            elif path == "/api/pipeline/run":
                res = self.orchestrator.run_full_pipeline()
                self._send_json(res)
                
            elif path == "/api/procurement/split-sourcing":
                user = body.get("user", "Category Lead")
                res = self.orchestrator.execute_split_sourcing_contingency(user)
                self._send_json(res)
                
            else:
                self._send_error(f"POST route '{path}' not found.", 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                self._send_error(f"Execution Error: {str(e)}", 500)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _serve_static(self, path: str):
        """Serves static files from web/ folder safely."""
        if path == "/" or path == "":
            rel_path = "index.html"
        else:
            rel_path = path.lstrip("/")

        # Prevent directory traversal
        norm_path = os.path.normpath(os.path.join(WEB_DIR, rel_path))
        if not norm_path.startswith(os.path.abspath(WEB_DIR)):
            self._send_error("Forbidden path access.", 403)
            return

        if not os.path.exists(norm_path) or os.path.isdir(norm_path):
            # Fallback to index.html for SPA routing if requested
            norm_path = os.path.join(WEB_DIR, "index.html")

        if not os.path.exists(norm_path):
            self._send_error("File not found.", 404)
            return

        mime_type, _ = mimetypes.guess_type(norm_path)
        if mime_type is None:
            mime_type = "application/octet-stream"

        try:
            with open(norm_path, "rb") as f:
                content = f.read()
            self._set_headers(200, mime_type)
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            # Client closed the socket prematurely (e.g. quick navigation or health check probe)
            pass
        except Exception as e:
            try:
                self._send_error(f"Error reading asset: {str(e)}", 500)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def log_message(self, format, *args):
        # Override to suppress noisy request logging in console
        return

def start_server(port: int = 8000, host: str = "0.0.0.0"):
    """Starts the Threaded HTTP Server."""
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, SourcingAPIHandler)
    print(f"[HTTP SERVER] Strategic Sourcing Platform running on http://0.0.0.0:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    start_server(port=port)

