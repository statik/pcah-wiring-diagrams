"""Generate Excalidraw wiring diagrams for the PCAH video distribution system.

Writes .excalidraw JSON files into diagrams/. Uses only the standard library.

Run: python3 generate_diagrams.py
"""

import json
import random
from pathlib import Path

random.seed(20260702)

UPDATED = 1751500000000
ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

INK = "#1e1e1e"
RED = "#e03131"
BLUE = "#1971c2"
GREEN = "#2f9e44"
PURPLE = "#9c36b5"
PURPLE_BG = "#eebefa"
GRAY = "#495057"
GRAY_BG = "#e9ecef"
BLUE_BG = "#a5d8ff"
RED_BG = "#ffc9c9"

CONV_W, CONV_H = 130, 70
TV_W, TV_H = 120, 60
CONV_LABEL = "SDI TO\nHDMI\nCONVERTER"
SPLITTER_LABEL = "8-WAY POWER SPLITTER"


def new_id():
    return "".join(random.choices(ALPHABET, k=16))


def text_box_size(content, font_size):
    lines = content.split("\n")
    width = max(len(line) for line in lines) * font_size * 0.6
    return width, len(lines) * font_size * 1.25


def top(el, dx=0):
    return (el["x"] + el["width"] / 2 + dx, el["y"])


def bottom(el, dx=0):
    return (el["x"] + el["width"] / 2 + dx, el["y"] + el["height"])


def left(el, dy=0):
    return (el["x"], el["y"] + el["height"] / 2 + dy)


def right(el, dy=0):
    return (el["x"] + el["width"], el["y"] + el["height"] / 2 + dy)


class Diagram:
    """Accumulates Excalidraw elements and serializes them to a .excalidraw file."""

    def __init__(self):
        self.elements = []

    def _base(self, kind, x, y, w, h, stroke, bg):
        el = {
            "id": new_id(),
            "type": kind,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "angle": 0,
            "strokeColor": stroke,
            "backgroundColor": bg,
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": None,
            "seed": random.randint(1, 2**31 - 1),
            "version": 1,
            "versionNonce": random.randint(1, 2**31 - 1),
            "isDeleted": False,
            "boundElements": [],
            "updated": UPDATED,
            "link": None,
            "locked": False,
        }
        self.elements.append(el)
        return el

    def rect(self, x, y, w, h, label=None, *, stroke=INK, bg="transparent", font=14):
        el = self._base("rectangle", x, y, w, h, stroke, bg)
        el["roundness"] = {"type": 3}
        if label:
            self._bind_label(el, label, font)
        return el

    def ellipse(self, x, y, w, h, *, stroke=INK, bg="transparent"):
        return self._base("ellipse", x, y, w, h, stroke, bg)

    def _bind_label(self, container, content, font):
        tw, th = text_box_size(content, font)
        tw = min(tw, container["width"] - 8)
        t = self._base(
            "text",
            container["x"] + container["width"] / 2 - tw / 2,
            container["y"] + container["height"] / 2 - th / 2,
            tw,
            th,
            container["strokeColor"],
            "transparent",
        )
        t.update(
            {
                "text": content,
                "originalText": content,
                "fontSize": font,
                "fontFamily": 1,
                "textAlign": "center",
                "verticalAlign": "middle",
                "containerId": container["id"],
                "autoResize": True,
                "lineHeight": 1.25,
            }
        )
        container["boundElements"].append({"id": t["id"], "type": "text"})

    def text(self, x, y, content, *, size=16, color=INK):
        tw, th = text_box_size(content, size)
        t = self._base("text", x, y, tw, th, color, "transparent")
        t.update(
            {
                "text": content,
                "originalText": content,
                "fontSize": size,
                "fontFamily": 1,
                "textAlign": "left",
                "verticalAlign": "top",
                "containerId": None,
                "autoResize": True,
                "lineHeight": 1.25,
            }
        )
        return t

    def _linear(self, kind, pts, color, head, width):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, y0 = pts[0]
        el = self._base(kind, x0, y0, max(xs) - min(xs), max(ys) - min(ys), color, "transparent")
        el["roundness"] = {"type": 2}
        el["strokeWidth"] = width
        el.update(
            {
                "points": [[px - x0, py - y0] for px, py in pts],
                "lastCommittedPoint": None,
                "startBinding": None,
                "endBinding": None,
                "startArrowhead": None,
                "endArrowhead": head,
            }
        )
        return el

    def arrow(self, pts, color, *, start=None, end=None, width=2):
        el = self._linear("arrow", pts, color, "triangle", width)
        if start is not None:
            el["startBinding"] = {"elementId": start["id"], "focus": 0, "gap": 1}
            start["boundElements"].append({"id": el["id"], "type": "arrow"})
        if end is not None:
            el["endBinding"] = {"elementId": end["id"], "focus": 0, "gap": 1}
            end["boundElements"].append({"id": el["id"], "type": "arrow"})
        return el

    def line(self, pts, color, *, width=2):
        return self._linear("line", pts, color, None, width)

    def save(self, path):
        doc = {
            "type": "excalidraw",
            "version": 2,
            "source": "pcah-wiring-diagrams generate_diagrams.py",
            "elements": self.elements,
            "appState": {"gridSize": 20, "viewBackgroundColor": "#ffffff"},
            "files": {},
        }
        path.write_text(json.dumps(doc, indent=2) + "\n")


def validate(diagram):
    """Check element ids are unique and every cross-reference resolves."""
    ids = [el["id"] for el in diagram.elements]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate element ids")
    known = set(ids)
    for el in diagram.elements:
        refs = [b["id"] for b in el["boundElements"]]
        refs += [el[k]["elementId"] for k in ("startBinding", "endBinding") if el.get(k)]
        if el.get("containerId"):
            refs.append(el["containerId"])
        missing = [r for r in refs if r not in known]
        if missing:
            raise ValueError(f"element {el['id']} has dangling references: {missing}")


def display_column(d, x, conv_y, tv_y, tv_num):
    """One converter feeding one display over HDMI; returns (converter, tv)."""
    conv = d.rect(x, conv_y, CONV_W, CONV_H, CONV_LABEL, stroke=PURPLE, bg=PURPLE_BG, font=12)
    tv = d.rect(x + (CONV_W - TV_W) / 2, tv_y, TV_W, TV_H, f"TV {tv_num}", font=16)
    d.arrow([bottom(conv), top(tv)], GREEN, start=conv, end=tv)
    return conv, tv


def power_source(d, label, x, y):
    """Label plus a red power-jack circle; returns the circle (center at y + 15)."""
    d.text(x, y + 5, label, size=16, color=INK)
    return d.ellipse(x + 90, y, 30, 30, stroke=RED, bg=RED_BG)


def legend(d, x, y, entries):
    """Horizontal legend strip. Entries: ('line', color, label) or ('box', stroke, bg, label)."""
    cx = x + 25
    mid = y + 35
    for entry in entries:
        if entry[0] == "line":
            _, color, label = entry
            d.line([(cx, mid), (cx + 45, mid)], color, width=3)
            cx += 55
        else:
            _, stroke, bg, label = entry
            d.rect(cx, mid - 14, 34, 28, stroke=stroke, bg=bg)
            cx += 44
        t = d.text(cx, mid - 9, label, size=13)
        cx += t["width"] + 40
    d.rect(x, y, cx - x - 10, 70)


def power_backbone(d):
    """Two power feeds, three 8-way splitters, ten converter+display columns.

    Returns the ten (converter, tv) pairs in TV order. Shared by the
    power-distribution and full-system diagrams.
    """
    columns = []
    p1 = power_source(d, "POWER 1", 30, 90)
    spl_a = d.rect(190, 80, 400, 50, SPLITTER_LABEL, stroke=GRAY, bg=GRAY_BG)
    spl_b = d.rect(725, 80, 580, 50, SPLITTER_LABEL, stroke=GRAY, bg=GRAY_BG)
    d.arrow([right(p1), left(spl_a)], RED, start=p1, end=spl_a)
    d.arrow([right(spl_a), left(spl_b)], RED, start=spl_a, end=spl_b)
    for i in range(7):
        x = 140 + 180 * i
        spl = spl_a if i < 3 else spl_b
        col = display_column(d, x, 210, 360, i + 1)
        d.arrow([(x + CONV_W / 2, 130), top(col[0])], RED, start=spl, end=col[0])
        columns.append(col)

    p2 = power_source(d, "POWER 2", 30, 560)
    spl_c = d.rect(190, 550, 400, 50, SPLITTER_LABEL, stroke=GRAY, bg=GRAY_BG)
    d.arrow([right(p2), left(spl_c)], RED, start=p2, end=spl_c)
    for i in range(3):
        x = 140 + 180 * i
        col = display_column(d, x, 680, 830, i + 8)
        d.arrow([(x + CONV_W / 2, 600), top(col[0])], RED, start=spl_c, end=col[0])
        columns.append(col)
    return columns


def power_distribution():
    d = Diagram()
    d.text(30, 10, "PCAH Video Wall — Power Distribution (10 Displays)", size=24)
    power_backbone(d)
    legend(
        d,
        140,
        960,
        [
            ("line", RED, "POWER"),
            ("line", GREEN, "HDMI"),
            ("box", PURPLE, PURPLE_BG, "SDI TO HDMI CONVERTER"),
            ("box", GRAY, GRAY_BG, SPLITTER_LABEL),
            ("box", INK, "transparent", "DISPLAY"),
        ],
    )
    return d


def sdi_daisy_chain():
    d = Diagram()
    d.text(30, 0, "PCAH Video Wall — SDI Daisy Chain (8 Displays)", size=24)
    p1 = power_source(d, "POWER 1", 30, 50)
    p2 = power_source(d, "POWER 2", 30, 110)
    source = d.rect(40, 230, 150, 70, "SDI SOURCE", stroke=BLUE, bg=BLUE_BG)

    cols = []
    for row, (conv_y, tv_y) in enumerate(((230, 390), (560, 720))):
        for i in range(4):
            cols.append(display_column(d, 260 + 200 * i, conv_y, tv_y, row * 4 + i + 1))
    convs = [conv for conv, _ in cols]

    d.arrow([right(source), left(convs[0])], BLUE, start=source, end=convs[0])
    for i in (0, 1, 2, 4, 5, 6):
        d.arrow([right(convs[i]), left(convs[i + 1])], BLUE, start=convs[i], end=convs[i + 1])
    d.arrow(
        [right(convs[3]), (1060, 265), (1060, 485), (200, 485), (200, 595), left(convs[4])],
        BLUE,
        start=convs[3],
        end=convs[4],
    )

    d.line([right(p1), (925, 65)], RED)
    d.line([right(p2), (225, 125), (225, 515), (925, 515)], RED)
    for i in range(4):
        cx = 325 + 200 * i
        d.arrow([(cx, 65), (cx, 230)], RED, end=convs[i])
        d.arrow([(cx, 515), (cx, 560)], RED, end=convs[4 + i])

    legend(
        d,
        40,
        850,
        [
            ("line", BLUE, "SDI (INPUT/THROUGH)"),
            ("line", RED, "POWER"),
            ("line", GREEN, "HDMI"),
            ("box", PURPLE, PURPLE_BG, "SDI TO HDMI CONVERTER"),
            ("box", BLUE, BLUE_BG, "SDI SOURCE"),
            ("box", INK, "transparent", "DISPLAY"),
        ],
    )
    return d


def sdi_distribution_amps():
    d = Diagram()
    d.text(30, 0, "PCAH Video Wall — SDI Distribution Amps (8 Displays)", size=24)
    p1 = power_source(d, "POWER 1", 30, 40)
    p2 = power_source(d, "POWER 2", 30, 95)
    source = d.rect(40, 175, 150, 60, "SDI SOURCE", stroke=BLUE, bg=BLUE_BG)
    da1 = d.rect(245, 180, 760, 50, "SDI DISTRIBUTION AMP (1 IN → 4 OUT)", stroke=GRAY, bg=GRAY_BG)
    da2 = d.rect(245, 560, 760, 50, "SDI DISTRIBUTION AMP (1 IN → 4 OUT)", stroke=GRAY, bg=GRAY_BG)

    d.arrow([right(source), left(da1)], BLUE, start=source, end=da1)
    d.arrow([right(p1), (300, 55), (300, 180)], RED, start=p1, end=da1)
    d.arrow([right(p2), (215, 110), (215, 525), (300, 525), (300, 560)], RED, start=p2, end=da2)
    d.arrow(
        [right(da1), (1080, 205), (1080, 500), (200, 500), (200, 585), left(da2)],
        BLUE,
        start=da1,
        end=da2,
    )

    for row, (da, conv_y, tv_y) in enumerate(((da1, 280, 430), (da2, 680, 830))):
        for i in range(4):
            cx = 260 + 200 * i + CONV_W / 2
            conv, _ = display_column(d, 260 + 200 * i, conv_y, tv_y, row * 4 + i + 1)
            d.arrow([(cx, da["y"] + da["height"]), (cx, conv_y)], BLUE, start=da, end=conv)

    d.text(
        245,
        920,
        "Converter power feeds not shown here — see 01-power-distribution.",
        size=13,
        color=GRAY,
    )
    legend(
        d,
        40,
        960,
        [
            ("line", BLUE, "SDI"),
            ("line", RED, "POWER"),
            ("line", GREEN, "HDMI"),
            ("box", PURPLE, PURPLE_BG, "SDI TO HDMI CONVERTER"),
            ("box", GRAY, GRAY_BG, "SDI DISTRIBUTION AMP"),
            ("box", INK, "transparent", "DISPLAY"),
        ],
    )
    return d


def full_system():
    d = Diagram()
    d.text(30, 10, "PCAH Video Wall — Full System: Power + SDI Signal (10 Displays)", size=24)
    columns = power_backbone(d)
    convs = [conv for conv, _ in columns]

    source = d.rect(5, 215, 110, 60, "SDI SOURCE", stroke=BLUE, bg=BLUE_BG, font=12)
    d.arrow([right(source), left(convs[0])], BLUE, start=source, end=convs[0])
    for i in (0, 1, 2, 3, 4, 5, 7, 8):
        d.arrow([right(convs[i]), left(convs[i + 1])], BLUE, start=convs[i], end=convs[i + 1])
    d.arrow(
        [right(convs[6]), (1410, 245), (1410, 645), (90, 645), (90, 715), left(convs[7])],
        BLUE,
        start=convs[6],
        end=convs[7],
    )

    legend(
        d,
        140,
        960,
        [
            ("line", BLUE, "SDI (INPUT/THROUGH)"),
            ("line", RED, "POWER"),
            ("line", GREEN, "HDMI (+ USB → USB-C POWER)"),
            ("box", PURPLE, PURPLE_BG, "SDI TO HDMI CONVERTER"),
            ("box", GRAY, GRAY_BG, SPLITTER_LABEL),
        ],
    )
    return d


def main():
    out = Path(__file__).parent / "diagrams"
    out.mkdir(exist_ok=True)
    diagrams = {
        "01-power-distribution": power_distribution(),
        "02-sdi-daisy-chain": sdi_daisy_chain(),
        "03-sdi-distribution-amps": sdi_distribution_amps(),
        "04-full-system": full_system(),
    }
    for name, diagram in diagrams.items():
        validate(diagram)
        diagram.save(out / f"{name}.excalidraw")
        print(f"wrote diagrams/{name}.excalidraw ({len(diagram.elements)} elements)")


if __name__ == "__main__":
    main()
