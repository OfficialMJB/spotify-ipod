export const STORAGE_KEY = "spotify-pocket-player.preferences.v1";

export const DEFAULT_PREFERENCES = Object.freeze({
  mode: "expanded",
  theme: "pocket",
  accent: "green",
});

const ALLOWED = Object.freeze({
  mode: new Set(["compact", "expanded"]),
  theme: new Set(["pocket", "minimal", "retro"]),
  accent: new Set(["green", "blue", "orange"]),
});

export function normalizePreferences(candidate) {
  const value = candidate && typeof candidate === "object" ? candidate : {};
  return Object.fromEntries(
    Object.entries(DEFAULT_PREFERENCES).map(([key, fallback]) => [
      key,
      ALLOWED[key].has(value[key]) ? value[key] : fallback,
    ]),
  );
}

export function loadPreferences(storage = globalThis.localStorage) {
  try {
    const saved = storage.getItem(STORAGE_KEY);
    return saved ? normalizePreferences(JSON.parse(saved)) : { ...DEFAULT_PREFERENCES };
  } catch {
    return { ...DEFAULT_PREFERENCES };
  }
}

export function savePreferences(preferences, storage = globalThis.localStorage) {
  const safePreferences = normalizePreferences(preferences);
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(safePreferences));
  } catch {
    // Storage can be unavailable in private browsing. The in-memory preference still applies.
  }
  return safePreferences;
}

export function resetPreferences(storage = globalThis.localStorage) {
  try {
    storage.removeItem(STORAGE_KEY);
  } catch {
    // Resetting the in-memory value is sufficient when browser storage is unavailable.
  }
  return { ...DEFAULT_PREFERENCES };
}

export function applyPreferences(preferences, root = document.documentElement) {
  const safePreferences = normalizePreferences(preferences);
  root.dataset.mode = safePreferences.mode;
  root.dataset.theme = safePreferences.theme;
  root.dataset.accent = safePreferences.accent;
  return safePreferences;
}
