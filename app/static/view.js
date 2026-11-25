import { api, copy, formatSize, startCountdown } from "/static/common.js";

const $ = (id) => document.getElementById(id);
const id = location.pathname.replace(/^\//, "");

function expired(message) {
  $("loading").classList.add("hidden");
  $("share").classList.add("hidden");
  $("gone").classList.remove("hidden");
  if (message) $("gone-text").textContent = message;
}

(async () => {
  let share;
  try {
    share = await api(`/api/v1/${encodeURIComponent(id)}`);
  } catch (e) {
    return expired(e.status === 404 ? null : e.message);
  }
  $("loading").classList.add("hidden");
  $("share").classList.remove("hidden");
  $("share-id").textContent = share.id;

  if (share.type === "text") {
    $("text-view").classList.remove("hidden");
    $("content").textContent = share.content;
    $("copy").onclick = (ev) => copy(share.content, ev.currentTarget);
  } else {
    $("file-view").classList.remove("hidden");
    $("file-name").textContent = share.filename;
    $("file-meta").textContent = formatSize(share.size);
    $("download").href = share.download_url;
  }
  startCountdown($("timer"), share.seconds_remaining, share.seconds_remaining, () => expired(null));
})();
