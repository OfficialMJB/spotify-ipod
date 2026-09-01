# ADR 0001: Shift to a customizable pocket player

- **Status:** Accepted
- **Date:** 2026-08-30

## Context

The original concept used a literal iPod-inspired body and click-wheel layout. During UX planning, that direction began constraining the player size, interaction model, and visual identity. The project goal is a cool custom Spotify interface, not a recreation of a particular hardware product.

## Decision

Build a compact, customizable Spotify-connected player with its own visual identity.

The MVP will include:

- Compact and expanded player modes
- A focused playlist and track browser
- Pocket, Minimal, and Retro preset themes
- One accessible accent-color preference
- Local persistence for application-owned appearance preferences

The MVP will not include a free-form layout editor, arbitrary CSS, user-created themes, drag-and-drop controls, or theme sharing.

## Why

- A distinct design is more original and avoids forcing every interaction into a click-wheel metaphor.
- Compact and expanded modes demonstrate responsive UI and state-management skills.
- Bounded presets provide meaningful customization without turning the MVP into a design-tool project.
- Keeping behavior consistent across themes makes accessibility and testing manageable.

## Consequences

- The repository name `spotify-ipod` may remain during development, but the public product name must be reconsidered.
- Diagram 01 needs a `Customize player` use case.
- Diagram 02 needs compact/expanded mode and customization branches.
- Diagrams 03-08 must be drawn for the new direction: compact player, expanded player, library browser, customization, welcome/authorization, and system states.
- Previously generated iPod-body reference PDFs are superseded and must not be used as authoritative tracing references.
- Spotify authentication, playlist access, playback integration, security, and policy requirements remain unchanged.
