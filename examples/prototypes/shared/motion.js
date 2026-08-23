const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
const transitionDuration = 190;
let navigationPending = false;

function navigateWithTransition(destination) {
  if (navigationPending) return;
  navigationPending = true;

  if (motionPreference.matches) {
    window.location.href = destination;
    return;
  }

  document.body.classList.add("is-leaving");
  window.setTimeout(() => {
    window.location.href = destination;
  }, transitionDuration);
}

window.startechNavigate = navigateWithTransition;

document.addEventListener("click", (event) => {
  const link = event.target.closest("a[href]");
  if (!link || event.defaultPrevented) return;
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  if (link.target || link.hasAttribute("download")) return;

  const rawHref = link.getAttribute("href");
  if (!rawHref || rawHref.startsWith("#")) return;

  const destination = new URL(link.href, window.location.href);
  if (destination.protocol !== window.location.protocol) return;

  event.preventDefault();
  navigateWithTransition(destination.href);
});

window.addEventListener("pageshow", () => {
  navigationPending = false;
  document.body.classList.remove("is-leaving");
});
