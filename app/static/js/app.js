import { api, ApiError, setCsrfToken } from "./api.js";
import { setupDesktopWindowSizing } from "./desktop-window.js";
import {
  activeLibraryItems,
  appendUniqueTracks,
  normalizeLibraryView,
  playbackContextUri,
} from "./library.js";
import { createPlayer, loadSpotifySdk, sdkErrorMessage } from "./player.js";
import {
  applyPreferences,
  loadPreferences,
  resetPreferences,
  savePreferences,
} from "./preferences.js";
import { createRenderer } from "./render.js";
import {
  authenticationErrorMessage,
  createInitialState,
  createStore,
  updateSection,
} from "./state.js";

const store = createStore(createInitialState(loadPreferences()));
const render = createRenderer();
let spotifyPlayer = null;
const callbackError = readAuthenticationError();

store.subscribe(render);
render(store.getState());
setupDesktopWindowSizing();

document.addEventListener("click", handleClick);
document.addEventListener("change", handlePreferenceChange);
document.addEventListener("keydown", handleKeydown);
document.addEventListener("submit", handleSubmit);

bootstrap();

async function bootstrap() {
  try {
    const payload = await api.getSession();
    const authenticated = Boolean(payload.authenticated ?? payload.logged_in);
    const configured = payload.configured !== false;
    setCsrfToken(payload.csrf_token);
    store.update((state) => updateSection(state, "session", {
      loading: false,
      authenticated,
      configured,
      user: payload.user || null,
      error: payload.error || callbackError,
    }));
    if (authenticated) await initializePlayback();
  } catch (error) {
    store.update((state) => updateSection(state, "session", {
      loading: false,
      error: errorMessage(error),
    }));
  }
}

async function initializePlayback() {
  store.update((state) => updateSection(state, "player", { status: "connecting", error: null }));
  try {
    const Spotify = await loadSpotifySdk();
    spotifyPlayer = createPlayer(Spotify, {
      name: document.documentElement.dataset.appName || document.title,
      getToken: async () => {
        let payload;
        try {
          payload = await api.getPlayerToken();
        } catch (error) {
          expireSession(error);
          throw error;
        }
        const token = payload.access_token || payload.token;
        if (!token) throw new Error("The server did not provide a playback token.");
        return token;
      },
      onState: (playback) => {
        store.update((state) => updateSection(state, "player", {
          ...playback,
          updatedAt: Date.now(),
          status: state.player.deviceId ? "ready" : state.player.status,
          error: null,
        }));
      },
      onReady: (deviceId) => {
        store.update((state) => updateSection(state, "player", {
          status: "ready",
          deviceId,
          error: null,
        }));
      },
      onError: (type, message) => {
        store.update((state) => updateSection(state, "player", {
          status: type === "not_ready" ? "offline" : "error",
          deviceId: type === "not_ready" ? null : state.player.deviceId,
          error: sdkErrorMessage(type, message),
        }));
      },
    });
    const connected = await spotifyPlayer.connect();
    if (!connected) throw new Error("Spotify did not connect the browser player.");
  } catch (error) {
    store.update((state) => updateSection(state, "player", {
      status: "error",
      error: errorMessage(error),
    }));
  }
}

async function handleClick(event) {
  const actionElement = event.target.closest("[data-action]");
  if (actionElement) {
    const action = actionElement.dataset.action;
    if (action === "open-library") return openLibrary();
    if (action === "library-view") return activateLibraryView(actionElement.dataset.libraryView);
    if (action === "load-more-liked") return loadMoreLikedSongs();
    if (action === "open-settings") return openPanel("settings");
    if (action === "close-panel") return openPanel(null);
    if (action === "library-back") return libraryBack();
    if (action === "toggle-mode") return toggleMode();
    if (action === "reset-preferences") return setPreferences(resetPreferences());
    if (action === "toggle-playback") return runPlayerCommand("togglePlay");
    if (action === "previous") return runPlayerCommand("previousTrack");
    if (action === "next") return runPlayerCommand("nextTrack");
    if (action === "logout") return logout();
  }

  const itemButton = event.target.closest("[data-library-index]");
  if (!itemButton || itemButton.disabled) return;
  const index = Number(itemButton.dataset.libraryIndex);
  selectLibraryIndex(index);
  if (itemButton.dataset.libraryKind === "playlist") {
    await openPlaylist(index);
  } else {
    await startTrack(index);
  }
}

function handleSubmit(event) {
  if (!event.target.matches("#track-search-form")) return;
  event.preventDefault();
  const input = event.target.querySelector("#track-search-input");
  searchTracks(input?.value || "");
}

function handlePreferenceChange(event) {
  const input = event.target.closest("#preferences-form input[type=radio]");
  if (!input) return;
  setPreferences({ ...store.getState().preferences, [input.name]: input.value });
}

function handleKeydown(event) {
  if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
  const tagName = event.target.tagName;
  const isTextInput = ["INPUT", "TEXTAREA", "SELECT"].includes(tagName);

  if ((event.key === "Escape" || event.key === "Backspace") && !isTextInput) {
    const state = store.getState();
    if (state.panel) {
      event.preventDefault();
      state.panel === "library" ? libraryBack() : openPanel(null);
    }
    return;
  }

  if (event.key === " " && !isTextInput && !event.target.closest("button, a, summary")) {
    event.preventDefault();
    runPlayerCommand("togglePlay");
    return;
  }

  const libraryButton = event.target.closest("[data-library-index]");
  if (!libraryButton) return;
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    moveLibraryFocus(event.key === "ArrowDown" ? 1 : -1);
  }
}

async function openLibrary() {
  openPanel("library");
  await activateLibraryView("liked");
}

async function activateLibraryView(candidate) {
  const view = normalizeLibraryView(candidate);
  const state = store.getState();
  const library = state.library;
  setLibrary({
    view,
    level: "playlists",
    message: "",
    selectedPlaylist: null,
    selectedIndex: 0,
    status: view === "liked"
      ? (library.likedLoaded ? "loaded" : "idle")
      : view === "playlists"
        ? (library.playlistsLoaded ? "loaded" : "idle")
        : (library.searchHasRun ? "loaded" : "idle"),
  });

  if (view === "liked" && !library.likedLoaded) return loadLikedSongs();
  if (view === "playlists" && !library.playlistsLoaded) return loadPlaylists();
  if (view === "search") {
    requestAnimationFrame(() => document.querySelector("#track-search-input")?.focus());
  } else {
    focusLibraryIndex(0);
  }
}

async function loadLikedSongs(offset = 0) {
  const existing = store.getState().library.likedTracks;
  setLibrary({ status: "loading", message: "", selectedIndex: 0 });
  try {
    const payload = await api.getLikedTracks({ offset, limit: 50 });
    const tracks = Array.isArray(payload.items)
      ? payload.items.map(normalizeTrack).filter((item) => item.id || item.uri)
      : [];
    setLibrary({
      status: "loaded",
      likedLoaded: true,
      likedTracks: offset ? appendUniqueTracks(existing, tracks) : tracks,
      likedPagination: normalizePagination(payload.pagination),
    });
    focusLibraryIndex(offset ? existing.length : 0);
  } catch (error) {
    if (expireSession(error)) return;
    setLibrary({ status: "error", message: errorMessage(error) });
  }
}

async function loadMoreLikedSongs() {
  const nextOffset = store.getState().library.likedPagination?.next_offset;
  if (!Number.isInteger(nextOffset) || nextOffset < 0) return;
  await loadLikedSongs(nextOffset);
}

async function searchTracks(candidate) {
  const query = candidate.trim().replace(/\s+/g, " ");
  if (!query) {
    return setLibrary({
      view: "search",
      status: "error",
      message: "Enter a song, artist, or album to search.",
      searchHasRun: false,
    });
  }
  setLibrary({
    view: "search",
    status: "loading",
    message: "",
    searchQuery: query,
    selectedIndex: 0,
  });
  try {
    const payload = await api.searchTracks(query, { limit: 10 });
    const results = Array.isArray(payload.items)
      ? payload.items.map(normalizeTrack).filter((item) => item.id || item.uri)
      : [];
    setLibrary({
      status: "loaded",
      searchHasRun: true,
      searchQuery: String(payload.query || query),
      searchResults: results,
    });
    focusLibraryIndex(0);
  } catch (error) {
    if (expireSession(error)) return;
    setLibrary({
      status: "error",
      searchHasRun: true,
      message: errorMessage(error),
    });
  }
}

function openPanel(panel) {
  store.update((state) => ({ ...state, panel }));
  requestAnimationFrame(() => {
    const selector = panel === "library" ? "#library-panel button" : panel === "settings" ? "#settings-panel input" : null;
    if (selector) document.querySelector(selector)?.focus();
  });
}

async function loadPlaylists() {
  setLibrary({ level: "playlists", status: "loading", message: "", selectedIndex: 0 });
  try {
    const playlists = (await api.getPlaylists()).map(normalizePlaylist).filter((item) => item.id);
    setLibrary({
      status: "loaded",
      playlistsLoaded: true,
      playlists,
      tracks: [],
      selectedPlaylist: null,
    });
    focusLibraryIndex(0);
  } catch (error) {
    if (expireSession(error)) return;
    setLibrary({ status: "error", message: errorMessage(error) });
  }
}

async function openPlaylist(index) {
  const playlist = store.getState().library.playlists[index];
  if (!playlist) return;
  setLibrary({
    view: "playlists",
    level: "tracks",
    status: "loading",
    message: "",
    selectedPlaylist: playlist,
    tracks: [],
    selectedIndex: 0,
  });
  try {
    const tracks = (await api.getTracks(playlist.id)).map(normalizeTrack).filter((item) => item.id || item.uri);
    setLibrary({ status: "loaded", tracks });
    focusLibraryIndex(0);
  } catch (error) {
    if (expireSession(error)) return;
    setLibrary({ status: "error", message: errorMessage(error) });
  }
}

async function startTrack(index) {
  const state = store.getState();
  const track = activeLibraryItems(state.library)[index];
  const deviceId = state.player.deviceId;
  if (!track || track.available === false) return;
  if (!spotifyPlayer || !deviceId) {
    return setNotice("The browser player is not ready yet. Wait a moment, then try again.");
  }

  try {
    // Spotify requires activation to happen in the user's click/key gesture call stack.
    await spotifyPlayer.activateElement();
    await api.startPlayback({
      device_id: deviceId,
      context_uri: playbackContextUri(state.library),
      track_uri: track.uri,
    });
    setNotice(null);
    openPanel(null);
  } catch (error) {
    if (expireSession(error)) return;
    setNotice(errorMessage(error));
  }
}

async function runPlayerCommand(method) {
  if (!spotifyPlayer || typeof spotifyPlayer[method] !== "function") {
    return setNotice("The browser player is not ready yet.");
  }
  try {
    await spotifyPlayer[method]();
    setNotice(null);
  } catch (error) {
    setNotice(errorMessage(error));
  }
}

function libraryBack() {
  const state = store.getState();
  if (state.library.view === "playlists" && state.library.level === "tracks") {
    const priorIndex = Math.max(0, state.library.playlists.findIndex((item) => item.id === state.library.selectedPlaylist?.id));
    setLibrary({
      level: "playlists",
      status: "loaded",
      message: "",
      tracks: [],
      selectedPlaylist: null,
      selectedIndex: priorIndex,
    });
    focusLibraryIndex(priorIndex);
  } else {
    openPanel(null);
  }
}

function moveLibraryFocus(offset) {
  const buttons = [...document.querySelectorAll("[data-library-index]:not(:disabled)")];
  if (!buttons.length) return;
  const currentIndex = buttons.indexOf(document.activeElement);
  const nextIndex = (currentIndex + offset + buttons.length) % buttons.length;
  const libraryIndex = Number(buttons[nextIndex].dataset.libraryIndex);
  selectLibraryIndex(libraryIndex);
  focusLibraryIndex(libraryIndex);
}

function focusLibraryIndex(index) {
  requestAnimationFrame(() => {
    document.querySelector(`[data-library-index="${index}"]:not(:disabled)`)?.focus();
  });
}

function selectLibraryIndex(selectedIndex) {
  setLibrary({ selectedIndex });
}

function toggleMode() {
  const current = store.getState().preferences;
  setPreferences({ ...current, mode: current.mode === "expanded" ? "compact" : "expanded" });
}

function setPreferences(candidate) {
  const preferences = savePreferences(candidate);
  applyPreferences(preferences);
  store.update((state) => ({ ...state, preferences }));
}

async function logout() {
  try {
    spotifyPlayer?.disconnect();
    await api.logout();
    window.location.assign("/");
  } catch (error) {
    setNotice(errorMessage(error));
  }
}

function setLibrary(patch) {
  store.update((state) => updateSection(state, "library", patch));
}

function setNotice(notice) {
  store.update((state) => ({ ...state, notice }));
}

function normalizePlaylist(item) {
  return {
    id: String(item.id || ""),
    uri: String(item.uri || ""),
    name: String(item.name || "Untitled playlist"),
    imageUrl: String(item.image_url || item.imageUrl || item.images?.[0]?.url || ""),
    ownerName: String(item.owner_name || item.ownerName || item.owner?.display_name || ""),
    trackCount: Number(item.track_count ?? item.trackCount ?? item.tracks?.total),
    eligible: item.eligible !== false,
    unavailableReason: String(item.unavailable_reason || ""),
    spotifyUrl: String(item.spotify_url || item.spotifyUrl || item.external_urls?.spotify || ""),
  };
}

function normalizeTrack(item) {
  const track = item.track || item;
  return {
    id: String(track.id || ""),
    uri: String(track.uri || ""),
    title: String(track.name || track.title || "Unknown track"),
    artists: Array.isArray(track.artists)
      ? track.artists.map((artist) => String(artist.name || artist)).filter(Boolean).join(", ")
      : String(track.artist || "Unknown artist"),
    album: String(track.album?.name || track.album || ""),
    artworkUrl: String(track.artwork_url || track.artworkUrl || track.album?.image_url || track.album?.images?.[0]?.url || ""),
    spotifyUrl: String(track.external_urls?.spotify || track.spotify_url || track.spotifyUrl || ""),
    available: item.available ?? !track.is_local,
  };
}

function normalizePagination(value) {
  const pagination = value && typeof value === "object" ? value : {};
  const rawNextOffset = pagination.next_offset;
  const nextOffset = Number(rawNextOffset);
  return {
    offset: Number.isInteger(Number(pagination.offset)) ? Number(pagination.offset) : 0,
    limit: Number.isInteger(Number(pagination.limit)) ? Number(pagination.limit) : 0,
    total: Number.isInteger(Number(pagination.total)) ? Number(pagination.total) : 0,
    next_offset: rawNextOffset !== null
      && rawNextOffset !== undefined
      && Number.isInteger(nextOffset)
      && nextOffset >= 0
      ? nextOffset
      : null,
  };
}

function errorMessage(error) {
  if (error instanceof ApiError || error instanceof Error) return error.message;
  return "Something unexpected happened. Please try again.";
}

function expireSession(error) {
  if (!(error instanceof ApiError) || error.status !== 401) return false;
  spotifyPlayer?.disconnect();
  spotifyPlayer = null;
  setCsrfToken("");
  store.update((state) => ({
    ...state,
    session: {
      ...state.session,
      authenticated: false,
      error: error.message,
    },
    panel: null,
    player: {
      ...state.player,
      status: "idle",
      deviceId: null,
      paused: true,
      error: null,
    },
  }));
  return true;
}

function readAuthenticationError() {
  const url = new URL(window.location.href);
  const message = authenticationErrorMessage(url.searchParams.get("auth_error"));
  if (url.searchParams.has("auth_error")) {
    url.searchParams.delete("auth_error");
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  }
  return message;
}
