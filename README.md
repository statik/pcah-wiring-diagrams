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

## Formats and editing

The diagram ships in three formats in `diagrams/`:

- **`pcah-video-wall.excalidraw`** — open at [excalidraw.com](https://excalidraw.com)
  (File → Open, or drag the file in), in VS Code with the Excalidraw extension,
  or in Obsidian.
- **`pcah-video-wall.drawio`** — open at [app.diagrams.net](https://app.diagrams.net)
  or in the draw.io desktop app.
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
