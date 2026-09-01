import assert from "node:assert/strict";
import test from "node:test";

import { setupDesktopWindowSizing } from "../../app/static/js/desktop-window.js";


class FakeResizeObserver {
  static instances = [];

  constructor(callback) {
    this.callback = callback;
    this.observed = [];
    this.disconnected = false;
    FakeResizeObserver.instances.push(this);
  }

  observe(element) {
    this.observed.push(element);
  }

  disconnect() {
    this.disconnected = true;
  }
}


function fixture({ desktopReady = true } = {}) {
  FakeResizeObserver.instances = [];
  const resizeCalls = [];
  const listeners = new Map();
  const root = { dataset: {} };
  const shell = { scrollWidth: 448.2, scrollHeight: 311.1 };
  const api = desktopReady
    ? { resize_window: (...dimensions) => resizeCalls.push(dimensions) }
    : undefined;
  const documentObject = {
    documentElement: root,
    querySelector: (selector) => selector === ".app-shell" ? shell : null,
  };
  const windowObject = {
    pywebview: api ? { api } : undefined,
    requestAnimationFrame: (callback) => callback(),
    addEventListener: (event, callback) => listeners.set(event, callback),
  };
  return { documentObject, windowObject, root, shell, resizeCalls, listeners };
}


test("desktop sizing marks the runtime and measures the application shell", () => {
  const values = fixture();

  const cleanup = setupDesktopWindowSizing({
    ...values,
    ResizeObserverClass: FakeResizeObserver,
  });

  assert.equal(values.root.dataset.runtime, "desktop");
  assert.deepEqual(values.resizeCalls, [[449, 312]]);
  assert.deepEqual(FakeResizeObserver.instances[0].observed, [values.shell]);

  cleanup();
  assert.equal(FakeResizeObserver.instances[0].disconnected, true);
});


test("desktop sizing waits for the pywebview bridge", () => {
  const values = fixture({ desktopReady: false });

  setupDesktopWindowSizing({
    ...values,
    ResizeObserverClass: FakeResizeObserver,
  });

  assert.equal(values.root.dataset.runtime, undefined);
  assert.equal(typeof values.listeners.get("pywebviewready"), "function");

  values.windowObject.pywebview = {
    api: { resize_window: (...dimensions) => values.resizeCalls.push(dimensions) },
  };
  values.listeners.get("pywebviewready")();

  assert.equal(values.root.dataset.runtime, "desktop");
  assert.deepEqual(values.resizeCalls, [[449, 312]]);
});
