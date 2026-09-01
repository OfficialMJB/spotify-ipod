export class ApiError extends Error {
  constructor(message, { status = 0, code = null, details = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let csrfToken = "";

export function setCsrfToken(value) {
  csrfToken = typeof value === "string" ? value : "";
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Accept", "application/json");
  if (csrfToken && !["GET", "HEAD"].includes((options.method || "GET").toUpperCase())) {
    headers.set("X-CSRF-Token", csrfToken);
  }

  let response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      ...options,
      headers,
    });
  } catch {
    throw new ApiError("The server could not be reached. Check that the Flask app is running.");
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json().catch(() => ({}))
    : {};

  if (!response.ok) {
    const message = payload.message || payload.error?.message || payload.error || defaultMessage(response.status);
    throw new ApiError(String(message), {
      status: response.status,
      code: payload.code || payload.error?.code || null,
      details: payload,
    });
  }

  return payload;
}

function defaultMessage(status) {
  if (status === 401) return "Your Spotify session has expired. Please sign in again.";
  if (status === 403) return "Spotify did not allow that action for this account or playlist.";
  if (status === 429) return "Spotify is receiving too many requests. Please wait and try again.";
  return "Something went wrong while talking to Spotify.";
}

function asItems(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.items)) return payload.items;
  return [];
}

export const api = Object.freeze({
  getSession: () => request("/api/session"),
  getPlayerToken: () => request("/api/player-token"),
  getPlaylists: async () => asItems(await request("/api/playlists")),
  getTracks: async (playlistId) => asItems(await request(`/api/playlists/${encodeURIComponent(playlistId)}/tracks`)),
  startPlayback: (body) => request("/api/playback/start", { method: "PUT", body: JSON.stringify(body) }),
  logout: () => request("/auth/logout", { method: "POST" }),
});
