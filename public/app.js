const jdInput = document.getElementById("jd-input");
const resumeInput = document.getElementById("resume-input");
const jdCount = document.getElementById("jd-count");
const resumeCount = document.getElementById("resume-count");
const scanBtn = document.getElementById("scan-btn");
const scanBeam = document.getElementById("scan-beam");
const loadingState = document.getElementById("loading-state");
const loadingMessage = document.getElementById("loading-message");
const results = document.getElementById("results");
const xrayToggleBtn = document.getElementById("xray-toggle-btn");
const xrayOverlay = document.getElementById("xray-overlay");
const scoreDelta = document.getElementById("score-delta");
const applyRescanBtn = document.getElementById("apply-rescan-btn");
const streamConsole = document.getElementById("stream-console");
const streamConsoleText = document.getElementById("stream-console-text");
const pdfBtn = document.getElementById("pdf-btn");
const pdfSection = document.getElementById("pdf-section");
const pdfFrame = document.getElementById("pdf-frame");
const pdfDownloadLink = document.getElementById("pdf-download-link");

const LOADING_MESSAGES = [
  "Parsing job description…",
  "Extracting keywords & qualifications…",
  "Cross-referencing resume content…",
  "Flagging weak bullet points…",
];

// ---- App state ----
let lastAnalysis = null;
let lastRewrites = [];
let previousMatchScore = null;
let xrayActive = false;
let currentPdfUrl = null;

jdInput.addEventListener("input", () => {
  jdCount.textContent = `${jdInput.value.length.toLocaleString()} chars`;
  updateScanButton();
});
resumeInput.addEventListener("input", () => {
  resumeCount.textContent = `${resumeInput.value.length.toLocaleString()} chars`;
  updateScanButton();
  // Resume text changed manually — X-ray view and delta context are stale now.
  if (xrayActive) toggleXray(false);
});

function updateScanButton() {
  scanBtn.disabled = !(jdInput.value.trim() && resumeInput.value.trim());
}
updateScanButton();

scanBtn.addEventListener("click", () => runScan({ showDelta: false }));
xrayToggleBtn.addEventListener("click", () => toggleXray(!xrayActive));
applyRescanBtn.addEventListener("click", applyRewritesAndRescan);
pdfBtn.addEventListener("click", generatePdfPreview);

async function runScan({ showDelta }) {
  const jobDescription = jdInput.value.trim();
  const resumeMarkdown = resumeInput.value.trim();
  if (!jobDescription || !resumeMarkdown) return;

  if (xrayActive) toggleXray(false);

  scanBtn.disabled = true;
  applyRescanBtn.disabled = true;
  scanBtn.textContent = "SCANNING…";
  scanBeam.classList.remove("hidden");
  loadingState.classList.remove("hidden");
  results.classList.add("hidden");
  scoreDelta.classList.add("hidden");

  let messageIndex = 0;
  loadingMessage.textContent = LOADING_MESSAGES[0];
  const messageInterval = setInterval(() => {
    messageIndex = Math.min(messageIndex + 1, LOADING_MESSAGES.length - 1);
    loadingMessage.textContent = LOADING_MESSAGES[messageIndex];
  }, 1400);

  try {
    // ---- Pass 1: keyword analysis (non-streaming — already fast) ----
    const analysis = await postJSON("/api/analyze", { jobDescription, resumeMarkdown });
    const scoreBefore = previousMatchScore;
    renderAnalysis(analysis, showDelta ? scoreBefore : null);
    lastAnalysis = analysis;
    xrayToggleBtn.classList.remove("hidden");

    results.classList.remove("hidden");
    loadingState.classList.add("hidden");
    scanBeam.classList.add("hidden");
    clearInterval(messageInterval);

    // ---- Pass 2: bullet rewriting, streamed live ----
    const rewriteResult = await streamRewrite(jobDescription, resumeMarkdown, analysis);
    renderRewrites(rewriteResult.rewrites);
    lastRewrites = rewriteResult.rewrites;
    applyRescanBtn.classList.toggle("hidden", rewriteResult.rewrites.length === 0);

    previousMatchScore = analysis.matchScore;
  } catch (err) {
    alert(`Scan failed: ${err.message}`);
    console.error(err);
  } finally {
    clearInterval(messageInterval);
    scanBeam.classList.add("hidden");
    loadingState.classList.add("hidden");
    streamConsole.classList.add("hidden");
    scanBtn.disabled = false;
    applyRescanBtn.disabled = false;
    scanBtn.textContent = "RUN_SCAN →";
    updateScanButton();
  }
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Request to ${url} failed (${res.status})`);
  }
  return res.json();
}

// ---- Feature: streaming bullet rewrites ----
async function streamRewrite(jobDescription, resumeMarkdown, keywordAnalysis) {
  streamConsole.classList.remove("hidden");
  streamConsoleText.textContent = "";

  const res = await fetch("/api/rewrite/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jobDescription, resumeMarkdown, keywordAnalysis }),
  });

  if (!res.ok || !res.body) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || `Streaming rewrite request failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let accumulated = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });

    if (chunk.includes("__STREAM_ERROR__:")) {
      const msg = chunk.split("__STREAM_ERROR__:")[1] || "Unknown streaming error";
      throw new Error(msg.trim());
    }

    accumulated += chunk;
    streamConsoleText.textContent = accumulated;
    streamConsoleText.scrollTop = streamConsoleText.scrollHeight;
  }

  streamConsole.classList.add("hidden");

  try {
    return JSON.parse(accumulated);
  } catch (e) {
    throw new Error("Received malformed JSON from the model stream.");
  }
}

// ---- Feature: score delta rendering ----
function renderAnalysis(analysis, previousScore) {
  document.getElementById("score-value").textContent = `${Math.round(analysis.matchScore)}%`;
  document.getElementById("score-summary").textContent = analysis.summary;

  if (previousScore !== null && previousScore !== undefined) {
    const diff = Math.round(analysis.matchScore - previousScore);
    scoreDelta.classList.remove("hidden", "positive", "negative", "neutral");
    if (diff > 0) {
      scoreDelta.textContent = `+${diff}%`;
      scoreDelta.classList.add("positive");
    } else if (diff < 0) {
      scoreDelta.textContent = `${diff}%`;
      scoreDelta.classList.add("negative");
    } else {
      scoreDelta.textContent = `±0%`;
      scoreDelta.classList.add("neutral");
    }
  } else {
    scoreDelta.classList.add("hidden");
  }

  const barsEl = document.getElementById("score-bars");
  barsEl.innerHTML = "";
  const total = 20;
  const lit = Math.round((analysis.matchScore / 100) * total);
  const color =
    analysis.matchScore >= 70 ? "var(--matched)" : analysis.matchScore >= 40 ? "var(--weak)" : "var(--missing)";

  for (let i = 0; i < total; i++) {
    const bar = document.createElement("div");
    bar.className = "score-bar";
    bar.style.height = `${8 + (i / total) * 28}px`;
    bar.style.background = i < lit ? color : "var(--hairline)";
    barsEl.appendChild(bar);
  }

  renderKeywordColumn("matched", analysis.matchedKeywords, (k) => k.importance, "--matched");
  renderKeywordColumn("weak", analysis.weaklyEmphasizedKeywords, (k) => k.reason, "--weak");
  renderKeywordColumn("missing", analysis.missingKeywords, (k) => k.importance, "--missing");
}

function renderKeywordColumn(prefix, items, subTextFn, colorVar) {
  const listEl = document.getElementById(`${prefix}-list`);
  const countEl = document.getElementById(`${prefix}-count`);
  countEl.textContent = `${items.length} items`;
  listEl.innerHTML = "";

  if (items.length === 0) {
    const empty = document.createElement("div");
    empty.className = "kw-empty";
    empty.textContent = "Nothing here.";
    listEl.appendChild(empty);
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "kw-item";
    li.style.borderColor = `color-mix(in srgb, var(${colorVar}) 30%, transparent)`;
    li.style.background = `color-mix(in srgb, var(${colorVar}) 10%, transparent)`;
    li.innerHTML = `<div class="kw-label">${escapeHtml(item.keyword)}</div><div class="kw-sub">${escapeHtml(subTextFn(item))}</div>`;
    listEl.appendChild(li);
  });
}

function renderRewrites(rewrites) {
  const listEl = document.getElementById("rewrites-list");
  const countLabel = document.getElementById("rewrites-count-label");
  listEl.innerHTML = "";

  countLabel.textContent = `${rewrites.length} BULLET${rewrites.length === 1 ? "" : "S"} REWRITTEN`;

  if (rewrites.length === 0) {
    const empty = document.createElement("div");
    empty.className = "kw-empty";
    empty.textContent = "No weak bullets detected — nothing to rewrite. Nice work.";
    listEl.appendChild(empty);
    return;
  }

  rewrites.forEach((bullet) => {
    const card = document.createElement("div");
    card.className = "rewrite-card";

    const afterHtml = bullet.hasPlaceholderMetric
      ? highlightPlaceholder(escapeHtml(bullet.rewritten))
      : escapeHtml(bullet.rewritten);

    card.innerHTML = `
      <div class="rewrite-grid">
        <div class="rewrite-half">
          <span class="rewrite-label muted">BEFORE</span>
          <p class="rewrite-before-text">${escapeHtml(bullet.original)}</p>
        </div>
        <div class="rewrite-half">
          <div class="row-between">
            <span class="rewrite-label col-matched">AFTER</span>
            <button class="copy-btn">COPY</button>
          </div>
          <p class="rewrite-after-text">${afterHtml}</p>
        </div>
      </div>
      <div class="rewrite-footer">
        ${bullet.hasPlaceholderMetric ? '<span class="placeholder-tag">FILL-IN NEEDED</span>' : ""}${escapeHtml(bullet.changeNotes)}
      </div>
    `;

    card.querySelector(".copy-btn").addEventListener("click", async (e) => {
      await navigator.clipboard.writeText(bullet.rewritten);
      e.target.textContent = "COPIED ✓";
      setTimeout(() => (e.target.textContent = "COPY"), 1500);
    });

    listEl.appendChild(card);
  });

  document.getElementById("copy-all-btn").onclick = async () => {
    const combined = rewrites.map((r) => `- ${r.rewritten}`).join("\n");
    await navigator.clipboard.writeText(combined);
  };
}

function highlightPlaceholder(text) {
  return text.replace(
    /(\[Insert metric:[^\]]*\])/g,
    '<mark class="metric-highlight">$1</mark>'
  );
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ---- Feature: ATS X-Ray mode ----
function toggleXray(activate) {
  xrayActive = activate;
  xrayToggleBtn.textContent = activate ? "X-RAY VIEW: ON" : "X-RAY VIEW: OFF";
  xrayToggleBtn.classList.toggle("active", activate);

  if (!activate) {
    xrayOverlay.classList.add("hidden");
    return;
  }

  if (!lastAnalysis) return;

  xrayOverlay.innerHTML = buildXrayHtml(
    resumeInput.value,
    lastAnalysis.matchedKeywords,
    lastAnalysis.weaklyEmphasizedKeywords,
    lastAnalysis.missingKeywords
  );
  xrayOverlay.classList.remove("hidden");
}

function buildXrayHtml(text, matched, weak, missing) {
  const escaped = escapeHtml(text);

  // Map lowercase keyword -> css class, longest keywords first so multi-word
  // phrases match before their shorter substrings do.
  const entries = [
    ...matched.map((k) => ({ keyword: k.keyword, cls: "xray-hit-matched" })),
    ...weak.map((k) => ({ keyword: k.keyword, cls: "xray-hit-weak" })),
  ]
    .filter((e) => e.keyword && e.keyword.trim().length > 0)
    .sort((a, b) => b.keyword.length - a.keyword.length);

  const lookup = new Map();
  entries.forEach((e) => {
    if (!lookup.has(e.keyword.toLowerCase())) lookup.set(e.keyword.toLowerCase(), e.cls);
  });

  let highlighted = escaped;
  if (entries.length > 0) {
    const pattern = entries
      .map((e) => e.keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
      .join("|");
    const regex = new RegExp(`(${pattern})`, "gi");
    highlighted = escaped.replace(regex, (match) => {
      const cls = lookup.get(match.toLowerCase()) || "xray-hit-matched";
      return `<span class="${cls}">${match}</span>`;
    });
  }

  const missingHighImportance = missing.filter((k) => k.importance === "high").map((k) => k.keyword);
  const missingNote =
    missingHighImportance.length > 0
      ? `<div class="xray-missing-note">NOT DETECTED IN THIS DOCUMENT (high priority): ${missingHighImportance
          .map(escapeHtml)
          .join(", ")}</div>`
      : "";

  const legend = `
    <div class="xray-legend">
      <span><span class="dot" style="background:var(--matched)"></span>matched keyword</span>
      <span><span class="dot" style="background:var(--weak)"></span>weakly emphasized</span>
      <span><span class="dot" style="background:#3a423a"></span>not recognized as a keyword</span>
    </div>
  `;

  return `${legend}<span class="xray-dim">${highlighted}</span>${missingNote}`;
}

// ---- Feature: apply rewrites + rescan, with score delta ----
async function applyRewritesAndRescan() {
  if (lastRewrites.length === 0) return;

  let updatedText = resumeInput.value;
  let appliedCount = 0;

  lastRewrites.forEach((bullet) => {
    const original = bullet.original.trim();
    if (original && updatedText.includes(original)) {
      updatedText = updatedText.replace(original, bullet.rewritten.trim());
      appliedCount++;
    }
  });

  resumeInput.value = updatedText;
  resumeCount.textContent = `${updatedText.length.toLocaleString()} chars`;

  if (appliedCount < lastRewrites.length) {
    console.warn(
      `Applied ${appliedCount}/${lastRewrites.length} rewrites — some original bullet text didn't match exactly (likely due to formatting differences) and were left unchanged.`
    );
  }

  await runScan({ showDelta: true });

  // If the PDF preview is already open, keep it in sync with the latest resume text.
  if (!pdfSection.classList.contains("hidden")) {
    await generatePdfPreview();
  }
}

// ---- Feature: live PDF preview ----
async function generatePdfPreview() {
  const resumeMarkdown = resumeInput.value.trim();
  if (!resumeMarkdown) return;

  pdfBtn.disabled = true;
  pdfBtn.textContent = "GENERATING…";

  try {
    const res = await fetch("/api/export-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resumeMarkdown }),
    });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `PDF generation failed (${res.status})`);
    }
    const blob = await res.blob();
    if (currentPdfUrl) URL.revokeObjectURL(currentPdfUrl);
    currentPdfUrl = URL.createObjectURL(blob);
    pdfFrame.src = currentPdfUrl;
    pdfDownloadLink.href = currentPdfUrl;
    pdfSection.classList.remove("hidden");
    pdfSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    alert(`PDF preview failed: ${err.message}`);
    console.error(err);
  } finally {
    pdfBtn.disabled = false;
    pdfBtn.textContent = "GENERATE PDF";
  }
}