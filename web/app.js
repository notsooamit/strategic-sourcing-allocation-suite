/**
 * TitanMfg™ Strategic Sourcing & Multi-Supplier Allocation Platform
 * Reactive ES6+ Frontend Application Architecture
 */

// Enterprise Persona Roster & Authorized Module Permissions
const PERSONAS = {
  executive: {
    id: "executive",
    name: "Robert Sterling",
    role: "Chief Procurement Officer (CPO)",
    badge: "Executive Level",
    defaultView: "view-cockpit",
    allowedViews: ["view-cockpit", "view-simulator", "view-governance"],
    canReleasePO: true
  },
  sourcing_lead: {
    id: "sourcing_lead",
    name: "Marcus Vance",
    role: "Global Category Sourcing Lead",
    badge: "Strategic Sourcing",
    defaultView: "view-allocation",
    allowedViews: ["view-allocation", "view-delay-radar", "view-simulator", "view-governance"],
    canReleasePO: false
  },
  plant_buyer: {
    id: "plant_buyer",
    name: "David Miller",
    role: "Plant Materials Operations Buyer",
    badge: "Plant Operations",
    defaultView: "view-demand-mrp",
    allowedViews: ["view-demand-mrp", "view-governance"],
    canReleasePO: true
  },
  quality_lead: {
    id: "quality_lead",
    name: "Dr. Aris Thorne",
    role: "Supplier Quality & Compliance Lead",
    badge: "Quality Assurance",
    defaultView: "view-scorecards",
    allowedViews: ["view-scorecards", "view-delay-radar", "view-governance"],
    canReleasePO: false
  }
};

// Global State Store
const STATE = {
  isLoggedIn: false,
  activePersona: "sourcing_lead",
  activeView: "view-allocation",
  apiBase: window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1") 
    ? window.location.origin 
    : window.location.origin,
  dashboard: {},
  materials: [],
  suppliers: [],
  plants: [],
  scorecards: [],
  allocationPlan: [],
  predictiveDelays: {},
  demandData: {},
  governanceCycle: {},
  activityFeed: [],
  tuning: {
    materialId: "MAT_001",
    plantId: "PLANT_01",
    week: "W01",
    netReq: 0,
    suppliers: []
  },
  charts: {}
};

// ============================================================================
// Initialization & Lifecycle
// ============================================================================
document.addEventListener("DOMContentLoaded", async () => {
  initLucideIcons();
  setupNavigation();
  setupModals();
  setupActivityDrawer();
  setupTuningStudioEvents();
  setupSimulatorEvents();
  setupFilterEvents();

  // Load all initial data from REST API Gateway in background
  await refreshAllData();
});

function initLucideIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// ============================================================================
// 1. Role-Based Login & Authentication Portal
// ============================================================================
window.loginAs = function(role) {
  if (!PERSONAS[role]) return;
  
  STATE.isLoggedIn = true;
  STATE.activePersona = role;
  
  // Hide login screen and display app layout
  const loginOverlay = document.getElementById("login-screen");
  const appContainer = document.getElementById("app-container");
  
  if (loginOverlay) loginOverlay.style.display = "none";
  if (appContainer) appContainer.style.display = "flex";
  
  // Apply persona-specific permissions and route to default view
  applyPersonaPermissions(role);
  
  console.log(`[AUTH] Successfully logged in as ${PERSONAS[role].name} (${PERSONAS[role].role})`);
};

window.logout = function() {
  STATE.isLoggedIn = false;
  
  // Show login screen and hide app layout
  const loginOverlay = document.getElementById("login-screen");
  const appContainer = document.getElementById("app-container");
  
  if (loginOverlay) loginOverlay.style.display = "flex";
  if (appContainer) appContainer.style.display = "none";
  
  console.log("[AUTH] User logged out, returned to landing portal.");
  initLucideIcons();
};

function applyPersonaPermissions(role) {
  const persona = PERSONAS[role];
  if (!persona) return;
  
  // 1. Update Header User Profile Widget
  const nameEl = document.getElementById("header-user-name");
  const roleEl = document.getElementById("header-user-role");
  if (nameEl) nameEl.textContent = persona.name;
  if (roleEl) roleEl.textContent = persona.role;
  
  // 2. Filter Sidebar Navigation Items (Show strictly authorized modules)
  const navItems = document.querySelectorAll("#sidebar-nav-menu .nav-item");
  navItems.forEach(item => {
    const allowedRolesStr = item.getAttribute("data-roles") || "";
    const allowedRoles = allowedRolesStr.split(",").map(r => r.trim());
    
    if (allowedRoles.includes(role)) {
      item.classList.remove("role-hidden");
      item.style.display = "block";
    } else {
      item.classList.add("role-hidden");
      item.style.display = "none";
    }
  });

  // 3. Show/Hide PO Release button based on role
  const poWrap = document.getElementById("sidebar-po-release-btn-wrap");
  if (poWrap) {
    poWrap.style.display = persona.canReleasePO ? "block" : "none";
  }

  // 4. Switch to Persona's Primary Default View
  switchView(persona.defaultView);
  
  initLucideIcons();
}

// ============================================================================
// View Navigation
// ============================================================================
function setupNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const targetView = item.getAttribute("data-view");
      switchView(targetView);
    });
  });
}

function switchView(viewId) {
  const currentPersona = PERSONAS[STATE.activePersona];
  
  // Enforce role authorization on view switching
  if (currentPersona && !currentPersona.allowedViews.includes(viewId)) {
    console.warn(`[RBAC] Access denied to ${viewId} for role ${STATE.activePersona}. Redirecting to ${currentPersona.defaultView}.`);
    viewId = currentPersona.defaultView;
  }

  STATE.activeView = viewId;
  
  document.querySelectorAll(".nav-item").forEach(item => {
    if (item.getAttribute("data-view") === viewId) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  document.querySelectorAll(".view-panel").forEach(panel => {
    if (panel.id === viewId) {
      panel.classList.add("active");
    } else {
      panel.classList.remove("active");
    }
  });

  initLucideIcons();
}
async function apiGet(endpoint) {
  try {
    const res = await fetch(`${STATE.apiBase}${endpoint}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`[API GET ERROR] ${endpoint}:`, err);
    return null;
  }
}

async function apiPost(endpoint, body) {
  try {
    const res = await fetch(`${STATE.apiBase}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store"
    });
    if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`[API POST ERROR] ${endpoint}:`, err);
    return null;
  }
}

// ============================================================================
// Master Data Sync
// ============================================================================
async function refreshAllData() {
  showEngineStatus("Solving & Reconciling...");
  
  const [
    kpis,
    materials,
    suppliers,
    plants,
    scorecards,
    plan,
    delays,
    demand,
    cycle,
    feed,
    spend,
    pricing
  ] = await Promise.all([
    apiGet("/api/dashboard"),
    apiGet("/api/materials"),
    apiGet("/api/suppliers"),
    apiGet("/api/plants"),
    apiGet("/api/scorecards"),
    apiGet("/api/procurement/plan"),
    apiGet("/api/delays/predictive"),
    apiGet("/api/demand"),
    apiGet("/api/sourcing/cycle"),
    apiGet("/api/activity/feed"),
    apiGet("/api/spend/analytics"),
    apiGet("/api/pricing")
  ]);

  if (kpis) STATE.dashboard = kpis;
  if (materials) STATE.materials = materials;
  if (suppliers) STATE.suppliers = suppliers;
  if (plants) STATE.plants = plants;
  if (scorecards) STATE.scorecards = scorecards;
  if (pricing) STATE.pricing = pricing;
  if (plan) STATE.allocationPlan = plan;
  if (delays) STATE.predictiveDelays = delays;
  if (demand) STATE.demandData = demand;
  if (cycle) STATE.governanceCycle = cycle;
  if (feed) STATE.activityFeed = feed;
  if (spend) STATE.spendAnalytics = spend;

  renderDashboardKPIs();
  renderSpendCharts();
  populateTuningDropdowns();
  
  const mrpPlantDrop = document.getElementById("mrp-filter-plant");
  if (mrpPlantDrop && STATE.plants.length > 0) {
    mrpPlantDrop.innerHTML = '<option value="ALL">All Plants</option>' + STATE.plants.map(p => `<option value="${p.plant_id}">${p.plant_id}</option>`).join("");
  }
  const mrpMatDrop = document.getElementById("mrp-filter-material");
  if (mrpMatDrop && STATE.materials.length > 0) {
    mrpMatDrop.innerHTML = '<option value="ALL">All Materials</option>' + STATE.materials.map(m => `<option value="${m.material_id}">${m.material_id}</option>`).join("");
  }
  renderTuningStudio();
  
  // Fix: Dynamically populate supplier dropdown for Simulator here too
  const supDropdown = document.getElementById("select-sim-supplier");
  if (supDropdown && STATE.suppliers && STATE.suppliers.length > 0) {
    supDropdown.innerHTML = STATE.suppliers.map(s => 
      `<option value="${s.supplier_id}">${s.supplier_id}: ${s.supplier_name}</option>`
    ).join("");
  }

  renderAllocationTable();
  renderDelayRadar();
  renderScorecards();
  renderDemandNetting();
  renderGovernanceStepper();
  renderActivityFeed();

  showEngineStatus("PuLP MILP Solver Active");
  initLucideIcons();
}

function showEngineStatus(text) {
  const el = document.getElementById("status-engine-text");
  if (el) el.textContent = text;
}

// ============================================================================
// View Navigation
// ============================================================================
function setupNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const targetView = item.getAttribute("data-view");
      switchView(targetView);
    });
  });

  const btnReopt = document.getElementById("btn-reoptimize");
  if (btnReopt) {
    btnReopt.addEventListener("click", async () => {
      btnReopt.classList.add("animate-spin");
      await apiPost("/api/pipeline/run", {});
      await refreshAllData();
      btnReopt.classList.remove("animate-spin");
      alert("✅ PuLP MILP Solver successfully re-optimized all 12-week material allocations!");
    });
  }
}

function switchView(viewId) {
  STATE.activeView = viewId;
  
  document.querySelectorAll(".nav-item").forEach(item => {
    if (item.getAttribute("data-view") === viewId) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  document.querySelectorAll(".view-panel").forEach(panel => {
    if (panel.id === viewId) {
      panel.classList.add("active");
    } else {
      panel.classList.remove("active");
    }
  });

  initLucideIcons();
}

// ============================================================================
// VIEW 1: Dashboard KPIs & Charts
// ============================================================================
function renderDashboardKPIs() {
  const d = STATE.dashboard;
  if (!d) return;

  const spendEl = document.getElementById("kpi-total-spend");
  const savingsEl = document.getElementById("kpi-savings-text");
  const otdEl = document.getElementById("kpi-weighted-otd");
  const ppmEl = document.getElementById("kpi-defect-ppm");
  const hhiEl = document.getElementById("kpi-hhi-index");
  const hhiDescEl = document.getElementById("kpi-hhi-desc");

  if (spendEl) spendEl.textContent = formatCurrency(d.total_spend_usd);
  if (savingsEl) {
    savingsEl.innerHTML = `<i data-lucide="trending-down" class="icon-xs"></i> Savings Realized: ${formatCurrency(d.cost_savings_usd)} (${d.cost_savings_pct}%)`;
  }
  if (otdEl) otdEl.textContent = `${d.mean_otd_pct}%`;
  if (ppmEl) ppmEl.textContent = `${d.ppm_defect_rate} PPM`;
  if (hhiEl) hhiEl.textContent = d.hhi_concentration_index;
  if (hhiDescEl) hhiDescEl.textContent = d.hhi_description;

  // Header Cadence Progress
  const cycleProg = document.getElementById("header-cycle-progress");
  const cyclePct = document.getElementById("header-cycle-pct");
  const cycleName = document.getElementById("header-cycle-name");
  if (cycleProg) cycleProg.style.width = `${d.cycle_progress_pct}%`;
  if (cyclePct) cyclePct.textContent = `${d.cycle_progress_pct}%`;
  if (cycleName) cycleName.textContent = d.cycle_current_stage;

  // Fix: Wire up Executive Brief CSV Export
  const btnExport = document.getElementById("btn-export-dashboard-csv");
  if (btnExport) {
    // Prevent multiple listeners
    const newBtn = btnExport.cloneNode(true);
    btnExport.parentNode.replaceChild(newBtn, btnExport);
    newBtn.addEventListener("click", () => {
      let csv = "KPI,Value\n";
      csv += `Total Spend USD,${d.total_spend_usd}\n`;
      csv += `Cost Savings USD,${d.cost_savings_usd}\n`;
      csv += `Mean OTD %,${d.mean_otd_pct}\n`;
      csv += `Defect PPM,${d.ppm_defect_rate}\n`;
      csv += `HHI Concentration,${d.hhi_concentration_index}\n`;
      csv += `Service Level %,${d.service_level_pct}\n`;
      
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.setAttribute('hidden', '');
      a.setAttribute('href', url);
      a.setAttribute('download', 'executive_brief.csv');
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    });
  }

  initLucideIcons();
}

function renderSpendCharts() {
  const spend = STATE.spendAnalytics;
  if (!spend) return;

  // 1. Category Spend Bar Chart
  const ctxCat = document.getElementById("chart-category-spend");
  if (ctxCat) {
    if (STATE.charts.categorySpend) STATE.charts.categorySpend.destroy();
    
    const catLabels = spend.by_category.map(c => c.category);
    const catData = spend.by_category.map(c => c.total_spend_usd);

    STATE.charts.categorySpend = new Chart(ctxCat, {
      type: "bar",
      data: {
        labels: catLabels,
        datasets: [{
          label: "Landed Spend ($)",
          data: catData,
          backgroundColor: "rgba(6, 182, 212, 0.75)",
          borderColor: "#06B6D4",
          borderWidth: 1,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => ` Spend: $${item.raw.toLocaleString()}`
            }
          }
        },
        scales: {
          x: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#94A3B8" } },
          y: { 
            grid: { color: "rgba(255, 255, 255, 0.05)" }, 
            ticks: { 
              color: "#94A3B8",
              callback: (val) => `$${(val / 1e6).toFixed(1)}M`
            } 
          }
        }
      }
    });
  }

  // 2. Supplier Share Donut Chart (HHI)
  const ctxSup = document.getElementById("chart-supplier-share");
  if (ctxSup) {
    if (STATE.charts.supplierShare) STATE.charts.supplierShare.destroy();

    const topSups = spend.by_supplier.slice(0, 6);
    const supLabels = topSups.map(s => s.supplier_name.split(" ")[0]);
    const supData = topSups.map(s => s.spend_share_pct);

    STATE.charts.supplierShare = new Chart(ctxSup, {
      type: "doughnut",
      data: {
        labels: supLabels,
        datasets: [{
          data: supData,
          backgroundColor: [
            "#6366F1", "#06B6D4", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6"
          ],
          borderWidth: 2,
          borderColor: "#0F172A"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "right", labels: { color: "#94A3B8", font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: (item) => ` ${item.label}: ${item.raw}% share`
            }
          }
        }
      }
    });
  }

  // 3. Plant Spend Bar Chart
  const ctxPlant = document.getElementById("chart-plant-spend");
  if (ctxPlant) {
    if (STATE.charts.plantSpend) STATE.charts.plantSpend.destroy();

    const plantLabels = spend.by_plant.map(p => p.plant_name.split(" ")[0]);
    const plantSpendVals = spend.by_plant.map(p => p.total_spend_usd);

    STATE.charts.plantSpend = new Chart(ctxPlant, {
      type: "bar",
      data: {
        labels: plantLabels,
        datasets: [{
          label: "Assembly Hub Spend",
          data: plantSpendVals,
          backgroundColor: "rgba(16, 185, 129, 0.7)",
          borderColor: "#10B981",
          borderWidth: 1,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#94A3B8" } },
          y: { 
            grid: { color: "rgba(255, 255, 255, 0.05)" }, 
            ticks: { 
              color: "#94A3B8",
              callback: (val) => `$${(val / 1e6).toFixed(1)}M`
            } 
          }
        }
      }
    });
  }

  // 4. 12-Week Time-Phased Trend Line Chart
  const ctxTrend = document.getElementById("chart-weekly-trend");
  if (ctxTrend && STATE.demandData.summary) {
    if (STATE.charts.weeklyTrend) STATE.charts.weeklyTrend.destroy();

    const weeks = STATE.demandData.summary.by_week.map(w => w.period_week);
    const grossVals = STATE.demandData.summary.by_week.map(w => w.gross_demand_units);
    const netVals = STATE.demandData.summary.by_week.map(w => w.net_requirement_units);

    STATE.charts.weeklyTrend = new Chart(ctxTrend, {
      type: "line",
      data: {
        labels: weeks,
        datasets: [
          {
            label: "Gross Demand",
            data: grossVals,
            borderColor: "#6366F1",
            backgroundColor: "rgba(99, 102, 241, 0.1)",
            fill: true,
            tension: 0.3
          },
          {
            label: "Net Sourcing",
            data: netVals,
            borderColor: "#06B6D4",
            backgroundColor: "transparent",
            borderDash: [5, 5],
            tension: 0.3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top", labels: { color: "#94A3B8" } }
        },
        scales: {
          x: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#94A3B8" } },
          y: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#94A3B8" } }
        }
      }
    });
  }
}

// ============================================================================
// VIEW 2: MILP Allocation Studio & Interactive Tuning Sliders
// ============================================================================
function populateTuningDropdowns() {
  const matSel = document.getElementById("select-tuning-material");
  const plantSel = document.getElementById("select-tuning-plant");

  if (matSel && STATE.materials.length > 0) {
    matSel.innerHTML = STATE.materials.map(m => 
      `<option value="${m.material_id}">${m.material_id}: ${m.material_name} (${m.category})</option>`
    ).join("");
    matSel.value = STATE.tuning.materialId;
  }

  if (plantSel && STATE.plants.length > 0) {
    plantSel.innerHTML = STATE.plants.map(p => 
      `<option value="${p.plant_id}">${p.plant_id}: ${p.plant_name} (${p.location})</option>`
    ).join("");
    plantSel.value = STATE.tuning.plantId;
  }
}

function setupTuningStudioEvents() {
  const matSel = document.getElementById("select-tuning-material");
  const plantSel = document.getElementById("select-tuning-plant");
  const weekSel = document.getElementById("select-tuning-week");

  const handleChange = () => {
    STATE.tuning.materialId = matSel.value;
    STATE.tuning.plantId = plantSel.value;
    STATE.tuning.week = weekSel.value;
    renderTuningStudio();
  };

  if (matSel) matSel.addEventListener("change", handleChange);
  if (plantSel) plantSel.addEventListener("change", handleChange);
  if (weekSel) weekSel.addEventListener("change", handleChange);

  const btnApply = document.getElementById("btn-apply-allocation-sliders");
  if (btnApply) {
    btnApply.addEventListener("click", async () => {
      // Collect constraints from the UI sliders
      const constraints = {};
      const matId = STATE.tuning.materialId;
      const plantId = STATE.tuning.plantId;
      const week = STATE.tuning.week;
      
      const sliders = document.querySelectorAll(".range-slider");
      sliders.forEach(slider => {
        const supId = slider.getAttribute("data-sup");
        const val = parseInt(slider.value);
        constraints[`${supId}_${matId}_${plantId}_${week}`] = val;
      });
      
      btnApply.innerHTML = `<i data-lucide="loader" class="icon-xs animate-spin"></i> Re-Optimizing MILP...`;
      
      const payload = {
        material_id: matId,
        plant_id: plantId,
        user: STATE.activePersona,
        constraints: constraints
      };
      
      const res = await apiPost("/api/sourcing/tune", payload);
      
      if (res && res.success) {
        alert("✅ Custom vendor sourcing split applied. Schedule synced with MRP constraints.");
        await refreshAllData();
      }
      btnApply.innerHTML = `<i data-lucide="check-circle" class="icon-xs"></i> Apply Tuned Sourcing Split`;
      initLucideIcons();
    });
  }
}

function renderTuningStudio() {
  const matId = STATE.tuning.materialId;
  const plantId = STATE.tuning.plantId;
  const week = STATE.tuning.week;

  // Find net requirement from demandData
  let netReq = 0;
  let grossReq = 0;
  let onHand = 0;
  let safetyStock = 0;
  let stdCost = 0.0;

  const matObj = STATE.materials.find(m => m.material_id === matId);
  if (matObj) stdCost = matObj.standard_cost_usd;

  if (STATE.demandData && STATE.demandData.net_requirements) {
    const match = STATE.demandData.net_requirements.find(
      r => r.material_id === matId && r.plant_id === plantId && r.period_week === week
    );
    if (match) {
      netReq = match.net_requirement_units;
      grossReq = match.gross_demand_units;
      onHand = match.on_hand_units;
      safetyStock = match.safety_stock_units || 0;
    }
  }

  STATE.tuning.netReq = netReq;

  // Update banner
  const grossEl = document.getElementById("tuning-gross-units");
  const onHandEl = document.getElementById("tuning-onhand-units");
  const safetyEl = document.getElementById("tuning-safety-units");
  const netEl = document.getElementById("tuning-net-units");
  const stdEl = document.getElementById("tuning-std-cost");

  if (grossEl) grossEl.textContent = `${grossReq.toLocaleString()} units`;
  if (onHandEl) onHandEl.textContent = `${onHand.toLocaleString()} units`;
  if (safetyEl) safetyEl.textContent = `${safetyStock.toLocaleString()} units`;
  if (netEl) netEl.textContent = `${netReq.toLocaleString()} units`;
  if (stdEl) stdEl.textContent = `$${stdCost.toFixed(2)} / unit`;

  // Find solved allocations for this (mat, plant, week)
  const allocs = STATE.allocationPlan.filter(
    a => a.material_id === matId && a.plant_id === plantId && a.period_week === week
  );

  // Find approved suppliers (Only show suppliers who are contracted for this specific material)
  const eligibleSupIds = STATE.pricing ? STATE.pricing.filter(p => p.material_id === matId).map(p => p.supplier_id) : [];
  
  let approvedSups = STATE.scorecards.filter(s => eligibleSupIds.includes(s.supplier_id));
  
  // If no pricing data loaded yet, fallback to all scorecards safely, but sort by allocated
  if (approvedSups.length === 0 && STATE.scorecards) {
     approvedSups = STATE.scorecards;
  }

  const container = document.getElementById("vendor-sliders-list");
  if (!container) return;

  container.innerHTML = approvedSups.map((sup, idx) => {
    // Check if supplier has allocation
    const alloc = allocs.find(a => a.supplier_id === sup.supplier_id);
    const initUnits = alloc ? alloc.allocated_units : 0;
    const initPct = netReq > 0 ? Math.round((initUnits / netReq) * 100) : 0;
    const moq = 500; // Standard MOQ threshold

    const hasViolation = initUnits > 0 && initUnits < moq;

    return `
      <div class="vendor-slider-card ${hasViolation ? 'has-violation' : ''}" id="slider-card-${sup.supplier_id}">
        <div class="vendor-slider-header">
          <div class="vendor-title-info">
            <span class="badge-status ${sup.reliability_rating === 'EXCELLENT' ? 'badge-green' : 'badge-amber'}">
              ${sup.reliability_rating}
            </span>
            <span class="vendor-name">${sup.supplier_name}</span>
            <span class="vendor-meta">(${sup.country} • OTD: ${sup.historical_otd_pct}% • Defect: ${sup.defect_ppm} PPM)</span>
          </div>
          <div class="vendor-slider-metrics">
            <span>MOQ: <strong>${moq} units</strong></span>
            <span>Allocated: <strong class="slider-metric-val text-cyan" id="val-units-${sup.supplier_id}">${initUnits.toLocaleString()} units</strong></span>
            <span>Share: <strong class="slider-metric-val text-emerald" id="val-pct-${sup.supplier_id}">${initPct}%</strong></span>
          </div>
        </div>

        <input type="range" class="range-slider" id="slider-${sup.supplier_id}" min="0" max="100" value="${initPct}" data-sup="${sup.supplier_id}" data-moq="${moq}">

        <div id="alert-moq-${sup.supplier_id}" class="moq-violation-alert" style="display: ${hasViolation ? 'flex' : 'none'};">
          <i data-lucide="alert-triangle" class="icon-xs"></i>
          <span>⚠️ Sub-MOQ Violation: <strong id="alert-units-${sup.supplier_id}">${initUnits}</strong> units is below contract Minimum Order Quantity (${moq} units).</span>
        </div>
      </div>
    `;
  }).join("");

  // Attach real-time slider input listeners
  approvedSups.forEach(sup => {
    const slider = document.getElementById(`slider-${sup.supplier_id}`);
    if (!slider) return;

    slider.addEventListener("input", (e) => {
      const pct = parseInt(e.target.value);
      const moq = parseInt(e.target.dataset.moq);
      const units = Math.round((pct / 100) * STATE.tuning.netReq);

      const valPct = document.getElementById(`val-pct-${sup.supplier_id}`);
      const valUnits = document.getElementById(`val-units-${sup.supplier_id}`);
      const alertEl = document.getElementById(`alert-moq-${sup.supplier_id}`);
      const cardEl = document.getElementById(`slider-card-${sup.supplier_id}`);
      const alertUnits = document.getElementById(`alert-units-${sup.supplier_id}`);

      if (valPct) valPct.textContent = `${pct}%`;
      if (valUnits) valUnits.textContent = `${units.toLocaleString()} units`;

      const isViolation = units > 0 && units < moq;
      if (alertEl) alertEl.style.display = isViolation ? "flex" : "none";
      if (cardEl) {
        if (isViolation) cardEl.classList.add("has-violation");
        else cardEl.classList.remove("has-violation");
      }
      if (alertUnits) alertUnits.textContent = units;
    });
  });

  initLucideIcons();
}

function renderAllocationTable() {
  const tbody = document.getElementById("tbody-allocation-plan");
  if (!tbody || !STATE.allocationPlan) return;

  tbody.innerHTML = STATE.allocationPlan.slice(0, 50).map(row => {
    const moqBadge = row.moq_compliance_status === "COMPLIANT" 
      ? `<span class="badge-status badge-green">COMPLIANT</span>`
      : `<span class="badge-status badge-red">SUB_MOQ</span>`;

    return `
      <tr>
        <td class="font-mono">${row.period_week}</td>
        <td><strong>${row.material_name}</strong> <span class="text-xs text-slate">(${row.material_id})</span></td>
        <td>${row.supplier_name}</td>
        <td>${row.plant_name}</td>
        <td class="font-mono font-bold">${row.allocated_units.toLocaleString()}</td>
        <td class="font-mono">$${row.unit_price_usd.toFixed(2)}</td>
        <td class="font-mono text-slate">$${row.freight_cost_per_unit_usd.toFixed(2)}</td>
        <td class="font-mono text-cyan font-bold">$${row.landed_cost_usd.toLocaleString()}</td>
        <td class="font-mono text-emerald">${row.po_release_week}</td>
        <td>${moqBadge}</td>
      </tr>
    `;
  }).join("");
}

// ============================================================================
// VIEW 3: Pre-PO Predictive Delay Radar
// ============================================================================
function renderDelayRadar() {
  const delays = STATE.predictiveDelays;
  if (!delays || !delays.summary) return;

  const countGreen = document.getElementById("radar-count-green");
  const countAmber = document.getElementById("radar-count-amber");
  const countRed = document.getElementById("radar-count-red");
  const badgeRed = document.getElementById("badge-red-delay-count");

  if (countGreen) countGreen.textContent = `${delays.summary.low_risk_green_count} Orders`;
  if (countAmber) countAmber.textContent = `${delays.summary.moderate_risk_amber_count} Orders`;
  if (countRed) countRed.textContent = `${delays.summary.high_risk_red_count} Orders`;
  if (badgeRed) badgeRed.textContent = delays.summary.high_risk_red_count;

  const tbody = document.getElementById("tbody-delay-radar");
  if (!tbody || !delays.alerts) return;

  tbody.innerHTML = delays.alerts.slice(0, 50).map(row => {
    let riskBadge = `<span class="badge-status badge-green">LOW (${row.delay_probability_pct}%)</span>`;
    if (row.risk_tier === "AMBER") {
      riskBadge = `<span class="badge-status badge-amber">MODERATE (${row.delay_probability_pct}%)</span>`;
    } else if (row.risk_tier === "RED") {
      riskBadge = `<span class="badge-status badge-red">HIGH (${row.delay_probability_pct}%)</span>`;
    }

    return `
      <tr>
        <td class="font-mono text-slate">${row.po_id}</td>
        <td><strong>${row.material_name}</strong></td>
        <td>${row.supplier_name}</td>
        <td>${row.plant_name}</td>
        <td class="font-mono">${row.period_week}</td>
        <td class="font-mono">${row.allocated_units.toLocaleString()}</td>
        <td class="font-mono">${row.utilization_pct}%</td>
        <td class="font-mono">${row.lead_time_variance_days} d</td>
        <td class="font-mono font-bold">${row.delay_probability_pct}%</td>
        <td>${riskBadge}</td>
        <td class="text-xs ${row.risk_tier === 'RED' ? 'text-rose font-bold' : 'text-slate'}">${row.recommended_action}</td>
      </tr>
    `;
  }).join("");

  const btnSplit = document.getElementById("btn-trigger-split-sourcing");
  if (btnSplit) {
    btnSplit.onclick = async () => {
      const res = await apiPost("/api/procurement/split-sourcing", { user: STATE.activePersona });
      if (res && res.shifts_count > 0) {
        alert(`✅ Split-Sourcing Contingency Applied!\n\nIdentified ${res.shifts_count} high-risk (RED) orders. Automatically stripped ${res.shifted_volume_units.toLocaleString()} units from struggling suppliers and re-allocated them to certified backup suppliers.\n\nMILP Network Rebalanced.`);
        await refreshAllData();
      } else {
        alert("✅ Network is already balanced. No high-risk allocations require contingency transfer.");
      }
    };
  }
}

// ============================================================================
// VIEW 4: Supplier Scorecards & Quality Matrix
// ============================================================================
function renderScorecards() {
  const sups = STATE.scorecards;
  if (!sups || sups.length === 0) return;

  // Quadrant Chart (OTD vs PPM)
  const ctx = document.getElementById("chart-scorecard-quadrant");
  if (ctx) {
    if (STATE.charts.scorecardQuadrant) STATE.charts.scorecardQuadrant.destroy();

    const points = sups.map(s => ({
      x: s.defect_ppm,
      y: s.historical_otd_pct,
      supplierName: s.supplier_name,
      rating: s.reliability_rating
    }));

    STATE.charts.scorecardQuadrant = new Chart(ctx, {
      type: "scatter",
      data: {
        datasets: [{
          label: "Suppliers",
          data: points,
          backgroundColor: (ctx) => {
            const raw = ctx.raw;
            if (!raw) return "#06B6D4";
            if (raw.rating === "EXCELLENT") return "#10B981";
            if (raw.rating === "GOOD") return "#06B6D4";
            if (raw.rating === "MARGINAL") return "#F59E0B";
            return "#EF4444";
          },
          pointRadius: 8,
          pointHoverRadius: 11
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          tooltip: {
            callbacks: {
              label: (item) => ` ${item.raw.supplierName}: OTD ${item.raw.y}%, Defect ${item.raw.x} PPM`
            }
          }
        },
        scales: {
          x: { 
            title: { display: true, text: "Defect PPM (Lower is Better)", color: "#94A3B8" },
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#94A3B8" }
          },
          y: { 
            title: { display: true, text: "Historical On-Time Delivery OTD % (Higher is Better)", color: "#94A3B8" },
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#94A3B8" }
          }
        }
      }
    });
  }

  // Table
  const tbody = document.getElementById("tbody-supplier-scorecards");
  if (!tbody) return;

  tbody.innerHTML = sups.map(s => {
    let ratingBadge = `<span class="badge-status badge-green">${s.reliability_rating}</span>`;
    if (s.reliability_rating === "GOOD") ratingBadge = `<span class="badge-status badge-blue">GOOD</span>`;
    if (s.reliability_rating === "MARGINAL") ratingBadge = `<span class="badge-status badge-amber">MARGINAL</span>`;
    if (s.reliability_rating === "HIGH_RISK") ratingBadge = `<span class="badge-status badge-red">HIGH RISK</span>`;

    return `
      <tr>
        <td class="font-mono text-cyan">${s.supplier_id}</td>
        <td><strong>${s.supplier_name}</strong></td>
        <td>${s.country}</td>
        <td>${s.tier}</td>
        <td>${s.iso_certified ? '✅ ISO-9001' : '❌ Non-Certified'}</td>
        <td class="font-mono font-bold text-emerald">${s.historical_otd_pct}%</td>
        <td class="font-mono font-bold">${s.defect_ppm} PPM</td>
        <td class="font-mono">${s.quality_audit_score} / 100</td>
        <td class="font-mono">${s.lead_time_variance_days} d</td>
        <td class="font-mono">${s.base_financial_risk_score}</td>
        <td class="font-mono font-bold text-amber">${s.composite_risk_index}</td>
        <td>${ratingBadge}</td>
      </tr>
    `;
  }).join("");
}

// ============================================================================
// VIEW 5: Demand & MRP Netting
// ============================================================================
function renderDemandNetting() {
  const d = STATE.demandData;
  if (!d || !d.summary) return;

  const grossEl = document.getElementById("mrp-total-gross");
  const netEl = document.getElementById("mrp-total-net");
  const covEl = document.getElementById("mrp-inventory-cov");

  if (grossEl) grossEl.textContent = `${d.summary.total_gross_demand_units.toLocaleString()} units`;
  if (netEl) netEl.textContent = `${d.summary.total_net_requirement_units.toLocaleString()} units`;
  if (covEl) covEl.textContent = `${d.summary.inventory_coverage_pct}%`;

  const tbody = document.getElementById("tbody-mrp-netting");
  if (!tbody || !d.net_requirements) return;

  tbody.innerHTML = d.net_requirements.slice(0, 50).map(row => {
    return `
      <tr>
        <td class="font-mono">${row.period_week}</td>
        <td class="font-mono text-cyan">${row.material_id}</td>
        <td><strong>${row.material_name}</strong></td>
        <td>${row.category}</td>
        <td>${row.plant_id}</td>
        <td class="font-mono">${row.gross_demand_units.toLocaleString()}</td>
        <td class="font-mono text-slate">${row.on_hand_units.toLocaleString()}</td>
        <td class="font-mono text-slate">${row.safety_stock_units.toLocaleString()}</td>
        <td class="font-mono font-bold text-cyan">${row.net_requirement_units.toLocaleString()}</td>
        <td><span class="badge-status ${row.criticality === 'HIGH' ? 'badge-red' : 'badge-blue'}">${row.criticality}</span></td>
        <td>
          <button class="btn-glass btn-sm" onclick="promptDemandOverride('${row.material_id}', '${row.plant_id}', '${row.period_week}', ${row.gross_demand_units})">
            Edit
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

window.promptDemandOverride = async function(matId, plantId, week, currVal) {
  const newValStr = prompt(`Enter new gross demand units for ${matId} at ${plantId} (${week}):`, currVal);
  if (!newValStr) return;
  const newVal = parseInt(newValStr);
  if (isNaN(newVal) || newVal < 0) return alert("Invalid demand quantity.");

  const res = await apiPost("/api/demand/override", {
    material_id: matId,
    plant_id: plantId,
    period_week: week,
    new_demand_units: newVal,
    user: STATE.activePersona
  });

  if (res && res.success) {
    alert(`✅ Demand updated to ${newVal.toLocaleString()} units. Solver re-optimized downstream plan.`);
    await refreshAllData();
  }
};

// ============================================================================
// VIEW 6: What-If Strategy Simulator
// ============================================================================
function setupSimulatorEvents() {
  const sliderCap = document.getElementById("slider-sim-cap");
  const valCap = document.getElementById("val-sim-cap");
  const sliderDemand = document.getElementById("slider-sim-demand");
  const valDemand = document.getElementById("val-sim-demand");
  const sliderLT = document.getElementById("slider-sim-leadtime");
  const valLT = document.getElementById("val-sim-leadtime");

  // Fix: Dynamically populate supplier dropdown
  const supDropdown = document.getElementById("select-sim-supplier");
  if (supDropdown && STATE.suppliers) {
    supDropdown.innerHTML = STATE.suppliers.map(s => 
      `<option value="${s.supplier_id}">${s.supplier_name}</option>`
    ).join("");
  }

  if (sliderCap) {
    sliderCap.addEventListener("input", (e) => {
      valCap.textContent = `-${e.target.value}%`;
    });
  }

  if (sliderDemand) {
    sliderDemand.addEventListener("input", (e) => {
      valDemand.textContent = `+${e.target.value}%`;
    });
  }

  if (sliderLT) {
    sliderLT.addEventListener("input", (e) => {
      valLT.textContent = `+${e.target.value} Wks`;
    });
  }

  // Presets
  document.querySelectorAll(".btn-scenario-preset").forEach(btn => {
    btn.addEventListener("click", () => {
      const preset = btn.getAttribute("data-preset");
      if (preset === "shutdown_s003") {
        sliderCap.value = 100;
        valCap.textContent = "-100%";
        document.getElementById("select-sim-supplier").value = "SUP_003";
      } else if (preset === "surge_detroit") {
        sliderDemand.value = 45;
        valDemand.textContent = "+45%";
      } else if (preset === "freight_delay") {
        sliderLT.value = 3;
        valLT.textContent = "+3 Wks";
      } else if (preset === "quality_purge") {
        sliderCap.value = 0;
        valCap.textContent = "0%";
      }
    });
  });

  const btnRun = document.getElementById("btn-run-simulation");
  if (btnRun) {
    btnRun.addEventListener("click", async () => {
      btnRun.disabled = true;
      btnRun.innerHTML = `<i data-lucide="loader" class="icon-xs animate-spin"></i> Simulating MILP...`;

      const targetSup = document.getElementById("select-sim-supplier").value;
      const capCutVal = parseInt(sliderCap.value);
      const capMult = { [targetSup]: (100 - capCutVal) / 100.0 };
      const demandSurge = parseFloat(sliderDemand.value);
      const ltDelay = parseInt(sliderLT.value);

      const payload = {
        scenario_name: `Stress Test (Cap -${capCutVal}%, Surge +${demandSurge}%, Delay +${ltDelay}w)`,
        supplier_capacity_cuts: capCutVal > 0 ? capMult : {},
        demand_surge_pct: demandSurge,
        lead_time_delay_weeks: ltDelay,
        user: STATE.activePersona
      };

      const res = await apiPost("/api/scenario/run", payload);
      btnRun.disabled = false;
      btnRun.innerHTML = `<i data-lucide="play" class="icon-xs"></i> Execute Stress-Test Simulation`;
      initLucideIcons();

      if (res) {
        renderSimulationResults(res);
      }
    });
  }

  const btnReset = document.getElementById("btn-reset-scenario");
  if (btnReset) {
    btnReset.addEventListener("click", () => {
      sliderCap.value = 0;
      valCap.textContent = "0%";
      sliderDemand.value = 0;
      valDemand.textContent = "0%";
      sliderLT.value = 0;
      valLT.textContent = "+0 Wks";
      document.getElementById("sim-delta-cost").textContent = "$0.00 (+0.0%)";
      document.getElementById("sim-delta-service").textContent = "100.0%";
      document.getElementById("sim-delta-unmet").textContent = "0 units";
      document.getElementById("sim-delta-hhi").textContent = "0";
      document.getElementById("sim-recommendations-list").textContent = "Execute simulation to generate prescriptive supply chain mitigation actions.";
    });
  }
}

function renderSimulationResults(res) {
  const dCost = document.getElementById("sim-delta-cost");
  const dServ = document.getElementById("sim-delta-service");
  const dUnmet = document.getElementById("sim-delta-unmet");
  const dHHI = document.getElementById("sim-delta-hhi");
  const recList = document.getElementById("sim-recommendations-list");

  if (dCost) {
    const sign = res.deltas.cost_delta_usd >= 0 ? "+" : "";
    dCost.textContent = `${sign}$${res.deltas.cost_delta_usd.toLocaleString()} (${sign}${res.deltas.cost_delta_pct}%)`;
    dCost.className = `impact-val ${res.deltas.cost_delta_pct > 0 ? 'text-rose' : 'text-emerald'}`;
  }

  if (dServ) {
    dServ.textContent = `${res.scenario.service_level_pct}%`;
    dServ.className = `impact-val ${res.scenario.service_level_pct < 100 ? 'text-rose font-bold' : 'text-emerald'}`;
  }

  if (dUnmet) {
    dUnmet.textContent = `${res.scenario.unmet_demand_units.toLocaleString()} units`;
  }

  if (dHHI) {
    dHHI.textContent = `${res.scenario.hhi_index}`;
  }

  if (recList && res.recommendations) {
    recList.innerHTML = res.recommendations.map(r => `<div>${r}</div>`).join("");
  }
}

// ============================================================================
// VIEW 7: 5-Stage Governance & Audit Ledger
// ============================================================================
function renderGovernanceStepper() {
  const cycle = STATE.governanceCycle;
  if (!cycle || !cycle.stages) return;

  const stepper = document.getElementById("governance-stepper");
  if (stepper) {
    stepper.innerHTML = cycle.stages.map((stage, idx) => {
      let statusClass = "locked";
      let statusBadge = `<span class="step-status-pill badge-slate">Locked</span>`;
      if (stage.status === "COMPLETED") {
        statusClass = "completed";
        statusBadge = `<span class="step-status-pill badge-green">Approved</span>`;
      } else if (stage.status === "IN_PROGRESS") {
        statusClass = "in-progress";
        statusBadge = `<span class="step-status-pill badge-blue">Active</span>`;
      }

      return `
        <div class="stage-step-item ${statusClass}">
          <div class="step-circle">${stage.status === 'COMPLETED' ? '✓' : stage.stage_num}</div>
          <span class="step-label">${stage.title}</span>
          <span class="step-role">${stage.role_title}</span>
          ${statusBadge}
        </div>
      `;
    }).join("");
  }

  const tbody = document.getElementById("tbody-governance-ledger");
  if (tbody && cycle.audit_trail) {
    tbody.innerHTML = cycle.audit_trail.map(row => {
      return `
        <tr>
          <td class="font-mono text-cyan font-bold">${row.audit_hash}</td>
          <td class="font-mono">${row.cycle_id}</td>
          <td class="font-bold">${row.stage.replace('STAGE_', '').replace(/_/g, ' ')}</td>
          <td>${row.owner_role}</td>
          <td>${row.decision}</td>
          <td class="font-mono ${row.financial_impact < 0 ? 'text-emerald' : 'text-slate'}">$${row.financial_impact.toLocaleString()}</td>
          <td class="font-mono text-cyan">${row.risk_impact}</td>
          <td><span class="badge-status badge-green">${row.status}</span></td>
          <td>${row.approved_by}</td>
          <td class="font-mono text-slate text-xs">${row.timestamp}</td>
        </tr>
      `;
    }).join("");
  }
}

// ============================================================================
// Activity Stream Drawer
// ============================================================================
function setupActivityDrawer() {
  const drawer = document.getElementById("activity-drawer");
  const btnToggle = document.getElementById("btn-toggle-activity");
  const btnClose = document.getElementById("btn-close-drawer");

  if (btnToggle && drawer) {
    btnToggle.addEventListener("click", () => {
      drawer.classList.toggle("open");
    });
  }

  if (btnClose && drawer) {
    btnClose.addEventListener("click", () => {
      drawer.classList.remove("open");
    });
  }
}

function renderActivityFeed() {
  const container = document.getElementById("activity-feed-list");
  if (!container || !STATE.activityFeed) return;

  container.innerHTML = STATE.activityFeed.map(item => {
    return `
      <div class="activity-item">
        <div class="activity-item-header">
          <span class="activity-user">${item.user}</span>
          <span class="activity-time">${item.timestamp}</span>
        </div>
        <div class="activity-details">${item.details}</div>
      </div>
    `;
  }).join("");
}

// ============================================================================
// Modals: PO Release & Governance Sign-Off
// ============================================================================
function setupModals() {
  // PO Release Modal
  const modalPO = document.getElementById("modal-po-release");
  const btnOpenPO = document.getElementById("btn-release-po-modal");
  const btnClosePO = document.getElementById("btn-close-po-modal");
  const btnConfirmEDI = document.getElementById("btn-confirm-release-edi");
  const btnDownloadCSV = document.getElementById("btn-download-po-csv");
  const btnCopyPO = document.getElementById("btn-copy-po-summary");

  if (btnOpenPO && modalPO) {
    btnOpenPO.addEventListener("click", () => {
      modalPO.classList.add("open");
      renderPOModalContent();
    });
  }

  if (btnClosePO && modalPO) {
    btnClosePO.addEventListener("click", () => modalPO.classList.remove("open"));
  }

  if (btnConfirmEDI && modalPO) {
    btnConfirmEDI.addEventListener("click", () => {
      alert("✅ Generating EDI 850 payload...\n\nAll Purchase Orders successfully formatted and queued for dispatch to SAP/Oracle ERP and EDI Supplier Network!");
      modalPO.classList.remove("open");
    });
  }

  if (btnDownloadCSV) {
    btnDownloadCSV.addEventListener("click", () => exportAllocationsToCSV());
  }

  if (btnCopyPO) {
    btnCopyPO.addEventListener("click", () => {
      const summaryText = `TrendWear Sourcing Allocation Summary:\nTotal Orders: ${STATE.allocationPlan.length}\nTotal Spend: $${STATE.dashboard.total_spend_usd.toLocaleString()}`;
      navigator.clipboard.writeText(summaryText);
      alert("✅ Order summary copied to clipboard!");
    });
  }

  // Sign-Off Modal
  const modalSign = document.getElementById("modal-signoff");
  const btnOpenSign = document.getElementById("btn-open-signoff-modal");
  const btnCloseSign = document.getElementById("btn-close-signoff-modal");
  const btnCancelSign = document.getElementById("btn-cancel-signoff");
  const btnSubmitSign = document.getElementById("btn-submit-signoff");

  if (btnOpenSign && modalSign) {
    btnOpenSign.addEventListener("click", () => modalSign.classList.add("open"));
  }

  if (btnCloseSign && modalSign) {
    btnCloseSign.addEventListener("click", () => modalSign.classList.remove("open"));
  }

  if (btnCancelSign && modalSign) {
    btnCancelSign.addEventListener("click", () => modalSign.classList.remove("open"));
  }

  if (btnSubmitSign && modalSign) {
    btnSubmitSign.addEventListener("click", async () => {
      const stage = document.getElementById("signoff-stage-select").value;
      const notes = document.getElementById("signoff-decision-text").value || "Formal governance stage review approved by committee.";
      const fin = parseFloat(document.getElementById("signoff-fin-impact").value) || 0;
      const risk = parseFloat(document.getElementById("signoff-risk-impact").value) || 0;

      const personaNames = {
        executive: "Robert Sterling (Chief Procurement Officer)",
        sourcing_lead: "Marcus Vance (Category Lead)",
        plant_buyer: "David Miller (Plant Materials Buyer)",
        quality_lead: "Dr. Aris Thorne (Quality Assurance Lead)"
      };

      const res = await apiPost("/api/sourcing/decide", {
        stage_id: stage,
        decision_text: notes,
        owner_role: STATE.activePersona,
        approved_by: personaNames[STATE.activePersona] || "Authorized Officer",
        financial_impact: fin,
        risk_impact: risk
      });

      if (res && res.success) {
        alert("✅ Governance stage ratified and recorded in immutable ledger!");
        modalSign.classList.remove("open");
        await refreshAllData();
      }
    });
  }
}

function renderPOModalContent() {
  const plan = STATE.allocationPlan;
  const countEl = document.getElementById("modal-po-count");
  const spendEl = document.getElementById("modal-po-spend");
  const tbody = document.getElementById("modal-po-tbody");

  if (countEl) countEl.textContent = `${plan.length} PO Lines`;
  if (spendEl && STATE.dashboard.total_spend_usd) {
    spendEl.textContent = `$${STATE.dashboard.total_spend_usd.toLocaleString()}`;
  }

  if (tbody) {
    tbody.innerHTML = plan.slice(0, 30).map((row, idx) => `
      <tr>
        <td class="font-mono text-cyan">PO-${row.supplier_id}-${row.period_week}</td>
        <td>${row.supplier_name}</td>
        <td>${row.material_name}</td>
        <td>${row.plant_name}</td>
        <td class="font-mono font-bold">${row.allocated_units.toLocaleString()}</td>
        <td class="font-mono text-emerald font-bold">$${row.landed_cost_usd.toLocaleString()}</td>
        <td class="font-mono">${row.po_release_week}</td>
      </tr>
    `).join("");
  }
}

function exportAllocationsToCSV() {
  const plan = STATE.allocationPlan;
  if (!plan || plan.length === 0) return;

  const headers = Object.keys(plan[0]).join(",");
  const rows = plan.map(r => Object.values(r).map(val => `"${val}"`).join(","));
  const csvContent = "data:text/csv;charset=utf-8," + [headers, ...rows].join("\n");

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `optimized_sourcing_plan_${new Date().toISOString().slice(0,10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function setupFilterEvents() {
  const allocFilter = document.getElementById("filter-allocation-table");
  if (allocFilter) {
    allocFilter.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      const rows = document.querySelectorAll("#tbody-allocation-plan tr");
      rows.forEach(r => {
        r.style.display = r.textContent.toLowerCase().includes(q) ? "" : "none";
      });
    });
  }

  const delayFilter = document.getElementById("filter-delay-risk");
  if (delayFilter) {
    delayFilter.addEventListener("change", (e) => {
      const val = e.target.value;
      const rows = document.querySelectorAll("#tbody-delay-radar tr");
      rows.forEach(r => {
        if (val === "ALL") r.style.display = "";
        else r.style.display = r.innerHTML.includes(val) ? "" : "none";
      });
    });
  }

  const applyMrpFilter = () => {
    const plantVal = document.getElementById("mrp-filter-plant")?.value || "ALL";
    const matVal = document.getElementById("mrp-filter-material")?.value || "ALL";
    const q = document.getElementById("filter-mrp-table")?.value.toLowerCase() || "";
    
    const rows = document.querySelectorAll("#tbody-mrp-netting tr");
    rows.forEach(r => {
      let show = true;
      if (plantVal !== "ALL" && !r.innerHTML.includes(plantVal)) show = false;
      if (matVal !== "ALL" && !r.innerHTML.includes(matVal)) show = false;
      if (q && !r.textContent.toLowerCase().includes(q)) show = false;
      r.style.display = show ? "" : "none";
    });
  };

  const mrpP = document.getElementById("mrp-filter-plant");
  const mrpM = document.getElementById("mrp-filter-material");
  const mrpQ = document.getElementById("filter-mrp-table");
  if (mrpP) mrpP.addEventListener("change", applyMrpFilter);
  if (mrpM) mrpM.addEventListener("change", applyMrpFilter);
  if (mrpQ) mrpQ.addEventListener("input", applyMrpFilter);

  // Scorecards Purge Button
  const btnPurge = document.getElementById("btn-simulate-purge");
  if (btnPurge) {
    btnPurge.addEventListener("click", async () => {
      const targetSup = prompt("Enter the Supplier ID to purge and ban from the network (e.g. SUP_011):", "SUP_011");
      if (!targetSup) return;
      btnPurge.innerHTML = `<i data-lucide="loader" class="icon-xs animate-spin"></i> Purging...`;
      const res = await apiPost("/api/scenario/run", {
        scenario_name: `Quality Purge - Banned ${targetSup}`,
        supplier_capacity_cuts: { [targetSup]: 0.0 }, // 0% capacity = banned
        user: STATE.activePersona
      });
      btnPurge.innerHTML = `<i data-lucide="shield-alert" class="icon-xs"></i> Simulate Quality Purge`;
      initLucideIcons();
      if (res && res.success !== false) {
        alert(`✅ Quality Purge Executed!\n\n${targetSup} has been banned from the network. The MILP Solver has automatically re-allocated all their volume to certified backups.\n\nCost Delta: ${res.deltas.cost_delta_pct > 0 ? '+' : ''}${res.deltas.cost_delta_pct}%`);
        await refreshAllData();
      }
    });
  }
}

function formatCurrency(num) {
  if (num === undefined || num === null) return "$0.00";
  return "$" + Number(num).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
