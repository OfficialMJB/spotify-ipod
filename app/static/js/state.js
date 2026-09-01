export function createInitialState(preferences) {
  return {
    session: {
      loading: true,
      authenticated: false,
      configured: true,
      user: null,
      error: null,
    },
    panel: null,
    library: {
      view: "liked",
      level: "playlists",
      status: "idle",
      message: "",
      playlists: [],
      playlistsLoaded: false,
      tracks: [],
      likedTracks: [],
      likedLoaded: false,
      likedPagination: null,
      searchResults: [],
      searchQuery: "",
      searchHasRun: false,
      selectedPlaylist: null,
      selectedIndex: 0,
    },
    player: {
      status: "idle",
      deviceId: null,
      paused: true,
      track: null,
      position: 0,
      duration: 0,
      updatedAt: null,
      error: null,
    },
    preferences,
    notice: null,
  };
}

export function createStore(initialState) {
  let state = initialState;
  const listeners = new Set();

  return {
    getState() {
      return state;
    },

    update(updater) {
      const nextState = typeof updater === "function" ? updater(state) : updater;
      if (!nextState || Object.is(nextState, state)) return state;
      state = nextState;
      listeners.forEach((listener) => listener(state));
      return state;
    },

    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

export function updateSection(state, section, patch) {
  return {
    ...state,
    [section]: {
      ...state[section],
      ...patch,
    },
  };
}

export function authenticationErrorMessage(code) {
  const messages = {
    invalid_state: "The sign-in response could not be verified. Please try signing in again.",
    access_denied: "Spotify access was declined. You can retry when you are ready.",
    invalid_scope: "Spotify rejected one or more requested permissions. Check the app configuration and retry.",
    spotify_temporarily_unavailable: "Spotify's authorization service is temporarily unavailable. Please retry.",
    authorization_request_invalid: "Spotify rejected this application's authorization request. Recheck the Client ID and redirect URI.",
    missing_code: "Spotify did not return the authorization needed to sign in. Please retry.",
    authorization_failed: "Spotify sign-in could not be completed. Please try again.",
  };
  return messages[code] || null;
}
