#!/usr/bin/env python3
"""
Render a simple HTML cheatsheet for Kanata layers from kenkyo.kbd.

- Parses defsrc to infer row sizes
- Parses the named layers and re-chunks into rows matching defsrc
- Produces docs/kenkyo_layers.html with a grid per layer

This is a light parser that relies on the aliases already added for readability.
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KBD = ROOT / "kenkyo.kbd"
OUT = ROOT / "docs" / "kenkyo_layers.html"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_comments(line: str) -> str:
    # Remove Kanata comments starting with ';;'
    return line.split(";;", 1)[0]


def tokens_from_lines(lines: list[str]) -> list[str]:
    toks: list[str] = []
    for ln in lines:
        ln = strip_comments(ln).strip()
        if not ln:
            continue
        # skip parentheses-only lines
        # split on whitespace; keep symbols like ']' and "'" as tokens
        toks.extend(ln.split())
    return toks


def parse_block(text: str, head: str) -> tuple[list[str], int, int]:
    """Return (lines, start_idx, end_idx) for a block starting with head.
    head example: "(defsrc" or "(deflayer main"
    """
    start = text.find(head)
    if start == -1:
        raise ValueError(f"Block not found: {head}")
    i = start
    depth = 0
    in_block = False
    lines: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == '(':
            depth += 1
            if not in_block:
                in_block = True
        elif ch == ')':
            depth -= 1
            if in_block and depth == 0:
                end = i
                # include up to this position
                block_text = text[start:end+1]
                block_lines = block_text.splitlines()
                # remove the first line containing the head and the last line with ')'
                inner = block_lines[1:-1]
                return inner, start, end + 1
        i += 1
    raise ValueError(f"Unclosed block for {head}")


def chunk_rows(tokens: list[str], row_sizes: list[int]) -> list[list[str]]:
    rows: list[list[str]] = []
    idx = 0
    for size in row_sizes:
        rows.append(tokens[idx: idx + size])
        idx += size
    return rows


def friendly_label(tok: str) -> str:
    t = tok
    if t == '_':
        return ''
    if t.startswith('@'):
        t = t[1:]
    # map common names to glyphs
    mapping = {
        'esc': '⎋', 'bspc': '⌫', 'del': '⌦', 'ret': '⏎', 'tab': '⇥',
        'spc': '␣', 'space': '␣', 'pp': '⏯', 'vold': '🔉', 'volu': '🔊', 'mute': '🔇',
        'lmet': '⌘', 'rmet': '⌘', 'lalt': '⌥', 'ralt': '⌥', 'lsft': '⇧', 'rsft': '⇧',
        'lctl': '⌃', 'rctl': '⌃', 'rght': '→', 'left': '←', 'up': '↑', 'down': '↓',
        'pgup': 'Pg↑', 'pgdn': 'Pg↓', 'home': 'Home', 'end': 'End', 'ins': 'Ins',
        'lsgt': '<>', 'bsl': '\\', 'slash': '/', 'dash': '-', 'btick': '`',
        'lbrk': '[', 'rbrkA': ']', 'comma': ',', 'dot': '.',
    }
    if t in mapping:
        return mapping[t]
    if re.fullmatch(r"f\d{1,2}", t):
        return t.upper()
    # single letter -> uppercase for readability
    if len(t) == 1 and t.isalpha():
        return t.upper()
    return t


def render_layer_html(name: str, rows: list[list[str]]) -> str:
    html = [f'<div class="layer"><div class="layer-name">{name}</div>']
    for r in rows:
        html.append('<div class="row">')
        for t in r:
            label = friendly_label(t)
            classes = ['key']
            if t in ('spc', '@spc', 'space', '@space'):  # widen space
                classes.append('wide2')
            if t == '_':
                classes.append('trans')
            html.append(f'<div class="{" ".join(classes)}">{label}</div>')
        html.append('</div>')
    html.append('</div>')
    return '\n'.join(html)


def build_html(layers: dict[str, list[list[str]]]) -> str:
    css = """
    body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; background:#111; color:#ddd; }
    .wrap { display:flex; flex-direction:column; gap:28px; padding:24px; }
    .layer { background:#1a1a1a; border:1px solid #333; border-radius:10px; padding:16px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
    .layer-name { font-weight:600; margin-bottom:10px; letter-spacing:0.5px; }
    .row { display:flex; gap:8px; margin:6px 0; }
    .key { min-width:42px; height:42px; display:flex; align-items:center; justify-content:center; background:#222; border:1px solid #444; border-radius:6px; font-size:14px; }
    .key.wide2 { min-width:110px; }
    .trans { opacity:0.2; }
    """
    parts = ["<html><head><meta charset='utf-8'><style>", css, "</style></head><body>", "<div class='wrap'>"]
    for name, rows in layers.items():
        parts.append(render_layer_html(name, rows))
    parts.append("</div></body></html>")
    return '\n'.join(parts)


def main() -> None:
    text = read_text(KBD)
    # Parse defsrc to get row sizes
    src_lines, _, _ = parse_block(text, "(defsrc")
    src_tokens = tokens_from_lines(src_lines)
    # derive rows by taking tokens per line (defsrc has 6 visible lines)
    # but use per-line counts from src_lines to preserve layout
    row_sizes: list[int] = []
    for ln in src_lines:
        tokc = len(strip_comments(ln).split())
        if tokc:
            row_sizes.append(tokc)
    # Parse layers of interest
    layers: dict[str, list[list[str]]] = {}
    for lname in ("main", "extend", "fumbol"):
        try:
            lyr_lines, *_ = parse_block(text, f"(deflayer {lname}")
        except ValueError:
            continue
        toks = tokens_from_lines(lyr_lines)
        rows = chunk_rows(toks, row_sizes)
        layers[lname] = rows

    html = build_html(layers)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()

