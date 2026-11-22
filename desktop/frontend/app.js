"use strict";

const byId = (id) => document.getElementById(id);
const list = byId("jobs");
const drop = byId("drop");
const device = byId("device");
const pick = byId("pick");
const clear = byId("clear");
const start = byId("start");
const notice = byId("notice");
let revision = -1;
let actionPending = false;
let actionError = "";
let snapshot = { jobs: [], running: false, active: -1 };

function controls() {
  const jobs = snapshot.jobs ?? [];
  const locked = actionPending || revision < 0 || snapshot.running;
  pick.disabled = locked;
  clear.disabled = locked || jobs.length === 0;
  start.disabled = locked || !jobs.some((job) => job.status !== "saved");
  device.disabled = locked || snapshot.cuda === false;
  const message = actionError || snapshot.notice || "";
  notice.hidden = !message;
  notice.textContent = message;
}

function render(state) {
  if (state.revision <= revision) return;
  if (revision < 0) {
    if (!state.cuda) device.querySelector('[value="cuda"]').remove();
    device.value = state.device;
  }
  revision = state.revision;
  snapshot = state;
  const jobs = state.jobs ?? [];
  byId("count").textContent = jobs.length ? jobs.length : "";
  byId("empty").hidden = jobs.length > 0;
  list.replaceChildren(...jobs.map((job) => {
    const row = document.createElement("li");
    const content = document.createElement("div");
    const filename = document.createElement("strong");
    filename.textContent = job.name;
    filename.title = job.input;
    content.append(filename);
    if (job.output || job.error) {
      const detail = document.createElement("span");
      detail.className = "detail";
      detail.textContent = job.error || job.output.split(/[\\/]/).pop();
      detail.title = job.output || job.error;
      content.append(detail);
    }
    const status = document.createElement("span");
    status.className = "job-status " + job.status;
    status.textContent = { queued: "Queued", working: "Working", saved: "Saved", failed: "Failed" }[job.status];
    row.append(content, status);
    return row;
  }));
  const active = jobs[state.active];
  const percent = active?.percent ?? 0;
  const stage = active?.stage ?? (active?.status === "saved" ? "Subtitle saved" :
    active?.status === "failed" ? "Transcription failed" : "Ready");
  byId("stage").textContent = stage.charAt(0).toUpperCase() + stage.slice(1);
  byId("percent").textContent = percent + "%";
  byId("progress").value = percent;
  controls();
}

async function invoke(method, ...args) {
  if (actionPending) return;
  actionPending = true;
  actionError = "";
  controls();
  try {
    await window.mygo.call("Desktop." + method, ...args);
    render(await window.mygo.call("Desktop.Snapshot"));
  } catch (error) {
    actionError = error.message || String(error);
  } finally {
    actionPending = false;
    controls();
  }
}

pick.addEventListener("click", () => invoke("PickFiles"));
clear.addEventListener("click", () => invoke("Clear"));
start.addEventListener("click", () => invoke("Start", device.value));

// MyGO supplies actual paths through Window.OnFileDrop.
document.addEventListener("dragover", (event) => {
  if (!event.dataTransfer.types.includes("Files")) return;
  event.preventDefault();
  drop.classList.toggle("over", !snapshot.running);
});
document.addEventListener("dragleave", (event) => {
  if (!event.relatedTarget) drop.classList.remove("over");
});
document.addEventListener("drop", (event) => {
  event.preventDefault();
  drop.classList.remove("over");
  actionError = "";
});

async function refresh() {
  try {
    render(await window.mygo.call("Desktop.Snapshot"));
  } catch (error) {
    if (revision < 0) {
      actionError = error.message || "Could not connect to Local SRT.";
      controls();
    }
  }
  setTimeout(refresh, snapshot.running ? 200 : 650);
}
refresh();
