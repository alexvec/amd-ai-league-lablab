"use strict";
// All fetched text reaches the DOM through textContent or text nodes. Never innerHTML.

const $ = (id) => document.getElementById(id);
const EXAMPLE = {
  question: "What does the key word MUST mean?",
  start_url: "https://www.rfc-editor.org/rfc/rfc2119.html",
};
let currentSnapshots = [];

function text(id, value) {
  $(id).textContent = value === null || value === undefined ? "none" : String(value);
}

function el(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
}

function safeLink(url) {
  let safe = null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") safe = parsed.href;
  } catch (_) {
    safe = null;
  }
  if (!safe) return el("span", "", String(url));
  const a = el("a", "", String(url));
  a.href = safe;
  a.rel = "noopener noreferrer nofollow";
  a.target = "_blank";
  return a;
}

async function loadHealth() {
  const response = await fetch("/health");
  const health = await response.json();
  text("health-backend", health.backend);
  text("health-model", health.model);
  text("health-deployment", health.deployment);
  text("health-amd", health.amd.statement);
  const note = $("backend-note");
  if (health.backend === "extractive-no-llm") {
    note.hidden = false;
    note.textContent = "This backend uses no language model. It follows links by keyword overlap and quotes the best-matching sentences, so it can return a real sentence that does not answer the question. Read the quote.";
  } else {
    note.hidden = true;
  }
}

async function loadTraces() {
  const response = await fetch("/traces");
  const { traces } = await response.json();
  const select = $("trace-select");
  select.replaceChildren();
  for (const trace of traces) {
    const option = el("option", "", `${trace.question} [${trace.backend}, ${trace.recorded_at}]`);
    option.value = trace.id;
    select.append(option);
  }
  $("replay").disabled = traces.length === 0;
  if (!traces.length) select.append(el("option", "", "No recorded runs"));
}

function setBusy(busy) {
  $("busy").hidden = !busy;
  $("ask").disabled = busy;
  $("replay").disabled = busy;
}

function showError(message) {
  const box = $("error");
  box.textContent = message;
  box.hidden = !message;
}

function findSnapshot(claim) {
  return currentSnapshots.find((s) => s.url === claim.source_url || s.final_url === claim.source_url);
}

function showPage(claim) {
  const page = $("page");
  page.replaceChildren();
  const snapshot = findSnapshot(claim);
  if (!snapshot) {
    text("page-meta", "No stored page for this claim.");
    return;
  }
  $("page-meta").replaceChildren(
    document.createTextNode(`${snapshot.title || "(untitled)"}, fetched ${snapshot.fetched_at}, sha256 ${snapshot.sha256.slice(0, 16)}. `),
    safeLink(snapshot.final_url),
  );
  const body = snapshot.text || "";
  const others = (claim.verified ? [claim] : []).filter((c) => Number.isInteger(c.start));
  let cursor = 0;
  let mark = null;
  for (const item of others) {
    page.append(document.createTextNode(body.slice(cursor, item.start)));
    mark = el("mark", "", body.slice(item.start, item.end));
    page.append(mark);
    cursor = item.end;
  }
  page.append(document.createTextNode(body.slice(cursor)));
  if (mark) {
    page.scrollTop = Math.max(0, mark.offsetTop - page.offsetTop - 60);
  }
}

function reasonText(claim) {
  const reasons = {
    ok: claim.match === "exact" ? "Quote found on the stored page, exact match." : "Quote found on the stored page after whitespace normalisation.",
    quote_not_found: "Quote is not on the stored page.",
    source_not_fetched: "The cited URL was never fetched in this run.",
    quote_too_short: "Quote is too short to prove anything.",
    empty_quote: "No quote was given.",
    number_not_in_quote: "The claim contains a number that its quote does not.",
    snapshot_hash_mismatch: "The stored page no longer matches its hash.",
  };
  return reasons[claim.reason] || String(claim.reason);
}

function renderClaims(claims) {
  const list = $("claims");
  list.replaceChildren();
  if (!claims.length) list.append(el("li", "muted", "No claims."));
  for (const claim of claims) {
    const item = el("li", claim.verified ? "claim ok" : "claim bad");
    const state = claim.verified ? "Verified" : "Unverified, removed from the answer";
    item.append(el("span", "badge", state));
    if (claim.injected_for_demo) item.append(el("span", "badge demo", "Altered by the demo switch"));
    item.append(el("p", "claim-text", claim.claim));
    if (claim.quote !== claim.claim) item.append(el("blockquote", "", claim.quote));
    item.append(el("p", "reason", reasonText(claim)));
    const source = el("p", "reason");
    source.append(document.createTextNode("Source: "), safeLink(claim.source_url));
    item.append(source);
    if (claim.verified) {
      const button = el("button", "quiet show", "Show on stored page");
      button.type = "button";
      button.addEventListener("click", () => showPage(claim));
      item.append(button);
    }
    list.append(item);
  }
}

function stepText(step) {
  const skip = new Set(["n", "t_ms", "type"]);
  return Object.entries(step)
    .filter(([key, value]) => !skip.has(key) && value !== null && value !== undefined && value !== "")
    .map(([key, value]) => `${key}: ${typeof value === "object" ? JSON.stringify(value) : value}`)
    .join("  ");
}

function renderSteps(trace) {
  const list = $("steps");
  list.replaceChildren();
  for (const step of trace.steps || []) {
    const item = el("li", `step step-${step.type}`);
    item.append(el("strong", "", step.type));
    item.append(el("span", "time", ` ${step.t_ms} ms `));
    item.append(el("span", "detail", stepText(step)));
    list.append(item);
  }
}

function render(data) {
  $("result").hidden = false;
  currentSnapshots = data.snapshots || [];
  const notice = $("replay-notice");
  notice.hidden = !data.replay_notice;
  notice.textContent = data.replay_notice || "";
  text("answer", data.answer || "No verified answer. Nothing below passed the checker, so nothing is claimed.");
  $("answer").classList.toggle("empty", !data.answer);
  const notes = $("notes");
  notes.replaceChildren();
  for (const note of data.notes || []) notes.append(el("li", "", note));
  const trace = data.trace;
  text("result-backend", trace.backend);
  text("result-model", trace.model);
  text("result-gpu", trace.inference_on_amd ? trace.gpu : "not applicable, inference did not run on AMD");
  const tokens = trace.tokens || {};
  text("trace-meta", `Mode ${trace.mode}. Backend ${trace.backend}. Model ${trace.model ?? "none"}. Tokens in ${tokens.prompt ?? "none"}, out ${tokens.completion ?? "none"}. Wall time ${trace.wall_ms} ms as recorded. Pages fetched ${trace.pages_fetched}.`);
  renderClaims(data.claims || []);
  renderSteps(trace);
  const first = (data.claims || []).find((c) => c.verified);
  $("page").replaceChildren();
  $("page-meta").textContent = "";
  if (first) showPage(first);
  $("result").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function post(body) {
  showError("");
  setBusy(true);
  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) {
      $("result").hidden = true;
      showError(data.error || `Request failed with status ${response.status}`);
      return;
    }
    render(data);
  } catch (error) {
    $("result").hidden = true;
    showError(`Request failed: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

$("ask-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const body = { question: $("question").value };
  const start = $("start-url").value.trim();
  if (start) body.start_url = start;
  if ($("inject").checked) body.demo_inject_fabricated_claim = true;
  post(body);
});

$("example").addEventListener("click", () => {
  $("question").value = EXAMPLE.question;
  $("start-url").value = EXAMPLE.start_url;
});

$("replay").addEventListener("click", () => {
  post({ mode: "replay", trace_id: $("trace-select").value });
});

loadHealth().catch((error) => showError(`Could not read /health: ${error.message}`));
loadTraces().catch(() => {});
