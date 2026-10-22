const SAMPLES = [
  `def average(numbers)
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)

print(average([1, 2, 3])`,
  `import os

def greet(name):
    message = "Hello " + name
    print(mesage)

greet("Sam")`,
  `def add_item(item, items=[]):
    items.append(item)
    return items

print(add_item("a"))
print(add_item("b"))`
];
let sampleIndex = 0;

const $ = (id) => document.getElementById(id);
const states = ["empty", "loading", "error", "diagnostics", "success"];
const editor = $("codeInput");
let currentFixed = "";

function show(...names) {
  states.forEach((state) => $("state-" + state).classList.toggle("hidden", !names.includes(state)));
}

function showError(message) {
  $("errorText").textContent = message;
  show("error");
}

function fillList(id, items) {
  const list = $(id);
  list.textContent = "";
  items.forEach((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    list.appendChild(item);
  });
}

function renderDiagnostics(result) {
  const list = $("diagList");
  list.textContent = "";
  const count = result.diagnostics.length;
  $("diagTitle").textContent = count === 0
    ? "No problems found by the automatic checks"
    : count + (count === 1 ? " problem found" : " problems found");

  result.diagnostics.forEach((diagnostic) => {
    const box = document.createElement("div");
    box.className = "diag" + (diagnostic.category === "Syntax error" ? " syntax" : "");
    const heading = document.createElement("b");
    heading.textContent = diagnostic.category + " (" + diagnostic.rule + ") — "
      + (diagnostic.line ? "line " + diagnostic.line : "line unknown");
    const message = document.createElement("div");
    message.textContent = diagnostic.message;
    box.append(heading, message);
    list.appendChild(box);
  });

  $("diagChecks").textContent = "Checks run: " + result.checks_run.join(", ");
  $("diagNotes").textContent = result.notes.join(" ");
}

function renderFix(data, originalCode) {
  const fix = data.fix;
  const verification = data.verification;
  $("category").textContent = fix.category;
  $("lineInfo").textContent = fix.line ? "Line " + fix.line : "Line unknown";

  const verified = verification.status === "statically_verified";
  const badge = $("verifyBadge");
  badge.textContent = verified ? "Statically verified" : "Suggested (not verified)";
  badge.className = "chip " + (verified ? "verified" : "suggested");

  const saveNote = data.saved_id ? " Saved to your history."
    : data.logged_in ? " Could not save this result to your history."
    : " Log in to save results to your history.";
  $("verifyNote").textContent = verification.note + " (AI model: " + data.model + ")" + saveNote;
  $("rootCause").textContent = fix.root_cause;
  $("beginner").textContent = fix.beginner_explanation;
  $("whyWorks").textContent = fix.why_fix_works;
  $("originalCode").textContent = originalCode;
  $("correctedCode").textContent = fix.corrected_code;
  fillList("changes", fix.changes);
  fillList("prevention", fix.prevention_tips.concat(fix.verification_recommendations));

  currentFixed = fix.corrected_code;
  show("diagnostics", "success");
}

async function analyze() {
  const code = editor.value;
  if (!code.trim()) {
    showError("The editor is empty. Write or paste some Python code first.");
    editor.focus();
    return;
  }
  if (code.length > 50000) {
    showError("Code is too long (limit: 50,000 characters).");
    return;
  }

  const button = $("analyzeBtn");
  button.disabled = true;
  show("loading");
  try {
    const response = await fetch("/api/debug", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content
      },
      body: JSON.stringify({ code, language: "python" })
    });
    const data = await response.json();
    if (!response.ok) {
      showError(data.error || "The server returned an error.");
      return;
    }
    renderDiagnostics(data.analysis);
    renderFix(data, code);
  } catch {
    showError("Could not connect to the app server. Start it with `python wsgi.py`, then refresh and try again.");
  } finally {
    button.disabled = false;
  }
}

async function copyFixed() {
  const message = $("copyMsg");
  try {
    if (!navigator.clipboard) {
      throw new Error("Clipboard access is unavailable in this browser.");
    }
    await navigator.clipboard.writeText(currentFixed);
    message.textContent = "Copied to clipboard.";
  } catch (error) {
    message.textContent = "Could not copy. Select the corrected code and copy it manually.";
  }
  window.setTimeout(() => { message.textContent = ""; }, 3000);
}

function downloadFixed() {
  const blob = new Blob([currentFixed], { type: "text/x-python" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "corrected.py";
  link.click();
  URL.revokeObjectURL(url);
}

function updateGutter() {
  const count = Math.max(12, editor.value.split("\n").length);
  $("editorGutter").textContent = Array.from({ length: count }, (_, index) => index + 1).join("\n");
}

$("analyzeBtn").addEventListener("click", analyze);
$("sampleBtn").addEventListener("click", () => {
  editor.value = SAMPLES[sampleIndex];
  sampleIndex = (sampleIndex + 1) % SAMPLES.length;
  updateGutter();
  editor.focus();
  show("empty");
});
$("clearBtn").addEventListener("click", () => {
  editor.value = "";
  updateGutter();
  editor.focus();
  show("empty");
});
$("copyBtn").addEventListener("click", copyFixed);
$("downloadBtn").addEventListener("click", downloadFixed);
editor.addEventListener("input", updateGutter);
editor.addEventListener("scroll", () => {
  $("editorGutter").scrollTop = editor.scrollTop;
});
editor.addEventListener("keydown", (event) => {
  if (event.key === "Tab") {
    event.preventDefault();
    editor.setRangeText("    ", editor.selectionStart, editor.selectionEnd, "end");
  } else if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    analyze();
  }
});
updateGutter();
