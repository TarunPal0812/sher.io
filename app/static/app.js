import { api, copy, startCountdown } from "/static/common.js";

const $ = (id) => document.getElementById(id);
let mode = "text";
let stopTimer = null;

const tabs = document.querySelectorAll('[role="tab"]');
tabs.forEach((tab) => tab.addEventListener("click", () => setMode(tab.dataset.mode)));

function setMode(next) {
  mode = next;
  tabs.forEach((t) => t.setAttribute("aria-selected", String(t.dataset.mode === mode)));
  $("text-pane").classList.toggle("hidden", mode !== "text");
  $("file-pane").classList.toggle("hidden", mode !== "file");
  $("error").textContent = "";
}

const fileInput = $("file");
const drop = $("drop");
fileInput.addEventListener("change", showFileName);
["dragover", "dragenter"].forEach((e) => drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((e) => drop.addEventListener(e, () => drop.classList.remove("over")));
drop.addEventListener("drop", (ev) => {
  ev.preventDefault();
  if (ev.dataTransfer.files.length) { fileInput.files = ev.dataTransfer.files; showFileName(); }
});
function showFileName() {
  $("drop-text").textContent = fileInput.files.length ? fileInput.files[0].name : "Choose a file or drop it here";
}

$("create-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const error = $("error");
  const submit = $("submit");
  error.textContent = "";
  const ttl = Number(new FormData(ev.target).get("ttl"));
  submit.disabled = true;
  try {
    let result;
    if (mode === "text") {
      const content = $("text").value;
      if (!content.trim()) throw new Error("Enter some text to share.");
      result = await api("/api/v1/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, ttl_minutes: ttl }),
      });
    } else {
      if (!fileInput.files.length) throw new Error("Choose a file to share.");
      const body = new FormData();
      body.append("file", fileInput.files[0]);
      body.append("ttl_minutes", String(ttl));
      result = await api("/api/v1/file", { method: "POST", body });
    }
    showResult(result);
  } catch (e) {
    error.textContent = e.message;
  } finally {
    submit.disabled = false;
  }
});

function showResult(r) {
  $("create-panel").classList.add("hidden");
  $("result-panel").classList.remove("hidden");
  $("ticket-id").textContent = r.id;
  $("ticket-url").textContent = r.url;
  $("copy").onclick = (ev) => copy(r.url, ev.currentTarget);
  stopTimer = startCountdown($("timer"), r.ttl_seconds, r.ttl_seconds, () => {
    $("ticket-url").textContent = "This link has expired.";
  });
}

$("again").addEventListener("click", () => {
  if (stopTimer) stopTimer();
  $("text").value = "";
  fileInput.value = "";
  showFileName();
  $("result-panel").classList.add("hidden");
  $("create-panel").classList.remove("hidden");
});
