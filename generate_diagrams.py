"""Generate wiring diagrams for the PCAH video distribution system.

Writes each diagram to diagrams/ in three formats: .excalidraw (editable),
.drawio (editable in diagrams.net), and .svg (read-only, embedded in the
README). Uses only the standard library.

Run: python3 generate_diagrams.py
"""

import json
import random
from pathlib import Path
from xml.sax.saxutils import escape

random.seed(20260702)

UPDATED = 1751500000000
ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

INK = "#1e1e1e"
RED = "#e03131"
BLUE = "#1971c2"
GREEN = "#2f9e44"
ORANGE = "#f08c00"
PURPLE = "#9c36b5"
PURPLE_BG = "#eebefa"
GRAY = "#495057"
GRAY_BG = "#e9ecef"
BLUE_BG = "#a5d8ff"
RED_BG = "#ffc9c9"

CONV_W, CONV_H = 130, 70
TV_W, TV_H = 120, 60
CONV_LABEL = "BLACKMAGIC\nSDI → HDMI"
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


def _svg_shape(el):
    fill = "none" if el["backgroundColor"] == "transparent" else el["backgroundColor"]
    common = f'fill="{fill}" stroke="{el["strokeColor"]}" stroke-width="{el["strokeWidth"]}"'
    x, y, w, h = el["x"], el["y"], el["width"], el["height"]
    if el["type"] == "rectangle":
        return [f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="10" {common}/>']
    cx, cy = x + w / 2, y + h / 2
    return [f'<ellipse cx="{cx:g}" cy="{cy:g}" rx="{w / 2:g}" ry="{h / 2:g}" {common}/>']


def _svg_text(el):
    parts = []
    size = el["fontSize"]
    line_h = size * 1.25
    lines = el["text"].split("\n")
    for i, line in enumerate(lines):
        if el["textAlign"] == "center":
            x = el["x"] + el["width"] / 2
            y = el["y"] + el["height"] / 2 + line_h * (i - (len(lines) - 1) / 2)
            anchor = ' text-anchor="middle" dominant-baseline="central"'
        else:
            x = el["x"]
            y = el["y"] + line_h * i + size * 0.9
            anchor = ""
        parts.append(
            f'<text x="{x:g}" y="{y:g}" font-size="{size}" fill="{el["strokeColor"]}"{anchor}>'
            f"{escape(line)}</text>"
        )
    return parts


def _svg_linear(el):
    pts = " ".join(f"{el['x'] + px:g},{el['y'] + py:g}" for px, py in el["points"])
    marker = f' marker-end="url(#arrow-{el["strokeColor"][1:]})"' if el["endArrowhead"] else ""
    return [
        f'<polyline points="{pts}" fill="none" stroke="{el["strokeColor"]}" '
        f'stroke-width="{el["strokeWidth"]}"{marker}/>'
    ]


def render_svg(elements):
    """Standalone SVG document for a diagram's elements (viewable on GitHub)."""
    xs, ys = [], []
    for el in elements:
        xs += [el["x"], el["x"] + el["width"]]
        ys += [el["y"], el["y"] + el["height"]]
    x0, y0 = min(xs) - 20, min(ys) - 20
    w, h = max(xs) - x0 + 20, max(ys) - y0 + 20
    colors = sorted({el["strokeColor"] for el in elements if el["type"] == "arrow"})
    markers = "".join(
        f'<marker id="arrow-{c[1:]}" markerWidth="9" markerHeight="7" refX="8" refY="3.5" '
        f'orient="auto"><path d="M0,0 L9,3.5 L0,7 Z" fill="{c}"/></marker>'
        for c in colors
    )
    draw = {
        "rectangle": _svg_shape,
        "ellipse": _svg_shape,
        "text": _svg_text,
        "arrow": _svg_linear,
        "line": _svg_linear,
    }
    body = "".join("".join(draw[el["type"]](el)) for el in elements)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:g} {y0:g} {w:g} {h:g}" '
        f'font-family="Helvetica, Arial, sans-serif"><defs>{markers}</defs>'
        f'<rect x="{x0:g}" y="{y0:g}" width="{w:g}" height="{h:g}" fill="#ffffff"/>{body}</svg>\n'
    )


def _xa(s):
    """Escape a string for use inside a double-quoted XML attribute."""
    return escape(s, {'"': "&quot;"})


def _drawio_vertex(el, label):
    geo = (
        f'<mxGeometry x="{el["x"]:g}" y="{el["y"]:g}" width="{el["width"]:g}" '
        f'height="{el["height"]:g}" as="geometry"/>'
    )
    if el["type"] == "text":
        style = (
            f"text;html=1;align=left;verticalAlign=top;"
            f"fontSize={el['fontSize']};fontColor={el['strokeColor']};"
        )
        value = _xa(el["text"]).replace("\n", "&lt;br&gt;")
    else:
        shape = "ellipse;" if el["type"] == "ellipse" else "rounded=1;"
        fill = "none" if el["backgroundColor"] == "transparent" else el["backgroundColor"]
        style = (
            f"{shape}whiteSpace=wrap;html=1;fillColor={fill};"
            f"strokeColor={el['strokeColor']};strokeWidth={el['strokeWidth']};"
        )
        value = ""
        if label:
            style += f"fontColor={label['strokeColor']};fontSize={label['fontSize']};"
            value = _xa(label["text"]).replace("\n", "&lt;br&gt;")
    return (
        f'<mxCell id="{el["id"]}" value="{value}" style="{style}" vertex="1" parent="1">'
        f"{geo}</mxCell>"
    )


def _drawio_edge(el, by_id):
    end = "block" if el["endArrowhead"] else "none"
    style = (
        f"edgeStyle=none;rounded=0;html=1;strokeColor={el['strokeColor']};"
        f"strokeWidth={el['strokeWidth']};endArrow={end};endFill=1;"
    )
    pts = [(el["x"] + px, el["y"] + py) for px, py in el["points"]]
    attrs = ""
    geo = ['<mxGeometry relative="1" as="geometry">']
    for binding, point, prefix, role in (
        (el["startBinding"], pts[0], "exit", "source"),
        (el["endBinding"], pts[-1], "entry", "target"),
    ):
        if binding:
            attrs += f' {role}="{binding["elementId"]}"'
            b = by_id[binding["elementId"]]
            rx = round((point[0] - b["x"]) / b["width"], 3)
            ry = round((point[1] - b["y"]) / b["height"], 3)
            style += f"{prefix}X={rx:g};{prefix}Y={ry:g};{prefix}Dx=0;{prefix}Dy=0;"
        else:
            geo.append(f'<mxPoint x="{point[0]:g}" y="{point[1]:g}" as="{role}Point"/>')
    if len(pts) > 2:
        mids = "".join(f'<mxPoint x="{x:g}" y="{y:g}"/>' for x, y in pts[1:-1])
        geo.append(f'<Array as="points">{mids}</Array>')
    geo.append("</mxGeometry>")
    return (
        f'<mxCell id="{el["id"]}" style="{style}" edge="1" parent="1"{attrs}>'
        f"{''.join(geo)}</mxCell>"
    )


def render_drawio(elements, name):
    """draw.io / diagrams.net document (uncompressed mxGraph XML)."""
    by_id = {el["id"]: el for el in elements}
    labels = {el["containerId"]: el for el in elements if el.get("containerId")}
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    for el in elements:
        if el["type"] in ("arrow", "line"):
            cells.append(_drawio_edge(el, by_id))
        elif el["type"] == "text" and el.get("containerId"):
            continue
        else:
            cells.append(_drawio_vertex(el, labels.get(el["id"])))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="app.diagrams.net" type="device">'
        f'<diagram id="{new_id()}" name="{_xa(name)}">'
        '<mxGraphModel dx="800" dy="600" grid="0" gridSize="10" guides="1" tooltips="1" '
        'connect="1" arrows="1" fold="1" page="0" pageScale="1" math="0" shadow="0">'
        f"<root>{''.join(cells)}</root></mxGraphModel></diagram></mxfile>\n"
    )


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


def converter_display(d, x, conv_y, tv_y, tv_num):
    """Converter + display pair: HDMI down to the TV, USB power back up from it."""
    conv = d.rect(x, conv_y, CONV_W, CONV_H, CONV_LABEL, stroke=PURPLE, bg=PURPLE_BG, font=12)
    tv = d.rect(x + (CONV_W - TV_W) / 2, tv_y, TV_W, TV_H, f"TV {tv_num}", font=16)
    d.arrow([bottom(conv, -25), top(tv, -25)], GREEN, start=conv, end=tv)
    d.arrow([top(tv, 25), bottom(conv, 25)], ORANGE, start=tv, end=conv)
    return conv, tv


def power_distribution():
    """Electric power only: two feeds, three splitters, ten TVs in 3/3/4 clusters."""
    d = Diagram()
    d.text(30, 10, "PCAH Video Wall — Power Distribution (10 Displays)", size=24)
    p1 = power_source(d, "POWER 1", 30, 90)
    spl_a = d.rect(190, 80, 400, 50, SPLITTER_LABEL, stroke=GRAY, bg=GRAY_BG)
    spl_b = d.rect(830, 80, 420, 50, SPLITTER_LABEL, stroke=GRAY, bg=GRAY_BG)
    d.arrow([right(p1), left(spl_a)], RED, start=p1, end=spl_a)
    d.arrow([right(spl_a), left(spl_b)], RED, start=spl_a, end=spl_b)
    p2 = power_source(d, "POWER 2", 30, 410)
    spl_c = d.rect(190, 400, 600, 50, SPLITTER_LABEL, stroke=GRAY, bg=GRAY_BG)
    d.arrow([right(p2), left(spl_c)], RED, start=p2, end=spl_c)

    clusters = (
        (spl_a, 200, 1, (140, 320, 500)),
        (spl_b, 200, 4, (800, 980, 1160)),
        (spl_c, 520, 7, (140, 320, 500, 680)),
    )
    for spl, tv_y, first_num, xs in clusters:
        for i, x in enumerate(xs):
            tv = d.rect(x, tv_y, TV_W, TV_H, f"TV {first_num + i}", font=16)
            d.arrow([(x + TV_W / 2, spl["y"] + spl["height"]), top(tv)], RED, start=spl, end=tv)

    d.text(
        190,
        620,
        "Converters draw power from the TVs' USB ports — see 04-full-system.",
        size=13,
        color=GRAY,
    )
    legend(
        d,
        140,
        670,
        [
            ("line", RED, "POWER"),
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
            ("box", PURPLE, PURPLE_BG, "BLACKMAGIC SDI → HDMI CONVERTER"),
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
            ("box", PURPLE, PURPLE_BG, "BLACKMAGIC SDI → HDMI CONVERTER"),
            ("box", GRAY, GRAY_BG, "SDI DISTRIBUTION AMP"),
            ("box", INK, "transparent", "DISPLAY"),
        ],
    )
    return d


def full_system():
    """Power + signal for all ten displays, arranged in 3/3/4 clusters.

    Splitters power the TVs; each converter is powered from its TV's USB port
    and receives video over a daisy-chained SDI run.
    """
    d = Diagram()
    d.text(30, 10, "PCAH Video Wall — Full System: Power + SDI Signal (10 Displays)", size=24)
    p1 = power_source(d, "POWER 1", 30, 90)
    spl_a = d.rect(270, 80, 440, 50, SPLITTER_LABEL, stroke=GRAY, bg=GRAY_BG)
    spl_b = d.rect(930, 80, 440, 50, SPLITTER_LABEL, stroke=GRAY, bg=GRAY_BG)
    d.arrow([right(p1), left(spl_a)], RED, start=p1, end=spl_a)
    d.arrow([right(spl_a), left(spl_b)], RED, start=spl_a, end=spl_b)
    p2 = power_source(d, "POWER 2", 30, 560)
    spl_c = d.rect(270, 550, 600, 50, SPLITTER_LABEL, stroke=GRAY, bg=GRAY_BG)
    d.arrow([right(p2), left(spl_c)], RED, start=p2, end=spl_c)

    clusters = (
        (spl_a, 210, 360, (140, 320, 500)),
        (spl_b, 210, 360, (800, 980, 1160)),
        (spl_c, 680, 830, (140, 320, 500, 680)),
    )
    convs = []
    for spl, conv_y, tv_y, xs in clusters:
        for x in xs:
            conv, tv = converter_display(d, x, conv_y, tv_y, len(convs) + 1)
            tv_mid = tv_y + TV_H / 2
            d.arrow(
                [(x + 160, spl["y"] + spl["height"]), (x + 160, tv_mid), (x + 125, tv_mid)],
                RED,
                start=spl,
                end=tv,
            )
            convs.append(conv)

    source = d.rect(5, 215, 110, 60, "SDI SOURCE", stroke=BLUE, bg=BLUE_BG, font=12)
    d.arrow([right(source), left(convs[0])], BLUE, start=source, end=convs[0])
    for i in (0, 1, 2, 3, 4, 6, 7, 8):
        d.arrow([right(convs[i]), left(convs[i + 1])], BLUE, start=convs[i], end=convs[i + 1])
    d.arrow(
        [right(convs[5]), (1350, 245), (1350, 630), (80, 630), (80, 715), left(convs[6])],
        BLUE,
        start=convs[5],
        end=convs[6],
    )

    legend(
        d,
        40,
        960,
        [
            ("line", BLUE, "SDI DAISY CHAIN"),
            ("line", RED, "POWER"),
            ("line", GREEN, "HDMI"),
            ("line", ORANGE, "USB-A → USB-C (CONVERTER POWER FROM TV)"),
            ("box", PURPLE, PURPLE_BG, "BLACKMAGIC SDI → HDMI CONVERTER"),
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
        (out / f"{name}.svg").write_text(render_svg(diagram.elements))
        (out / f"{name}.drawio").write_text(render_drawio(diagram.elements, name))
        print(f"wrote diagrams/{name}.{{excalidraw,svg,drawio}} ({len(diagram.elements)} elements)")


if __name__ == "__main__":
    main()
