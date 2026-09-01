import { applyPreferences } from "./preferences.js";
import { formatTime, projectedPosition } from "./player.js";

export function createRenderer(documentObject = document) {
  const elements = {
    welcome: documentObject.querySelector("#welcome-view"),
    player: documentObject.querySelector("#player-view"),
    login: documentObject.querySelector("#login-link"),
    configurationNote: documentObject.querySelector("#configuration-note"),
    status: documentObject.querySelector("#status-region"),
    authenticatedOnly: [...documentObject.querySelectorAll("[data-authenticated-only]")],
    artwork: documentObject.querySelector("#artwork"),
    artworkPlaceholder: documentObject.querySelector("#artwork-placeholder"),
    playbackLabel: documentObject.querySelector("#playback-label"),
    trackTitle: documentObject.querySelector("#track-title"),
    trackArtist: documentObject.querySelector("#track-artist"),
    trackAlbum: documentObject.querySelector("#track-album"),
    spotifyLink: documentObject.querySelector("#spotify-link"),
    progress: documentObject.querySelector("#track-progress"),
    position: documentObject.querySelector("#position-time"),
    duration: documentObject.querySelector("#duration-time"),
    playButton: documentObject.querySelector('[data-action="toggle-playback"]'),
    playIcon: documentObject.querySelector("[data-play-icon]"),
    previous: documentObject.querySelector('[data-action="previous"]'),
    next: documentObject.querySelector('[data-action="next"]'),
    modeLabel: documentObject.querySelector("[data-mode-label]"),
    modeButton: documentObject.querySelector('[data-action="toggle-mode"]'),
    libraryPanel: documentObject.querySelector("#library-panel"),
    settingsPanel: documentObject.querySelector("#settings-panel"),
    libraryLevel: documentObject.querySelector("#library-level"),
    libraryTitle: documentObject.querySelector("#library-title"),
    libraryMessage: documentObject.querySelector("#library-message"),
    libraryList: documentObject.querySelector("#library-list"),
    preferenceInputs: [...documentObject.querySelectorAll("#preferences-form input")],
  };

  let currentState = null;
  let progressFrame = null;
  const requestFrame = documentObject.defaultView?.requestAnimationFrame?.bind(documentObject.defaultView);

  return function render(state) {
    currentState = state;
    applyPreferences(state.preferences, documentObject.documentElement);
    renderSession(elements, state);
    renderNotice(elements, state);
    renderPlayer(elements, state);
    renderPanels(elements, state);
    renderLibrary(elements, state, documentObject);
    renderPreferences(elements, state);
    if (requestFrame && progressFrame === null && shouldAnimateProgress(state.player)) {
      progressFrame = requestFrame(updateProgress);
    }
  };

  function updateProgress() {
    progressFrame = null;
    if (!currentState) return;
    renderProgress(elements, currentState.player);
    if (requestFrame && shouldAnimateProgress(currentState.player)) {
      progressFrame = requestFrame(updateProgress);
    }
  }
}

function renderSession(elements, state) {
  const { loading, authenticated, configured } = state.session;
  elements.welcome.hidden = authenticated;
  elements.player.hidden = !authenticated;
  elements.login.hidden = loading || !configured;
  elements.login.setAttribute("aria-disabled", String(loading || !configured));
  elements.configurationNote.hidden = configured || loading;
  elements.authenticatedOnly.forEach((element) => { element.hidden = !authenticated; });
}

function renderNotice(elements, state) {
  const message = state.notice || state.session.error || state.player.error;
  elements.status.hidden = !message;
  elements.status.textContent = message || "";
}

function renderPlayer(elements, state) {
  const { player } = state;
  const track = player.track;
  elements.playbackLabel.textContent = player.status === "connecting"
    ? "Connecting player"
    : track
      ? (player.paused ? "Paused" : "Now playing")
      : (player.status === "ready" ? "Player ready" : "Nothing playing");
  elements.trackTitle.textContent = track?.title || "Choose a track";
  elements.trackTitle.title = track?.title || "";
  elements.trackArtist.textContent = track?.artists || "Open your library to get started";
  elements.trackArtist.title = track?.artists || "";
  elements.trackAlbum.textContent = track?.album || "";
  elements.trackAlbum.title = track?.album || "";

  const artworkUrl = safeHttpUrl(track?.artworkUrl);
  elements.artwork.hidden = !artworkUrl;
  elements.artworkPlaceholder.hidden = Boolean(artworkUrl);
  if (artworkUrl) {
    if (elements.artwork.src !== artworkUrl) elements.artwork.src = artworkUrl;
    elements.artwork.alt = `Album artwork for ${track.album || track.title}`;
  } else {
    elements.artwork.removeAttribute("src");
    elements.artwork.alt = "";
  }

  elements.spotifyLink.href = safeSpotifyUrl(track?.spotifyUrl) || "https://open.spotify.com/";
  renderProgress(elements, player);

  const canControl = player.status === "ready" && Boolean(player.deviceId);
  elements.playButton.disabled = !canControl;
  elements.previous.disabled = !canControl;
  elements.next.disabled = !canControl;
  elements.playIcon.textContent = player.paused ? "▶" : "❚❚";
  elements.playButton.setAttribute("aria-label", player.paused ? "Play" : "Pause");
  const nextMode = state.preferences.mode === "expanded" ? "compact" : "expanded";
  elements.modeLabel.textContent = titleCase(nextMode);
  elements.modeButton.setAttribute("aria-label", `Switch to ${nextMode} player`);
}

function renderProgress(elements, player) {
  const position = projectedPosition(player);
  elements.progress.max = Math.max(player.duration, 1);
  elements.progress.value = Math.min(position, player.duration || 0);
  elements.position.textContent = formatTime(position);
  elements.duration.textContent = formatTime(player.duration);
}

function shouldAnimateProgress(player) {
  return player.status === "ready"
    && !player.paused
    && player.duration > 0
    && projectedPosition(player) < player.duration;
}

function renderPanels(elements, state) {
  elements.libraryPanel.hidden = state.panel !== "library";
  elements.settingsPanel.hidden = state.panel !== "settings";
}

function renderLibrary(elements, state, documentObject) {
  const library = state.library;
  const isTracks = library.level === "tracks";
  elements.libraryLevel.textContent = isTracks ? "Playlist" : "Your library";
  elements.libraryTitle.textContent = isTracks ? library.selectedPlaylist?.name || "Tracks" : "Playlists";
  elements.libraryMessage.textContent = libraryMessage(library);
  elements.libraryMessage.hidden = !elements.libraryMessage.textContent;
  elements.libraryList.replaceChildren();

  const items = isTracks ? library.tracks : library.playlists;
  for (const [index, item] of items.entries()) {
    const listItem = documentObject.createElement("li");
    listItem.className = "library-item";
    const button = documentObject.createElement("button");
    button.type = "button";
    button.dataset.libraryIndex = String(index);
    button.dataset.libraryKind = isTracks ? "track" : "playlist";
    button.setAttribute("aria-current", String(index === library.selectedIndex));
    button.disabled = isTracks ? item.available === false : item.eligible === false;
    button.title = item.name || item.title || "";

    const thumbnail = documentObject.createElement("span");
    thumbnail.className = "library-thumbnail";
    const imageUrl = safeHttpUrl(item.imageUrl || item.artworkUrl);
    if (imageUrl) {
      const image = documentObject.createElement("img");
      image.src = imageUrl;
      image.alt = "";
      thumbnail.append(image);
    } else {
      thumbnail.textContent = isTracks ? "♪" : "♫";
    }

    const copy = documentObject.createElement("span");
    copy.className = "library-copy";
    const primary = documentObject.createElement("strong");
    primary.textContent = item.name || item.title || "Untitled";
    const secondary = documentObject.createElement("small");
    secondary.textContent = isTracks
      ? (item.available === false ? "Unavailable" : item.artists || "Unknown artist")
      : (item.eligible === false ? item.unavailableReason || "Unavailable in development mode" : playlistDescription(item));
    copy.append(primary, secondary);

    const chevron = documentObject.createElement("span");
    chevron.className = "library-chevron";
    chevron.setAttribute("aria-hidden", "true");
    chevron.textContent = isTracks ? "▶" : "›";
    button.append(thumbnail, copy, chevron);
    listItem.append(button);
    const spotifyUrl = safeSpotifyUrl(item.spotifyUrl);
    if (spotifyUrl) {
      const spotifyLink = documentObject.createElement("a");
      spotifyLink.className = "library-spotify-link";
      spotifyLink.href = spotifyUrl;
      spotifyLink.target = "_blank";
      spotifyLink.rel = "noopener noreferrer";
      spotifyLink.setAttribute("aria-label", `Open ${item.name || item.title || "item"} in Spotify`);
      spotifyLink.textContent = "↗";
      listItem.append(spotifyLink);
    }
    elements.libraryList.append(listItem);
  }
}

function renderPreferences(elements, state) {
  elements.preferenceInputs.forEach((input) => {
    input.checked = state.preferences[input.name] === input.value;
  });
}

function libraryMessage(library) {
  if (library.status === "loading") return library.level === "tracks" ? "Loading tracks…" : "Loading playlists…";
  if (library.status === "error") return library.message || "The library could not be loaded.";
  if (library.status === "loaded") {
    const items = library.level === "tracks" ? library.tracks : library.playlists;
    if (!items.length) return library.level === "tracks" ? "This playlist has no available tracks." : "No eligible playlists were found.";
  }
  return "";
}

function playlistDescription(playlist) {
  if (playlist.ownerName) return `By ${playlist.ownerName}`;
  if (Number.isFinite(Number(playlist.trackCount))) return `${Number(playlist.trackCount)} tracks`;
  return "Playlist";
}

function safeHttpUrl(value) {
  if (!value) return "";
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}

function safeSpotifyUrl(value) {
  const url = safeHttpUrl(value);
  if (!url) return "";
  try {
    const host = new URL(url).hostname;
    return host === "open.spotify.com" || host.endsWith(".spotify.com") ? url : "";
  } catch {
    return "";
  }
}

function titleCase(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
