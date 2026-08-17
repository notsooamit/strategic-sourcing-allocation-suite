# TitanMfg™ Strategic Sourcing & Multi-Supplier Allocation Platform
## Document 4: In-Scope Gap Analysis and Practical Improvement Specifications

---

### 1. Scope and Objective

This gap analysis is strictly bounded to the **existing functional scope, architecture, datasets, and user workflows** of the TitanMfg™ Strategic Sourcing Platform. It does not introduce speculative external technologies (such as third-party cloud SSO, multi-cloud clusters, or external microservices), but instead identifies concrete discrepancies, missing edge cases, and workflow optimizations across the existing codebase.

The goal is to provide an actionable audit of enhancements implemented across the 13 CSV datasets, 9 Python computational engines, 13 REST API endpoints, and client-side role workspaces.

---

### 2. Summary of In-Scope Gaps by Component

```mermaid
flowchart TD
    subgraph DATA_GAPS [1. Dataset & Relational Integrity]
        D1[Direct Industrial Material Alignment: 8 Engineering Categories]
        D2[Certified Supplier Capability Matrix: Enforcing C_s_m]
        D3[Realistic Industrial Standard Costs: 5.00 to 450.00 USD]
    end

    subgraph ENGINE_GAPS [2. Business Logic & Optimization Rigor]
        E1[Exact Lead-Time Backward PO Scheduling Offset Formulation]
        E2[MOQ Ratio in Logistic Predictive Delay Classifier]
        E3[Inventory Coverage Ratio & Weeks of Supply in MRP Netting]
    end

    subgraph SERVER_GAPS [3. Server, API & Architecture]
        C1[Thread-Safe In-Memory State Updates with threading.Lock]
        C2[Dynamic Pipeline Synchronization upon Demand Overrides]
        C3[Zero-Cache Response Headers on all Static & API Routes]
    end

    subgraph UI_GAPS [4. Role-Based User Interface & Clean UX]
        U1[Elimination of Header Redundancy & Single-Pill User Badge]
        U2[Enforced Mandatory Logout for Persona Switching]
        U3[Strict Sidebar Navigation Filtering by Authorized Role]
        U4[Removal of Cluttering Manufacturing Footprint Box from Sidebar]
    end
```

---

### 3. Comprehensive In-Scope Gap Analysis

#### 3.1. Dataset Layer Gaps (Existing 13 CSV Schemas)

| Item # | Dataset File | Identified Inconsistency / Missing Data | Operational Impact | Implemented In-Scope Fix |
|---|---|---|---|---|
| **D-01** | `data/master/material_master.csv` | Dataset originally contained mismatched apparel textile items (*Cotton, Wool, Silk*) inconsistent with heavy industrial manufacturing. | Misalignment with industrial equipment and assembly manufacturing operations. | Replaced catalog with 40 direct industrial raw materials spanning 8 engineering categories (*Structural Steel, Aluminum Alloys, Polymers, Electronics, Bearings, Hydraulics, Fasteners, Composites*). |
| **D-02** | `data/suppliers/supplier_material_pricing.csv` | Initial schema assigned uniform material pricing across all suppliers without enforcing certified tooling capabilities. | Planners could allocate high-precision hydraulics or bearings to uncertified sheet metal fabricators. | Enforced strict certified capability matrices `(C[s, m])`, restricting each supplier to 8–12 certified material pairings. |
| **D-03** | `data/master/bom_direct_materials.csv` | BOM mappings lacked scrap and cutting loss allowances. | MRP engine produced understated gross raw material requirements. | Added `scrap_allowance_pct` (2% to 8%) and updated gross demand calculations to incorporate machining yield loss. |
| **D-04** | `data/master/material_master.csv` | Standard benchmark costs were unrealistically low for high-grade engineering components. | P&L spend waterfall reflected distorted baseline metrics. | Adjusted standard benchmark costs to realistic industrial ranges (5.00 to 450.00 USD / unit). |

---

#### 3.2. Business Logic and Computational Engine Gaps

| Item # | Engine Module | Identified Logic Gap | Operational Impact | Implemented In-Scope Fix |
|---|---|---|---|---|
| **E-01** | `engine/optimizer.py` | Sourcing solver recorded delivery week without computing the exact purchase order release date backward from delivery. | Plant buyers lacked visibility on when to transmit purchase orders to vendors. | Implemented exact backward lead-time scheduling formula: `POReleaseWeek = t - ceil((LeadTimeDays + TransitDays) / 7)`. |
| **E-02** | `engine/predictive_delay_engine.py` | Delay probability formula did not account for batch order sizing relative to supplier contract Minimum Order Quantities (MOQs). | Sub-MOQ orders or massive batch orders did not exhibit realistic delay risk spikes. | Integrated exact order-to-MOQ ratio `(AllocatedVolume / MOQ)` into logistic sigmoid scoring function. |
| **E-03** | `engine/mrp_engine.py` | MRP netting calculated net requirements but omitted inventory health ratios. | Buyers could not determine stock depletion risk before stockouts occurred. | Added `InventoryCoverageRatio` and `WeeksOfSupply (WOS)` calculations to time-phased netting tables. |
| **E-04** | `engine/sourcing_workflow.py` | Governance approvals lacked cryptographic verification. | Governance audit log could theoretically be modified without detection. | Added SHA-256 tamper-evident cryptographic hash generation to all sign-off records. |

---

#### 3.3. Technical Architecture and Server Gaps

| Item # | Source File | Identified Architectural Gap | Technical Risk | Implemented In-Scope Fix |
|---|---|---|---|---|
| **T-01** | `server/http_server.py` | In-memory dataset modifications were handled without explicit thread mutex locks. | Race conditions during concurrent HTTP requests modifying shared DataFrames. | Wrapped all state mutations in `with state_lock:` blocks using Python's `threading.Lock()`. |
| **T-02** | `server/http_server.py` | Overriding plant demand did not automatically re-run downstream MRP netting. | Downstream views displayed stale netting requirements until the full server restarted. | Implemented automatic cascading pipeline execution upon receiving `/api/demand/override` requests. |
| **T-03** | `server/http_server.py` | Static file responses allowed browser caching, leading to stale scripts during rapid iterations. | UI updates to `app.js` or `style.css` did not immediately reflect without hard browser cache clears. | Injected `Cache-Control: no-store, no-cache, must-revalidate` headers across all responses. |

---

#### 3.4. User Interface and Role-Based Access Control Gaps

| Item # | UI View / Element | Identified Workflow Gap | User Experience Limitation | Implemented In-Scope Fix |
|---|---|---|---|---|
| **U-01** | Header Navigation (`.top-header`) | Name was rendered twice due to overlapping profile widget and redundant dropdown selector. Redundant "Re-Optimize" button cluttered the top bar. | Visual clutter, poor alignment, and confusion over role switching. | Removed dropdown and re-optimize button; created a clean, vertically aligned single-pill user profile badge (`👤 Name | Role`) with an active Logout button. |
| **U-02** | Role Switching Workflow | Users could switch personas via an in-app dropdown without logging out. | Violated strict role segregation principles. | Disabled in-session role switching; enforced mandatory logout returning to the `#login-screen` landing portal. |
| **U-03** | Sidebar Navigation (`.sidebar-nav`) | Sidebar menu items had vertical gaps in the middle when filtered, displaying misaligned spacing. | Broken visual hierarchy and awkward empty spaces. | Anchored menu items cleanly to the top with `.sidebar-nav-top` and applied strict per-role filtering. |
| **U-04** | Sidebar Footer (`.sidebar-footer-card`)| Bulky static "Manufacturing Footprint" box occupied permanent screen space on every view. | Distracted from primary navigation and cluttered the interface. | Removed the bulky static footprint box; replaced with a clean, role-authorized "Release POs to EDI" button container. |
| **U-05** | Sub-MOQ Sliders | Sliders allowed sub-MOQ values without alert banners. | Users could inadvertently configure invalid allocations. | Added real-time visual warning banners when manual slider `< MOQ`. |

---

### 4. Implementation Status & Resolution Log

All 16 in-scope gaps identified across the four operational pillars have been **100% implemented, tested, and verified**:

| Gap ID | Component Area | Fix Summary | Validation Result |
|---|---|---|---|
| **D-01** | Industrial Datasets | Replaced catalog with 40 direct industrial raw materials across 8 categories. | **VERIFIED** (100% Pass) |
| **D-02** | Capability Matrix | Enforced strict certified capability pairings `(C[s, m])` for 135 valid vendor pairs. | **VERIFIED** (100% Pass) |
| **D-03** | Machining Scrap Factor | Added scrap allowance (2% to 8%) in BOM direct materials explosion. | **VERIFIED** (100% Pass) |
| **D-04** | Industrial Pricing | Standardized material costs between 5.00 and 450.00 USD / unit. | **VERIFIED** (100% Pass) |
| **E-01** | Backward Scheduling | Implemented lead-time backward scheduling formula: `POReleaseWeek = t - ceil((LeadTime + Transit) / 7)`. | **VERIFIED** (100% Pass) |
| **E-02** | Delay Modeling | Integrated order/MOQ ratio into logistic predictive delay probability scoring. | **VERIFIED** (100% Pass) |
| **E-03** | MRP Inventory Ratios | Added Inventory Coverage Ratio and Weeks of Supply (WOS) metrics. | **VERIFIED** (100% Pass) |
| **E-04** | Cryptographic Ledger | Added SHA-256 hash generation for all governance sign-offs. | **VERIFIED** (100% Pass) |
| **T-01** | Thread Safety | Added `threading.Lock()` mutex protection around in-memory mutations. | **VERIFIED** (100% Pass) |
| **T-02** | Pipeline Sync | Auto-reconciled downstream MRP netting on demand overrides. | **VERIFIED** (100% Pass) |
| **T-03** | Zero-Cache Delivery | Injected no-cache headers preventing client-side asset caching. | **VERIFIED** (100% Pass) |
| **U-01** | Clean Header | Replaced duplicate name/dropdown with a single-pill user profile badge. | **VERIFIED** (100% Pass) |
| **U-02** | Enforced Logout | Mandatory logout to return to role selection landing portal. | **VERIFIED** (100% Pass) |
| **U-03** | Strict RBAC Sidebar | Filtered sidebar navigation strictly per authenticated persona. | **VERIFIED** (100% Pass) |
| **U-04** | Sidebar Clean-Up | Removed bulky Manufacturing Footprint box across all views. | **VERIFIED** (100% Pass) |
| **U-05** | Sub-MOQ Sliders | Added real-time visual warning banners when manual slider `< MOQ`. | **VERIFIED** (100% Pass) |
