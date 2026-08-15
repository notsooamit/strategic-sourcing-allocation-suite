# TitanMfg™ Strategic Sourcing & Multi-Supplier Allocation Platform
## Document 2: Core Business Flows, Mathematical Formulations, and Decision Framework

---

### 1. Executive Summary & Problem Statement

**TitanMfg™ Strategic Sourcing Platform** orchestrates direct raw material procurement across 40 industrial material codes, 12 certified global suppliers, and 5 assembly manufacturing plants over a 12-week operational planning horizon.

In industrial manufacturing, strategic sourcing operates under multi-dimensional trade-offs:
1. **Landed Procurement Cost**: Minimizing contract purchase prices and multimodal freight expenses.
2. **Operational Continuity & Anti-Concentration**: Eliminating single-point-of-failure vulnerabilities through mandatory split-sourcing and Herfindahl-Hirschman Index (HHI) concentration limits.
3. **Quality Conformance Ceilings**: Preventing assembly line stoppages by enforcing strict Defect Parts Per Million ($\le 250\text{ PPM}$) and audit score hurdles ($\ge 85$).
4. **Physical Supply Constraints**: Respecting vendor production capacity limits and contract Minimum Order Quantities (MOQs).
5. **Dynamic Lead-Time Synchronization**: Executing exact backward lead-time scheduling from dock-delivery date back to purchase order release date.

---

### 2. End-to-End Operational Architecture

```mermaid
flowchart TD
    subgraph STAGE1 [1. Multi-Plant Demand Aggregation & MRP Netting]
        D1[Plant Gross Demand Forecast] --> D2[BOM Usage & Machining Scrap Explosion]
        D2 --> D3[Time-Phased Inventory Netting & Safety Buffers]
        D3 --> D4[Net Sourcing Requirements NetReq]
    end

    subgraph STAGE2 [2. Supplier Capability & Performance Auditing]
        S1[Supplier Capability Matrix Certified Pairs] --> S2[Historical OTD % & Defect PPM Telemetry]
        S2 --> S3[Composite Risk Index R_s & Audit Scores]
    end

    subgraph STAGE3 [3. PuLP Mixed-Integer Linear Programming MILP Solver]
        D4 --> OPT[Global Multi-Objective MILP Optimization Model]
        S1 --> OPT
        S3 --> OPT
        OPT --> SOL[Solved Optimal Allocation Schedule & Backward Lead-Time Release]
    end

    subgraph STAGE4 [4. Pre-PO Predictive Delivery Delay Radar]
        SOL --> PRED[Logistic Regression Delay Classifier P_Delay]
        PRED --> ALERT[Red / Amber / Green Risk Classification & Mitigation Rebalancing]
    end

    subgraph STAGE5 [5. What-If Disruption Simulation & Governance]
        ALERT --> SIM[Interactive Scenario Simulator: Outages, Demand Surges, Freight Shocks]
        SIM --> GOV[5-Stage Cross-Functional Governance & Cryptographic Audit Ledger]
    end
```

---

### 3. Detailed Operational Steps & Mathematical Logic

#### Flow 1: Multi-Plant Material Demand Aggregation & MRP Netting

##### 1.1. Bill of Materials (BOM) Explosion
Given weekly assembly requirements for finished SKUs across 5 manufacturing facilities, gross material demand incorporates cutting and machining scrap allowances:

$$\text{GrossDemand}_{m, p, t} = \sum_{k \in \text{SKUs}} \text{ProductionPlan}_{k, p, t} \times \text{UsageQty}_{k, m} \times (1 + \text{ScrapAllowance}_{k, m})$$

##### 1.2. Time-Phased Inventory Netting
Net raw material procurement requirements account for physical on-hand warehouse inventory and required safety stock buffers:

$$\text{NetReq}_{m, p, t} = \max\left(0, \text{GrossDemand}_{m, p, t} + \text{SafetyStock}_{m, p} - \text{OnHand}_{m, p} - \text{InTransit}_{m, p, t}\right)$$

##### 1.3. Inventory Coverage Ratio and Weeks of Supply (WOS)
To monitor plant stock health before placing purchase orders:

$$\text{InventoryCoverageRatio}_{m, p} = \frac{\text{OnHand}_{m, p}}{\text{SafetyStock}_{m, p}}$$

$$\text{WeeksOfSupply}_{m, p} = \frac{\text{OnHand}_{m, p}}{\frac{1}{12} \sum_{t=1}^{12} \text{GrossDemand}_{m, p, t}}$$

---

#### Flow 2: Supplier Material Capability Matrix & Performance Auditing

##### 2.1. Certified Capability Matrix ($\mathcal{C}_{s, m}$)
A binary qualification parameter defines whether supplier $s$ is certified to produce material $m$:

$$\mathcal{C}_{s, m} = \begin{cases} 1 & \text{if supplier } s \text{ is certified and tooling-validated for material } m \\ 0 & \text{otherwise} \end{cases}$$

##### 2.2. Quality Conformance Score ($S_{\text{Qual}}$)
Quality audit scores combine incoming parts defect rates and annual engineering audits:

$$S_{\text{Qual}}(s) = 0.50 \times \left(1 - \frac{\text{DefectPPM}_s}{1,000,000}\right) + 0.50 \times \left(\frac{\text{AuditScore}_s}{100}\right)$$

##### 2.3. Composite Risk Index ($R_s$)
A unified risk metric weighting delivery variance, financial liquidity, and geopolitical exposure:

$$R_s = 0.40 \times (1 - \text{OTD}_s) + 0.35 \times \left(\frac{\text{LeadTimeVarianceDays}_s}{7.0}\right) + 0.25 \times \left(\frac{\text{FinancialRiskScore}_s}{5.0}\right)$$

---

#### Flow 3: Multi-Objective Mixed-Integer Linear Programming (PuLP MILP) Solver

##### 3.1. Decision Variables
- $x_{s, m, p, t} \ge 0$: Continuous volume of material $m$ allocated to supplier $s$ for delivery to plant $p$ in week $t$.
- $y_{s, m, p, t} \in \{0, 1\}$: Binary order activation indicator ($1$ if an order is placed with supplier $s$, $0$ otherwise).

##### 3.2. Objective Function Formulation
The optimization engine minimizes total landed cost, logistics freight, supplier risk penalties, and fixed PO order processing overhead:

$$\min Z = \sum_{s} \sum_{m} \sum_{p} \sum_{t} \left[ \left(\text{UnitPrice}_{s, m} + \text{FreightCost}_{s, p}\right) x_{s, m, p, t} + \lambda_{\text{risk}} \cdot R_s \cdot \text{StandardCost}_m \cdot x_{s, m, p, t} + \text{SetupCost} \cdot y_{s, m, p, t} \right]$$

*Where $\lambda_{\text{risk}} = 0.15$ is the risk trade-off weighting coefficient.*

##### 3.3. Linear Constraints
1. **Demand Satisfaction**:
$$\sum_{s \mid \mathcal{C}_{s,m}=1} x_{s, m, p, t} = \text{NetReq}_{m, p, t} \quad \forall m, p, t$$

2. **Supplier Weekly Production Capacity Limits**:
$$\sum_{p} x_{s, m, p, t} \le \text{MaxCapacity}_{s, m, t} \cdot y_{s, m, p, t} \quad \forall s, m, t$$

3. **Contract Minimum Order Quantities (MOQs)**:
$$x_{s, m, p, t} \ge \text{MOQ}_{s, m} \cdot y_{s, m, p, t} \quad \forall s, m, p, t$$

4. **Multi-Sourcing Anti-Concentration Share Bands**:
$$\text{MinShare}_{s, m} \cdot \text{NetReq}_{m, p, t} \cdot y_{s, m, p, t} \le x_{s, m, p, t} \le \text{MaxShare}_{s, m} \cdot \text{NetReq}_{m, p, t} \quad \forall s, m, p, t$$
*(Typically enforced as $\text{MinShare} = 15\%$, $\text{MaxShare} = 60\%$ to ensure dual-sourcing resilience).*

5. **Quality PPM Threshold**:
$$\sum_{s} \text{DefectPPM}_s \cdot x_{s, m, p, t} \le 250 \cdot \text{NetReq}_{m, p, t} \quad \forall m, p, t$$

##### 3.4. Lead-Time Backward PO Scheduling
Purchase order dispatch dates are calculated backward from the target plant receipt week:

$$\text{POReleaseWeek}(s, m, p, t) = t - \left\lceil \frac{\text{LeadTimeDays}_{s, m} + \text{TransitDays}_{s, p}}{7} \right\rceil$$

---

#### Flow 4: Pre-PO Predictive Delivery Delay Probability Engine

##### 4.1. Logistic Regression Delay Scoring Formulation
Before transmitting POs to ERP/EDI, each allocation is evaluated by a machine learning logistic scoring model predicting the probability of transit delay exceeding 3 days ($P(\text{Delay} > 3\text{d})$):

$$P(\text{Delay}) = \sigma\left(\beta_0 + \beta_1 (1 - \text{OTD}_s) + \beta_2 \cdot \text{VarianceDays}_s + \beta_3 \cdot \text{TransitDays}_{s, p} + \beta_4 (1 - \text{LaneReliability}_{s, p}) + \beta_5 \cdot \left(\frac{x_{s,m,p,t}}{\text{MOQ}_{s,m}}\right)\right)$$

*Where $\sigma(z) = \frac{1}{1 + e^{-z}}$.*

##### 4.2. Risk Tier Classification & Prescriptive Routing
| Risk Tier | Probability Threshold | Status Label | Automated Prescriptive Action |
|---|---|---|---|
| **GREEN** | $P(\text{Delay}) < 0.25$ | Low Disruption Risk | Approve standard EDI purchase order release. |
| **AMBER** | $0.25 \le P(\text{Delay}) \le 0.50$ | Moderate Lead-Time Variance | Schedule $+3\text{ day}$ warehouse buffer or shift to expedited freight. |
| **RED** | $P(\text{Delay}) > 0.50$ | Critical Delivery Bottleneck | Trigger split-sourcing reallocation to certified secondary supplier. |

---

#### Flow 5: Interactive What-If Disruption Simulation & Stress-Testing

Planners simulate macroeconomic shocks in sub-second real time:
1. **Supplier Shutdown / Outage**: Simulates complete shutdown ($\text{Capacity} = 0$) of a Tier-1 vendor (e.g., `SUP_001`). Re-optimizes across remaining certified vendors to evaluate landed spend cost surges.
2. **Plant Demand Spikes**: Injects $+10\%$ to $+50\%$ surges across automotive assembly hubs.
3. **Logistics Bottlenecks**: Adds $+1$ to $+3$ weeks of transit delay to trans-Pacific/trans-Atlantic maritime corridors.
4. **Quality Ceiling Purge**: Disqualifies vendors exceeding 150 PPM, demonstrating quality trade-offs.

---

#### Flow 6: 5-Stage Strategic Sourcing Governance Cadence & Audit Ledger

```mermaid
stateDiagram-v2
    [*] --> Stage1_DemandValidation
    Stage1_DemandValidation --> Stage2_SupplierCapabilityAudit: Plant Materials Lead Sign-Off
    Stage2_SupplierCapabilityAudit --> Stage3_AllocationOptimization: Quality Assurance Lead Sign-Off
    Stage3_AllocationOptimization --> Stage4_ExecutiveSignOff: Strategic Sourcing Lead Sign-Off
    Stage4_ExecutiveSignOff --> Stage5_POReleaseEDI: Chief Procurement Officer CPO Sign-Off
    Stage5_POReleaseEDI --> [*]: PO Transmitted to ERP/EDI
```

Each stage transition generates a tamper-evident audit record hashed with SHA-256:

$$\text{AuditHash} = \text{SHA256}\left(\text{CycleID} \,\|\, \text{Stage} \,\|\, \text{Approver} \,\|\, \text{Timestamp} \,\|\, \text{FinancialImpact}\right)$$

---

### 4. Cross-Functional RACI Responsibility Matrix

| Sourcing Workflow Step | David Miller (Plant Buyer) | Dr. Aris Thorne (Quality Lead) | Marcus Vance (Category Lead) | Robert Sterling (CPO) |
|---|---|---|---|---|
| **1. Demand & MRP Netting** | **Accountable (A)** | Informed (I) | Consulted (C) | Informed (I) |
| **2. Supplier Auditing & Scorecards**| Informed (I) | **Accountable (A)** | Consulted (C) | Informed (I) |
| **3. Sourcing Allocation & Sliders** | Consulted (C) | Consulted (C) | **Accountable (A)** | Informed (I) |
| **4. Pre-PO Delay Radar & Split-Sourcing**| Informed (I) | Consulted (C) | **Accountable (A)** | Informed (I) |
| **5. What-If Disruption Simulation** | Informed (I) | Informed (I) | **Responsible (R)** | **Accountable (A)** |
| **6. 5-Stage Governance Sign-Off** | Responsible (R) | Responsible (R) | Responsible (R) | **Accountable (A)** |
| **7. 1-Click PO Release to EDI** | **Accountable (A)** | Informed (I) | Informed (I) | **Accountable (A)** |
