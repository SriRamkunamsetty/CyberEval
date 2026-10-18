/**
 * CyberEval - Frontend Application Logic
 * Integrates all 8 modules and 6 signature innovations.
 * Strictly adheres to enterprise secure web standards (safe DOM manipulation, zero innerHTML injection).
 */

const API_BASE = "/api/v1";

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initLeaderboard();
  initScenarios();
  initModelProviders();
  initEvaluationForm();
  initGraphTab();
  initRegressionGatekeeper();
  initReviewQueue();
  initLeakageAuditor();
});

// =========================================================================
// 1. NAVIGATION TABS
// =========================================================================
function initTabs() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", (e) => {
      const currentTab = e.currentTarget;
      tabs.forEach(t => t.classList.remove("active"));
      currentTab.classList.add("active");

      const tabName = currentTab.getAttribute("data-tab");
      const targetPaneId = `pane-${tabName}`;
      document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.remove("active");
      });
      const targetPane = document.getElementById(targetPaneId);
      if (targetPane) targetPane.classList.add("active");

      // Trigger tab-specific refresh if switching
      if (tabName === "scenarios") initScenarios();
      if (tabName === "claim-graph") initGraphTab();
      if (tabName === "regression") initRegressionGatekeeper();
      if (tabName === "review") initReviewQueue();
    });
  });

  document.getElementById("btn-quick-run")?.addEventListener("click", () => {
    const evalTab = document.querySelector('.nav-tab[data-tab="evaluation"]');
    if (evalTab) evalTab.click();
  });
}

// =========================================================================
// 2. LEADERBOARD & RUNS (Overview Tab)
// =========================================================================
async function initLeaderboard() {
  const tbody = document.getElementById("leaderboard-tbody");
  const refreshBtn = document.getElementById("btn-refresh-runs");

  async function loadRuns() {
    try {
      const res = await fetch(`${API_BASE}/evaluations`);
      if (!res.ok) return;
      const runs = await res.json();
      tbody.replaceChildren();

      if (runs.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 9;
        cell.style.textAlign = "center";
        cell.style.color = "#64748b";
        cell.textContent = "No evaluation runs recorded yet. Click 'Run Eval' above to execute your first benchmark!";
        row.appendChild(cell);
        tbody.appendChild(row);
        return;
      }

      runs.forEach(run => {
        const tr = document.createElement("tr");

        // Model Name & Label
        const tdModel = document.createElement("td");
        const nameStrong = document.createElement("strong");
        nameStrong.textContent = run.model_name;
        nameStrong.style.display = "block";
        const labelSpan = document.createElement("span");
        labelSpan.textContent = `[${run.run_label}] · ${run.reproducibility_hash.substring(0, 8)}`;
        labelSpan.style.fontSize = "0.75rem";
        labelSpan.style.color = "#64748b";
        tdModel.appendChild(nameStrong);
        tdModel.appendChild(labelSpan);
        tr.appendChild(tdModel);

        // Overall Score
        const tdScore = document.createElement("td");
        tdScore.style.fontWeight = "700";
        tdScore.textContent = formatPct(run.overall_score);
        tr.appendChild(tdScore);

        // Factual Accuracy
        const tdFactual = document.createElement("td");
        tdFactual.textContent = formatPct(run.factual_correctness);
        tr.appendChild(tdFactual);

        // Evidence Grounding
        const tdGround = document.createElement("td");
        tdGround.textContent = formatPct(run.evidence_grounding);
        tr.appendChild(tdGround);

        // Attack Chain F1
        const tdChain = document.createElement("td");
        tdChain.textContent = formatPct(run.attack_chain_validity);
        tr.appendChild(tdChain);

        // 95% Bootstrap CI
        const tdCI = document.createElement("td");
        tdCI.textContent = `[${formatPct(run.ci_lower)}, ${formatPct(run.ci_upper)}]`;
        tdCI.style.fontFamily = "JetBrains Mono, monospace";
        tdCI.style.fontSize = "0.8rem";
        tr.appendChild(tdCI);

        // Unsupported Rate
        const tdUnsup = document.createElement("td");
        tdUnsup.textContent = formatPct(run.unsupported_claim_rate);
        if ((run.unsupported_claim_rate || 0) > 0.15) {
          tdUnsup.style.color = "#fb7185";
        }
        tr.appendChild(tdUnsup);

        // Safety Gate Badge
        const tdGate = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = run.critical_gates_passed ? "badge badge-emerald" : "badge badge-rose";
        badge.textContent = run.critical_gates_passed ? "PASSED" : "FAILED";
        tdGate.appendChild(badge);
        tr.appendChild(tdGate);

        // Actions (Report export)
        const tdActions = document.createElement("td");
        const btnReport = document.createElement("button");
        btnReport.className = "btn-secondary";
        btnReport.style.padding = "0.3rem 0.6rem";
        btnReport.style.fontSize = "0.75rem";
        btnReport.textContent = "Audit Report";
        btnReport.addEventListener("click", () => {
          window.open(`${API_BASE}/reports/${run.id}/markdown`, "_blank");
        });
        tdActions.appendChild(btnReport);
        tr.appendChild(tdActions);

        tbody.appendChild(tr);
      });
    } catch (err) {
      console.error("Error loading runs:", err);
    }
  }

  refreshBtn?.addEventListener("click", loadRuns);
  loadRuns();
}

// =========================================================================
// 3. SCENARIOS REGISTRY
// =========================================================================
async function initScenarios() {
  const tbody = document.getElementById("scenarios-tbody");
  const catFilter = document.getElementById("filter-category");
  let defaultVersionId = null;

  async function loadScenarios() {
    try {
      const dsRes = await fetch(`${API_BASE}/datasets`);
      const datasets = await dsRes.json();
      if (!datasets || datasets.length === 0) return;
      
      const v = datasets[0].versions[0];
      defaultVersionId = v.id;

      const category = catFilter.value;
      let url = `${API_BASE}/datasets/${datasets[0].id}/versions/${v.id}/scenarios`;
      if (category) url += `?category=${category}`;

      const res = await fetch(url);
      const scenarios = await res.json();
      tbody.replaceChildren();

      document.getElementById("stat-scenarios-count").textContent = scenarios.length;

      scenarios.forEach(sc => {
        const tr = document.createElement("tr");

        // Code
        const tdCode = document.createElement("td");
        tdCode.style.fontFamily = "JetBrains Mono, monospace";
        tdCode.style.fontWeight = "600";
        tdCode.textContent = sc.scenario_code;
        tr.appendChild(tdCode);

        // Title
        const tdTitle = document.createElement("td");
        tdTitle.textContent = sc.title;
        tr.appendChild(tdTitle);

        // Category
        const tdCat = document.createElement("td");
        const catBadge = document.createElement("span");
        catBadge.className = "badge badge-cyan";
        catBadge.textContent = sc.category.replace("_", " ");
        tdCat.appendChild(catBadge);
        tr.appendChild(tdCat);

        // Difficulty
        const tdDiff = document.createElement("td");
        tdDiff.textContent = sc.difficulty.toUpperCase();
        tr.appendChild(tdDiff);

        // Evidence logs count
        const tdEv = document.createElement("td");
        tdEv.textContent = `${sc.tags?.length || 2} telemetry feeds`;
        tr.appendChild(tdEv);

        // Counterfactual
        const tdCF = document.createElement("td");
        if (sc.counterfactual_pair_id) {
          const cfBadge = document.createElement("span");
          cfBadge.className = "badge badge-amber";
          cfBadge.textContent = sc.is_counterfactual_variant ? "Variant (B)" : "Base (A)";
          tdCF.appendChild(cfBadge);
        } else {
          tdCF.textContent = "—";
        }
        tr.appendChild(tdCF);

        // Action View
        const tdAct = document.createElement("td");
        const btnView = document.createElement("button");
        btnView.className = "btn-secondary";
        btnView.style.padding = "0.3rem 0.6rem";
        btnView.style.fontSize = "0.75rem";
        btnView.textContent = "Inspect";
        btnView.addEventListener("click", () => openScenarioModal(sc.id));
        tdAct.appendChild(btnView);
        tr.appendChild(tdAct);

        tbody.appendChild(tr);
      });
    } catch (err) {
      console.error("Error loading scenarios:", err);
    }
  }

  catFilter?.addEventListener("change", loadScenarios);
  loadScenarios();
}

async function openScenarioModal(scenarioId) {
  const modal = document.getElementById("modal-scenario-detail");
  const title = document.getElementById("modal-scenario-title");
  const body = document.getElementById("modal-scenario-body");

  try {
    const res = await fetch(`${API_BASE}/datasets/scenarios/${scenarioId}`);
    const sc = await res.json();
    title.textContent = `[${sc.scenario_code}] ${sc.title}`;
    body.replaceChildren();

    const descP = document.createElement("p");
    descP.style.marginBottom = "1rem";
    descP.textContent = sc.narrative;
    body.appendChild(descP);

    const evTitle = document.createElement("h4");
    evTitle.style.color = "#38bdf8";
    evTitle.style.marginBottom = "0.5rem";
    evTitle.textContent = `Telemetry Evidence Logs (${sc.evidence_items.length})`;
    body.appendChild(evTitle);

    sc.evidence_items.forEach(ev => {
      const evBox = document.createElement("div");
      evBox.style.background = "rgba(0,0,0,0.5)";
      evBox.style.padding = "0.75rem";
      evBox.style.borderRadius = "6px";
      evBox.style.marginBottom = "0.75rem";
      evBox.style.fontFamily = "JetBrains Mono, monospace";

      const evHeader = document.createElement("div");
      evHeader.style.color = "#34d399";
      evHeader.style.fontWeight = "600";
      evHeader.textContent = `[${ev.evidence_code}] ${ev.evidence_type.toUpperCase()} · ${ev.timestamp_observed || ''}`;
      evBox.appendChild(evHeader);

      const pre = document.createElement("pre");
      pre.style.marginTop = "0.4rem";
      pre.style.fontSize = "0.75rem";
      pre.style.overflowX = "auto";
      pre.textContent = JSON.stringify(ev.raw_payload, null, 2);
      evBox.appendChild(pre);

      body.appendChild(evBox);
    });

    modal.classList.add("active");
  } catch (err) {
    console.error("Error inspecting scenario:", err);
  }
}

document.getElementById("modal-close-btn")?.addEventListener("click", () => {
  document.getElementById("modal-scenario-detail")?.classList.remove("active");
});

// =========================================================================
// 4. MODEL PROVIDERS
// =========================================================================
async function initModelProviders() {
  const selectModel = document.getElementById("select-model");
  try {
    const res = await fetch(`${API_BASE}/models/providers`);
    const providers = await res.json();
    selectModel.replaceChildren();

    providers.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.name;
      opt.textContent = `${p.display_name} (${p.provider_type})`;
      selectModel.appendChild(opt);
    });
  } catch (err) {
    console.error("Error loading providers:", err);
  }
}

// =========================================================================
// 5. EVALUATION RUN EXECUTION
// =========================================================================
function initEvaluationForm() {
  const form = document.getElementById("form-run-eval");
  const progressContainer = document.getElementById("eval-progress-container");
  const submitBtn = document.getElementById("btn-submit-eval");

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    submitBtn.disabled = true;
    progressContainer.style.display = "block";

    const modelName = document.getElementById("select-model").value;
    const runLabel = document.getElementById("input-run-label").value;
    const subsetRaw = document.getElementById("input-subset-codes").value;
    const subset = subsetRaw ? subsetRaw.split(",").map(s => s.strip ? s.strip() : s.trim()) : null;

    try {
      const dsRes = await fetch(`${API_BASE}/datasets`);
      const datasets = await dsRes.json();
      const versionId = datasets[0].versions[0].id;

      const payload = {
        dataset_version_id: versionId,
        model_name: modelName,
        run_label: runLabel,
        scenario_subset_codes: subset && subset.length > 0 ? subset : null,
      };

      const res = await fetch(`${API_BASE}/evaluations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        alert(`Evaluation failed: ${err.detail || 'Unknown error'}`);
        return;
      }

      const run = await res.json();
      progressContainer.style.display = "none";
      submitBtn.disabled = false;

      // Switch to overview leaderboard
      document.querySelector('.nav-tab[data-tab="overview"]')?.click();
      initLeaderboard();
    } catch (err) {
      console.error("Evaluation execution error:", err);
      submitBtn.disabled = false;
      progressContainer.style.display = "none";
    }
  });
}

// =========================================================================
// 6. CLAIM-TO-EVIDENCE GRAPH (Innovation 1)
// =========================================================================
let visualizer = null;
async function initGraphTab() {
  visualizer = new ClaimGraphVisualizer("claim-graph-svg", "graph-details-card");
  const selectResp = document.getElementById("select-graph-response");
  const loadBtn = document.getElementById("btn-load-graph");

  async function populateResponses() {
    try {
      const res = await fetch(`${API_BASE}/evaluations`);
      const runs = await res.json();
      if (!runs || runs.length === 0) return;

      const latestRunId = runs[0].id;
      const detailRes = await fetch(`${API_BASE}/evaluations/${latestRunId}/results`);
      const detail = await detailRes.json();

      selectResp.replaceChildren();
      detail.responses.forEach(r => {
        const opt = document.createElement("option");
        opt.value = r.id;
        opt.textContent = `Scenario Response: ${r.scenario_id.substring(0, 8)} (${r.raw_completion.substring(0, 40)}...)`;
        selectResp.appendChild(opt);
      });

      if (detail.responses.length > 0) {
        loadGraph(detail.responses[0].id);
      }
    } catch (err) {
      console.error("Error populating graph responses:", err);
    }
  }

  async function loadGraph(responseId) {
    if (!responseId) return;
    try {
      const res = await fetch(`${API_BASE}/claims/graph/${responseId}`);
      if (!res.ok) return;
      const graphData = await res.json();
      visualizer.render(graphData);
    } catch (err) {
      console.error("Error loading graph:", err);
    }
  }

  loadBtn?.addEventListener("click", () => {
    loadGraph(selectResp.value);
  });

  populateResponses();
}

// =========================================================================
// 7. REGRESSION GATEKEEPER (Innovation 4)
// =========================================================================
async function initRegressionGatekeeper() {
  const selCand = document.getElementById("select-reg-candidate");
  const selBase = document.getElementById("select-reg-baseline");
  const btnRunGate = document.getElementById("btn-run-gate-check");
  const tbody = document.getElementById("regression-diffs-tbody");
  const banner = document.getElementById("gate-verdict-banner");

  async function populateRunSelectors() {
    try {
      const res = await fetch(`${API_BASE}/evaluations`);
      const runs = await res.json();
      selCand.replaceChildren();
      selBase.replaceChildren();

      runs.forEach((r, i) => {
        const optC = document.createElement("option");
        optC.value = r.id;
        optC.textContent = `[${r.model_name}] ${r.run_label} (${formatPct(r.overall_score)})`;
        selCand.appendChild(optC);

        const optB = document.createElement("option");
        optB.value = r.id;
        optB.textContent = `[${r.model_name}] ${r.run_label} (${formatPct(r.overall_score)})`;
        if (i === runs.length - 1) optB.selected = true;
        selBase.appendChild(optB);
      });
    } catch (err) {
      console.error("Error populating runs for regression:", err);
    }
  }

  btnRunGate?.addEventListener("click", async () => {
    const candId = selCand.value;
    const baseId = selBase.value;
    if (!candId || !baseId) {
      alert("Please select both Candidate and Baseline runs.");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/regressions/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate_run_id: candId, baseline_run_id: baseId }),
      });
      const data = await res.json();

      banner.style.display = "block";
      banner.className = data.is_gate_passed ? "badge-emerald" : "badge-rose";
      banner.replaceChildren();

      const title = document.createElement("h3");
      title.textContent = `CI/CD Gate Verdict: ${data.gate_verdict}`;
      title.style.marginBottom = "0.5rem";
      banner.appendChild(title);

      const summaryP = document.createElement("p");
      summaryP.textContent = `Overall Score Delta: ${(data.overall_score_delta * 100).toFixed(2)}% | Regressed Scenarios: ${data.scenarios_regressed_count} | New Unsupported Claims: ${data.new_unsupported_claims_count}`;
      banner.appendChild(summaryP);

      if (data.blocked_reasons && data.blocked_reasons.length > 0) {
        const ul = document.createElement("ul");
        ul.style.marginTop = "0.5rem";
        data.blocked_reasons.forEach(r => {
          const li = document.createElement("li");
          li.textContent = r;
          ul.appendChild(li);
        });
        banner.appendChild(ul);
      }

      tbody.replaceChildren();
      data.scenario_diffs.forEach(diff => {
        const tr = document.createElement("tr");

        const tdCode = document.createElement("td");
        tdCode.textContent = diff.scenario_code;
        tr.appendChild(tdCode);

        const tdCat = document.createElement("td");
        tdCat.textContent = diff.category;
        tr.appendChild(tdCat);

        const tdBase = document.createElement("td");
        tdBase.textContent = formatPct(diff.baseline_score);
        tr.appendChild(tdBase);

        const tdCand = document.createElement("td");
        tdCand.textContent = formatPct(diff.candidate_score);
        tr.appendChild(tdCand);

        const tdDelta = document.createElement("td");
        tdDelta.textContent = `${(diff.score_delta * 100).toFixed(1)}%`;
        tdDelta.style.color = diff.score_delta < -0.1 ? "#fb7185" : (diff.score_delta > 0.1 ? "#34d399" : "#fff");
        tr.appendChild(tdDelta);

        const tdStatus = document.createElement("td");
        const stBadge = document.createElement("span");
        stBadge.className = diff.status === "REGRESSED" ? "badge badge-rose" : (diff.status === "IMPROVED" ? "badge badge-emerald" : "badge badge-cyan");
        stBadge.textContent = diff.status;
        tdStatus.appendChild(stBadge);
        tr.appendChild(tdStatus);

        const tdReasons = document.createElement("td");
        tdReasons.textContent = diff.reasons?.join("; ") || "—";
        tr.appendChild(tdReasons);

        tbody.appendChild(tr);
      });
    } catch (err) {
      console.error("Gate check error:", err);
    }
  });

  populateRunSelectors();
}

// =========================================================================
// 8. REVIEW QUEUE & COHEN'S KAPPA (Innovation 3)
// =========================================================================
async function initReviewQueue() {
  const tbody = document.getElementById("review-tasks-tbody");
  try {
    const res = await fetch(`${API_BASE}/reviews/tasks`);
    const tasks = await res.json();
    tbody.replaceChildren();

    if (tasks.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 6;
      td.style.textAlign = "center";
      td.style.color = "#64748b";
      td.textContent = "No review tasks in queue. All double-blind review workloads are calibrated.";
      tr.appendChild(td);
      tbody.appendChild(tr);
    }
  } catch (err) {
    console.error("Error loading review tasks:", err);
  }
}

// =========================================================================
// 9. LEAKAGE AUDITOR (Innovation 6)
// =========================================================================
async function initLeakageAuditor() {
  const btn = document.getElementById("btn-run-leakage-audit");
  const container = document.getElementById("leakage-report-container");

  btn?.addEventListener("click", async () => {
    container.textContent = "Auditing benchmark dataset splits for cross-split contamination...";
    try {
      const dsRes = await fetch(`${API_BASE}/datasets`);
      const datasets = await dsRes.json();
      const versionId = datasets[0].versions[0].id;

      const res = await fetch(`${API_BASE}/audit/leakage/${versionId}`);
      const report = await res.json();

      container.replaceChildren();

      const title = document.createElement("h3");
      title.style.color = report.integrity_passed ? "#34d399" : "#fb7185";
      title.textContent = report.integrity_passed ? "✓ Benchmark Integrity Verified: Zero Leakage Detected" : "⚠️ Leakage Detected Across Splits";
      title.style.marginBottom = "0.75rem";
      container.appendChild(title);

      const pMeta = document.createElement("p");
      pMeta.textContent = `Total Scenarios Audited: ${report.total_scenarios_audited} | Cross-Split Violations: ${report.leakage_violations_count} | High-Similarity Pairs: ${report.near_duplicate_pairs_count}`;
      container.appendChild(pMeta);
    } catch (err) {
      container.textContent = "Error executing leakage audit.";
    }
  });
}

function formatPct(val) {
  if (val === undefined || val === null) return "0.0%";
  return `${(val * 100).toFixed(1)}%`;
}
