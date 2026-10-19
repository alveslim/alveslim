import json
from datetime import datetime

COLORS = {
    0: "#161b22",
    1: "#0e4429",
    2: "#006d32",
    3: "#26a641",
    4: "#39d353",
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def render():
    with open("data/contributions.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    weeks = data["weeks"]
    total = data["total_contributions"]

    width = 860
    height = 195
    cell_size = 11
    cell_gap = 3
    step = cell_size + cell_gap
    grid_x = 48
    grid_y = 36

    rects = []
    month_labels = []
    last_month = None

    for w_idx, week in enumerate(weeks):
        for d in week:
            if d:
                dt = datetime.strptime(d["date"], "%Y-%m-%d")
                if dt.day <= 7 and dt.month != last_month:
                    m_name = MONTH_NAMES[dt.month - 1]
                    mx = grid_x + w_idx * step
                    month_labels.append(
                        f'<text x="{mx}" y="{grid_y - 10}" class="label">{m_name}</text>'
                    )
                    last_month = dt.month
                break

        for d_idx, day in enumerate(week):
            if not day:
                continue
            x = grid_x + w_idx * step
            y = grid_y + d_idx * step
            color = COLORS.get(day["level"], COLORS[0])
            delay = round((w_idx * 0.022) + (d_idx * 0.035), 3)
            rects.append(
                f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" rx="2.5" ry="2.5" '
                f'fill="{color}" class="cell" style="animation-delay: {delay}s">'
                f'<title>{day["date"]}: {day["count"]} contributions</title></rect>'
            )

    day_labels = [
        f'<text x="16" y="{grid_y + 1 * step + 9}" class="label">Mon</text>',
        f'<text x="16" y="{grid_y + 3 * step + 9}" class="label">Wed</text>',
        f'<text x="16" y="{grid_y + 5 * step + 9}" class="label">Fri</text>',
    ]

    legend_x = width - 155
    legend_y = height - 24
    legend_items = [f'<text x="{legend_x - 32}" y="{legend_y + 9}" class="label">Less</text>']
    for lvl in range(5):
        lx = legend_x + lvl * (cell_size + 3)
        legend_items.append(
            f'<rect x="{lx}" y="{legend_y}" width="{cell_size}" height="{cell_size}" rx="2.5" ry="2.5" fill="{COLORS[lvl]}" />'
        )
    legend_items.append(
        f'<text x="{legend_x + 5 * (cell_size + 3) + 4}" y="{legend_y + 9}" class="label">More</text>'
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; }}
    .label {{ fill: #8b949e; font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 10px; }}
    .footer {{ fill: #c9d1d9; font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 12px; font-weight: 600; }}
    .cell {{
      opacity: 0;
      transform: translateY(-6px);
      animation: popIn 0.35s cubic-bezier(0.22, 1, 0.36, 1) forwards;
    }}
    @keyframes popIn {{
      to {{
        opacity: 1;
        transform: translateY(0);
      }}
    }}
  </style>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" ry="10" class="bg" />
  {"".join(month_labels)}
  {"".join(day_labels)}
  {"".join(rects)}
  <text x="{grid_x}" y="{height - 15}" class="footer">{total:,} contributions in the last year</text>
  {"".join(legend_items)}
</svg>'''

    with open("contrib-heatmap.svg", "w", encoding="utf-8") as f:
        f.write(svg)

if __name__ == "__main__":
    render()