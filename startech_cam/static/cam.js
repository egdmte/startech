(function () {
  "use strict";

  const clocks = [...document.querySelectorAll("[data-session-clock]")];
  if (clocks.length) {
    const expiresAt = Number(clocks[0].dataset.sessionExpiresAt) * 1000;
    const updateClock = () => {
      const remaining = Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000));
      const minutes = String(Math.floor(remaining / 60)).padStart(2, "0");
      const seconds = String(remaining % 60).padStart(2, "0");
      clocks.forEach((clock) => { clock.textContent = `${minutes}:${seconds}`; });
      document.querySelectorAll("[data-session-minutes]").forEach((part) => { part.textContent = minutes; });
      document.querySelectorAll("[data-session-seconds]").forEach((part) => { part.textContent = seconds; });
      if (remaining === 0) window.location.replace("/login?expired=1");
    };
    updateClock();
    window.setInterval(updateClock, 1000);
  }

  document.querySelectorAll("[data-range]").forEach((input) => {
    const output = input.closest("label")?.querySelector("[data-range-output]");
    if (!output) return;
    const render = () => {
      const numeric = Number(input.value);
      const prefix = numeric > 0 && Number(input.min) < 0 ? "+" : "";
      output.textContent = `${prefix}${input.value}${input.dataset.rangeSuffix || ""}`;
    };
    input.addEventListener("input", render);
    render();
  });

  const orientationPreview = document.querySelector("[data-orientation-preview]");
  document.querySelectorAll('input[name="sac_niyeti.kamera.yon_derecesi"]').forEach((input) => {
    input.addEventListener("change", () => {
      if (input.checked && orientationPreview) orientationPreview.textContent = `${input.value}°`;
    });
  });

  const fullOutputGate = document.querySelector("[data-full-output-gate]");
  const outputModes = [...document.querySelectorAll('input[name="sac_niyeti.surus.surucu_cikis_modu"]')];
  if (fullOutputGate && outputModes.length) {
    const renderOutputGate = () => {
      const selected = outputModes.find((option) => option.checked)?.value;
      fullOutputGate.classList.toggle("is-visible", selected === "full");
    };
    outputModes.forEach((option) => option.addEventListener("change", renderOutputGate));
    renderOutputGate();
  }

  const detailTitle = document.querySelector("[data-component-title]");
  const detailCopy = document.querySelector("[data-component-description]");
  document.querySelectorAll("[data-component-name]").forEach((hotspot) => {
    const preview = () => {
      if (detailTitle) detailTitle.textContent = hotspot.dataset.componentName;
      if (detailCopy) detailCopy.textContent = hotspot.dataset.componentCopy;
    };
    hotspot.addEventListener("mouseenter", preview);
    hotspot.addEventListener("focus", preview);
    hotspot.addEventListener("touchstart", preview, { passive: true });
  });

  document.querySelectorAll("[data-workshop-form]").forEach((form) => {
    const countdown = form.querySelector("[data-workshop-countdown]");
    const count = form.querySelector("[data-workshop-count]");
    const startNow = form.querySelector("[data-workshop-now]");
    const cancel = form.querySelector("[data-workshop-cancel]");
    const submit = form.querySelector(".workshop-submit");
    const workshopDelaySeconds = 7;
    let interval = null;
    let remaining = workshopDelaySeconds;

    const reset = () => {
      if (interval !== null) window.clearInterval(interval);
      interval = null;
      remaining = workshopDelaySeconds;
      if (count) count.textContent = String(workshopDelaySeconds);
      if (countdown) countdown.hidden = true;
      if (submit) submit.disabled = false;
    };
    const queue = () => {
      if (interval !== null) window.clearInterval(interval);
      interval = null;
      if (submit) submit.disabled = true;
      HTMLFormElement.prototype.submit.call(form);
    };

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!form.reportValidity() || interval !== null) return;
      remaining = workshopDelaySeconds;
      if (count) count.textContent = String(remaining);
      if (countdown) countdown.hidden = false;
      if (submit) submit.disabled = true;
      interval = window.setInterval(() => {
        remaining -= 1;
        if (count) count.textContent = String(Math.max(0, remaining));
        if (remaining <= 0) queue();
      }, 1000);
    });
    startNow?.addEventListener("click", queue);
    cancel?.addEventListener("click", reset);
  });

  const workshopJob = document.querySelector("[data-workshop-job]");
  if (workshopJob && ["PENDING", "CLAIMED"].includes(workshopJob.dataset.jobStatus)) {
    const statusUrl = workshopJob.dataset.statusUrl;
    const poll = async () => {
      try {
        const response = await fetch(statusUrl, { headers: { Accept: "application/json" } });
        if (!response.ok) return;
        const result = await response.json();
        const status = workshopJob.querySelector("[data-workshop-job-status]");
        if (status) status.textContent = result.status;
        if (["ACCEPTED", "REJECTED", "EXPIRED"].includes(result.status)) {
          window.location.reload();
          return;
        }
      } catch (_error) {
        // A later poll may recover; the server and YAREN enforce command expiry.
      }
      window.setTimeout(poll, 1000);
    };
    window.setTimeout(poll, 800);
  }

  document.addEventListener("click", (event) => {
    const anchor = event.target.closest("a[href]");
    if (!anchor || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const target = new URL(anchor.href, window.location.href);
    if (target.origin !== window.location.origin || anchor.hasAttribute("download") || anchor.target) return;
    event.preventDefault();
    document.querySelector("[data-page]")?.classList.add("is-leaving");
    window.setTimeout(() => { window.location.href = anchor.href; }, 130);
  });
})();
