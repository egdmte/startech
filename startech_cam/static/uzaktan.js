(() => {
  const shell = document.querySelector("[data-uzaktan-shell]");
  if (!shell) return;

  const rail = shell.querySelector("[data-uzaktan-rail]");
  const panels = [...shell.querySelectorAll("[data-uzaktan-panel]")];
  const navigation = [...shell.querySelectorAll("[data-uzaktan-nav]")];
  const setPanel = (name, { compact = true } = {}) => {
    panels.forEach((panel) => { panel.hidden = panel.dataset.uzaktanPanel !== name; });
    navigation.forEach((item) => item.setAttribute(
      "aria-current",
      String(item.dataset.uzaktanNav === name),
    ));
    shell.classList.toggle("is-compact", compact);
    rail?.setAttribute("aria-expanded", String(!compact));
  };

  navigation.forEach((item) => item.addEventListener("click", () => {
    const target = item.dataset.uzaktanNav;
    if (target) setPanel(target);
  }));
  shell.querySelectorAll("[data-uzaktan-open]").forEach((item) => item.addEventListener("click", () => {
    setPanel(item.dataset.uzaktanOpen);
  }));
  shell.querySelectorAll("[data-uzaktan-expand]").forEach((item) => item.addEventListener("click", () => {
    shell.classList.remove("is-compact");
    rail?.setAttribute("aria-expanded", "true");
  }));

  const confirmation = shell.querySelector("[data-uzaktan-confirmation]");
  const countdown = shell.querySelector("[data-uzaktan-countdown]");
  const begin = shell.querySelector("[data-uzaktan-begin]");
  const cancel = shell.querySelector("[data-uzaktan-cancel]");
  const request = shell.querySelector("[data-uzaktan-request]");
  let timer = null;
  const resetConfirmation = () => {
    if (timer) window.clearInterval(timer);
    timer = null;
    confirmation?.removeAttribute("hidden");
    countdown?.setAttribute("hidden", "");
  };
  begin?.addEventListener("click", () => {
    if (!confirmation || !countdown || !request) return;
    confirmation.setAttribute("hidden", "");
    countdown.removeAttribute("hidden");
    const output = countdown.querySelector("[data-uzaktan-seconds]");
    let remaining = 5;
    output.textContent = String(remaining);
    timer = window.setInterval(() => {
      remaining -= 1;
      output.textContent = remaining > 0 ? String(remaining) : "";
      if (remaining <= 0) {
        window.clearInterval(timer);
        timer = null;
        request.requestSubmit();
      }
    }, 1000);
  });
  cancel?.addEventListener("click", resetConfirmation);
})();
