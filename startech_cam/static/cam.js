(function () {
  "use strict";

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

  const frameJob = document.querySelector("[data-frame-job]");
  if (frameJob && ["PENDING", "CLAIMED"].includes(frameJob.dataset.jobStatus)) {
    const poll = async () => {
      try {
        const response = await fetch(frameJob.dataset.statusUrl, { headers: { Accept: "application/json" } });
        if (response.ok) {
          const result = await response.json();
          const status = frameJob.querySelector("[data-frame-job-status]");
          if (status) status.textContent = result.status;
          if (["ACCEPTED", "REJECTED", "EXPIRED"].includes(result.status)) {
            window.location.reload();
            return;
          }
        }
      } catch (_error) {
        // The job has a server-side expiry; a later poll can recover.
      }
      window.setTimeout(poll, 800);
    };
    window.setTimeout(poll, 500);
  }

  const calibration = document.querySelector("[data-camera-calibration]");
  const sourceImage = calibration?.querySelector("[data-calibration-image]");
  const perspectiveCanvas = calibration?.querySelector("[data-perspective-canvas]");
  const maskCanvas = calibration?.querySelector("[data-hsv-canvas]");
  const pointInput = calibration?.querySelector("[data-perspective-points]");
  if (calibration && sourceImage && perspectiveCanvas && maskCanvas && pointInput) {
    const targets = JSON.parse(calibration.dataset.hsvTargets);
    let points = JSON.parse(pointInput.value);
    let draggedPoint = null;
    let maskFrame = null;
    let maskScheduled = false;
    const perspectiveContext = perspectiveCanvas.getContext("2d");
    const maskContext = maskCanvas.getContext("2d");
    const targetSelect = calibration.querySelector("[data-hsv-target]");
    const hsvInputs = Object.fromEntries(
      [...calibration.querySelectorAll("[data-hsv-range]")].map((input) => [input.dataset.hsvRange, input])
    );

    const drawPerspective = () => {
      perspectiveContext.clearRect(0, 0, perspectiveCanvas.width, perspectiveCanvas.height);
      perspectiveContext.drawImage(sourceImage, 0, 0, perspectiveCanvas.width, perspectiveCanvas.height);
      perspectiveContext.lineWidth = Math.max(3, perspectiveCanvas.width / 280);
      perspectiveContext.strokeStyle = "#1464ff";
      perspectiveContext.fillStyle = "rgba(20, 100, 255, .18)";
      perspectiveContext.beginPath();
      perspectiveContext.moveTo(points[0][0], points[0][1]);
      perspectiveContext.lineTo(points[1][0], points[1][1]);
      perspectiveContext.lineTo(points[3][0], points[3][1]);
      perspectiveContext.lineTo(points[2][0], points[2][1]);
      perspectiveContext.closePath();
      perspectiveContext.fill();
      perspectiveContext.stroke();
      points.forEach((point, index) => {
        perspectiveContext.beginPath();
        perspectiveContext.fillStyle = "#ffffff";
        perspectiveContext.strokeStyle = "#075dff";
        perspectiveContext.arc(point[0], point[1], Math.max(9, perspectiveCanvas.width / 70), 0, Math.PI * 2);
        perspectiveContext.fill();
        perspectiveContext.stroke();
        perspectiveContext.fillStyle = "#075dff";
        perspectiveContext.font = `700 ${Math.max(12, perspectiveCanvas.width / 55)}px Inter, sans-serif`;
        perspectiveContext.textAlign = "center";
        perspectiveContext.textBaseline = "middle";
        perspectiveContext.fillText(String(index + 1), point[0], point[1]);
      });
      pointInput.value = JSON.stringify(points);
    };

    const canvasPoint = (event) => {
      const bounds = perspectiveCanvas.getBoundingClientRect();
      return [
        Math.round((event.clientX - bounds.left) * perspectiveCanvas.width / bounds.width),
        Math.round((event.clientY - bounds.top) * perspectiveCanvas.height / bounds.height),
      ];
    };
    perspectiveCanvas.addEventListener("pointerdown", (event) => {
      const selected = canvasPoint(event);
      draggedPoint = points
        .map((point, index) => ({ index, distance: Math.hypot(point[0] - selected[0], point[1] - selected[1]) }))
        .sort((left, right) => left.distance - right.distance)[0].index;
      perspectiveCanvas.setPointerCapture(event.pointerId);
      points[draggedPoint] = selected;
      drawPerspective();
    });
    perspectiveCanvas.addEventListener("pointermove", (event) => {
      if (draggedPoint === null) return;
      const selected = canvasPoint(event);
      points[draggedPoint] = [
        Math.max(0, Math.min(perspectiveCanvas.width, selected[0])),
        Math.max(0, Math.min(perspectiveCanvas.height, selected[1])),
      ];
      drawPerspective();
    });
    const stopDragging = () => { draggedPoint = null; };
    perspectiveCanvas.addEventListener("pointerup", stopDragging);
    perspectiveCanvas.addEventListener("pointercancel", stopDragging);

    const rgbToHsv = (red, green, blue) => {
      const r = red / 255;
      const g = green / 255;
      const b = blue / 255;
      const maximum = Math.max(r, g, b);
      const minimum = Math.min(r, g, b);
      const difference = maximum - minimum;
      let hue = 0;
      if (difference !== 0) {
        if (maximum === r) hue = ((g - b) / difference) % 6;
        else if (maximum === g) hue = (b - r) / difference + 2;
        else hue = (r - g) / difference + 4;
      }
      hue = Math.round(((hue * 60 + 360) % 360) / 2);
      const saturation = maximum === 0 ? 0 : Math.round((difference / maximum) * 255);
      return [hue, saturation, Math.round(maximum * 255)];
    };

    const drawMask = () => {
      maskScheduled = false;
      if (!maskFrame) return;
      const lower = [Number(hsvInputs.lower_h.value), Number(hsvInputs.lower_s.value), Number(hsvInputs.lower_v.value)];
      const upper = [Number(hsvInputs.upper_h.value), Number(hsvInputs.upper_s.value), Number(hsvInputs.upper_v.value)];
      const result = maskContext.createImageData(maskCanvas.width, maskCanvas.height);
      for (let index = 0; index < maskFrame.data.length; index += 4) {
        const hsv = rgbToHsv(maskFrame.data[index], maskFrame.data[index + 1], maskFrame.data[index + 2]);
        const matched = hsv.every((value, channel) => value >= lower[channel] && value <= upper[channel]);
        const shade = matched ? 255 : 0;
        result.data[index] = shade;
        result.data[index + 1] = shade;
        result.data[index + 2] = shade;
        result.data[index + 3] = 255;
      }
      maskContext.putImageData(result, 0, 0);
    };
    const scheduleMask = () => {
      if (maskScheduled) return;
      maskScheduled = true;
      window.requestAnimationFrame(drawMask);
    };
    const selectTarget = () => {
      const target = targets[targetSelect.value];
      ["lower_h", "lower_s", "lower_v"].forEach((name, index) => { hsvInputs[name].value = target.lower[index]; });
      ["upper_h", "upper_s", "upper_v"].forEach((name, index) => { hsvInputs[name].value = target.upper[index]; });
      Object.values(hsvInputs).forEach((input) => {
        const output = input.closest("label")?.querySelector("[data-hsv-output]");
        if (output) output.textContent = input.value;
      });
      scheduleMask();
    };
    targetSelect.addEventListener("change", selectTarget);
    Object.values(hsvInputs).forEach((input) => input.addEventListener("input", () => {
      const output = input.closest("label")?.querySelector("[data-hsv-output]");
      if (output) output.textContent = input.value;
      scheduleMask();
    }));

    const initializeCalibration = () => {
      drawPerspective();
      const offscreen = document.createElement("canvas");
      offscreen.width = maskCanvas.width;
      offscreen.height = maskCanvas.height;
      const context = offscreen.getContext("2d", { willReadFrequently: true });
      context.drawImage(sourceImage, 0, 0, offscreen.width, offscreen.height);
      maskFrame = context.getImageData(0, 0, offscreen.width, offscreen.height);
      selectTarget();
    };
    if (sourceImage.complete) initializeCalibration();
    else sourceImage.addEventListener("load", initializeCalibration, { once: true });
  }

  const releaseProgress = document.querySelector("[data-release-progress]");
  const releasePage = document.querySelector("[data-release-page]");
  document.querySelectorAll("[data-release-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!form.reportValidity() || !releaseProgress || !releasePage) return;

      const controller = new AbortController();
      const step = releaseProgress.querySelector("[data-release-step]");
      const detail = releaseProgress.querySelector("[data-release-detail]");
      const cancel = releaseProgress.querySelector("[data-release-cancel]");
      const buttons = [...document.querySelectorAll("[data-release-form] button")];
      buttons.forEach((button) => { button.disabled = true; });
      releasePage.hidden = true;
      releaseProgress.hidden = false;
      if (step) step.textContent = releasePage.dataset.releaseRechecking;
      if (detail) detail.textContent = `${form.dataset.releaseSource} · ${releasePage.dataset.releaseProfileLabel} ${form.dataset.releaseProfile}`;

      const abort = () => controller.abort();
      cancel?.addEventListener("click", abort, { once: true });
      try {
        const response = await fetch(form.action || window.location.href, {
          method: "POST",
          body: new FormData(form),
          signal: controller.signal,
          headers: { Accept: "application/zip" },
        });
        if (!response.ok) throw new Error(`KERİM rejected the build (${response.status}).`);
        const blob = await response.blob();
        const disposition = response.headers.get("Content-Disposition") || "";
        const filenameMatch = disposition.match(/filename\*?=(?:UTF-8''|\")?([^\";]+)/i);
        const filename = filenameMatch ? decodeURIComponent(filenameMatch[1]) : "startech-vehicle.zip";
        const objectUrl = URL.createObjectURL(blob);
        const download = document.createElement("a");
        download.href = objectUrl;
        download.download = filename;
        document.body.appendChild(download);
        download.click();
        download.remove();
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 30_000);
        if (step) step.textContent = releasePage.dataset.releaseComplete;
        if (detail) {
          const commit = response.headers.get("X-STARTECH-Git-Commit")?.slice(0, 7) || "exact commit";
          const profile = response.headers.get("X-STARTECH-Profile") || form.dataset.releaseProfile;
          detail.textContent = `${filename} · ${commit} · ${releasePage.dataset.releaseProfileLabel} ${profile}`;
        }
        if (cancel) cancel.textContent = releasePage.dataset.releaseReturn;
        cancel?.addEventListener("click", () => window.location.reload(), { once: true });
      } catch (error) {
        if (step) step.textContent = error.name === "AbortError" ? releasePage.dataset.releaseCancelled : releasePage.dataset.releaseFailed;
        if (detail) detail.textContent = error.name === "AbortError" ? releasePage.dataset.releaseNoDownload : error.message;
        if (cancel) cancel.textContent = releasePage.dataset.releaseReturn;
        cancel?.addEventListener("click", () => window.location.reload(), { once: true });
      }
    });
  });

  const vehicleRun = document.querySelector("[data-vehicle-run]");
  if (vehicleRun) {
    const animation = document.querySelector("[data-run-animation]");
    const stateIcon = document.querySelector("[data-run-state-icon]");
    const stateOutput = document.querySelector("[data-run-state]");
    const countdownOutput = document.querySelector("[data-run-countdown]");
    const jobStatus = vehicleRun.querySelector("[data-run-job-status]");
    const log = vehicleRun.querySelector("[data-run-log]");
    const stateLabels = {
      RUN_RECEIVED: vehicleRun.dataset.stateRunReceived,
      RUN_INITIATED: vehicleRun.dataset.stateRunInitiated,
      RUN_HALT_NOCON: vehicleRun.dataset.stateRunHaltNocon,
      RUN_CANCELLED: vehicleRun.dataset.stateRunCancelled,
      RUN_INTERRUPTED: vehicleRun.dataset.stateRunInterrupted,
      RUN_COMPLETED: vehicleRun.dataset.stateRunCompleted,
      RUN_FAILED: vehicleRun.dataset.stateRunFailed,
    };
    let cursor = Number(vehicleRun.dataset.lastSequence || -1);

    window.setTimeout(() => {
      if (animation) animation.hidden = true;
      if (stateIcon) stateIcon.hidden = false;
    }, 1900);

    const renderState = (state) => {
      if (stateOutput && state) stateOutput.textContent = stateLabels[state] || state;
      if (countdownOutput && state && state !== "RUN_RECEIVED") countdownOutput.textContent = "";
    };
    const appendEvent = (event) => {
      if (!log || log.querySelector(`[data-sequence="${event.sequence}"]`)) return;
      const article = document.createElement("article");
      article.dataset.sequence = String(event.sequence);
      const sequence = document.createElement("span");
      sequence.textContent = String(event.sequence);
      const identity = document.createElement("strong");
      identity.textContent = `${event.module} · ${event.kind}`;
      const detail = document.createElement("code");
      detail.textContent = JSON.stringify(event.data);
      article.append(sequence, identity, detail);
      log.append(article);
      log.scrollTop = log.scrollHeight;
      cursor = Math.max(cursor, Number(event.sequence));
      if (event.module === "ADAM" && event.data?.state) renderState(event.data.state);
      if (countdownOutput && Number.isInteger(event.data?.countdown_remaining)) {
        countdownOutput.textContent = vehicleRun.dataset.countdownTemplate.replace(
          "__SECONDS__",
          String(event.data.countdown_remaining),
        );
      }
    };
    const terminalStatuses = new Set(["ACCEPTED", "REJECTED", "EXPIRED"]);
    const poll = async () => {
      let delay = 1000;
      try {
        const separator = vehicleRun.dataset.statusUrl.includes("?") ? "&" : "?";
        const response = await fetch(
          `${vehicleRun.dataset.statusUrl}${separator}after=${cursor}`,
          { headers: { Accept: "application/json" } },
        );
        if (response.ok) {
          const result = await response.json();
          result.events.forEach(appendEvent);
          renderState(result.adam_state);
          vehicleRun.dataset.jobStatus = result.status;
          if (jobStatus) jobStatus.textContent = result.status;
          if (result.events.length >= 200) delay = 20;
          else if (terminalStatuses.has(result.status)) return;
        }
      } catch (_error) {
        // The run and warning live on the car; reconnecting this page resumes the log.
      }
      window.setTimeout(poll, delay);
    };
    if (!terminalStatuses.has(vehicleRun.dataset.jobStatus)) {
      window.setTimeout(poll, 350);
    }
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
