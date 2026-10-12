"use strict";

const api = `http://${location.hostname === "localhost" ? "localhost" : "127.0.0.1"}:8000`;
const $ = (id) => document.getElementById(id);
const labels = (value) => String(value).replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
const factors = [
  ["industry_alignment", "Industry"],
  ["funding_stage_alignment", "Stage"],
  ["ticket_size_compatibility", "Ticket size"],
  ["semantic_thesis_similarity", "Thesis keywords"],
  ["geographic_alignment", "Geography"],
  ["portfolio_compatibility", "Portfolio"],
];
const state = { mode: "founder", profiles: [], liveEnabled: false, loadVersion: 0 };

function element(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = String(content);
  return node;
}

async function getJson(path, options) {
  const response = await fetch(api + path, options);
  let body;
  try { body = await response.json(); }
  catch { throw new Error(`The API returned an unreadable response (${response.status}).`); }
  if (!response.ok) {
    const code = body?.error?.code;
    const message = body?.error?.message || "The request could not be completed.";
    throw new Error(`${message}${code ? ` (${code})` : ""}`);
  }
  return body;
}

function setStatus(message, isError = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", isError);
}

function setMode(mode) {
  state.mode = mode;
  for (const value of ["founder", "investor"]) {
    const button = $(`${value}-mode`);
    button.classList.toggle("active", mode === value);
    button.setAttribute("aria-pressed", String(mode === value));
  }
  $("objective").value = mode === "founder"
    ? "Find investors aligned with our business, funding stage, and target markets."
    : "Find businesses that fit our investment thesis, including eligible exploration opportunities.";
  $("results").replaceChildren();
  $("run-notes").replaceChildren();
  $("run-mode").textContent = "Awaiting search";
  setStatus("Choose a demo profile and run a search to see ranked matches.");
  loadProfiles();
}

function updateProfileSummary() {
  const profile = state.profiles.find((item) => item.id === $("profile").value);
  if (!profile) { $("profile-summary").textContent = ""; return; }
  $("profile-summary").textContent = state.mode === "founder"
    ? `${profile.one_liner} · ${labels(profile.funding_stage)} · raising ${Number(profile.amount_raising.amount).toLocaleString()} ${profile.amount_raising.currency}`
    : `${profile.thesis} · ${labels(profile.stage_flexibility)} stage policy`;
}

async function loadProfiles() {
  const version = ++state.loadVersion;
  const mode = state.mode;
  const select = $("profile");
  select.replaceChildren(new Option("Loading fictional profiles…", ""));
  select.disabled = true;
  try {
    const page = await getJson(mode === "founder" ? "/api/businesses?limit=50" : "/api/investors?limit=50");
    if (version !== state.loadVersion) return;
    state.profiles = page.items;
    select.replaceChildren(...page.items.map((profile) => new Option(profile.name, profile.id)));
    select.disabled = false;
    const preferred = mode === "founder" ? "business_solargrid_africa" : "investor_greenfront";
    if (page.items.some((profile) => profile.id === preferred)) select.value = preferred;
    updateProfileSummary();
  } catch (error) {
    if (version !== state.loadVersion) return;
    select.replaceChildren(new Option("API unavailable", ""));
    $("connection").textContent = `Cannot reach the local API at ${api}. Start the backend, then refresh this page.`;
    $("connection").className = "connection bad";
    setStatus(error.message, true);
  }
}

function populateOptions(id, values) {
  const select = $(id);
  for (const value of values) select.add(new Option(labels(value), value));
}

async function initialize() {
  $("founder-mode").addEventListener("click", () => setMode("founder"));
  $("investor-mode").addEventListener("click", () => setMode("investor"));
  $("profile").addEventListener("change", updateProfileSummary);
  $("execution").addEventListener("change", () => {
    $("execution-note").textContent = $("execution").value === "live"
      ? "AI-assisted mode makes a billable OpenAI request. You will confirm before each run."
      : "Engine mode does not call OpenAI or spend API credits.";
  });
  $("match-form").addEventListener("submit", runMatch);
  try {
    const [health, metadata] = await Promise.all([getJson("/api/health"), getJson("/api/metadata")]);
    state.liveEnabled = health.live_agent_enabled;
    populateOptions("industry", metadata.industries);
    populateOptions("stage", metadata.funding_stages);
    if (state.liveEnabled) {
      const option = $("execution").options[1];
      option.disabled = false;
      option.textContent = "AI-assisted (uses credits)";
    }
    $("connection").textContent = `Local API connected · ${state.liveEnabled ? "AI-assisted option available" : "free engine mode"} · all entities are fictional`;
    $("connection").className = "connection good";
    await loadProfiles();
  } catch (error) {
    $("connection").textContent = `Cannot reach the local API at ${api}. Start the backend, then refresh this page.`;
    $("connection").className = "connection bad";
    setStatus(error.message, true);
  }
}

async function runMatch(event) {
  event.preventDefault();
  const profile = state.profiles.find((item) => item.id === $("profile").value);
  if (!profile) { setStatus("Choose a demo profile first.", true); return; }
  const live = $("execution").value === "live";
  if (live && !window.confirm("This starts one billable OpenAI run. The exact cost is not shown here. Continue?")) return;
  const request = {
    mode: state.mode,
    objective: $("objective").value.trim(),
    business_profile: state.mode === "founder" ? profile : null,
    investor_profile: state.mode === "investor" ? profile : null,
    constraints: {
      industries: $("industry").value ? [$("industry").value] : null,
      stages: $("stage").value ? [$("stage").value] : null,
      geographies: null,
      ticket_size: null,
      excluded_entity_ids: [],
      include_exploration_matches: $("explore").checked,
      display_currency: "USD",
    },
    top_k: Number($("top-k").value),
    conversation_id: null,
  };
  const modeAtStart = state.mode;
  $("submit").disabled = true;
  $("results").replaceChildren();
  $("run-notes").replaceChildren();
  $("run-mode").textContent = live ? "AI run in progress" : "Engine run in progress";
  setStatus(live ? "The agent is working. Please wait; do not resubmit this request." : "Checking eligibility and ranking candidates…");
  try {
    const result = await getJson(live ? "/api/agent/match" : "/api/matches", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(live ? { "X-VentureMatch-Live": "true" } : {}) },
      body: JSON.stringify(request),
    });
    if (modeAtStart === state.mode) renderResult(result);
  } catch (error) {
    if (modeAtStart === state.mode) {
      $("run-mode").textContent = "Search failed";
      setStatus(`${error.message}${live ? " The outcome may be uncertain; check the server before trying again." : ""}`, true);
    }
  } finally { $("submit").disabled = false; }
}

function renderResult(result) {
  const data = result.response;
  const isLive = result.execution_mode === "ai_assisted";
  $("run-mode").textContent = isLive ? "AI-assisted analysis" : "Matching engine · no API cost";
  setStatus(data.matches.length
    ? `${data.matches.length} ranked ${data.matches.length === 1 ? "match" : "matches"}${result.considered_count !== undefined ? ` from ${result.considered_count} eligible candidates` : ""}. Open a card to inspect scoring and source evidence.`
    : "No eligible matches under these filters. Try removing the industry or stage filter, or include stage exploration.");
  const highlights = new Map((result.highlights || []).map((item) => [item.candidate_id, item]));
  $("results").replaceChildren(...data.matches.map((match) => renderCard(match, highlights.get(match.candidate_entity_id))));
  const notes = $("run-notes");
  if (isLive && data.activity?.length) {
    notes.append(element("p", "", `Agent steps: ${data.activity.map((item) => `${labels(item.step)} (${item.status})`).join(" · ")}`));
  }
  for (const warning of data.warnings || []) notes.append(element("p", "", warning));
  for (const missing of data.missing_information || []) notes.append(element("p", "", `Missing information: ${missing}`));
  if (isLive) {
    notes.append(element("p", "", "AI selected evidence from engine results. Usage may be unavailable; check Platform billing for actual charges."));
    for (const warning of result.cleanup_warnings || []) notes.append(element("p", "concern", `Cleanup: ${warning}`));
  }
}

function renderCard(match, highlight) {
  const card = element("article", "match-card");
  const head = element("div", "match-head");
  const identity = element("div");
  identity.append(element("div", "rank", `MATCH ${String(match.rank).padStart(2, "0")}`));
  identity.append(element("div", "match-name", match.candidate_name));
  const tags = element("div", "match-tags");
  tags.append(element("span", `tag ${match.eligibility_status === "exploration_eligible" ? "exploration" : ""}`,
    match.eligibility_status === "exploration_eligible" ? "Stage exploration" : "Core eligible"));
  tags.append(element("span", "tag", `${labels(match.confidence)} confidence`));
  identity.append(tags);
  const score = element("div", "score", Number(match.overall_score).toFixed(1));
  score.append(element("small", "", " / 100"));
  head.append(identity, score);
  card.append(head, element("p", "explanation", match.explanation));
  const details = element("details");
  details.append(element("summary", "", "See score breakdown and evidence"));
  const breakdown = element("div", "factor-list");
  for (const [key, name] of factors) {
    const value = Number(match.score_breakdown[key]);
    const row = element("div", "factor");
    const bar = element("div", "bar");
    const fill = element("span", "fill");
    fill.style.width = `${Math.max(0, Math.min(100, value))}%`;
    bar.append(fill);
    row.append(element("span", "", name), bar, element("strong", "", value.toFixed(0)));
    breakdown.append(row);
  }
  details.append(breakdown);
  if (highlight?.statements?.length) {
    details.append(element("div", "detail-heading", "Agent-selected highlights"));
    const list = element("ul", "evidence-list");
    for (const statement of highlight.statements) list.append(element("li", "", statement));
    details.append(list);
  }
  details.append(element("div", "detail-heading", "Traceable evidence"));
  const evidence = element("ul", "evidence-list");
  for (const item of match.evidence) evidence.append(element("li", "", `${item.statement} · ${item.source_entity_id}.${item.source_field}`));
  details.append(evidence);
  if (match.concerns.length) {
    details.append(element("div", "detail-heading", "Points to consider"));
    const concerns = element("ul", "evidence-list concern");
    for (const item of match.concerns) concerns.append(element("li", "", item.message));
    details.append(concerns);
  }
  const raise = match.eligibility?.normalized_raise;
  const ticket = match.eligibility?.normalized_ticket;
  if (raise && ticket) {
    details.append(element("p", "field-note", `FX comparison: ${Number(raise.original.amount).toLocaleString()} ${raise.original.currency} ≈ ${Number(raise.normalized_amount).toLocaleString()} USD; ticket ${Number(ticket.original.minimum).toLocaleString()}–${Number(ticket.original.maximum).toLocaleString()} ${ticket.original.currency}. ${raise.rate_source}, ${raise.rate_timestamp}. Illustrative rates.`));
  }
  card.append(details);
  return card;
}

initialize();
