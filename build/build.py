#!/usr/bin/env python3
"""Assemble the shipped static HTML pages from templates + real asset files.

Run from the repo root: `python3 build/build.py` (or `just build`).

Source of truth lives under assets/ and build/templates/; the generated
*.html files at the repo root are committed build output (see ROADMAP.md
Phase 1b), kept in sync by re-running this script, never hand-edited.
"""
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
TEMPLATES = ROOT / "build" / "templates"

DICE_FACES = range(1, 7)
DICE_VARIANTS = range(4)


def build_dice_sprites_js():
    lines = ["const DICE_SPRITES = {"]
    for face in DICE_FACES:
        uris = []
        for variant in DICE_VARIANTS:
            raw = (ASSETS / "dice" / f"{face}_{variant}.png").read_bytes()
            b64 = base64.b64encode(raw).decode("ascii")
            uris.append(f"'data:image/png;base64,{b64}'")
        lines.append(f"  {face}: [{', '.join(uris)}],")
    lines.append("};")
    return "\n".join(lines)


def build_one(page, dice_sprites_js, dp_data_json, font_b64, bg_b64):
    template_path = TEMPLATES / f"template.{page['template']}.html"
    html = template_path.read_text(encoding="utf-8")

    html = html.replace("{{TITLE}}", page["title"])
    html = html.replace("{{META_DESCRIPTION}}", page["meta_description"])
    html = html.replace("{{ES_HREF}}", page["es_href"])
    html = html.replace("{{EN_HREF}}", page["en_href"])
    html = html.replace("{{SIBLING_HREF}}", page["sibling_href"])
    html = html.replace("{{DICE_SPRITES_JS}}", dice_sprites_js)
    html = html.replace("{{DP_DATA_JSON}}", dp_data_json)
    html = html.replace("{{FONT_BASE64}}", font_b64)
    html = html.replace("{{BACKGROUND_BASE64}}", bg_b64)

    remaining = re.findall(r"\{\{[A-Z_]+\}\}", html)
    if remaining:
        raise SystemExit(f"{page['output']}: unfilled placeholders: {sorted(set(remaining))}")

    out_path = ROOT / page["output"]
    out_path.write_text(html, encoding="utf-8")
    print(f"built {page['output']} ({len(html):,} bytes)")


def main():
    pages = json.loads((ROOT / "build" / "pages.json").read_text(encoding="utf-8"))
    dice_sprites_js = build_dice_sprites_js()
    dp_data_json = (ASSETS / "dp-data.json").read_text(encoding="utf-8")
    font_b64 = base64.b64encode((ASSETS / "pixelfont.woff2").read_bytes()).decode("ascii")
    bg_b64 = base64.b64encode((ASSETS / "background.jpg").read_bytes()).decode("ascii")

    for page in pages:
        build_one(page, dice_sprites_js, dp_data_json, font_b64, bg_b64)


if __name__ == "__main__":
    sys.exit(main())
