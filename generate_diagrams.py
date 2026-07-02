"""Generate the wiring diagram for the PCAH video wall.

Writes the diagram to diagrams/ in four formats: .excalidraw (editable),
.drawio (editable in diagrams.net), .svg (read-only, embedded in the README),
and .png with the draw.io diagram embedded (downloadable and still editable).
Uses only the standard library; the PNG export shells out to the draw.io
desktop app and is skipped if it isn't installed.

Run: python3 generate_diagrams.py
"""

import json
import random
import shutil
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

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
    """Converter + display pair.

    One green run carries HDMI plus the USB-A → USB-C power cable; the
    arrowhead shows the power draw from the TV into the converter.
    """
    conv = d.rect(x, conv_y, CONV_W, CONV_H, CONV_LABEL, stroke=PURPLE, bg=PURPLE_BG, font=12)
    tv = d.rect(x + (CONV_W - TV_W) / 2, tv_y, TV_W, TV_H, f"TV {tv_num}", font=16)
    d.arrow([top(tv), bottom(conv)], GREEN, start=tv, end=conv)
    return conv, tv


def video_wall():
    """Power + signal for all ten displays, arranged in 3/3/4 clusters.

    Power strips sit below each TV cluster and feed up into the TVs, keeping
    the red power runs clear of the blue SDI daisy chain, which enters the
    bottom cluster from the right and runs right to left.
    """
    d = Diagram()
    d.text(30, 10, "PCAH Video Wall — Power + SDI Signal (10 Displays)", size=24)

    clusters = (
        (210, 360, (140, 320, 500)),
        (210, 360, (800, 980, 1160)),
        (680, 830, (140, 320, 500, 680)),
    )
    columns = []
    for conv_y, tv_y, xs in clusters:
        for x in xs:
            columns.append(converter_display(d, x, conv_y, tv_y, len(columns) + 1))
    convs = [conv for conv, _ in columns]
    tvs = [tv for _, tv in columns]

    p1 = power_source(d, "POWER 1", 30, 480)
    spl_a = d.rect(175, 470, 420, 50, SPLITTER_LABEL, stroke=GRAY, bg=GRAY_BG)
    spl_b = d.rect(835, 470, 420, 50, SPLITTER_LABEL, stroke=GRAY, bg=GRAY_BG)
    d.arrow([right(p1), left(spl_a)], RED, start=p1, end=spl_a)
    d.arrow([right(spl_a), left(spl_b)], RED, start=spl_a, end=spl_b)
    p2 = power_source(d, "POWER 2", 30, 950)
    spl_c = d.rect(175, 940, 600, 50, SPLITTER_LABEL, stroke=GRAY, bg=GRAY_BG)
    d.arrow([right(p2), left(spl_c)], RED, start=p2, end=spl_c)
    for tv, spl in zip(tvs, [spl_a] * 3 + [spl_b] * 3 + [spl_c] * 4, strict=True):
        d.arrow([(tv["x"] + TV_W / 2, spl["y"]), bottom(tv)], RED, start=spl, end=tv)

    source = d.rect(5, 215, 110, 60, "SDI SOURCE", stroke=BLUE, bg=BLUE_BG, font=12)
    d.arrow([right(source), left(convs[0])], BLUE, start=source, end=convs[0])
    for i in range(5):
        d.arrow([right(convs[i]), left(convs[i + 1])], BLUE, start=convs[i], end=convs[i + 1])
    d.arrow(
        [right(convs[5]), (1350, 245), (1350, 715), right(convs[9])],
        BLUE,
        start=convs[5],
        end=convs[9],
    )
    for i in (9, 8, 7):
        d.arrow([left(convs[i]), right(convs[i - 1])], BLUE, start=convs[i], end=convs[i - 1])

    legend(
        d,
        40,
        1060,
        [
            ("line", BLUE, "SDI DAISY CHAIN"),
            ("line", RED, "POWER"),
            ("line", GREEN, "HDMI + USB-C POWER (FROM TV)"),
            ("box", PURPLE, PURPLE_BG, "BLACKMAGIC SDI → HDMI CONVERTER"),
            ("box", GRAY, GRAY_BG, SPLITTER_LABEL),
            ("box", INK, "transparent", "DISPLAY"),
        ],
    )
    return d


DRAWIO_BINARIES = ("drawio", "/Applications/draw.io.app/Contents/MacOS/draw.io")


def export_editable_png(drawio_path, png_path):
    """Render a PNG with the draw.io diagram embedded, so the PNG itself is editable.

    Returns False (with a notice) when the draw.io desktop app isn't installed.
    """
    binary = next((b for b in DRAWIO_BINARIES if shutil.which(b)), None)
    if binary is None:
        print("draw.io app not found — skipped PNG export (install draw.io desktop to enable)")
        return False
    subprocess.run(
        [binary, "-x", "-f", "png", "-s", "2", "--embed-diagram", "-o", png_path, drawio_path],
        check=True,
        capture_output=True,
    )
    return True


def main():
    out = Path(__file__).parent / "diagrams"
    out.mkdir(exist_ok=True)
    diagram = video_wall()
    validate(diagram)
    name = "pcah-video-wall"
    diagram.save(out / f"{name}.excalidraw")
    (out / f"{name}.svg").write_text(render_svg(diagram.elements))
    (out / f"{name}.drawio").write_text(render_drawio(diagram.elements, name))
    formats = "{excalidraw,svg,drawio,png}"
    if not export_editable_png(str(out / f"{name}.drawio"), str(out / f"{name}.png")):
        formats = "{excalidraw,svg,drawio}"
    print(f"wrote diagrams/{name}.{formats} ({len(diagram.elements)} elements)")


if __name__ == "__main__":
    main()
