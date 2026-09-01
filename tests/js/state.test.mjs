import assert from "node:assert/strict";
import test from "node:test";

import {
  authenticationErrorMessage,
  createInitialState,
  createStore,
  updateSection,
} from "../../app/static/js/state.js";

test("store publishes a state update to subscribers", () => {
  const store = createStore(createInitialState({ mode: "expanded", theme: "pocket", accent: "green" }));
  let published;
  const unsubscribe = store.subscribe((state) => { published = state; });

  store.update((state) => updateSection(state, "player", { status: "ready", deviceId: "device-1" }));

  assert.equal(store.getState().player.status, "ready");
  assert.equal(published.player.deviceId, "device-1");
  unsubscribe();
});

test("updateSection keeps unrelated state references intact", () => {
  const original = createInitialState({ mode: "expanded", theme: "pocket", accent: "green" });
  const next = updateSection(original, "library", { status: "loading" });

  assert.notEqual(next.library, original.library);
  assert.equal(next.player, original.player);
  assert.equal(next.library.status, "loading");
});

test("store ignores empty updates", () => {
  const initial = createInitialState({ mode: "expanded", theme: "pocket", accent: "green" });
  const store = createStore(initial);
  let calls = 0;
  store.subscribe(() => { calls += 1; });
  store.update(null);

  assert.equal(store.getState(), initial);
  assert.equal(calls, 0);
});

test("authentication errors are whitelisted and actionable", () => {
  assert.match(authenticationErrorMessage("invalid_state"), /verified/);
  assert.match(authenticationErrorMessage("access_denied"), /declined/);
  assert.match(authenticationErrorMessage("invalid_scope"), /permissions/);
  assert.match(authenticationErrorMessage("spotify_temporarily_unavailable"), /temporarily/);
  assert.match(authenticationErrorMessage("authorization_request_invalid"), /redirect URI/);
  assert.equal(authenticationErrorMessage("unexpected"), null);
});
