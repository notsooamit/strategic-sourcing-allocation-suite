"""
Strategic Sourcing & Multi-Supplier Allocation Enterprise Platform
Main Startup Script
"""

import os
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Check if data exists, if not generate it
data_dir = os.path.join(BASE_DIR, "data", "master")
if not os.path.exists(os.path.join(data_dir, "material_master.csv")):
    print("[INIT] Datasets not found. Generating synthetic relational datasets...")
    import subprocess
    subprocess.run([sys.executable, os.path.join(BASE_DIR, "scripts", "generate_synthetic_data.py")], check=True)

from server.http_server import start_server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"================================================================================")
    print(f"   STRATEGIC SOURCING & MULTI-SUPPLIER ALLOCATION OPTIMIZATION PLATFORM")
    print(f"   Listening on http://localhost:{port}")
    print(f"================================================================================")
    start_server(port=port)
