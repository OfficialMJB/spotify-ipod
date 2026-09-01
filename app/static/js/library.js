const LIBRARY_VIEWS = new Set(["liked", "playlists", "search"]);

export function normalizeLibraryView(value) {
  return LIBRARY_VIEWS.has(value) ? value : "liked";
}

export function activeLibraryItems(library) {
  const view = normalizeLibraryView(library?.view);
  if (view === "liked") return library?.likedTracks || [];
  if (view === "search") return library?.searchResults || [];
  return library?.level === "tracks"
    ? library?.tracks || []
    : library?.playlists || [];
}

export function playbackContextUri(library) {
  return normalizeLibraryView(library?.view) === "playlists"
    && library?.level === "tracks"
    ? library?.selectedPlaylist?.uri || null
    : null;
}

export function appendUniqueTracks(existing, incoming) {
  const merged = [...(existing || [])];
  const keys = new Set(merged.map(trackKey).filter(Boolean));
  for (const track of incoming || []) {
    const key = trackKey(track);
    if (key && keys.has(key)) continue;
    merged.push(track);
    if (key) keys.add(key);
  }
  return merged;
}

function trackKey(track) {
  return track?.uri || track?.id || null;
}
