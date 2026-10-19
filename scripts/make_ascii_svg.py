import html
from PIL import Image

RAMP = " .`:-=+*cs#%@"  # Claro (espaço) -> Escuro (@)
COLS = 95
ROWS = 52

def make_svg(img_path="source-prepped.png", out_svg="flavio-ascii.svg"):
    img = Image.open(img_path).convert("L").resize((COLS, ROWS))
    pixels = img.load()

    lines = []
    for r in range(ROWS):
        row_chars = []
        for c in range(COLS):
            val = pixels[c, r]
            idx = int((255 - val) / 255 * (len(RAMP) - 1))
            row_chars.append(RAMP[idx])
        lines.append("".join(row_chars))

    clip_defs = []
    text_rows = []
    y_start = 78
    line_h = 14.2

    for r, line in enumerate(lines):
        y = round(y_start + r * line_h, 1)
        begin_s = round(r * 0.045, 3)
        escaped = html.escape(line)
        clip_defs.append(
            f'<clipPath id="r{r}"><rect x="30" y="{y - 12}" width="0" height="16">'
            f'<animate attributeName="width" from="0" to="780" begin="{begin_s}s" dur="0.06s" fill="freeze" />'
            f'</rect></clipPath>'
        )
        text_rows.append(
            f'<text x="36" y="{y}" clip-path="url(#r{r})" xml:space="preserve">{escaped}</text>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="880" viewBox="0 0 840 880">
  <defs>{"".join(clip_defs)}</defs>
  <style>
    .win {{ fill: #0d1117; stroke: #30363d; stroke-width: 2px; }}
    .hdr {{ fill: #161b22; }}
    .title {{ fill: #8b949e; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 16px; }}
    .ascii {{ fill: #c9d1d9; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 13px; letter-spacing: 0.5px; }}
  </style>
  <rect x="1" y="1" width="838" height="878" rx="14" class="win" />
  <path d="M 15 1 H 825 A 14 14 0 0 1 839 15 V 48 H 1 V 15 A 14 14 0 0 1 15 1 Z" class="hdr" />
  <line x1="1" y1="48" x2="839" y2="48" stroke="#30363d" stroke-width="1.5" />
  <circle cx="26" cy="24" r="7" fill="#ff5f56" />
  <circle cx="50" cy="24" r="7" fill="#ffbd2e" />
  <circle cx="74" cy="24" r="7" fill="#27c93f" />
  <text x="420" y="30" text-anchor="middle" class="title">alveslim@github — ascii</text>
  <g class="ascii">
    {"".join(text_rows)}
  </g>
</svg>'''

    with open(out_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Gerado {out_svg} com sucesso!")

if __name__ == "__main__":
    make_svg()