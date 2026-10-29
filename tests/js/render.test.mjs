import assert from "node:assert/strict";
import test from "node:test";

import { createRenderer } from "../../app/static/js/render.js";
import { createInitialState, updateSection } from "../../app/static/js/state.js";

function createDocument() {
  const nodes = new Map();
  const documentObject = { activeElement: null, documentElement: { dataset: {} } };

  function element() {
    return {
      children: [],
      dataset: {},
      isConnected: true,
      src: "",
      setAttribute() {},
      removeAttribute() {},
      append(...children) {
        for (const child of children) {
          child.isConnected = this.isConnected;
          this.children.push(child);
        }
      },
      replaceChildren(...children) {
        for (const child of this.children) {
          child.isConnected = false;
          for (const descendant of child.children) descendant.isConnected = false;
        }
        this.children = [];
        this.append(...children);
      },
      focus() { documentObject.activeElement = this; },
    };
  }

  documentObject.querySelector = (selector) => {
    if (!nodes.has(selector)) nodes.set(selector, element());
    return nodes.get(selector);
  };
  documentObject.querySelectorAll = () => [];
  documentObject.createElement = element;
  return documentObject;
}

test("player updates preserve the focused library item while library updates still render", () => {
  const documentObject = createDocument();
  const render = createRenderer(documentObject);
  let state = createInitialState({ mode: "expanded", theme: "pocket", accent: "green" });
  state = updateSection(state, "library", {
    view: "liked",
    status: "loaded",
    likedTracks: [{ id: "one", title: "First song", artists: "Artist" }],
  });
  render(state);

  const list = documentObject.querySelector("#library-list");
  const firstButton = list.children[0].children[0];
  firstButton.focus();
  state = updateSection(state, "player", {
    status: "ready",
    deviceId: "device",
    paused: true,
    track: { title: "Now playing song", artists: "New artist", album: "New album" },
    position: 30_000,
    duration: 180_000,
  });
  render(state);

  assert.equal(documentObject.activeElement, firstButton);
  assert.equal(list.children[0].children[0], firstButton);
  assert.equal(firstButton.isConnected, true);
  assert.equal(documentObject.querySelector("#track-title").textContent, "Now playing song");
  assert.equal(documentObject.querySelector("#track-artist").textContent, "New artist");
  assert.equal(documentObject.querySelector("#position-time").textContent, "0:30");
  assert.equal(documentObject.querySelector("#duration-time").textContent, "3:00");
  assert.equal(documentObject.querySelector('[data-action="toggle-playback"]').disabled, false);

  state = updateSection(state, "library", {
    likedTracks: [...state.library.likedTracks, { id: "two", title: "Second song", artists: "Artist" }],
  });
  render(state);
  assert.equal(list.children.length, 2);
  assert.notEqual(list.children[0].children[0], firstButton);
});
