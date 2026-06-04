// ── DOM refs ────────────────────────────────────────────────────────────────
const generatorsEl        = document.getElementById("generators");
const modelEl             = document.getElementById("embedding_model");
const openaiWrap          = document.getElementById("openai_wrap");
const codestralWrap       = document.getElementById("codestral_wrap");
const runBtn              = document.getElementById("run_btn");
const inspectBtn          = document.getElementById("inspect_btn");
const downloadLink        = document.getElementById("download_link");
const downloadWrap        = document.getElementById("download_wrap");
const modelNoteEl         = document.getElementById("model_note");
const inspectStatusEl     = document.getElementById("inspect_status");
const findingsPanel       = document.getElementById("findings_panel");
const findingsChat        = document.getElementById("findings_chat");
const findingsSpinner     = document.getElementById("findings_spinner");
const findingsDetails     = document.getElementById("findings_details");
const browseSutBtn        = document.getElementById("browse_sut_btn");
const browseGrammarBtn    = document.getElementById("browse_grammar_btn");
const selectAllGeneratorsBtn = document.getElementById("select_all_generators");
const selectAllGeneratorsLabel = document.getElementById("select_all_generators_label");
const genAutoNote         = document.getElementById("gen_auto_note");
const genAutoNoteText     = document.getElementById("gen_auto_note_text");
const runErrorEl          = document.getElementById("run_error");
const selectedGenInfoEl   = document.getElementById("selected_gen_info");
const pipelineProgress    = document.getElementById("pipeline_progress");
const numInputsSlider     = document.getElementById("num_inputs_slider");
const budgetSlider        = document.getElementById("budget_slider");
const numInputsEl         = document.getElementById("num_inputs");
const budgetEl            = document.getElementById("budget");
const candidateEstimateEl = document.getElementById("candidate_estimate");
const finalEstimateEl     = document.getElementById("final_estimate");
const runValidationEl     = document.getElementById("run_validation");
const summaryGeneratorsEl = document.getElementById("summary_generators");
const summaryModelEl      = document.getElementById("summary_model");
const summaryCandidatesEl = document.getElementById("summary_candidates");
const summaryFinalEl      = document.getElementById("summary_final");
const summaryCandidatesFlowEl = document.getElementById("summary_candidates_flow");
const summaryFinalFlowEl  = document.getElementById("summary_final_flow");
const summaryModeEl       = document.getElementById("summary_mode");
const summaryCommandEl    = document.getElementById("summary_command");
const summaryWorkingDirectoryEl = document.getElementById("summary_working_directory");
const summaryInputModeEl  = document.getElementById("summary_input_mode");
const summaryExportEl     = document.getElementById("summary_export");
const readyToRunEl        = document.getElementById("ready_to_run");
const exportPrioritizedEl = document.getElementById("export_prioritized_inputs");
const exportFormatEl      = document.getElementById("export_format");

// ── State ───────────────────────────────────────────────────────────────────
let runId           = null;
let timer           = null;
let currentManifest = null;
let nativeBrowseEnabled = true;
let currentStep     = 1;

const CONTEXT_STEPS = {
  1: {
    title: "What happens next?",
    items: [
      ["Detect execution setup", "Find build, run, and input execution commands."],
      ["Validate grammar & tools", "Check grammar availability and required generators."],
      ["Prepare configuration", "Suggest compatible generators, embeddings, and run settings."],
    ],
  },
  2: {
    title: "Configure the run",
    items: [
      ["Analysis complete", "Review the detected project and grammar findings."],
      ["Choose generators", "Select compatible generator families or let SpreadEx decide."],
      ["Pick embedding model", "Use a local or API-backed model for diversity mapping."],
    ],
  },
  3: {
    title: "Run and export",
    items: [
      ["Confirm execution", "Review the command, working directory, and input mode."],
      ["Smoke test first", "Run a small check before the full generator pipeline."],
      ["Export inputs", "Download the prioritized input bundle when the run completes."],
    ],
  },
};

const GENERATOR_UI = {
  fuzzingbook: {
    icon: "fuzzingbook",
    logo: "/ui/assets/fuzzing_book_icon.png",
    description: "Probabilistic fuzzing from grammar rules.",
  },
  fandango: {
    icon: "fandango",
    logo: "/ui/assets/fandango_logo.png",
    description: "Constraint-driven generation with evolutionary search.",
    tooltip: "Fandango combines grammars with constraints and uses evolutionary search to produce high-quality valid inputs.",
  },
  isla: {
    icon: "isla",
    logo: "/ui/assets/isla_logo.png",
    description: "Constraint-solving for valid structured inputs.",
    tooltip: "ISLa is a grammar-aware string constraint solver that generates inputs satisfying grammar and semantic constraints.",
  },
  llm: {
    icon: "llm",
    logo: "/ui/assets/llm_icon.png",
    description: "Prompt-guided input generation using LLM knowledge.",
  },
  clusgram: {
    icon: "clusgram",
    logo: "/ui/assets/clusgram_icon.png",
    label: "ClusGram",
    description: "Rule-coverage-driven generation for diverse inputs.",
  },
};

// ── Grammar tabs ─────────────────────────────────────────────────────────────
document.querySelectorAll(".tab-bar .tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    const bar = btn.closest(".tab-bar");
    bar.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    const target = btn.dataset.tab;
    ["grammar_file_tab", "grammar_paste_tab", "grammar_later_tab"].forEach((id) => {
      document.getElementById(id).classList.toggle("hidden", id !== `${target}_tab`);
    });
    updateApiVisibility();
  });
});

// ── Step navigation ──────────────────────────────────────────────────────────
function showStep(n) {
  const direction = n >= currentStep ? "forward" : "back";
  currentStep = n;

  document.querySelectorAll(".step-card").forEach((el, i) => {
    const isActive = i + 1 === n;
    el.classList.toggle("hidden", !isActive);
    el.classList.remove("slide-in-right", "slide-in-left");
    if (isActive) {
      void el.offsetWidth;
      el.classList.add(direction === "back" ? "slide-in-left" : "slide-in-right");
    }
  });
  for (let i = 1; i <= 3; i++) {
    const dot = document.getElementById(`dot${i}`);
    if (dot) dot.classList.toggle("active", i <= n);
    const line = document.getElementById(`line${i}`);
    if (line) line.classList.toggle("active", i < n);
  }
  updateContextPanel(n);
  updateFindingsVisibility(n);
  if (n === 3) updateRunReview();
}

function updateContextPanel(step) {
  const copy = CONTEXT_STEPS[step] || CONTEXT_STEPS[1];
  const title = document.getElementById("context_title");
  if (title) title.textContent = copy.title;

  copy.items.forEach(([itemTitle, itemDesc], index) => {
    const idx = index + 1;
    const item = document.getElementById(`context_item_${idx}`);
    const heading = document.getElementById(`context_item_${idx}_title`);
    const desc = document.getElementById(`context_item_${idx}_desc`);
    if (heading) heading.textContent = itemTitle;
    if (desc) desc.textContent = itemDesc;
    if (item) {
      item.classList.toggle("done", idx < step);
      item.classList.toggle("active", idx === step);
    }
  });
}

function updateFindingsVisibility(step) {
  if (!currentManifest || !findingsPanel) return;
  findingsPanel.classList.remove("hidden");
  if (findingsDetails) findingsDetails.open = step === 2;
}

// ── Chat bubbles ─────────────────────────────────────────────────────────────
function addChatBubble(text, type = "info") {
  const div = document.createElement("div");
  div.className = `chat-bubble ${type}`;
  div.textContent = text;
  findingsChat.appendChild(div);
}

// ── Findings panel ────────────────────────────────────────────────────────────
function renderFindingsPanel(manifest) {
  findingsChat.innerHTML = "";
  findingsSpinner.classList.add("hidden");
  findingsPanel.classList.remove("hidden");
  if (findingsDetails) findingsDetails.open = true;

  const profile = manifest.sut_analysis || manifest.project_profile || {};
  const grammar = manifest.grammar_analysis || manifest.grammar_validation || {};
  const deps    = manifest.dependency_readiness || {};

  // Summary bubble
  const lang    = profile.language || "unknown language";
  const build   = profile.build_system || "no build system detected";
  const gfmt    = grammar.original_format;
  const gDesc   = gfmt && gfmt !== "unknown" && gfmt !== "none"
    ? `found a ${gfmt} grammar`
    : "no grammar detected";
  const depDesc = deps.status === "ready"
    ? "All required tools appear to be installed."
    : "Some tools may need installing — see details below.";
  addChatBubble(
    `Here's what I found: your project uses ${lang} with ${build}. I ${gDesc}. ${depDesc}`,
    "info"
  );

  // ── Language / build detection card ─────────────────────────────────────────
  const confPct   = Math.round((profile.confidence || 0) * 100);
  const confLabel = confPct >= 80 ? "high confidence" : confPct >= 50 ? "moderate confidence" : "low confidence";
  const buildStr  = (profile.build_system && profile.build_system !== "unknown")
    ? `${profile.build_system} build`
    : "no recognized build system";
  const runTpl    = profile.run_command_template || "not detected";
  addChatBubble(
    `Detected: ${lang} / ${buildStr} (${confPct}% — ${confLabel}). Run template: ${runTpl}.`,
    "lang"
  );

  if (profile.entry_point) {
    addChatBubble(`Entry point: ${profile.entry_point}`, "lang");
  }

  const candidates = profile.run_command_candidates || [];
  if (candidates.length > 1) {
    addChatBubble(
      `${candidates.length} run command candidates found. The most likely was auto-selected — review in Step 3 → Advanced settings if needed.`,
      "info"
    );
  }

  if (confPct < 50) {
    addChatBubble(
      "Run command detection confidence is low. Open 'Advanced execution settings' in Step 3 and verify the command before running.",
      "warn"
    );
    const adv = document.getElementById("advanced_run");
    if (adv) adv.open = true;
  }

  // Profile warnings from inspector
  (profile.warnings || []).forEach((w) => addChatBubble(w, "warn"));

  // ── Run command missing ───────────────────────────────────────────────────────
  if (!profile.run_command_template) {
    addChatBubble(
      "I couldn't auto-detect a run command for this project. Please open 'Advanced execution settings' in Step 3 and fill it in before running.",
      "warn"
    );
    const adv = document.getElementById("advanced_run");
    if (adv) adv.open = true;
  }

  // ── Grammar adapter confidence ────────────────────────────────────────────────
  if (gfmt && gfmt !== "unknown" && gfmt !== "none") {
    const gConf    = grammar.confidence || 0;
    const gConfPct = Math.round(gConf * 100);
    const gNote    = (grammar.warnings && grammar.warnings.length)
      ? `Adapter note: ${grammar.warnings[0]}`
      : "Adaptation succeeded.";
    addChatBubble(
      `Grammar format: ${gfmt} (${gConfPct}% confidence). ${gNote}`,
      gConf < 0.5 ? "warn" : "info"
    );
  }

  // ── No grammar ────────────────────────────────────────────────────────────────
  if (!gfmt || gfmt === "unknown" || gfmt === "none") {
    addChatBubble(
      "No grammar was provided — SpreadEx will use grammar-free generators. " +
      "Add a grammar file to unlock ISLa and Fandango for more structured inputs.",
      "info"
    );
  }

  // ── Missing deps ──────────────────────────────────────────────────────────────
  if (deps.needs && deps.needs.length) {
    addChatBubble(
      `Some tools aren't installed: ${deps.needs.join(", ")}. SpreadEx will skip generators that depend on them.`,
      "warn"
    );
  }

  // Populate run command fields in Step 3
  const rcEl = document.getElementById("run_command_template");
  const wdEl = document.getElementById("working_directory");
  const imEl = document.getElementById("input_execution_mode");
  if (rcEl) rcEl.value = profile.run_command_template || "";
  if (wdEl) wdEl.value = profile.working_directory || "";
  if (imEl) imEl.value = profile.input_execution_mode || "file_arg";

  updateGeneratorCompatibility(grammar);
}

// ── Options loading ───────────────────────────────────────────────────────────
async function loadOptions() {
  const res  = await fetch("/api/options");
  const data = await res.json();
  nativeBrowseEnabled = !!data.native_browse_enabled;
  if (browseSutBtn)     browseSutBtn.disabled    = !nativeBrowseEnabled;
  if (browseGrammarBtn) browseGrammarBtn.disabled = !nativeBrowseEnabled;

  const families = data.generator_families || {};
  data.generators.forEach((g) => {
    generatorsEl.appendChild(createGeneratorCard(g, {
      label: families[g]?.label || GENERATOR_UI[g]?.label || g,
      description: GENERATOR_UI[g]?.description || families[g]?.description || "",
      selectable: true,
    }));
  });
  generatorsEl.appendChild(createGeneratorCard("clusgram", {
    label: GENERATOR_UI.clusgram.label,
    description: GENERATOR_UI.clusgram.description,
    selectable: false,
    upcoming: true,
  }));

  data.models.forEach((m) => {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    modelEl.appendChild(opt);
  });
  modelEl.value = "unixcoder";
  updateApiVisibility();
  onGeneratorChange();
}

function createGeneratorCard(g, options) {
    const card = document.createElement("label");
    card.className = "gen-card";
    card.dataset.gen = g;
    if (options.upcoming) card.classList.add("upcoming");
    if (GENERATOR_UI[g]?.tooltip) card.title = GENERATOR_UI[g].tooltip;
    const cb = document.createElement("input");
    cb.type  = "checkbox";
    cb.value = g;
    cb.disabled = !options.selectable;
    if (options.selectable) {
      cb.addEventListener("change", () => {
        card.classList.toggle("checked", cb.checked);
        onGeneratorChange();
      });
    }
    const fakeCheck = document.createElement("span");
    fakeCheck.className = "gen-checkmark";
    fakeCheck.setAttribute("aria-hidden", "true");
    if (options.upcoming) fakeCheck.classList.add("hidden");
    const icon = document.createElement("span");
    icon.className = `gen-icon gen-icon-${GENERATOR_UI[g]?.icon || "default"}`;
    icon.setAttribute("aria-hidden", "true");
    if (GENERATOR_UI[g]?.logo) {
      const img = document.createElement("img");
      img.src = GENERATOR_UI[g].logo;
      img.alt = "";
      img.loading = "lazy";
      icon.appendChild(img);
    }
    const copy = document.createElement("span");
    copy.className = "gen-copy";
    const name = document.createElement("span");
    name.className = "gen-name";
    name.textContent = options.label;
    const desc = document.createElement("span");
    desc.className = "gen-desc";
    desc.textContent = options.description || "";
    const badge = document.createElement("span");
    badge.className = options.upcoming ? "gen-coming-soon" : "gen-recommended hidden";
    badge.textContent = options.upcoming ? "Coming soon" : "Recommended";
    copy.appendChild(name);
    if (desc.textContent) copy.appendChild(desc);
    copy.appendChild(badge);
    card.appendChild(cb);
    card.appendChild(fakeCheck);
    card.appendChild(icon);
    card.appendChild(copy);
    return card;
}

function updateGeneratorCompatibility(report) {
  const status = report?.generator_status || {};
  generatorsEl.querySelectorAll(".gen-card").forEach((card) => {
    if (card.classList.contains("upcoming")) return;
    const cb   = card.querySelector("input");
    const badge = card.querySelector(".gen-recommended");
    const info = status[cb.value] || { compatible: false, reason: "Not validated." };
    cb.disabled = !info.compatible;
    cb.checked  = cb.checked && !!info.compatible;
    card.classList.toggle("checked",   cb.checked);
    card.classList.toggle("disabled",  cb.disabled);
    card.classList.toggle("recommended", !!info.compatible);
    if (badge) badge.classList.toggle("hidden", !info.compatible);
    card.title = info.reason || "";
  });
  onGeneratorChange();
  updateApiVisibility();
}

function selectedGenerators() {
  return [...generatorsEl.querySelectorAll("input[type=checkbox]:checked")].map((x) => x.value);
}

function onGeneratorChange() {
  const sel = selectedGenerators();
  if (genAutoNote) {
    genAutoNote.classList.toggle("selected", sel.length > 0);
  }
  if (genAutoNoteText) {
    genAutoNoteText.innerHTML = sel.length > 0
      ? "<strong>Using selected generators only.</strong> Clear the selection if you want SpreadEx to compare all compatible generators automatically."
      : "<strong>Not sure which to pick?</strong> Leave all unselected and SpreadEx will run all compatible generators and choose the best one for your project.";
  }
  updateSelectAllButton();
  updateApiVisibility();
  updateRunReview();
}

function compatibleGeneratorCheckboxes() {
  return [...generatorsEl.querySelectorAll(".gen-card input[type=checkbox]:not(:disabled)")];
}

function updateSelectAllButton() {
  if (!selectAllGeneratorsBtn) return;
  const boxes = compatibleGeneratorCheckboxes();
  const allChecked = boxes.length > 0 && boxes.every((cb) => cb.checked);
  selectAllGeneratorsBtn.classList.toggle("active", allChecked);
  selectAllGeneratorsBtn.disabled = boxes.length === 0;
  if (selectAllGeneratorsLabel) {
    selectAllGeneratorsLabel.textContent = allChecked ? "Clear all" : "Select all";
  }
}

function updateApiVisibility() {
  const model = modelEl.value;
  const needsOpenai = model === "openai" || selectedGenerators().includes("llm");
  openaiWrap.classList.toggle("hidden", !needsOpenai);
  codestralWrap.classList.toggle("hidden", model !== "codestral");
  const notes = {
    unixcoder:      "UnixCoder runs locally — no API key needed.",
    graph_codebert: "GraphCodeBERT runs locally — requires local package setup.",
    qwen3:          "Qwen3 runs locally — requires local package setup.",
    openai:         "OpenAI embeddings — API key used only for this session.",
    codestral:      "Codestral (Mistral) embeddings — Mistral API key required.",
  };
  modelNoteEl.textContent = notes[model] || "";
  updateRunReview();
}

modelEl.addEventListener("change", updateApiVisibility);

selectAllGeneratorsBtn?.addEventListener("click", () => {
  const boxes = compatibleGeneratorCheckboxes();
  const shouldSelect = !boxes.every((cb) => cb.checked);
  boxes.forEach((cb) => {
    cb.checked = shouldSelect;
    cb.closest(".gen-card")?.classList.toggle("checked", shouldSelect);
  });
  onGeneratorChange();
});

function selectedOrCompatibleGeneratorCount() {
  const selected = selectedGenerators();
  return selected.length || compatibleGeneratorCheckboxes().length || 1;
}

function selectedOrCompatibleGeneratorNames() {
  const selected = selectedGenerators();
  if (!selected.length) return "All compatible generators";
  return selected.map((gen) => {
    const card = generatorsEl.querySelector(`.gen-card[data-gen="${gen}"]`);
    return card?.querySelector(".gen-name")?.textContent || gen;
  }).join(", ");
}

function selectedOrCompatibleGeneratorNameList() {
  const selected = selectedGenerators();
  if (!selected.length) return ["All compatible generators"];
  return selected.map((gen) => {
    const card = generatorsEl.querySelector(`.gen-card[data-gen="${gen}"]`);
    return card?.querySelector(".gen-name")?.textContent || gen;
  });
}

function modelDisplayName(model) {
  const names = {
    unixcoder: "UniXCoder",
    graph_codebert: "GraphCodeBERT",
    qwen3: "Qwen3",
    openai: "OpenAI",
    codestral: "Codestral",
  };
  return names[model] || model;
}

function modeDisplayName(mode) {
  const names = {
    file_arg: "File Argument",
    stdin: "Standard Input",
  };
  return names[mode] || mode;
}

function renderPills(container, values, variant = "green", icon = "") {
  if (!container) return;
  container.innerHTML = "";
  values.forEach((value) => {
    const pill = document.createElement("span");
    pill.className = `summary-pill ${variant}`;
    pill.textContent = icon ? `${icon} ${value}` : value;
    container.appendChild(pill);
  });
}

function syncBudgetControls(source) {
  if (!numInputsEl || !budgetEl || !numInputsSlider || !budgetSlider) return;

  let inputs = Number(numInputsEl.value) || 1;
  if (source === "inputs_slider") inputs = Number(numInputsSlider.value);
  inputs = Math.max(1, Math.min(500, inputs));
  numInputsEl.value = String(inputs);
  numInputsSlider.value = String(Math.max(10, Math.min(500, inputs)));

  const candidates = selectedOrCompatibleGeneratorCount() * inputs;
  budgetSlider.max = String(Math.max(1, candidates));

  let budget = Number(budgetEl.value) || 1;
  if (source === "budget_slider") budget = Number(budgetSlider.value);
  budget = Math.max(1, budget);
  if (source !== "budget_input") {
    budget = Math.min(candidates, budget);
  }
  budgetEl.value = String(budget);
  budgetSlider.value = String(Math.min(candidates, budget));
}

function updateRunReview(source = "") {
  if (!numInputsEl || !budgetEl) return;
  syncBudgetControls(source);

  const generatorCount = selectedOrCompatibleGeneratorCount();
  const inputs = Number(numInputsEl.value) || 1;
  const candidates = generatorCount * inputs;
  const budget = Number(budgetEl.value) || 1;
  const mode = document.getElementById("input_execution_mode")?.value || "file_arg";
  const commandConfirmed = !!document.getElementById("command_confirmed")?.checked;
  const command = document.getElementById("run_command_template")?.value.trim() || "";
  const errors = [];

  if (inputs < 1) errors.push("Generation budget must be at least 1.");
  if (budget > candidates) errors.push("Final test suite size cannot exceed estimated candidates.");
  if (budget < 1) errors.push("Final test suite size must be at least 1.");
  if (!commandConfirmed) errors.push("Confirm the command is safe before starting the run.");
  if (mode === "file_arg" && command && !command.includes("{input_file}")) {
    errors.push("File-argument mode requires {input_file} in the run command template.");
  }

  if (candidateEstimateEl) {
    candidateEstimateEl.textContent = `Estimated candidates: ${generatorCount} generators × ${inputs} inputs = ${candidates} inputs`;
  }
  if (finalEstimateEl) {
    finalEstimateEl.textContent = `Keeping ${budget} of ${candidates} candidate inputs`;
  }
  renderPills(summaryGeneratorsEl, selectedOrCompatibleGeneratorNameList(), "green");
  renderPills(summaryModelEl, [modelDisplayName(modelEl.value || "unixcoder")], "neutral");
  if (summaryCandidatesEl) summaryCandidatesEl.textContent = String(candidates);
  if (summaryCandidatesFlowEl) summaryCandidatesFlowEl.textContent = String(candidates);
  if (summaryFinalEl) summaryFinalEl.textContent = String(budget);
  if (summaryFinalFlowEl) summaryFinalFlowEl.textContent = String(budget);
  renderPills(summaryModeEl, [modeDisplayName(mode)], "gray", "⚙");
  if (summaryCommandEl) {
    summaryCommandEl.textContent = command || "Auto-detected or configured below";
  }
  if (summaryWorkingDirectoryEl) {
    summaryWorkingDirectoryEl.textContent = document.getElementById("working_directory")?.value.trim() || "Project root";
  }
  if (summaryInputModeEl) {
    summaryInputModeEl.textContent = modeDisplayName(mode);
  }
  if (summaryExportEl) {
    const exportText = exportPrioritizedEl?.checked
      ? `${exportFormatEl?.value || "Input Files + Metadata CSV"}`
      : "Saved internally only";
    renderPills(summaryExportEl, [exportText], "gray", "📄");
  }
  if (readyToRunEl) {
    readyToRunEl.classList.toggle("blocked", errors.length > 0);
    const title = readyToRunEl.querySelector("strong");
    const body = readyToRunEl.querySelector("p");
    if (title) title.textContent = errors.length ? "Needs Review" : "Ready to Run";
    if (body) {
      body.textContent = errors.length
        ? "Resolve the highlighted configuration issue before starting the SpreadEx run."
        : `SpreadEx will generate ${candidates} candidate inputs, prioritize the best ${budget} using Cluster Coverage (CC), and export the final test suite.`;
    }
  }

  if (runValidationEl) {
    runValidationEl.textContent = errors.join(" ");
    runValidationEl.classList.toggle("hidden", errors.length === 0);
  }
  if (runBtn && !timer) {
    runBtn.disabled = errors.length > 0;
  }
}

numInputsSlider?.addEventListener("input", () => updateRunReview("inputs_slider"));
budgetSlider?.addEventListener("input", () => updateRunReview("budget_slider"));
numInputsEl?.addEventListener("input", () => updateRunReview("inputs_input"));
budgetEl?.addEventListener("input", () => updateRunReview("budget_input"));
exportPrioritizedEl?.addEventListener("change", () => updateRunReview());
exportFormatEl?.addEventListener("change", () => updateRunReview());
["run_command_template", "working_directory", "input_execution_mode", "command_confirmed"].forEach((id) => {
  const el = document.getElementById(id);
  el?.addEventListener("input", () => updateRunReview());
  el?.addEventListener("change", () => updateRunReview());
});

// ── Step 1 validation ────────────────────────────────────────────────────────
function clearStep1Errors() {
  ["sut_location", "grammar_location", "grammar_text"].forEach((id) => {
    document.getElementById(id)?.classList.remove("input-invalid");
    const e = document.getElementById(id + "_error");
    if (e) { e.textContent = ""; e.hidden = true; }
  });
}

function setFieldError(inputId, msg) {
  document.getElementById(inputId)?.classList.add("input-invalid");
  const e = document.getElementById(inputId + "_error");
  if (e) { e.textContent = msg; e.hidden = false; }
}

function validateStep1() {
  clearStep1Errors();
  let ok = true;

  const sut = document.getElementById("sut_location")?.value.trim();
  if (!sut) {
    setFieldError("sut_location", "Project path is required. Enter a local folder path or a GitHub URL.");
    ok = false;
  }

  const activeTab = document.querySelector(".tab-bar .tab.active")?.dataset.tab;
  if (activeTab === "grammar_file") {
    const loc = document.getElementById("grammar_location")?.value.trim();
    if (!loc) {
      setFieldError("grammar_location", "Enter a grammar file path or URL, or switch to Paste or Infer mode.");
      ok = false;
    }
  } else if (activeTab === "grammar_paste") {
    const txt = document.getElementById("grammar_text")?.value.trim();
    if (!txt) {
      setFieldError("grammar_text", "Paste your grammar text above, or switch to Upload or Infer mode.");
      ok = false;
    }
  }

  return ok;
}

// ── Constraint chips ──────────────────────────────────────────────────────────
document.querySelectorAll(".chip-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const el = document.getElementById("llm_constraints");
    if (!el) return;
    const chip = btn.textContent.trim();
    const current = el.value.trim();
    if (!current.includes(chip)) {
      el.value = current ? `${current}; ${chip}` : chip;
    }
  });
});

// ── Auto-derive subject from path ─────────────────────────────────────────────
function deriveSubject(sutLocation) {
  if (!sutLocation) return "default";
  const clean = sutLocation.replace(/\/+$/, "");
  const part  = clean.split(/[/\\]/).pop() || "default";
  return part.toLowerCase().replace(/[^a-z0-9_-]/g, "-").slice(0, 50) || "default";
}

// ── Inspect ────────────────────────────────────────────────────────────────────
async function inspectProject() {
  inspectStatusEl.textContent = "Analyzing project…";
  inspectStatusEl.className = "status-inline";
  findingsPanel.classList.add("hidden");
  findingsChat.innerHTML = "";
  findingsSpinner.classList.remove("hidden");
  findingsPanel.classList.remove("hidden");
  if (findingsDetails) findingsDetails.open = true;

  const sutLocation = document.getElementById("sut_location").value.trim();
  const activeTab   = document.querySelector(".tab-bar .tab.active")?.dataset.tab;
  const mineLater   = activeTab === "grammar_later";

  document.getElementById("subject").value = deriveSubject(sutLocation);

  const body = {
    subject:           document.getElementById("subject").value,
    sut_location:      sutLocation,
    grammar_location:  document.getElementById("grammar_location").value.trim() || null,
    grammar_text:      document.getElementById("grammar_text").value.trim() || null,
    grammar_mine_later: mineLater,
    llm_constraints:   document.getElementById("llm_constraints").value.trim() || null,
  };

  const res = await fetch("/api/inspect", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Inspection failed.");
  }

  currentManifest = await res.json();
  runId = currentManifest.run_id;
  inspectStatusEl.textContent = "Analysis complete.";
  inspectStatusEl.className = "status-inline ok";
  renderFindingsPanel(currentManifest);
  showStep(2);
}

// ── Browse helpers ─────────────────────────────────────────────────────────────
async function pickSutPath(initial) {
  const res = await fetch("/browse/sut", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ initial }),
  });
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Browse failed."); }
  return res.json();
}

async function pickGrammarPath(initial) {
  const res = await fetch("/browse/grammar", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ initial }),
  });
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Browse failed."); }
  return res.json();
}

// ── Create run ─────────────────────────────────────────────────────────────────
async function createRun() {
  if (!currentManifest?.run_id) throw new Error("Analyze the project first.");
  updateRunReview();
  if (runValidationEl && !runValidationEl.classList.contains("hidden")) {
    throw new Error(runValidationEl.textContent || "Fix the run configuration before starting.");
  }

  const gens = selectedGenerators();
  const body = {
    run_id:                  currentManifest.run_id,
    generators:              gens,
    auto_select_generator:   gens.length === 0,
    embedding_model:         modelEl.value,
    prioritization_budget:   Number(document.getElementById("budget").value),
    num_inputs_per_generator: Number(document.getElementById("num_inputs").value),
    run_command_template:    document.getElementById("run_command_template").value.trim(),
    input_execution_mode:    document.getElementById("input_execution_mode").value,
    working_directory:       document.getElementById("working_directory").value.trim() || null,
    command_confirmed:       document.getElementById("command_confirmed").checked,
    openai_api_key:          document.getElementById("openai_api_key").value || null,
    codestral_api_key:       document.getElementById("codestral_api_key").value || null,
  };

  const res = await fetch("/api/runs", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  });
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Run failed to start."); }
  return res.json();
}

// ── Pipeline stage UI ──────────────────────────────────────────────────────────
const STAGE_MAP = {
  step2_smoke_test:                "stage_smoke",
  step3_generator_execution:       "stage_generate",
  step4_model_embeddings_and_cc:   "stage_embed",
  step5_prioritization_and_export: "stage_prioritize",
};
const STAGE_ORDER = Object.keys(STAGE_MAP);

function updatePipelineUI(step, status) {
  const currentIdx = STAGE_ORDER.indexOf(step);
  STAGE_ORDER.forEach((s, i) => {
    const el = document.getElementById(STAGE_MAP[s]);
    if (!el) return;
    if (i < currentIdx)                                el.dataset.state = "done";
    else if (i === currentIdx && status === "failed")  el.dataset.state = "failed";
    else if (i === currentIdx)                         el.dataset.state = "running";
    else                                               el.dataset.state = "pending";
  });
}

function markAllStagesDone() {
  STAGE_ORDER.forEach((s) => {
    const el = document.getElementById(STAGE_MAP[s]);
    if (el) el.dataset.state = "done";
  });
}

// ── Poll ───────────────────────────────────────────────────────────────────────
async function poll() {
  if (!runId) return;
  const res  = await fetch(`/api/runs/${runId}`);
  const data = await res.json();

  if (STAGE_MAP[data.step]) updatePipelineUI(data.step, data.status);

  if (data.status === "completed") {
    clearInterval(timer); timer = null;
    markAllStagesDone();
    if (data.outputs?.download) {
      downloadLink.href = data.outputs.download;
      downloadWrap.classList.remove("hidden");
      const selGen = data.outputs?.selected_generator || data.outputs?.run_report?.selected_generator;
      if (selGen && selectedGenInfoEl) {
        selectedGenInfoEl.textContent = `Selected generator: ${selGen}`;
      }
    }
    runBtn.disabled = false;
    runBtn.textContent = "Run SpreadEx";
  } else if (data.status === "failed") {
    clearInterval(timer); timer = null;
    if (data.step && STAGE_MAP[data.step]) updatePipelineUI(data.step, "failed");
    runErrorEl.textContent = `Run failed: ${data.error || "unknown error"}`;
    runErrorEl.classList.remove("hidden");
    runBtn.disabled = false;
    runBtn.textContent = "Run SpreadEx";
  }
}

// ── Event listeners ────────────────────────────────────────────────────────────
inspectBtn.addEventListener("click", async () => {
  if (!validateStep1()) return;
  inspectBtn.disabled = true;
  try {
    await inspectProject();
  } catch (e) {
    findingsSpinner.classList.add("hidden");
    addChatBubble(`Analysis failed. Please check the project path or permissions and try again. ${e.message}`, "error");
    findingsPanel.classList.remove("hidden");
    inspectStatusEl.textContent = "Analysis failed. Please check the project path or permissions and try again.";
    inspectStatusEl.className = "status-inline error";
  } finally {
    inspectBtn.disabled = false;
  }
});

document.getElementById("next_to_step3")?.addEventListener("click", () => {
  showStep(3);
});

document.getElementById("back_to_step1")?.addEventListener("click", () => {
  showStep(1);
});

document.getElementById("back_to_step2")?.addEventListener("click", () => {
  showStep(2);
});

runBtn.addEventListener("click", async () => {
  downloadWrap.classList.add("hidden");
  runErrorEl.classList.add("hidden");
  pipelineProgress.classList.remove("hidden");
  STAGE_ORDER.forEach((s) => {
    const el = document.getElementById(STAGE_MAP[s]);
    if (el) el.dataset.state = "pending";
  });
  runBtn.disabled = true;
  runBtn.textContent = "Running SpreadEx…";

  try {
    const created = await createRun();
    runId = created.run_id;
    if (timer) clearInterval(timer);
    timer = setInterval(poll, 1500);
    await poll();
  } catch (e) {
    runErrorEl.textContent = e.message;
    runErrorEl.classList.remove("hidden");
    runBtn.disabled = false;
    runBtn.textContent = "Run SpreadEx";
  }
});

browseSutBtn?.addEventListener("click", async () => {
  const orig = browseSutBtn.innerHTML;
  browseSutBtn.disabled = true;
  browseSutBtn.textContent = "Opening…";
  try {
    const data = await pickSutPath(document.getElementById("sut_location").value.trim());
    if (data.path) document.getElementById("sut_location").value = data.path;
  } catch (_) { /* native browse unavailable */ }
  finally {
    browseSutBtn.disabled = false;
    browseSutBtn.innerHTML = orig;
  }
});

browseGrammarBtn?.addEventListener("click", async () => {
  const orig = browseGrammarBtn.innerHTML;
  browseGrammarBtn.disabled = true;
  browseGrammarBtn.textContent = "Opening…";
  try {
    const data = await pickGrammarPath(
      document.getElementById("grammar_location").value.trim() ||
      document.getElementById("sut_location").value.trim()
    );
    if (data.path) document.getElementById("grammar_location").value = data.path;
  } catch (_) { /* native browse unavailable */ }
  finally {
    browseGrammarBtn.disabled = false;
    browseGrammarBtn.innerHTML = orig;
  }
});

// ── Boot ───────────────────────────────────────────────────────────────────────
updateContextPanel(1);
updateRunReview();
loadOptions().catch((e) => {
  addChatBubble(`Failed to load options: ${e.message}`, "error");
});
