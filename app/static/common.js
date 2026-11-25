export function formatClock(total) {
  const m = Math.floor(total / 60);
  const s = String(total % 60).padStart(2, "0");
  return `${m}:${s}`;
}

export function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** Drains a bar and counts down. Uses a local clock from the server's
 *  seconds_remaining, so a wrong device clock can't skew it. */
export function startCountdown(root, secondsRemaining, totalSeconds, onDone) {
  const fill = root.querySelector(".fill");
  const text = root.querySelector(".text");
  const end = performance.now() + secondsRemaining * 1000;
  root.classList.remove("low");
  const id = setInterval(tick, 250);
  tick();
  function tick() {
    const left = Math.max(0, Math.ceil((end - performance.now()) / 1000));
    fill.style.transform = `scaleX(${Math.min(1, left / totalSeconds)})`;
    text.textContent = left > 0 ? `Expires in ${formatClock(left)}` : "Expired";
    root.classList.toggle("low", left <= 60);
    if (left === 0) { clearInterval(id); onDone && onDone(); }
  }
  return () => clearInterval(id);
}

export async function api(path, options) {
  const res = await fetch(path, options);
  let body = null;
  try { body = await res.json(); } catch { /* non-JSON error */ }
  if (!res.ok) {
    const msg = body && body.error ? body.error.message : "Something went wrong. Try again.";
    throw Object.assign(new Error(msg), { status: res.status });
  }
  return body;
}

export async function copy(text, button) {
  const original = button.textContent;
  try { await navigator.clipboard.writeText(text); button.textContent = "Copied"; }
  catch { button.textContent = "Press Ctrl+C"; }
  setTimeout(() => { button.textContent = original; }, 1500);
}
