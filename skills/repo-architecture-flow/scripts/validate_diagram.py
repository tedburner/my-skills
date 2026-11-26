#!/usr/bin/env python3
"""Deterministic XML, Z-order, orthogonal routing, and text/box overlap validator
for .svg and .drawio architecture diagrams (supports both Engineering Standard
and Sketch / Excalidraw themes, including A-vs-B comparison diagrams).

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
SVG_TOKEN_RE = re.compile(r"[MmLlHhVvQqCcAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
BADGE_ID_RE = re.compile(r"^(?:badge|pill|tag|chip)[-_]", re.IGNORECASE)
HIGHLIGHT_ID_RE = re.compile(r"^(?:hl|highlight)[-_]", re.IGNORECASE)


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
            width += font_size * 0.56
    return width


def extract_cjk_terms(text: str) -> set[str]:
    return set(CJK_RE.findall(text))


def is_enclosed(inner: Box, outer: Box, tol: float = 2.5) -> bool:
    return (
        inner.x >= outer.x - tol
        and inner.y >= outer.y - tol
        and (inner.x + inner.w) <= (outer.x + outer.w + tol)
        and (inner.y + inner.h) <= (outer.y + outer.h + tol)
    )


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
            elif cmd == "Q":
                # Quadratic curve: allowed for small 90-degree rounded corners (chord <= 32px)
                nx, ny = float(tokens[i + 2]), float(tokens[i + 3])
                dx, dy = abs(nx - cx), abs(ny - cy)
                if dx > 28.0 and dy > 28.0 and math.hypot(dx, dy) > 36.0:
                    errors.append(
                        f"SVG <path {elem_id}> has sweeping diagonal Q-curve "
                        f"({cx:.1f},{cy:.1f}) -> ({nx:.1f},{ny:.1f}); keep Q curves for rounded 90-deg corners only"
                    )
                cx, cy = nx, ny
                i += 4
            elif cmd == "q":
                dx_raw, dy_raw = float(tokens[i + 2]), float(tokens[i + 3])
                if abs(dx_raw) > 28.0 and abs(dy_raw) > 28.0 and math.hypot(dx_raw, dy_raw) > 36.0:
                    errors.append(
                        f"SVG <path {elem_id}> has sweeping diagonal relative q-curve d=({dx_raw:.1f},{dy_raw:.1f})"
                    )
                cx += dx_raw
                cy += dy_raw
                i += 4
            elif cmd == "C":
                nx, ny = float(tokens[i + 4]), float(tokens[i + 5])
                dx, dy = abs(nx - cx), abs(ny - cy)
                if dx > 28.0 and dy > 28.0 and math.hypot(dx, dy) > 36.0:
                    errors.append(
                        f"SVG <path {elem_id}> has sweeping diagonal C-curve "
                        f"({cx:.1f},{cy:.1f}) -> ({nx:.1f},{ny:.1f})"
                    )
                cx, cy = nx, ny
                i += 6
            elif cmd == "c":
                dx_raw, dy_raw = float(tokens[i + 4]), float(tokens[i + 5])
                if abs(dx_raw) > 28.0 and abs(dy_raw) > 28.0 and math.hypot(dx_raw, dy_raw) > 36.0:
                    errors.append(
                        f"SVG <path {elem_id}> has sweeping diagonal relative c-curve d=({dx_raw:.1f},{dy_raw:.1f})"
                    )
                cx += dx_raw
                cy += dy_raw
                i += 6
            elif cmd == "A":
                nx, ny = float(tokens[i + 5]), float(tokens[i + 6])
                dx, dy = abs(nx - cx), abs(ny - cy)
                if dx > 28.0 and dy > 28.0 and math.hypot(dx, dy) > 36.0:
                    errors.append(
                        f"SVG <path {elem_id}> has large diagonal arc ({cx:.1f},{cy:.1f}) -> ({nx:.1f},{ny:.1f})"
                    )
                cx, cy = nx, ny
                i += 7
            elif cmd == "a":
                dx_raw, dy_raw = float(tokens[i + 5]), float(tokens[i + 6])
                if abs(dx_raw) > 28.0 and abs(dy_raw) > 28.0 and math.hypot(dx_raw, dy_raw) > 36.0:
                    errors.append(
                        f"SVG <path {elem_id}> has large relative diagonal arc d=({dx_raw:.1f},{dy_raw:.1f})"
                    )
                cx += dx_raw
                cy += dy_raw
                i += 7
            else:
                i += 1
        except (IndexError, ValueError):
            break


def iter_svg_non_defs(elem: ET.Element) -> list[ET.Element]:
    out: list[ET.Element] = []

    def walk(node: ET.Element) -> None:
        if strip_ns(node.tag).lower() == "defs":
            return
        out.append(node)
        for child in node:
            walk(child)

    walk(elem)
    return out


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

    for idx, elem in enumerate(iter_svg_non_defs(root)):
        tag = strip_ns(elem.tag).lower()
        elem_id = f"id='{elem.attrib.get('id', f'#{idx}')}'"
        role = elem.attrib.get("data-role", "").lower()

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
            if role in ("decor", "divider"):
                continue
            is_short_decor_line = False
            if tag == "line":
                try:
                    x1 = float(elem.attrib.get("x1", "0"))
                    y1 = float(elem.attrib.get("y1", "0"))
                    x2 = float(elem.attrib.get("x2", "0"))
                    y2 = float(elem.attrib.get("y2", "0"))
                    seg_len = math.hypot(x2 - x1, y2 - y1)
                    if seg_len <= 22.0 and not elem.attrib.get("marker-end"):
                        is_short_decor_line = True
                    elif abs(x2 - x1) > 3.0 and abs(y2 - y1) > 3.0 and seg_len > 18.0:
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
            elif tag == "path":
                check_svg_orthogonal_path(elem_id, elem.attrib.get("d", ""), errors)

            if not is_short_decor_line and first_text_idx is not None:
                late_edges += 1

    if late_edges > 0:
        warnings.append(
            f"SVG has {late_edges} edge line/path element(s) placed after <text> nodes; "
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


def is_highlight_backing(b: Box, smap: dict[str, str]) -> bool:
    if HIGHLIGHT_ID_RE.match(b.cell_id):
        return True
    return not html_to_lines(b.raw_value) and smap.get("strokeColor", "").lower() == "none" and b.h <= 48


def is_inline_badge_in_card(small: Box, big: Box) -> bool:
    if not is_enclosed(small, big):
        return False
    big_area = max(big.w * big.h, 1.0)
    small_area = small.w * small.h
    if BADGE_ID_RE.match(small.cell_id) and small_area < big_area * 0.65:
        return True
    return small.h <= big.h * 0.85 and small_area <= big_area * 0.38 and len(html_to_lines(small.raw_value)) == 1


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
    style_maps: dict[str, dict[str, str]] = {}
    for cid, b in rel_boxes.items():
        ax, ay = abs_xy(cid)
        abs_boxes[cid] = Box(cid, b.parent_id, ax, ay, b.w, b.h, b.style, b.raw_value, b.index)
        style_maps[cid] = parse_style(b.style)

    # Identify background containers & marker highlight backings vs foreground cards
    container_ids: set[str] = set(parent_children.keys())
    highlight_ids: set[str] = set()
    max_width = max((b.w for b in abs_boxes.values()), default=0.0)

    for cid, b in abs_boxes.items():
        smap = style_maps[cid]
        if is_highlight_backing(b, smap):
            highlight_ids.add(cid)
            continue
        if b.w >= max_width * 0.75 and b.h >= 80 and not html_to_lines(b.raw_value):
            container_ids.add(cid)
            continue
        if smap.get("dashed") == "1" and b.h >= 70 and len(html_to_lines(b.raw_value)) <= 1:
            container_ids.add(cid)
            continue
        enclosed = sum(
            1
            for oid, ob in abs_boxes.items()
            if oid != cid
            and oid not in highlight_ids
            and is_enclosed(ob, b)
            and (ob.w * ob.h) < (b.w * b.h * 0.85)
            and not is_inline_badge_in_card(ob, b)
        )
        if enclosed >= 2:
            container_ids.add(cid)
            if len(html_to_lines(b.raw_value)) >= 2 and smap.get("verticalAlign") != "top":
                warnings.append(
                    f"Draw.io container id='{cid}' holds child elements and multi-line value without verticalAlign=top; "
                    "split into blank frame + header bar to prevent center-text overlap"
                )

    leaf_cards = [
        b
        for cid, b in abs_boxes.items()
        if cid not in container_ids
        and cid not in highlight_ids
        and style_maps[cid].get("text") != "1"
        and b.w > 4
        and b.h > 4
    ]
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

    # Edge orthogonal style & cross-column waypoint check
    for idx, cell, smap in edges:
        eid = cell.attrib.get("id", f"edge_{idx}")
        edge_style = smap.get("edgeStyle", "")
        if "orthogonalEdgeStyle" not in edge_style and "elbowEdgeStyle" not in edge_style:
            warnings.append(f"Draw.io edge id='{eid}' lacks edgeStyle=orthogonalEdgeStyle (risk of diagonal line)")
        src = cell.attrib.get("source")
        tgt = cell.attrib.get("target")
        if src in abs_boxes and tgt in abs_boxes:
            sb, tb = abs_boxes[src], abs_boxes[tgt]
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
            if not is_enclosed(b, pb, tol=2.5):
                errors.append(
                    f"Draw.io vertex id='{cid}' overflows its parent container id='{pb.cell_id}'"
                )

    # Leaf card & text overlap check (exempting highlight backings, thin dividers, and valid inline badges)
    check_nodes = [
        b
        for cid, b in abs_boxes.items()
        if cid not in container_ids
        and cid not in highlight_ids
        and b.w > 6
        and b.h > 6
    ]
    for i, a in enumerate(check_nodes):
        for b in check_nodes[i + 1 :]:
            ix = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
            iy = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
            if ix <= 3.0 or iy <= 3.0:
                continue
            # Allow valid inline code pill badge nested inside its host step card
            if is_inline_badge_in_card(a, b) or is_inline_badge_in_card(b, a):
                host, badge = (b, a) if is_inline_badge_in_card(a, b) else (a, b)
                host_smap = style_maps[host.cell_id]
                host_lines = html_to_lines(host.raw_value)
                if host_lines:
                    try:
                        h_fs = float(host_smap.get("fontSize", "12"))
                    except ValueError:
                        h_fs = 12.0
                    label_px = estimate_line_px(host_lines[0], h_fs)
                    if label_px + badge.w + 28.0 > host.w:
                        warnings.append(
                            f"Draw.io inline badge id='{badge.cell_id}' inside id='{host.cell_id}' may crowd host text "
                            f"(label ~{label_px:.0f}px + badge {badge.w:.0f}px > card width {host.w:.0f}px)"
                        )
                continue
            errors.append(
                f"Draw.io elements overlap: id='{a.cell_id}' ({a.x:.0f},{a.y:.0f},{a.w:.0f}x{a.h:.0f}) "
                f"and id='{b.cell_id}' ({b.x:.0f},{b.y:.0f},{b.w:.0f}x{b.h:.0f}) intersect by {ix:.0f}x{iy:.0f}px"
            )

    # Text capacity check
    for cid, b in abs_boxes.items():
        lines = html_to_lines(b.raw_value)
        if not lines or b.w <= 0 or b.h <= 0:
            continue
        smap = style_maps[cid]
        try:
            font_size = float(smap.get("fontSize", "12"))
        except ValueError:
            font_size = 12.0
        if font_size < 10.0:
            warnings.append(f"Draw.io vertex id='{cid}' has fontSize={font_size:g} (< 10px minimum)")
        is_compact_pill = bool(BADGE_ID_RE.match(cid)) or b.h <= 28.0
        pad_x = 4.0 if smap.get("text") == "1" else (8.0 if is_compact_pill else 12.0)
        pad_y = 2.0 if smap.get("text") == "1" else (4.0 if is_compact_pill else 8.0)
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
