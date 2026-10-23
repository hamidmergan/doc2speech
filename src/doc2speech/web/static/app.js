"use strict";

const $ = (id) => document.getElementById(id);
const fields = {
  voice: $("voice"), language: $("language"), speed: $("speed"), format: $("format"),
  baseUrl: $("base-url"), model: $("model"), apiKey: $("api-key"),
};

let info = { max_chars: 100000, extensions: [] };
let mode = "text";
let chosenFile = null;
let polling = null;
let audioUrl = "";

function show(element, visible) {
  element.hidden = !visible;
}

function fail(message) {
  $("error").textContent = message;
  show($("error"), !!message);
}

async function detail(response, fallback) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
  } catch (e) {
    const text = await response.text().catch(() => "");
    if (text) return text;
  }
  return fallback;
}

function updateCount() {
  const count = $("text").value.length;
  const over = count > info.max_chars;
  $("count").textContent = count.toLocaleString() + " / " + info.max_chars.toLocaleString() + " characters";
  $("count").classList.toggle("over", over);
}

function setMode(next) {
  mode = next;
  $("tab-text").classList.toggle("active", next === "text");
  $("tab-file").classList.toggle("active", next === "file");
  show($("pane-text"), next === "text");
  show($("pane-file"), next === "file");
  fail("");
}

function settings(form) {
  form.append("voice", fields.voice.value);
  form.append("language", fields.language.value);
  form.append("format", fields.format.value);
  form.append("base_url", fields.baseUrl.value);
  form.append("model", fields.model.value);
  form.append("api_key", fields.apiKey.value);
  return form;
}

function busy(running) {
  $("submit").disabled = running;
  $("preview").disabled = running;
  show($("progress"), running);
}

async function load() {
  const response = await fetch("/api/info");
  info = await response.json();
  for (const name of info.formats) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    $("format").append(option);
  }
  fields.format.value = info.format;
  fields.voice.value = info.voice || "";
  fields.language.value = info.language || "";
  fields.speed.value = info.speed === null ? "" : String(info.speed);
  fields.baseUrl.value = info.base_url || "";
  fields.model.value = info.model || "";
  if (info.has_key) fields.apiKey.placeholder = "set on the server";
  $("extensions").textContent = info.extensions.join(", ") + ", up to " + info.max_upload_mb + " MB";
  updateCount();
}

async function submit() {
  fail("");
  const form = settings(new FormData());
  form.append("speed", fields.speed.value);
  if (mode === "file") {
    if (!chosenFile) return fail("Please choose a file.");
    form.append("file", chosenFile);
  } else {
    if (!$("text").value.trim()) return fail("Please enter some text.");
    form.append("text", $("text").value);
  }
  busy(true);
  $("progress").textContent = "Generating audio…";
  show($("result"), false);
  const response = await fetch("/api/speak", { method: "POST", body: form });
  if (!response.ok) {
    busy(false);
    return fail(await detail(response, "Audio generation failed."));
  }
  polling = setInterval(poll, 1000);
  poll();
}

async function poll() {
  const response = await fetch("/api/job");
  if (!response.ok) return;
  const job = await response.json();
  if (job.state === "running") {
    $("progress").textContent = job.total > 1
      ? "Synthesizing part " + Math.min(job.done + 1, job.total) + " of " + job.total + "…"
      : "Generating audio…";
    return;
  }
  clearInterval(polling);
  polling = null;
  busy(false);
  if (job.state === "error") return fail(job.error || "Audio generation failed.");
  if (job.state !== "done") return;
  const audio = await fetch("/api/audio");
  if (!audio.ok) return fail(await detail(audio, "The audio could not be loaded."));
  if (audioUrl) URL.revokeObjectURL(audioUrl);
  audioUrl = URL.createObjectURL(await audio.blob());
  $("audio").src = audioUrl;
  $("download").href = audioUrl;
  $("download").download = job.name;
  $("result-name").textContent = job.name;
  show($("result"), true);
}

async function previewVoice() {
  fail("");
  $("preview-note").textContent = "Loading…";
  $("preview").disabled = true;
  const response = await fetch("/api/preview", { method: "POST", body: settings(new FormData()) });
  $("preview").disabled = false;
  $("preview-note").textContent = "";
  if (!response.ok) return fail(await detail(response, "The preview failed."));
  const player = $("preview-audio");
  if (player.src) URL.revokeObjectURL(player.src);
  player.src = URL.createObjectURL(await response.blob());
  player.play();
}

function pickFile(file) {
  chosenFile = file;
  $("chosen").textContent = file ? file.name : "";
  show($("chosen"), !!file);
  fail("");
}

$("tab-text").onclick = () => setMode("text");
$("tab-file").onclick = () => setMode("file");
$("text").oninput = updateCount;
$("submit").onclick = () => submit().catch((e) => { busy(false); fail(String(e)); });
$("preview").onclick = () => previewVoice().catch((e) => { $("preview").disabled = false; fail(String(e)); });
$("file").onchange = (e) => pickFile(e.target.files[0] || null);
$("again").onclick = () => {
  show($("result"), false);
  $("text").value = "";
  pickFile(null);
  $("file").value = "";
  updateCount();
};

const drop = $("drop");
drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  drop.classList.remove("over");
  pickFile(e.dataTransfer.files[0] || null);
});

load().catch((e) => fail(String(e)));
