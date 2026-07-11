const API_BASE = window.location.hostname === "localhost"
  ? "http://localhost:8000"
  : "/api";

const form = document.getElementById("review-form");
const rulePackSelect = document.getElementById("rule-pack");
const statusEl = document.getElementById("status");
const runButton = document.getElementById("run-button");
const resultsPanel = document.getElementById("results-panel");
const summaryEl = document.getElementById("summary");
const markdownEl = document.getElementById("report-markdown");
const jsonEl = document.getElementById("report-json");

async function loadRulePacks() {
  const response = await fetch(`${API_BASE}/rule-packs`);
  if (!response.ok) {
    rulePackSelect.innerHTML = "<option value=\"ncc-accessibility-v1\">ncc-accessibility-v1</option>";
    return;
  }

  const payload = await response.json();
  rulePackSelect.innerHTML = payload.rule_packs
    .map((pack) => `<option value="${pack}">${pack}</option>`)
    .join("");
}

function renderSummary(summary) {
  summaryEl.innerHTML = `
    <div class="summary-card pass"><span>Pass</span><strong>${summary.pass}</strong></div>
    <div class="summary-card fail"><span>Fail</span><strong>${summary.fail}</strong></div>
    <div class="summary-card needs"><span>Needs checking</span><strong>${summary.needs_checking}</strong></div>
    <div class="summary-card"><span>Total rules</span><strong>${summary.total}</strong></div>
  `;
}

function setActiveTab(tabName) {
  document.querySelectorAll(".tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });
  markdownEl.hidden = tabName !== "markdown";
  jsonEl.hidden = tabName !== "json";
}

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => setActiveTab(button.dataset.tab));
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  runButton.disabled = true;
  statusEl.textContent = "Running pipeline: extracting geometry → retrieving NCC → evaluating rules…";

  const formData = new FormData(form);
  try {
    const response = await fetch(`${API_BASE}/reviews`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || "Review failed");
    }

    const payload = await response.json();
    const report = payload.report;
    renderSummary(report.summary);
    markdownEl.textContent = report.markdown;
    jsonEl.textContent = JSON.stringify(report, null, 2);
    resultsPanel.hidden = false;
    setActiveTab("markdown");
    statusEl.textContent = `Completed run ${payload.run_id}`;
  } catch (error) {
    statusEl.textContent = error.message;
  } finally {
    runButton.disabled = false;
  }
});

loadRulePacks().catch(() => {
  rulePackSelect.innerHTML = "<option value=\"ncc-accessibility-v1\">ncc-accessibility-v1</option>";
});
