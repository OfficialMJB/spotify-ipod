import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_PREFERENCES,
  STORAGE_KEY,
  applyPreferences,
  loadPreferences,
  normalizePreferences,
  resetPreferences,
  savePreferences,
} from "../../app/static/js/preferences.js";

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
    value: (key) => values.get(key),
  };
}

test("normalizePreferences accepts only whitelisted values", () => {
  assert.deepEqual(
    normalizePreferences({ mode: "tiny", theme: "retro", accent: "purple", token: "do-not-store" }),
    { mode: "expanded", theme: "retro", accent: "green" },
  );
});

test("loadPreferences recovers from malformed storage", () => {
  const storage = memoryStorage({ [STORAGE_KEY]: "not json" });
  assert.deepEqual(loadPreferences(storage), DEFAULT_PREFERENCES);
});

test("savePreferences writes only normalized display preferences", () => {
  const storage = memoryStorage();
  savePreferences({ mode: "compact", theme: "minimal", accent: "blue", access_token: "secret" }, storage);
  assert.deepEqual(JSON.parse(storage.value(STORAGE_KEY)), {
    mode: "compact",
    theme: "minimal",
    accent: "blue",
  });
});

test("resetPreferences clears storage and returns defaults", () => {
  const storage = memoryStorage({ [STORAGE_KEY]: "saved" });
  assert.deepEqual(resetPreferences(storage), DEFAULT_PREFERENCES);
  assert.equal(storage.value(STORAGE_KEY), undefined);
});

test("applyPreferences updates only validated data attributes", () => {
  const root = { dataset: {} };
  applyPreferences({ mode: "compact", theme: "invalid", accent: "orange" }, root);
  assert.deepEqual(root.dataset, { mode: "compact", theme: "pocket", accent: "orange" });
});
