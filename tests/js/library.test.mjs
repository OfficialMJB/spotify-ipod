import assert from "node:assert/strict";
import test from "node:test";

import {
  activeLibraryItems,
  appendUniqueTracks,
  normalizeLibraryView,
  playbackContextUri,
} from "../../app/static/js/library.js";


test("library views expose the correct active items", () => {
  const library = {
    view: "liked",
    level: "playlists",
    likedTracks: [{ id: "liked" }],
    playlists: [{ id: "playlist" }],
    tracks: [{ id: "playlist-track" }],
    searchResults: [{ id: "search" }],
  };

  assert.equal(activeLibraryItems(library)[0].id, "liked");
  assert.equal(activeLibraryItems({ ...library, view: "search" })[0].id, "search");
  assert.equal(activeLibraryItems({ ...library, view: "playlists" })[0].id, "playlist");
  assert.equal(activeLibraryItems({ ...library, view: "playlists", level: "tracks" })[0].id, "playlist-track");
  assert.equal(normalizeLibraryView("unexpected"), "liked");
});


test("only playlist tracks provide playback context", () => {
  const library = {
    view: "playlists",
    level: "tracks",
    selectedPlaylist: { uri: "spotify:playlist:playlist123" },
  };

  assert.equal(playbackContextUri(library), "spotify:playlist:playlist123");
  assert.equal(playbackContextUri({ ...library, view: "liked" }), null);
  assert.equal(playbackContextUri({ ...library, view: "search" }), null);
});


test("liked-song pagination appends tracks without duplicates", () => {
  const result = appendUniqueTracks(
    [{ id: "one", uri: "spotify:track:one" }],
    [
      { id: "one-copy", uri: "spotify:track:one" },
      { id: "two", uri: "spotify:track:two" },
    ],
  );

  assert.deepEqual(result.map((track) => track.id), ["one", "two"]);
});
