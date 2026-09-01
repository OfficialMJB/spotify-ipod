const SDK_URL = "https://sdk.scdn.co/spotify-player.js";
let sdkPromise;

export function loadSpotifySdk({ windowObject = window, documentObject = document } = {}) {
  if (windowObject.Spotify?.Player) return Promise.resolve(windowObject.Spotify);
  if (sdkPromise) return sdkPromise;

  sdkPromise = new Promise((resolve, reject) => {
    const existingCallback = windowObject.onSpotifyWebPlaybackSDKReady;
    windowObject.onSpotifyWebPlaybackSDKReady = () => {
      if (typeof existingCallback === "function") existingCallback();
      resolve(windowObject.Spotify);
    };

    let script = documentObject.querySelector(`script[src="${SDK_URL}"]`);
    if (!script) {
      script = documentObject.createElement("script");
      script.src = SDK_URL;
      script.async = true;
      script.defer = true;
      documentObject.head.append(script);
    }
    script.addEventListener("error", () => reject(new Error("Spotify's playback player could not be loaded.")), { once: true });
  });

  return sdkPromise;
}

export function normalizePlaybackState(playbackState) {
  if (!playbackState) {
    return { paused: true, position: 0, duration: 0, track: null };
  }

  const current = playbackState.track_window?.current_track;
  return {
    paused: Boolean(playbackState.paused),
    position: finiteNonNegative(playbackState.position),
    duration: finiteNonNegative(playbackState.duration || current?.duration_ms),
    track: current ? normalizeSdkTrack(current) : null,
  };
}

export function normalizeSdkTrack(track) {
  const album = track.album || {};
  return {
    id: String(track.id || ""),
    uri: String(track.uri || ""),
    title: String(track.name || "Unknown track"),
    artists: Array.isArray(track.artists)
      ? track.artists.map((artist) => String(artist.name || "")).filter(Boolean).join(", ")
      : "Unknown artist",
    album: String(album.name || ""),
    artworkUrl: Array.isArray(album.images) ? String(album.images[0]?.url || "") : "",
    spotifyUrl: track.id ? `https://open.spotify.com/track/${encodeURIComponent(track.id)}` : "https://open.spotify.com/",
  };
}

export function sdkErrorMessage(type, message = "") {
  const messages = {
    account_error: "Spotify Premium is required for playback in this browser.",
    authentication_error: "Spotify could not authorize playback. Sign in again and retry.",
    autoplay_failed: "Your browser blocked automatic playback. Select the track again to start it.",
    initialization_error: "This browser could not initialize Spotify playback.",
    playback_error: "Spotify could not play that track. Try another track or open Spotify.",
    not_ready: "The browser player went offline. Check your connection and retry.",
  };
  return messages[type] || message || "Spotify playback is unavailable right now.";
}

export function createPlayer(Spotify, { getToken, onState, onReady, onError, name = "Spotify Pocket Player" }) {
  const player = new Spotify.Player({
    name,
    getOAuthToken(callback) {
      Promise.resolve(getToken())
        .then(callback)
        .catch((error) => onError("authentication_error", error.message));
    },
    volume: 0.8,
  });

  ["initialization_error", "authentication_error", "account_error", "playback_error"].forEach((type) => {
    player.addListener(type, ({ message }) => onError(type, message));
  });
  player.addListener("autoplay_failed", () => onError("autoplay_failed"));
  player.addListener("ready", ({ device_id: deviceId }) => onReady(deviceId));
  player.addListener("not_ready", () => onError("not_ready"));
  player.addListener("player_state_changed", (state) => onState(normalizePlaybackState(state)));
  return player;
}

export function formatTime(milliseconds) {
  const totalSeconds = Math.floor(finiteNonNegative(milliseconds) / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

export function projectedPosition(player, now = Date.now()) {
  const position = finiteNonNegative(player?.position);
  const duration = finiteNonNegative(player?.duration);
  const updatedAt = finiteNonNegative(player?.updatedAt);
  if (player?.paused || player?.status !== "ready" || !updatedAt) {
    return Math.min(position, duration || position);
  }
  const elapsed = Math.max(0, finiteNonNegative(now) - updatedAt);
  return Math.min(position + elapsed, duration || position + elapsed);
}

function finiteNonNegative(value) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : 0;
}
