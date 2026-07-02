"""Export the PCAH video wall diagram from its draw.io source.

diagrams/pcah-video-wall.drawio is the master file — edit it in draw.io, then
run this script to refresh the derived formats:

  .svg        — embedded in the README (rendered by the draw.io CLI)
  .png        — downloadable, with the diagram embedded (draw.io CLI)
  .excalidraw — converted from the draw.io XML for Excalidraw users

The SVG/PNG steps shell out to the draw.io desktop app and are skipped with a
notice if it isn't installed; the Excalidraw conversion is pure standard
library.

Run: python3 export_diagrams.py
"""

import base64
import html
import json
import random
import re
import shutil
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

random.seed(20260702)

UPDATED = 1751500000000
ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
INK = "#1e1e1e"
DRAWIO_BINARIES = ("drawio", "/Applications/draw.io.app/Contents/MacOS/draw.io")


def new_id():
    return "".join(random.choices(ALPHABET, k=16))


def text_box_size(content, font_size):
    lines = content.split("\n")
    width = max(len(line) for line in lines) * font_size * 0.6
    return width, len(lines) * font_size * 1.25


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

    def rect(
        self, x, y, w, h, label=None, *, stroke=INK, bg="transparent", font=14, label_color=None
    ):
        el = self._base("rectangle", x, y, w, h, stroke, bg)
        el["roundness"] = {"type": 3}
        if label:
            self._bind_label(el, label, font, label_color or stroke)
        return el

    def ellipse(
        self, x, y, w, h, label=None, *, stroke=INK, bg="transparent", font=14, label_color=None
    ):
        el = self._base("ellipse", x, y, w, h, stroke, bg)
        if label:
            self._bind_label(el, label, font, label_color or stroke)
        return el

    def _bind_label(self, container, content, font, color):
        tw, th = text_box_size(content, font)
        tw = min(tw, container["width"] - 8)
        t = self._base(
            "text",
            container["x"] + container["width"] / 2 - tw / 2,
            container["y"] + container["height"] / 2 - th / 2,
            tw,
            th,
            color,
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

    def arrow(self, pts, color, *, start=None, end=None, width=2, head="triangle"):
        el = self._linear("arrow", pts, color, head, width)
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
            "source": "pcah-wiring-diagrams export_diagrams.py",
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


def load_cells(path):
    """Return the mxCell elements from a .drawio file (compressed or plain)."""
    diagram = ET.parse(path).getroot().find("diagram")
    model = diagram.find("mxGraphModel")
    if model is None:
        packed = base64.b64decode(diagram.text.strip())
        model = ET.fromstring(urllib.parse.unquote(zlib.decompress(packed, -15).decode()))
    return model.find("root").findall("mxCell")


def parse_style(style):
    parsed = {}
    for item in (style or "").split(";"):
        if item:
            key, _, value = item.partition("=")
            parsed[key] = value
    return parsed


def label_text(value):
    if not value:
        return None
    text = re.sub(r"<br\s*/?>", "\n", value)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text) or None


def center(el):
    return (el["x"] + el["width"] / 2, el["y"] + el["height"] / 2)


def point_attr(geometry, role):
    for p in geometry.findall("mxPoint"):
        if p.get("as") == role:
            return (float(p.get("x", 0)), float(p.get("y", 0)))
    return None


def fixed_point(el, style, prefix):
    """Absolute coordinates of a draw.io exitX/exitY (or entryX/entryY) anchor."""
    if not style.get(f"{prefix}X"):
        return None
    return (
        el["x"] + float(style[f"{prefix}X"]) * el["width"],
        el["y"] + float(style[f"{prefix}Y"]) * el["height"],
    )


def border_point(el, toward):
    """Where a line from the element's center toward a point crosses its border."""
    cx, cy = center(el)
    dx, dy = toward[0] - cx, toward[1] - cy
    scales = [el["width"] / 2 / abs(dx)] if dx else []
    scales += [el["height"] / 2 / abs(dy)] if dy else []
    if not scales:
        return (cx, cy)
    return (cx + dx * min(scales), cy + dy * min(scales))


def anchor(el, style, prefix, geometry, role, hint):
    """Resolve one end of an edge to absolute coordinates."""
    if el is None:
        return point_attr(geometry, role) or hint
    return fixed_point(el, style, prefix) or border_point(el, hint or center(el))


def convert_vertex(d, cell):
    style = parse_style(cell.get("style"))
    g = cell.find("mxGeometry")
    x, y = float(g.get("x", 0)), float(g.get("y", 0))
    w, h = float(g.get("width", 0)), float(g.get("height", 0))
    text = label_text(cell.get("value"))
    if "text" in style:
        size = int(style.get("fontSize", 16))
        return d.text(x, y, text or "", size=size, color=style.get("fontColor", INK))
    stroke = style.get("strokeColor", INK)
    fill = style.get("fillColor", "none")
    shape = d.ellipse if "ellipse" in style else d.rect
    return shape(
        x,
        y,
        w,
        h,
        text,
        stroke=stroke,
        bg="transparent" if fill == "none" else fill,
        font=int(style.get("fontSize", 14)),
        label_color=style.get("fontColor", stroke),
    )


def convert_edge(d, cell, by_id):
    style = parse_style(cell.get("style"))
    g = cell.find("mxGeometry")
    waypoints = [
        (float(p.get("x")), float(p.get("y")))
        for arr in g.findall("Array")
        if arr.get("as") == "points"
        for p in arr.findall("mxPoint")
    ]
    src = by_id.get(cell.get("source"))
    tgt = by_id.get(cell.get("target"))
    start_hint = waypoints[0] if waypoints else (center(tgt) if tgt is not None else None)
    start = anchor(src, style, "exit", g, "sourcePoint", start_hint)
    end = anchor(tgt, style, "entry", g, "targetPoint", waypoints[-1] if waypoints else start)
    pts = [start, *waypoints, end]
    color = style.get("strokeColor", INK)
    width = int(style.get("strokeWidth", 1))
    headless = style.get("endArrow") == "none"
    if headless and src is None and tgt is None:
        d.line(pts, color, width=width)
    else:
        d.arrow(pts, color, start=src, end=tgt, width=width, head=None if headless else "triangle")


def convert_to_excalidraw(cells):
    d = Diagram()
    by_id = {}
    for cell in cells:
        if cell.get("vertex") == "1":
            by_id[cell.get("id")] = convert_vertex(d, cell)
    for cell in cells:
        if cell.get("edge") == "1":
            convert_edge(d, cell, by_id)
    return d


def export_via_drawio(master):
    """Render SVG and editable PNG with the draw.io CLI; skip if not installed."""
    binary = next((b for b in DRAWIO_BINARIES if shutil.which(b)), None)
    if binary is None:
        print("draw.io app not found — skipped SVG/PNG export (install draw.io desktop)")
        return False
    for fmt, extra in (
        ("svg", ["--embed-svg-fonts", "false", "--svg-theme", "light"]),
        ("png", ["-s", "2", "--embed-diagram"]),
    ):
        out = master.with_suffix(f".{fmt}")
        subprocess.run(
            [binary, "-x", "-f", fmt, *extra, "-o", str(out), str(master)],
            check=True,
            capture_output=True,
        )
    svg_path = master.with_suffix(".svg")
    svg = re.sub(
        r"(<svg[^>]*>)",
        r'\1<rect fill="#ffffff" width="100%" height="100%"/>',
        svg_path.read_text(),
        count=1,
    )
    svg_path.write_text(svg.rstrip("\n") + "\n")
    return True


def main():
    master = Path(__file__).parent / "diagrams" / "pcah-video-wall.drawio"
    diagram = convert_to_excalidraw(load_cells(master))
    validate(diagram)
    diagram.save(master.with_suffix(".excalidraw"))
    formats = "{excalidraw,svg,png}" if export_via_drawio(master) else "{excalidraw}"
    print(f"exported diagrams/pcah-video-wall.{formats} from the .drawio master")


if __name__ == "__main__":
    main()
