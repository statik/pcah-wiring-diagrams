# PCAH Wiring Diagrams

The wiring diagram for the PCAH video wall: an SDI source daisy-chained through
a Blackmagic SDI→HDMI converter at each of 10 displays, arranged in three
clusters (3 top-left, 3 top-right, 4 below), with shared power distribution.

How each display is wired:

- **Red** — electric power from the wall feeds, through 8-way power splitters,
  to each TV.
- **Blue** — the SDI video feed, daisy-chained converter to converter through
  their SDI through ports.
- **Green** — the HDMI cable into the TV plus the USB-A → USB-C cable the
  converter uses to draw power from the TV; the arrowhead shows that power
  draw, from the TV into the converter.

![PCAH video wall wiring diagram](diagrams/pcah-video-wall.svg)

**[Open in draw.io](https://app.diagrams.net/#Uhttps%3A%2F%2Fraw.githubusercontent.com%2Fstatik%2Fpcah-wiring-diagrams%2Fmain%2Fdiagrams%2Fpcah-video-wall.drawio)**
— edits a copy in the browser; use File → Save As to keep your changes. To edit
and commit straight back to this repo, use the
[GitHub-connected editor](https://app.diagrams.net/#Hstatik%2Fpcah-wiring-diagrams%2Fmain%2Fdiagrams%2Fpcah-video-wall.drawio)
(asks to authorize GitHub on first use).

**[Download the PNG](diagrams/pcah-video-wall.png?raw=true)** — the draw.io
diagram is embedded inside the PNG, so the image can be shared anywhere and
still opened for editing at [app.diagrams.net](https://app.diagrams.net).

## Formats and editing

The diagram ships in four formats in `diagrams/`:

- **`pcah-video-wall.excalidraw`** — open at [excalidraw.com](https://excalidraw.com)
  (File → Open, or drag the file in), in VS Code with the Excalidraw extension,
  or in Obsidian.
- **`pcah-video-wall.drawio`** — use the "Open in draw.io" link above, or open
  the file at [app.diagrams.net](https://app.diagrams.net) / in the draw.io
  desktop app.
- **`pcah-video-wall.png`** — downloadable image with the draw.io diagram
  embedded; drag it into app.diagrams.net to edit.
- **`pcah-video-wall.svg`** — read-only export, embedded above and viewable in
  any browser.

## Regenerating from code

All three files are produced by [generate_diagrams.py](generate_diagrams.py)
(standard library only), which is the easiest way to make structural changes
like adding a display column or re-spacing a row:

```sh
python3 generate_diagrams.py
```

The formats don't sync with each other: a hand edit in one format won't appear
in the others (or survive a regeneration), so structural edits belong in the
script.
