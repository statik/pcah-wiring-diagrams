# PCAH Wiring Diagrams

Editable wiring diagrams for the PCAH video wall: an SDI source feeding
SDI-to-HDMI converters at each display, with shared power distribution.

The diagrams are [Excalidraw](https://excalidraw.com) files in `diagrams/`:

| File | What it shows |
|------|---------------|
| `01-power-distribution.excalidraw` | Two power feeds and three 8-way splitters powering 10 converter+display columns |
| `02-sdi-daisy-chain.excalidraw` | SDI source looped through 8 converters via their SDI through ports |
| `03-sdi-distribution-amps.excalidraw` | SDI source into 1→4 distribution amps feeding 8 converters |
| `04-full-system.excalidraw` | Combined view from the original whiteboard sketch: power + SDI daisy chain for all 10 displays |

## Editing

Any of these work — no account or install-to-server needed:

- **excalidraw.com** — open the site, then File → Open (or drag the `.excalidraw` file in).
  Save back with File → Save to disk.
- **VS Code** — install the "Excalidraw" extension and open the file directly.
- **Obsidian** — the Excalidraw plugin opens these files too.

## Regenerating from code

The files are produced by [generate_diagrams.py](generate_diagrams.py) (standard
library only), which is the easiest way to make structural changes like adding a
display column or re-spacing a row:

```sh
python3 generate_diagrams.py
```

Hand edits made in Excalidraw are fine too — just know that re-running the script
overwrites the files.

## Notes on the source material

These were redrawn from photos of AI-rendered diagrams plus the original
whiteboard sketch. A few things were tidied along the way:

- The source legends mislabeled colors (e.g. red marked as "POWER (3G/HD/SD-SDI)").
  Here red is always power, blue is always SDI, green is always HDMI.
- In the daisy-chain diagram, the power drops were regularized so POWER 1 feeds the
  top row and POWER 2 the bottom row.
- The distribution-amp diagram shows power to the amps only; converter power is
  covered by `01-power-distribution`.
- The whiteboard sketch notes that green also carries USB→USB-C power to the
  converters; the full-system legend preserves that.
