import assert from "node:assert/strict";
import test from "node:test";

import {
  createPlayer,
  formatTime,
  normalizePlaybackState,
  projectedPosition,
  sdkErrorMessage,
} from "../../app/static/js/player.js";

test("normalizePlaybackState maps SDK state into application state", () => {
  const result = normalizePlaybackState({
    paused: false,
    position: 12_345,
    duration: 180_000,
    track_window: {
      current_track: {
        id: "track-id",
        uri: "spotify:track:track-id",
        name: "A Song",
        artists: [{ name: "Artist One" }, { name: "Artist Two" }],
        album: { name: "An Album", images: [{ url: "https://image.example/cover.jpg" }] },
      },
    },
  });

  assert.equal(result.paused, false);
  assert.equal(result.position, 12_345);
  assert.equal(result.track.title, "A Song");
  assert.equal(result.track.artists, "Artist One, Artist Two");
  assert.equal(result.track.spotifyUrl, "https://open.spotify.com/track/track-id");
});

test("normalizePlaybackState handles an empty SDK state", () => {
  assert.deepEqual(normalizePlaybackState(null), {
    paused: true,
    position: 0,
    duration: 0,
    track: null,
  });
});

test("formatTime clamps invalid input and formats durations", () => {
  assert.equal(formatTime(65_999), "1:05");
  assert.equal(formatTime(-200), "0:00");
  assert.equal(formatTime(Number.NaN), "0:00");
});

test("projectedPosition advances active playback and clamps at duration", () => {
  assert.equal(projectedPosition({ status: "ready", paused: false, position: 10_000, duration: 12_000, updatedAt: 1_000 }, 2_500), 11_500);
  assert.equal(projectedPosition({ status: "ready", paused: false, position: 10_000, duration: 12_000, updatedAt: 1_000 }, 5_000), 12_000);
  assert.equal(projectedPosition({ status: "ready", paused: true, position: 10_000, duration: 12_000, updatedAt: 1_000 }, 5_000), 10_000);
});

test("sdkErrorMessage gives actionable account guidance", () => {
  assert.match(sdkErrorMessage("account_error"), /Premium/);
  assert.equal(sdkErrorMessage("unknown", "Spotify said no"), "Spotify said no");
});

test("createPlayer wires token, state, ready, and error callbacks", async () => {
  class FakePlayer {
    constructor(options) {
      this.options = options;
      this.listeners = new Map();
    }
    addListener(name, callback) { this.listeners.set(name, callback); }
  }

  const errors = [];
  const player = createPlayer({ Player: FakePlayer }, {
    getToken: () => "access-token",
    onState: () => {},
    onReady: () => {},
    onError: (...args) => errors.push(args),
  });

  let receivedToken;
  player.options.getOAuthToken((token) => { receivedToken = token; });
  await Promise.resolve();
  assert.equal(receivedToken, "access-token");
  assert.equal(player.listeners.has("player_state_changed"), true);
  assert.equal(player.listeners.has("account_error"), true);
  assert.equal(player.listeners.has("autoplay_failed"), true);
  assert.deepEqual(errors, []);
});
