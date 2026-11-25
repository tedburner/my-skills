#!/usr/bin/env python3
"""Deterministic XML, Z-order, orthogonal routing, and text/box overlap validator
for .svg and .drawio architecture diagrams.

Cross-platform using only the Python standard library.
Exit code: 0 when no [ERROR] is found, 1 otherwise.
"""

from __future__ import annotations

import argparse
import base64
import html
import math
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\b(?:TODO|FIXME|TBD)\b|\[PROJECT\]|<project>|\ufffd")
HTML_BR_RE = re.compile(r"<\s*br\s*/?\s*>|</\s*(?:p|div|li|tr)\s*>", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
SVG_TOKEN_RE = re.compile(r"[MmLlHhVvZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


@dataclass
class Box:
    cell_id: str
    parent_id: str
    x: float
    y: float
    w: float
    h: float
    style: str
    raw_value: str
    index: int


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def parse_style(style: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in style.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            result[k.strip()] = v.strip()
        else:
            result[part] = "1"
    return result


def html_to_lines(raw: str) -> list[str]:
    if not raw:
        return []
    unescaped = html.unescape(raw)
    with_breaks = HTML_BR_RE.sub("\n", unescaped)
    clean = HTML_TAG_RE.sub("", with_breaks)
    return [line.strip() for line in clean.splitlines() if line.strip()]


def estimate_line_px(text: str, font_size: float) -> float:
    width = 0.0
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff" or "\u3000" <= ch <= "\u303f" or "\uff00" <= ch <= "\uffef":
            width += font_size * 1.05
        else:
            width += font_size * 0.60
    return width


def extract_cjk_terms(text: str) -> set[str]:
    return set(CJK_RE.findall(text))


def check_svg_orthogonal_path(elem_id: str, d_attr: str, errors: list[str]) -> None:
    tokens = SVG_TOKEN_RE.findall(d_attr)
    cx, cy = 0.0, 0.0
    cmd = ""
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.isalpha():
            cmd = tok
            i += 1
            if cmd in ("Z", "z"):
                continue
            continue
        try:
            if cmd == "M":
                cx, cy = float(tokens[i]), float(tokens[i + 1])
                cmd = "L"
                i += 2
            elif cmd == "m":
                cx += float(tokens[i])
                cy += float(tokens[i + 1])
                cmd = "l"
                i += 2
            elif cmd == "L":
                nx, ny = float(tokens[i]), float(tokens[i + 1])
                dx, dy = abs(nx - cx), abs(ny - cy)
                if dx > 3.0 and dy > 3.0 and math.hypot(dx, dy) > 18.0:
                    errors.append(
                        f"SVG <path {elem_id}> has non-orthogonal diagonal segment "
                        f"({cx:.1f},{cy:.1f}) -> ({nx:.1f},{ny:.1f})"
                    )
                cx, cy = nx, ny
                i += 2
            elif cmd == "l":
                dx_raw, dy_raw = float(tokens[i]), float(tokens[i + 1])
                dx, dy = abs(dx_raw), abs(dy_raw)
                if dx > 3.0 and dy > 3.0 and math.hypot(dx, dy) > 18.0:
                    errors.append(
                        f"SVG <path {elem_id}> has non-orthogonal relative diagonal segment "
                        f"d=({dx_raw:.1f},{dy_raw:.1f})"
                    )
                cx += dx_raw
                cy += dy_raw
                i += 2
            elif cmd == "H":
                cx = float(tokens[i])
                i += 1
            elif cmd == "h":
                cx += float(tokens[i])
                i += 1
            elif cmd == "V":
                cy = float(tokens[i])
                i += 1
            elif cmd == "v":
                cy += float(tokens[i])
                i += 1
            else:
                i += 1
        except (IndexError, ValueError):
            break


def validate_svg(path: Path, errors: list[str], warnings: list[str]) -> set[str]:
    cjk_terms: set[str] = set()
    if not path.exists():
        errors.append(f"SVG file does not exist: {path}")
        return cjk_terms

    raw = path.read_text(encoding="utf-8", errors="replace")
    if PLACEHOLDER_RE.search(raw):
        errors.append(f"SVG contains unresolved placeholder or garbled character: {path.name}")

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        errors.append(f"SVG XML parse error in {path.name}: {exc}")
        return cjk_terms

    if strip_ns(root.tag).lower() != "svg":
        errors.append(f"SVG root element is <{strip_ns(root.tag)}>, expected <svg>")
        return cjk_terms

    if not (root.attrib.get("viewBox") or (root.attrib.get("width") and root.attrib.get("height"))):
        warnings.append("SVG root lacks both viewBox and explicit width/height attributes")

    first_text_idx: int | None = None
    late_edges = 0

    for idx, elem in enumerate(root.iter()):
        tag = strip_ns(elem.tag).lower()
        elem_id = f"id='{elem.attrib.get('id', f'#{idx}')}'"
        if tag == "text":
            if first_text_idx is None:
                first_text_idx = idx
            full_text = "".join(elem.itertext()).strip()
            cjk_terms.update(extract_cjk_terms(full_text))
            fs_str = elem.attrib.get("font-size", "").replace("px", "").strip()
            if fs_str:
                try:
                    if float(fs_str) < 10.0:
                        warnings.append(f"SVG <text {elem_id}> font-size={fs_str} is below 10px minimum")
                except ValueError:
                    pass
        elif tag in ("line", "polyline", "path"):
            in_defs = False
            # Marker paths inside <defs> are arrowheads, not diagram edges
            if tag == "path" and elem.attrib.get("d", "").strip().upper().endswith("Z"):
                d_val = elem.attrib.get("d", "")
                if len(d_val) < 40 and ("marker" in elem.attrib.get("id", "").lower() or "M 0" in d_val or "M0" in d_val):
                    in_defs = True
            if not in_defs and first_text_idx is not None:
                late_edges += 1
            if tag == "line":
                try:
                    x1 = float(elem.attrib.get("x1", "0"))
                    y1 = float(elem.attrib.get("y1", "0"))
                    x2 = float(elem.attrib.get("x2", "0"))
                    y2 = float(elem.attrib.get("y2", "0"))
                    if abs(x2 - x1) > 3.0 and abs(y2 - y1) > 3.0 and math.hypot(x2 - x1, y2 - y1) > 18.0:
                        errors.append(
                            f"SVG <line {elem_id}> is diagonal ({x1:.1f},{y1:.1f})->({x2:.1f},{y2:.1f})"
                        )
                except ValueError:
                    pass
            elif tag == "polyline":
                pts_raw = re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)", elem.attrib.get("points", ""))
                pts = [(float(pts_raw[j]), float(pts_raw[j + 1])) for j in range(0, len(pts_raw) - 1, 2)]
                for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                    if abs(x2 - x1) > 3.0 and abs(y2 - y1) > 3.0 and math.hypot(x2 - x1, y2 - y1) > 18.0:
                        errors.append(
                            f"SVG <polyline {elem_id}> has diagonal segment ({x1:.1f},{y1:.1f})->({x2:.1f},{y2:.1f})"
                        )
            elif tag == "path" and not in_defs:
                check_svg_orthogonal_path(elem_id, elem.attrib.get("d", ""), errors)

    if late_edges > 0:
        warnings.append(
            f"SVG has {late_edges} line/path element(s) placed after <text> nodes; "
            "place edges before cards/text so lines stay in the background layer"
        )

    return cjk_terms


def load_mxgraph_root(diagram_elem: ET.Element, errors: list[str]) -> ET.Element | None:
    for child in diagram_elem:
        if strip_ns(child.tag) == "mxGraphModel":
            return child
    encoded = (diagram_elem.text or "").strip()
    if not encoded:
        errors.append("Draw.io <diagram> contains neither <mxGraphModel> nor compressed payload")
        return None
    try:
        raw_bytes = base64.b64decode(encoded)
        inflated = zlib.decompress(raw_bytes, -15).decode("utf-8")
        xml_text = urllib.parse.unquote(inflated)
        return ET.fromstring(xml_text)
    except Exception as exc:
        errors.append(f"Failed to decode compressed Draw.io <diagram>: {exc}")
        return None


def validate_drawio(path: Path, errors: list[str], warnings: list[str]) -> set[str]:
    cjk_terms: set[str] = set()
    if not path.exists():
        errors.append(f"Draw.io file does not exist: {path}")
        return cjk_terms

    raw = path.read_text(encoding="utf-8", errors="replace")
    if PLACEHOLDER_RE.search(raw):
        errors.append(f"Draw.io contains unresolved placeholder or garbled character: {path.name}")

    try:
        xml_root = ET.fromstring(raw)
    except ET.ParseError as exc:
        errors.append(f"Draw.io XML parse error in {path.name}: {exc}")
        return cjk_terms

    if strip_ns(xml_root.tag) != "mxfile":
        errors.append(f"Draw.io root element is <{strip_ns(xml_root.tag)}>, expected <mxfile>")
        return cjk_terms

    diagrams = [elem for elem in xml_root.iter() if strip_ns(elem.tag) == "diagram"]
    if not diagrams:
        errors.append("Draw.io <mxfile> contains no <diagram> element")
        return cjk_terms

    graph_model = load_mxgraph_root(diagrams[0], errors)
    if graph_model is None:
        return cjk_terms

    cells = [elem for elem in graph_model.iter() if strip_ns(elem.tag) == "mxCell"]
    rel_boxes: dict[str, Box] = {}
    parent_children: dict[str, list[str]] = {}
    edges: list[tuple[int, ET.Element, dict[str, str]]] = []

    for idx, cell in enumerate(cells):
        cid = cell.attrib.get("id", f"cell_{idx}")
        style_str = cell.attrib.get("style", "")
        style_map = parse_style(style_str)
        val = cell.attrib.get("value", "")

        if "image" in style_map or "data:image" in style_str or style_map.get("shape") == "image":
            errors.append(f"Draw.io cell id='{cid}' embeds an image instead of native editable mxGraph shapes")

        for line in html_to_lines(val):
            cjk_terms.update(extract_cjk_terms(line))

        if cell.attrib.get("vertex") == "1":
            geom = next((c for c in cell if strip_ns(c.tag) == "mxGeometry"), None)
            if geom is None:
                continue
            try:
                x = float(geom.attrib.get("x", "0"))
                y = float(geom.attrib.get("y", "0"))
                w = float(geom.attrib.get("width", "0"))
                h = float(geom.attrib.get("height", "0"))
            except ValueError:
                errors.append(f"Draw.io vertex id='{cid}' has non-numeric mxGeometry")
                continue
            pid = cell.attrib.get("parent", "1")
            rel_boxes[cid] = Box(cid, pid, x, y, w, h, style_str, val, idx)
            parent_children.setdefault(pid, []).append(cid)
        elif cell.attrib.get("edge") == "1":
            edges.append((idx, cell, style_map))

    if len(rel_boxes) < 4:
        errors.append(f"Draw.io has only {len(rel_boxes)} vertex cells (expected >= 4 editable nodes)")
    if len(edges) < 2:
        warnings.append(f"Draw.io has only {len(edges)} edge cells; check if call-chain arrows are missing")

    def abs_xy(cid: str, seen: set[str] | None = None) -> tuple[float, float]:
        if cid not in rel_boxes:
            return (0.0, 0.0)
        seen = seen or set()
        if cid in seen:
            return (rel_boxes[cid].x, rel_boxes[cid].y)
        seen.add(cid)
        b = rel_boxes[cid]
        px, py = abs_xy(b.parent_id, seen)
        return (px + b.x, py + b.y)

    abs_boxes: dict[str, Box] = {}
    for cid, b in rel_boxes.items():
        ax, ay = abs_xy(cid)
        abs_boxes[cid] = Box(cid, b.parent_id, ax, ay, b.w, b.h, b.style, b.raw_value, b.index)

    # Identify background containers vs foreground leaf module cards
    container_ids: set[str] = set(parent_children.keys())
    max_width = max((b.w for b in abs_boxes.values()), default=0.0)
    for cid, b in abs_boxes.items():
        smap = parse_style(b.style)
        # Wide band frames or dashed group boxes without multi-line card content act as background containers
        if b.w >= max_width * 0.75 and b.h >= 80:
            container_ids.add(cid)
        elif smap.get("dashed") == "1" and b.h >= 70 and len(html_to_lines(b.raw_value)) <= 1:
            container_ids.add(cid)
        # Container check: boxes that geometrically enclose >= 2 smaller boxes
        enclosed = sum(
            1
            for oid, ob in abs_boxes.items()
            if oid != cid
            and ob.x >= b.x - 2
            and ob.y >= b.y - 2
            and (ob.x + ob.w) <= (b.x + b.w + 2)
            and (ob.y + ob.h) <= (b.y + b.h + 2)
            and (ob.w * ob.h) < (b.w * b.h * 0.85)
        )
        if enclosed >= 2:
            container_ids.add(cid)
            if len(html_to_lines(b.raw_value)) >= 2 and smap.get("verticalAlign") != "top":
                warnings.append(
                    f"Draw.io container id='{cid}' holds child elements and multi-line value without verticalAlign=top; "
                    "split into blank frame + header bar to prevent center-text overlap"
                )

    leaf_cards = [b for cid, b in abs_boxes.items() if cid not in container_ids and parse_style(b.style).get("text") != "1"]
    first_leaf_idx = min((b.index for b in leaf_cards), default=None)
    if first_leaf_idx is not None:
        edges_after_cards = [
            cell.attrib.get("id", f"edge_{idx}")
            for idx, cell, _ in edges
            if idx > first_leaf_idx
        ]
        if edges_after_cards:
            sample = ", ".join(edges_after_cards[:5])
            errors.append(
                f"Draw.io Z-order violation: {len(edges_after_cards)} edge mxCell(s) ({sample}) appear AFTER "
                "module card vertices; place all edge mxCells before module card vertices so lines never cover text"
            )

    # Edge orthogonal style & center-anchor check
    for idx, cell, smap in edges:
        eid = cell.attrib.get("id", f"edge_{idx}")
        edge_style = smap.get("edgeStyle", "")
        if "orthogonalEdgeStyle" not in edge_style and "elbowEdgeStyle" not in edge_style:
            warnings.append(f"Draw.io edge id='{eid}' lacks edgeStyle=orthogonalEdgeStyle (risk of diagonal line)")
        src = cell.attrib.get("source")
        tgt = cell.attrib.get("target")
        if src in abs_boxes and tgt in abs_boxes:
            sb, tb = abs_boxes[src], abs_boxes[tgt]
            # Check if crossing columns between cards without exit/entry or explicit waypoints
            s_cx, t_cx = sb.x + sb.w / 2.0, tb.x + tb.w / 2.0
            geom = next((c for c in cell if strip_ns(c.tag) == "mxGeometry"), None)
            has_points = geom is not None and any(strip_ns(c.tag) == "Array" for c in geom)
            if abs(s_cx - t_cx) > 60 and not has_points and "exitY" not in smap and "entryY" not in smap:
                warnings.append(
                    f"Draw.io cross-column edge id='{eid}' ({src} -> {tgt}) has neither exitY/entryY nor explicit mxPoint waypoints"
                )

    # Child bounds vs explicit parent container
    for cid, b in abs_boxes.items():
        if b.parent_id in abs_boxes:
            pb = abs_boxes[b.parent_id]
            if (
                b.x < pb.x - 2
                or b.y < pb.y - 2
                or (b.x + b.w) > (pb.x + pb.w + 2)
                or (b.y + b.h) > (pb.y + pb.h + 2)
            ):
                errors.append(
                    f"Draw.io vertex id='{cid}' overflows its parent container id='{pb.cell_id}'"
                )

    # Leaf card overlap check
    check_nodes = [b for cid, b in abs_boxes.items() if cid not in container_ids and b.w > 8 and b.h > 8]
    for i, a in enumerate(check_nodes):
        for b in check_nodes[i + 1 :]:
            ix = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
            iy = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
            if ix > 3.0 and iy > 3.0:
                errors.append(
                    f"Draw.io elements overlap: id='{a.cell_id}' ({a.x:.0f},{a.y:.0f},{a.w:.0f}x{a.h:.0f}) "
                    f"and id='{b.cell_id}' ({b.x:.0f},{b.y:.0f},{b.w:.0f}x{b.h:.0f}) intersect by {ix:.0f}x{iy:.0f}px"
                )

    # Text capacity check
    for cid, b in abs_boxes.items():
        lines = html_to_lines(b.raw_value)
        if not lines or b.w <= 0 or b.h <= 0:
            continue
        smap = parse_style(b.style)
        try:
            font_size = float(smap.get("fontSize", "12"))
        except ValueError:
            font_size = 12.0
        if font_size < 10.0:
            warnings.append(f"Draw.io vertex id='{cid}' has fontSize={font_size:g} (< 10px minimum)")
        pad_x = 12.0 if smap.get("text") != "1" else 4.0
        pad_y = 8.0 if smap.get("text") != "1" else 2.0
        usable_w = max(b.w - pad_x, font_size)
        wrapped_lines = 0
        for line in lines:
            est_w = estimate_line_px(line, font_size)
            wrapped_lines += max(1, math.ceil(est_w / usable_w))
        needed_h = wrapped_lines * (font_size * 1.38) + pad_y
        if cid not in container_ids and needed_h > b.h + 4.0:
            warnings.append(
                f"Draw.io text overflow risk in id='{cid}': ~{wrapped_lines} wrapped line(s) at fontSize={font_size:g} "
                f"need ~{needed_h:.0f}px height, box height is {b.h:.0f}px"
            )

    return cjk_terms


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SVG and Draw.io architecture diagrams.")
    parser.add_argument("--svg", type=Path, help="Path to generated .svg diagram.")
    parser.add_argument("--drawio", type=Path, help="Path to generated .drawio diagram.")
    args = parser.parse_args()

    if not args.svg and not args.drawio:
        parser.error("Provide at least one of --svg or --drawio")

    errors: list[str] = []
    warnings: list[str] = []
    svg_terms: set[str] = set()
    drawio_terms: set[str] = set()

    if args.svg:
        svg_terms = validate_svg(args.svg, errors, warnings)
    if args.drawio:
        drawio_terms = validate_drawio(args.drawio, errors, warnings)

    if args.svg and args.drawio and svg_terms and drawio_terms:
        overlap = svg_terms & drawio_terms
        smaller = min(len(svg_terms), len(drawio_terms))
        if smaller >= 4 and len(overlap) / smaller < 0.5:
            warnings.append(
                f"Low label overlap between SVG and Draw.io ({len(overlap)}/{smaller} shared Chinese terms); "
                "ensure both files represent the exact same version and module names"
            )

    for err in errors:
        print(f"[ERROR] {err}")
    for warn in warnings:
        print(f"[WARN]  {warn}")

    if not errors and not warnings:
        print("[PASS] Diagram validation passed with 0 errors and 0 warnings.")
    elif not errors:
        print(f"[PASS] Diagram validation passed with 0 errors ({len(warnings)} warning(s) to review).")
    else:
        print(f"[FAIL] Diagram validation failed with {len(errors)} error(s) and {len(warnings)} warning(s).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
