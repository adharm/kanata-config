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


def parse_all_defalias(text: str) -> dict[str, str]:
    """Collect alias -> raw expression from all defalias blocks."""
    aliases: dict[str, str] = {}
    start = 0
    while True:
        idx = text.find("(defalias", start)
        if idx == -1:
            break
        inner, s, e = parse_block(text, "(defalias")
        for ln in inner:
            ln = strip_comments(ln).strip()
            if not ln or ln.startswith(";;"):
                continue
            # lines are like: name  (expr...)
            m = re.match(r"^([A-Za-z0-9_]+)\s+(.+)$", ln)
            if not m:
                continue
            name, expr = m.group(1), m.group(2).strip()
            aliases[name] = expr
        start = e
    return aliases


def build_alias_descriptions(aliases: dict[str, str]) -> dict[str, str]:
    """Create a descriptive label for known alias patterns."""
    mod_icon = {
        'lctl': '⌃', 'rctl': '⌃',
        'lsft': '⇧', 'rsft': '⇧',
        'lalt': '⌥', 'ralt': '⌥',
        'lmet': '⌘', 'rmet': '⌘',
    }
    key_icon = {
        'spc': '␣', 'space': '␣', 'tab': '⇥', 'bspc': '⌫', 'ret': '⏎', 'esc': '⎋',
        'slash': '/', 'bsl': '\\', 'lsgt': '<>', 'comma': ',', 'dot': '.',
    }

    desc: dict[str, str] = {}
    for name, expr in aliases.items():
        e = expr.replace('\n', ' ')
        # charmod simple: (t! charmod <char> <mod>)
        m = re.search(r"\(t!\s*charmod\s+(\S+)\s+(lctl|lalt|lsft|lmet|rctl|ralt|rsft|rmet)\)", e)
        if m:
            ch, mod = m.group(1), m.group(2)
            ch_lbl = key_icon.get(ch, ch.upper() if len(ch) == 1 else ch)
            desc[name] = f"{ch_lbl} {mod_icon.get(mod, mod)}"
            continue

        # space to layer: (t! charmod spc (multi (layer-switch <layer>) ...))
        m = re.search(r"\(t!\s*charmod\s+spc\s+\(multi\s+\(layer-switch\s+(\w+)\)\s*\)", e)
        if m:
            layer = m.group(1)
            desc[name] = f"␣ → {layer.capitalize()}"
            continue

        # layer hold: (t! charmod <key> (layer-while-held <layer>))
        m = re.search(r"\(t!\s*charmod\s+(\S+)\s+\(layer-while-held\s+(\w+)\)\)", e)
        if m:
            ch, layer = m.group(1), m.group(2)
            ch_lbl = key_icon.get(ch, ch.upper() if len(ch) == 1 else ch)
            desc[name] = f"{ch_lbl} → {layer.capitalize()}"
            continue

        # chord: (chord group key)
        m = re.search(r"\(chord\s+\w+\s+(.+?)\)$", e)
        if m:
            ch = m.group(1).strip()
            ch_lbl = key_icon.get(ch, ch.upper() if len(ch) == 1 else ch)
            desc[name] = f"{ch_lbl}"
            continue

        # layer switch helper
        m = re.search(r"\(layer-switch\s+(\w+)\)", e)
        if m:
            layer = m.group(1)
            desc[name] = f"→ {layer.capitalize()}"
            continue

        # press virtual shift
        if "press-virtualkey shift" in e:
            desc[name] = "⇧ press"
            continue

        # fall back to alias name upper
        desc[name] = name.upper()
    return desc


def friendly_label(tok: str, alias_desc: dict[str, str]) -> str:
    t = tok
    if t == '_':
        return ''
    if t.startswith('@'):
        name = t[1:]
        return alias_desc.get(name, name.upper())
    # map common names to glyphs
    mapping = {
        'esc': '⎋', 'bspc': '⌫', 'del': '⌦', 'ret': '⏎', 'tab': '⇥', 'caps': '⇪',
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


def key_width_class(shape_tok: str) -> str:
    # Assign rough width classes based on physical key from defsrc
    wide = {
        'tab': 'w-15', 'caps': 'w-17', 'lsft': 'w-20', 'rsft': 'w-23', 'bspc': 'w-17',
        'ret': 'w-20', 'spc': 'w-50',
    }
    return wide.get(shape_tok, '')


def render_layer_html(name: str, rows: list[list[str]], shape_rows: list[list[str]], alias_desc: dict[str, str]) -> str:
    html = [f'<div class="layer"><div class="layer-name">{name}</div>']
    for ri, r in enumerate(rows):
        row_class = f'row r{ri}'
        html.append(f'<div class="{row_class}">')
        for ci, t in enumerate(r):
            label = friendly_label(t, alias_desc)
            classes = ['key']
            if t == '_':
                classes.append('trans')
            # width by shape
            shape_tok = shape_rows[ri][ci] if ri < len(shape_rows) and ci < len(shape_rows[ri]) else ''
            wcls = key_width_class(shape_tok)
            if wcls:
                classes.append(wcls)
            # additionally widen explicit space aliases
            if t in ('spc', '@spc', 'space', '@space'):
                classes.append('w-50')
            html.append(f'<div class="{" ".join(classes)}">{label}</div>')
        html.append('</div>')
    html.append('</div>')
    return '\n'.join(html)


def build_html(layers: dict[str, list[list[str]]], shape_rows: list[list[str]], alias_desc: dict[str, str]) -> str:
    css = """
    body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; background:#111; color:#ddd; }
    .wrap { display:flex; flex-direction:column; gap:28px; padding:24px; }
    .layer { background:#1a1a1a; border:1px solid #333; border-radius:10px; padding:16px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
    .layer-name { font-weight:600; margin-bottom:10px; letter-spacing:0.5px; }
    .row { display:flex; gap:8px; margin:6px 0; }
    .r2 { margin-left: 20px; }  /* Tab row */
    .r3 { margin-left: 36px; }  /* Caps row */
    .r4 { margin-left: 56px; }  /* Shift row */
    .r5 { margin-left: 90px; }  /* Space row */
    .key { min-width:44px; height:44px; display:flex; align-items:center; justify-content:center; background:#222; border:1px solid #444; border-radius:6px; font-size:14px; padding:0 6px; }
    .trans { opacity:0.22; }
    /* width classes roughly modeled on ANSI keyboard */
    .w-15 { min-width: 66px; }
    .w-17 { min-width: 78px; }
    .w-20 { min-width: 96px; }
    .w-23 { min-width: 110px; }
    .w-50 { min-width: 320px; }
    """
    parts = ["<html><head><meta charset='utf-8'><style>", css, "</style></head><body>", "<div class='wrap'>"]
    for name, rows in layers.items():
        parts.append(render_layer_html(name, rows, shape_rows, alias_desc))
    parts.append("</div></body></html>")
    return '\n'.join(parts)


def main() -> None:
    text = read_text(KBD)
    # Parse defsrc to get row sizes and physical shapes
    src_lines, _, _ = parse_block(text, "(defsrc")
    src_tokens = tokens_from_lines(src_lines)
    # derive rows by taking tokens per line (defsrc has 6 visible lines)
    # but use per-line counts from src_lines to preserve layout
    row_sizes: list[int] = []
    for ln in src_lines:
        tokc = len(strip_comments(ln).split())
        if tokc:
            row_sizes.append(tokc)
    # Physical shape rows (per defsrc line)
    shape_rows: list[list[str]] = []
    for ln in src_lines:
        toks = strip_comments(ln).split()
        if toks:
            shape_rows.append(toks)

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

    # Parse alias definitions for descriptive labels
    aliases = parse_all_defalias(text)
    alias_desc = build_alias_descriptions(aliases)

    html = build_html(layers, shape_rows, alias_desc)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
