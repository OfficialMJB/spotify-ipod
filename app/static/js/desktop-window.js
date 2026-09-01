export function setupDesktopWindowSizing({
  documentObject = document,
  windowObject = window,
  ResizeObserverClass = globalThis.ResizeObserver,
} = {}) {
  const root = documentObject.documentElement;
  const shell = documentObject.querySelector(".app-shell");
  if (!root || !shell || typeof ResizeObserverClass !== "function") return null;

  let observer = null;
  let resizePending = false;

  function requestResize() {
    if (resizePending) return;
    resizePending = true;
    const schedule = windowObject.requestAnimationFrame
      ? windowObject.requestAnimationFrame.bind(windowObject)
      : (callback) => callback();
    schedule(() => {
      resizePending = false;
      const resizeWindow = windowObject.pywebview?.api?.resize_window;
      if (typeof resizeWindow !== "function") return;
      try {
        const result = resizeWindow(
          Math.ceil(shell.scrollWidth),
          Math.ceil(shell.scrollHeight),
        );
        result?.catch?.(() => {});
      } catch {
        // Losing the native bridge should not break the browser application.
      }
    });
  }

  function start() {
    if (observer) return;
    root.dataset.runtime = "desktop";
    observer = new ResizeObserverClass(requestResize);
    observer.observe(shell);
    requestResize();
  }

  if (windowObject.pywebview?.api) {
    start();
  } else {
    windowObject.addEventListener("pywebviewready", start, { once: true });
  }

  return () => observer?.disconnect();
}
