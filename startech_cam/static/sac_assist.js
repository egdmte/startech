(function () {
  "use strict";

  const page = document.querySelector("[data-sac-assist]");
  if (!page) return;

  const named = (name) => page.querySelector(`[name="${name}"]`);
  const clamp = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));
  const loadLocalImage = (file, callback) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      const image = new Image();
      image.addEventListener("load", () => callback(image), { once: true });
      image.src = String(reader.result);
    }, { once: true });
    reader.readAsDataURL(file);
  };

  const widthInput = named("kalibrasyon.kamera.genislik");
  const heightInput = named("kalibrasyon.kamera.yukseklik");
  const framePreview = page.querySelector("[data-frame-preview]");
  if (widthInput && heightInput && framePreview) {
    const renderFrame = () => {
      const width = Math.max(1, Number(widthInput.value) || 1);
      const height = Math.max(1, Number(heightInput.value) || 1);
      framePreview.style.aspectRatio = `${width} / ${height}`;
      framePreview.querySelector("[data-frame-size]").textContent = `${width} × ${height}`;
    };
    page.querySelectorAll("[data-frame-preset]").forEach((button) => {
      button.addEventListener("click", () => {
        [widthInput.value, heightInput.value] = button.dataset.framePreset.split(",");
        renderFrame();
      });
    });
    widthInput.addEventListener("input", renderFrame);
    heightInput.addEventListener("input", renderFrame);
    renderFrame();
  }

  const perspective = page.querySelector("[data-sac-perspective]");
  if (perspective) {
    const canvas = perspective.querySelector("[data-sac-perspective-canvas]");
    const context = canvas.getContext("2d");
    const valueInput = page.querySelector("[data-sac-perspective-value]");
    const imageInput = perspective.querySelector("[data-sac-image]");
    let points = JSON.parse(valueInput.value);
    let sourceImage = null;
    let draggedPoint = null;

    const drawBackground = () => {
      context.clearRect(0, 0, canvas.width, canvas.height);
      if (sourceImage) {
        context.drawImage(sourceImage, 0, 0, canvas.width, canvas.height);
        return;
      }
      context.fillStyle = "#f5f5f5";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.strokeStyle = "#dedede";
      context.lineWidth = Math.max(1, canvas.width / 840);
      for (let x = 0; x <= canvas.width; x += canvas.width / 8) {
        context.beginPath(); context.moveTo(x, 0); context.lineTo(x, canvas.height); context.stroke();
      }
      for (let y = 0; y <= canvas.height; y += canvas.height / 6) {
        context.beginPath(); context.moveTo(0, y); context.lineTo(canvas.width, y); context.stroke();
      }
    };
    const draw = () => {
      drawBackground();
      context.lineWidth = Math.max(3, canvas.width / 280);
      context.strokeStyle = "#075dff";
      context.fillStyle = "rgba(7, 93, 255, .16)";
      context.beginPath();
      context.moveTo(points[0][0], points[0][1]);
      context.lineTo(points[1][0], points[1][1]);
      context.lineTo(points[3][0], points[3][1]);
      context.lineTo(points[2][0], points[2][1]);
      context.closePath(); context.fill(); context.stroke();
      points.forEach((point, index) => {
        context.beginPath();
        context.fillStyle = "#fff"; context.strokeStyle = "#075dff";
        context.arc(point[0], point[1], Math.max(10, canvas.width / 70), 0, Math.PI * 2);
        context.fill(); context.stroke();
        context.fillStyle = "#075dff";
        context.font = `700 ${Math.max(12, canvas.width / 55)}px Inter, sans-serif`;
        context.textAlign = "center"; context.textBaseline = "middle";
        context.fillText(String(index + 1), point[0], point[1]);
      });
      valueInput.value = JSON.stringify(points);
    };
    const pointerPosition = (event) => {
      const bounds = canvas.getBoundingClientRect();
      return [
        clamp(Math.round((event.clientX - bounds.left) * canvas.width / bounds.width), 0, canvas.width),
        clamp(Math.round((event.clientY - bounds.top) * canvas.height / bounds.height), 0, canvas.height),
      ];
    };
    canvas.addEventListener("pointerdown", (event) => {
      const selected = pointerPosition(event);
      draggedPoint = points.map((point, index) => ({ index, distance: Math.hypot(point[0] - selected[0], point[1] - selected[1]) })).sort((a, b) => a.distance - b.distance)[0].index;
      canvas.setPointerCapture(event.pointerId);
      points[draggedPoint] = selected; draw();
    });
    canvas.addEventListener("pointermove", (event) => {
      if (draggedPoint === null) return;
      points[draggedPoint] = pointerPosition(event); draw();
    });
    const stopDragging = () => { draggedPoint = null; };
    canvas.addEventListener("pointerup", stopDragging);
    canvas.addEventListener("pointercancel", stopDragging);
    imageInput.addEventListener("change", () => {
      const file = imageInput.files[0];
      if (!file) return;
      loadLocalImage(file, (image) => { sourceImage = image; draw(); });
    });
    draw();
  }

  const rgbToHsv = (red, green, blue) => {
    const r = red / 255, g = green / 255, b = blue / 255;
    const maximum = Math.max(r, g, b), minimum = Math.min(r, g, b), difference = maximum - minimum;
    let hue = 0;
    if (difference !== 0) {
      if (maximum === r) hue = ((g - b) / difference) % 6;
      else if (maximum === g) hue = (b - r) / difference + 2;
      else hue = (r - g) / difference + 4;
    }
    hue = Math.round(((hue * 60 + 360) % 360) / 2);
    return [hue, maximum === 0 ? 0 : Math.round(difference / maximum * 255), Math.round(maximum * 255)];
  };

  page.querySelectorAll("[data-sac-hsv-editor]").forEach((editor) => {
    const documentInput = page.querySelector("[data-sac-hsv-document]");
    const configuration = JSON.parse(documentInput.value);
    const kind = editor.dataset.hsvKind;
    const targetSelect = editor.querySelector("[data-sac-hsv-target]");
    const rangePicker = editor.querySelector("[data-sac-range-picker]");
    const rangeSelect = editor.querySelector("[data-sac-hsv-range-index]");
    const controls = Object.fromEntries([...editor.querySelectorAll("[data-sac-hsv]")].map((input) => [input.dataset.sacHsv, input]));
    const minimumArea = editor.querySelector("[data-sac-min-area]");
    const triggerAreaBlock = editor.querySelector("[data-sac-trigger-area]");
    const triggerArea = editor.querySelector("[data-sac-trigger-area-input]");
    const sourceCanvas = editor.querySelector("[data-sac-source-canvas]");
    const maskCanvas = editor.querySelector("[data-sac-mask-canvas]");
    const sourceContext = sourceCanvas.getContext("2d", { willReadFrequently: true });
    const maskContext = maskCanvas.getContext("2d");
    const imageInput = editor.querySelector("[data-sac-image]");
    let sourceFrame = null;

    const targetRanges = () => kind === "profiles" ? [{ alt: configuration[targetSelect.value].alt, ust: configuration[targetSelect.value].ust }] : configuration[targetSelect.value].araliklar;
    const selectedRange = () => targetRanges()[Number(rangeSelect?.value || 0)];
    const save = () => { documentInput.value = JSON.stringify(configuration); };
    const showPlaceholder = (context, text) => {
      context.fillStyle = "#f4f4f4"; context.fillRect(0, 0, sourceCanvas.width, sourceCanvas.height);
      context.fillStyle = "#777"; context.font = "20px Inter, sans-serif"; context.textAlign = "center"; context.textBaseline = "middle";
      context.fillText(text, sourceCanvas.width / 2, sourceCanvas.height / 2);
    };
    const drawMask = () => {
      if (!sourceFrame) { showPlaceholder(maskContext, "HSV"); return; }
      const ranges = targetRanges();
      const result = maskContext.createImageData(maskCanvas.width, maskCanvas.height);
      for (let index = 0; index < sourceFrame.data.length; index += 4) {
        const hsv = rgbToHsv(sourceFrame.data[index], sourceFrame.data[index + 1], sourceFrame.data[index + 2]);
        const matched = ranges.some((range) => hsv.every((value, channel) => value >= range.alt[channel] && value <= range.ust[channel]));
        const shade = matched ? 255 : 0;
        result.data[index] = shade; result.data[index + 1] = shade; result.data[index + 2] = shade; result.data[index + 3] = 255;
      }
      maskContext.putImageData(result, 0, 0);
    };
    const loadControls = () => {
      if (rangeSelect) {
        const ranges = targetRanges();
        const previous = Math.min(Number(rangeSelect.value || 0), ranges.length - 1);
        rangeSelect.replaceChildren(...ranges.map((_range, index) => new Option(`Range ${index + 1}`, String(index))));
        rangeSelect.value = String(previous);
        if (rangePicker) rangePicker.hidden = ranges.length < 2;
      }
      const range = selectedRange();
      ["lower_h", "lower_s", "lower_v"].forEach((name, index) => { controls[name].value = range.alt[index]; });
      ["upper_h", "upper_s", "upper_v"].forEach((name, index) => { controls[name].value = range.ust[index]; });
      Object.values(controls).forEach((input) => { input.closest("label").querySelector("[data-sac-hsv-output]").textContent = input.value; });
      if (minimumArea) minimumArea.value = configuration[targetSelect.value].min_alan;
      if (triggerAreaBlock) triggerAreaBlock.hidden = !("tetik_alan" in configuration[targetSelect.value]);
      if (triggerArea && !triggerAreaBlock.hidden) triggerArea.value = configuration[targetSelect.value].tetik_alan;
      drawMask();
    };
    const updateRange = () => {
      const range = selectedRange();
      range.alt = [Number(controls.lower_h.value), Number(controls.lower_s.value), Number(controls.lower_v.value)];
      range.ust = [Number(controls.upper_h.value), Number(controls.upper_s.value), Number(controls.upper_v.value)];
      Object.values(controls).forEach((input) => { input.closest("label").querySelector("[data-sac-hsv-output]").textContent = input.value; });
      save(); drawMask();
    };
    targetSelect.addEventListener("change", loadControls);
    rangeSelect?.addEventListener("change", loadControls);
    Object.values(controls).forEach((input) => input.addEventListener("input", updateRange));
    minimumArea?.addEventListener("input", () => { configuration[targetSelect.value].min_alan = Number(minimumArea.value); save(); });
    triggerArea?.addEventListener("input", () => { configuration[targetSelect.value].tetik_alan = Number(triggerArea.value); save(); });
    imageInput.addEventListener("change", () => {
      const file = imageInput.files[0];
      if (!file) return;
      loadLocalImage(file, (image) => {
        sourceContext.drawImage(image, 0, 0, sourceCanvas.width, sourceCanvas.height);
        sourceFrame = sourceContext.getImageData(0, 0, sourceCanvas.width, sourceCanvas.height);
        drawMask();
      });
    });
    showPlaceholder(sourceContext, "PHOTO"); showPlaceholder(maskContext, "HSV"); loadControls();
  });

  const calculator = page.querySelector("[data-command-calculator]");
  if (calculator) {
    const errorInput = calculator.querySelector("[data-example-error]");
    const render = () => {
      const minimum = Number(named("ayarlar.hiz.min").value);
      const target = Number(named("ayarlar.hiz.hedef").value);
      const maximum = Number(named("ayarlar.hiz.max").value);
      const gain = Number(named("ayarlar.hiz.k_speed").value);
      const error = Number(errorInput.value);
      const command = clamp(target - gain * Math.abs(error), minimum, maximum);
      calculator.querySelector("[data-error-output]").textContent = String(error);
      calculator.querySelector("[data-speed-formula]").textContent = `${target} − ${gain} × |${error}|`;
      calculator.querySelector("[data-speed-result]").textContent = `${command.toFixed(1)}% PWM`;
    };
    errorInput.addEventListener("input", render);
    ["ayarlar.hiz.min", "ayarlar.hiz.hedef", "ayarlar.hiz.max", "ayarlar.hiz.k_speed"].forEach((name) => named(name).addEventListener("input", render));
    render();
  }
}());
