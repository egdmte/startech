(function () {
  "use strict";

  const clock = document.querySelector("[data-session-clock]");
  const progress = document.querySelector("[data-session-progress]");
  if (clock && progress) {
    const expiresAt = Number(clock.dataset.sessionExpiresAt) * 1000;
    const initialRemaining = Math.max(1, Math.ceil((expiresAt - Date.now()) / 1000));
    const updateClock = () => {
      const remaining = Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000));
      const minutes = String(Math.floor(remaining / 60)).padStart(2, "0");
      const seconds = String(remaining % 60).padStart(2, "0");
      clock.textContent = `${minutes}:${seconds}`;
      progress.style.transform = `scaleX(${Math.min(1, remaining / initialRemaining)})`;
      if (remaining === 0) {
        window.location.replace("/login?expired=1");
      }
    };
    updateClock();
    window.setInterval(updateClock, 1000);
  }

  document.querySelectorAll("[data-range]").forEach((input) => {
    const output = input.closest("label")?.querySelector("[data-range-output]");
    if (!output) return;
    input.addEventListener("input", () => { output.textContent = input.value; });
  });

  document.addEventListener("click", (event) => {
    const anchor = event.target.closest("a[href]");
    if (!anchor || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const target = new URL(anchor.href, window.location.href);
    if (target.origin !== window.location.origin || anchor.hasAttribute("download") || anchor.target) return;
    event.preventDefault();
    document.querySelector(".app-frame")?.classList.add("is-leaving");
    window.setTimeout(() => { window.location.href = anchor.href; }, 130);
  });
})();
