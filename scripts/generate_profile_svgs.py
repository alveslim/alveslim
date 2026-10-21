import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

USERNAME = os.getenv("GITHUB_USER", "alveslim")
URL = f"https://github.com/users/{USERNAME}/contributions"

COLORS = {
    0: "#161b22",
    1: "#0e4429",
    2: "#006d32",
    3: "#26a641",
    4: "#39d353",
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def fetch_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "text/html",
    }
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)
    summary_match = re.search(
        r"([\d,]+)\s+contributions?\s+in the last year",
        page_text,
        re.IGNORECASE,
    )
    page_total = int(summary_match.group(1).replace(",", "")) if summary_match else None

    tooltips = {}
    for tip in soup.find_all("tool-tip"):
        for_id = tip.get("for")
        text = tip.get_text(strip=True)
        m = re.search(r"(\d+)\s+contribution", text)
        count = int(m.group(1)) if m else 0
        if for_id:
            tooltips[for_id] = count

    days = []
    for cell in soup.select("td.ContributionCalendar-day"):
        d_str = cell.get("data-date")
        if not d_str:
            continue
        level = int(cell.get("data-level", "0"))
        cell_id = cell.get("id")
        count = tooltips.get(cell_id, 0)
        if count == 0 and level > 0:
            count = {1: 1, 2: 3, 3: 6, 4: 10}.get(level, 1)
        days.append({"date": d_str, "count": count, "level": level})

    days.sort(key=lambda x: x["date"])

    weeks = []
    current_week = [None] * 7
    for d in days:
        dt = datetime.strptime(d["date"], "%Y-%m-%d").date()
        dow = (dt.weekday() + 1) % 7
        if dow == 0 and any(current_week):
            weeks.append(current_week)
            current_week = [None] * 7
        current_week[dow] = d
    if any(current_week):
        weeks.append(current_week)

    total_contributions = page_total if page_total is not None else sum(d["count"] for d in days)
    active_days = sum(1 for d in days if d["count"] > 0)
    total_days = len(days)

    longest_streak = 0
    longest_start = longest_end = None
    cur_s = 0
    cur_start = None

    for d in days:
        if d["count"] > 0:
            cur_s += 1
            if cur_s == 1:
                cur_start = d["date"]
            if cur_s > longest_streak:
                longest_streak = cur_s
                longest_start = cur_start
                longest_end = d["date"]
        else:
            cur_s = 0

    current_streak = 0
    current_start = current_end = None
    for i, d in enumerate(reversed(days)):
        if i == 0 and d["count"] == 0:
            continue
        if d["count"] > 0:
            if current_streak == 0:
                current_end = d["date"]
            current_streak += 1
            current_start = d["date"]
        else:
            break

    best_day = max(days, key=lambda x: x["count"]) if days else {"date": "", "count": 0}
    avg_per_day = round(total_contributions / max(total_days, 1), 1)

    monthly = {}
    for d in days:
        ym = d["date"][:7]
        monthly[ym] = monthly.get(ym, 0) + d["count"]
    monthly_list = [{"month": k, "count": v} for k, v in sorted(monthly.items())][-12:]

    return {
        "username": USERNAME,
        "total_contributions": total_contributions,
        "active_days": active_days,
        "total_days": total_days,
        "current_streak": {"days": current_streak, "start": current_start, "end": current_end},
        "longest_streak": {"days": longest_streak, "start": longest_start, "end": longest_end},
        "best_day": best_day,
        "avg_per_day": avg_per_day,
        "monthly": monthly_list,
        "weeks": weeks,
    }

def render_heatmap(data):
    weeks = data["weeks"]
    total = data["total_contributions"]
    width, height = 860, 195
    cell_size, cell_gap = 11, 3
    step = cell_size + cell_gap
    grid_x, grid_y = 48, 36

    month_labels = []
    cells = []
    active_cells = []
    last_month = None

    # Monta as células usando os dados buscados diariamente no GitHub.
    for w_idx, week in enumerate(weeks):
        for day in week:
            if day:
                dt = datetime.strptime(day["date"], "%Y-%m-%d")
                # Inclui também o primeiro mês parcial (ex.: Oct), como no GitHub.
                if (w_idx == 0 and last_month is None) or (
                    dt.day <= 7 and dt.month != last_month
                ):
                    month_labels.append(
                        f'<text x="{grid_x + w_idx * step}" y="{grid_y - 10}" '
                        f'class="label">{MONTH_NAMES[dt.month - 1]}</text>'
                    )
                    last_month = dt.month
                break

        for d_idx, day in enumerate(week):
            if not day:
                continue

            cell = {
                "x": grid_x + w_idx * step,
                "y": grid_y + d_idx * step,
                "week": w_idx,
                "weekday": d_idx,
                "date": day["date"],
                "count": int(day["count"]),
                "level": int(day["level"]),
                "delay": round((w_idx * 0.022) + (d_idx * 0.035), 3),
            }
            cells.append(cell)
            if cell["count"] > 0:
                active_cells.append(cell)

    # Distribui focos de neon ao longo do calendário. Cada foco usa uma
    # célula real com contribuição; células sem atividade nunca recebem neon.
    anchors = []
    if active_cells:
        min_x = min(cell["x"] for cell in active_cells)
        max_x = max(cell["x"] for cell in active_cells)
        span = max(max_x - min_x + step, step)
        zone_count = 8

        for zone_index in range(zone_count):
            low = min_x + span * zone_index / zone_count
            high = min_x + span * (zone_index + 1) / zone_count
            candidates = [
                cell for cell in active_cells
                if low <= cell["x"] < high
                or (zone_index == zone_count - 1 and cell["x"] == high)
            ]
            if not candidates:
                continue

            candidates.sort(
                key=lambda cell: (cell["count"], -cell["y"]),
                reverse=True,
            )
            anchor = next(
                (
                    cell for cell in candidates
                    if all(abs(cell["x"] - existing["x"]) >= step * 1.5 for existing in anchors)
                ),
                None,
            )
            if anchor is not None:
                anchors.append(anchor)

    zone_keys = set()
    for cell in active_cells:
        if any(
            abs(cell["x"] - anchor["x"]) <= step
            and abs(cell["y"] - anchor["y"]) <= step * 2
            for anchor in anchors
        ):
            zone_keys.add((cell["x"], cell["y"]))

    # Uma estrela por foco e algumas cintilações adicionais nos grupos ativos.
    zone_cells = [cell for cell in active_cells if (cell["x"], cell["y"]) in zone_keys]
    stars = []
    for anchor in anchors:
        key = (anchor["x"], anchor["y"])
        if key not in {(cell["x"], cell["y"]) for cell in stars}:
            stars.append(anchor)

    extra_candidates = sorted(
        zone_cells,
        key=lambda cell: (-cell["count"], cell["x"], cell["y"]),
    )
    for index, cell in enumerate(extra_candidates):
        if len(stars) >= 24:
            break
        key = (cell["x"], cell["y"])
        if key in {(star["x"], star["y"]) for star in stars}:
            continue
        if cell["count"] >= 8 or index % 3 == 0:
            stars.append(cell)

    defs = '''<defs>
    <filter id="starGlow" x="-150%" y="-150%" width="400%" height="400%">
      <feGaussianBlur stdDeviation="1.2" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="zoneGlow" x="-150%" y="-150%" width="400%" height="400%">
      <feGaussianBlur stdDeviation="2.1" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="zoneAura" x="-220%" y="-220%" width="540%" height="540%">
      <feGaussianBlur stdDeviation="4.8"/>
    </filter>
  </defs>'''

    day_labels = [
        f'<text x="16" y="{grid_y + 1 * step + 9}" class="label">Mon</text>',
        f'<text x="16" y="{grid_y + 3 * step + 9}" class="label">Wed</text>',
        f'<text x="16" y="{grid_y + 5 * step + 9}" class="label">Fri</text>',
    ]

    # Halos grandes, pero localizados en pequeños grupos.
    aura_colors = ["#42ff7a", "#31ffd3", "#9c7bff"]
    auras = []
    for index, anchor in enumerate(anchors):
        cx = anchor["x"] + cell_size / 2
        cy = anchor["y"] + cell_size / 2
        color = aura_colors[index % len(aura_colors)]
        delay = round((index * 0.37) % 2.5, 2)
        auras.append(
            f'<circle cx="{cx}" cy="{cy}" r="13" fill="{color}" opacity="0" '
            f'filter="url(#zoneAura)">'
            f'<animate attributeName="opacity" values="0;0.58;0.18;0" '
            f'keyTimes="0;0.28;0.65;1" dur="2.35s" begin="{delay}s" '
            f'repeatCount="indefinite"/>'
            f'<animate attributeName="r" values="7;14;9;7" dur="2.35s" '
            f'begin="{delay}s" repeatCount="indefinite"/>'
            f'</circle>'
        )

    rects = []
    for cell in cells:
        x, y = cell["x"], cell["y"]
        color = COLORS.get(cell["level"], COLORS[0])
        key = (x, y)
        is_zone = key in zone_keys and cell["count"] > 0
        filter_attr = ' filter="url(#zoneGlow)"' if is_zone else ""
        pulse = ""
        if is_zone:
            phase = round(
                ((cell["week"] + cell["weekday"] * 2 + cell["count"]) % 11) / 3,
                2,
            )
            duration = round(1.55 + (cell["weekday"] % 4) * 0.19, 2)
            pulse = (
                f'<animate attributeName="fill-opacity" values="0.68;1;0.76;1" '
                f'keyTimes="0;0.34;0.67;1" dur="{duration}s" '
                f'begin="{phase}s" repeatCount="indefinite"/>'
            )

        rects.append(
            f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
            f'rx="2.5" ry="2.5" fill="{color}"{filter_attr} opacity="0">'
            f'<title>{cell["date"]}: {cell["count"]} contributions</title>'
            f'<animate attributeName="opacity" values="0;1" dur="0.42s" '
            f'begin="{cell["delay"]}s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 -4;0 0" dur="0.42s" begin="{cell["delay"]}s" fill="freeze"/>'
            f'{pulse}</rect>'
        )

    star_shapes = []
    star_colors = ["#f8fffc", "#d5c3ff", "#a9ffed"]
    for index, cell in enumerate(stars):
        cx = cell["x"] + cell_size / 2
        cy = cell["y"] + cell_size / 2
        size = 5.1 if index % 4 == 0 or cell["count"] >= 12 else 3.8
        color = star_colors[(index + 2) % len(star_colors)]
        delay = round(((index * 7 + 2) % 31) / 10, 1)
        duration = round(1.7 + (index % 5) * 0.24, 2)
        star_shapes.append(
            f'<path d="M {cx} {cy - size} L {cx + 0.9} {cy - 0.9} '
            f'L {cx + size} {cy} L {cx + 0.9} {cy + 0.9} '
            f'L {cx} {cy + size} L {cx - 0.9} {cy + 0.9} '
            f'L {cx - size} {cy} L {cx - 0.9} {cy - 0.9} Z" '
            f'fill="{color}" filter="url(#starGlow)" opacity="0">'
            f'<animate attributeName="opacity" values="0;1;0.12;0" '
            f'keyTimes="0;0.15;0.58;1" dur="{duration}s" begin="{delay}s" '
            f'repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="rotate" '
            f'values="0 {cx} {cy};45 {cx} {cy};0 {cx} {cy}" '
            f'dur="{duration}s" begin="{delay}s" repeatCount="indefinite"/>'
            f'</path>'
        )

    legend_x, legend_y = width - 155, height - 24
    legend_items = [
        f'<text x="{legend_x - 32}" y="{legend_y + 9}" class="label">Less</text>'
    ]
    for level in range(5):
        lx = legend_x + level * (cell_size + 3)
        legend_items.append(
            f'<rect x="{lx}" y="{legend_y}" width="{cell_size}" height="{cell_size}" '
            f'rx="2.5" ry="2.5" fill="{COLORS[level]}" />'
        )
    legend_items.append(
        f'<text x="{legend_x + 5 * (cell_size + 3) + 4}" '
        f'y="{legend_y + 9}" class="label">More</text>'
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; }}
    .label {{ fill: #b8c7bc; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 10px; }}
    .footer {{ fill: #c9d1d9; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; font-weight: 600; }}
  </style>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" ry="10" class="bg" />
  {defs}
  {"".join(month_labels)}
  {"".join(day_labels)}
  {"".join(auras)}
  {"".join(rects)}
  {"".join(star_shapes)}
  <text x="{grid_x}" y="{height - 15}" class="footer">{total:,} contributions in the last year</text>
  {"".join(legend_items)}
</svg>'''

    with open("contrib-heatmap.svg", "w", encoding="utf-8") as f:
        f.write(svg)

def refresh_readme_heatmap_url():
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    cache_key = datetime.utcnow().strftime("%Y%m%d")
    url = f"https://raw.githubusercontent.com/{USERNAME}/{USERNAME}/main/contrib-heatmap.svg?v={cache_key}"
    pattern = re.compile(
        r'<img src="[^"]*contrib-heatmap\.svg[^"]*" width="100%" alt="([^"]*)" />'
    )

    updated, replacements = pattern.subn(
        lambda match: f'<img src="{url}" width="100%" alt="{match.group(1)}" />',
        content,
        count=1,
    )
    if replacements:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(updated)

def fmt_range(start, end):
    if not start or not end:
        return "—"
    s = datetime.strptime(start, "%Y-%m-%d").strftime("%b %d")
    e = datetime.strptime(end, "%Y-%m-%d").strftime("%b %d")
    return f"{s} → {e}"

def fmt_date(d):
    if not d:
        return "—"
    return datetime.strptime(d, "%Y-%m-%d").strftime("%b %d, %Y")

def render_stats(d):
    cur_s = d["current_streak"]["days"]
    cur_range = fmt_range(d["current_streak"]["start"], d["current_streak"]["end"])
    long_s = d["longest_streak"]["days"]
    long_range = fmt_range(d["longest_streak"]["start"], d["longest_streak"]["end"])

    total_c = f'{d["total_contributions"]:,}'
    active_d = d["active_days"]
    total_d = d["total_days"]
    best_c = d["best_day"]["count"]
    best_dt = fmt_date(d["best_day"]["date"])
    avg_c = d["avg_per_day"]

    monthly = d["monthly"]
    max_m = max((m["count"] for m in monthly), default=1) or 1

    bars_svg = []
    bar_x_start, bar_y_bottom, bar_max_h, bar_w, bar_gap = 54, 815, 195, 44, 18

    for idx, m in enumerate(monthly):
        cnt = m["count"]
        h = max(int((cnt / max_m) * bar_max_h), 8)
        x = bar_x_start + idx * (bar_w + bar_gap)
        y = bar_y_bottom - h
        m_num = int(m["month"].split("-")[1])
        m_lbl = MONTH_NAMES[m_num - 1]
        fill = "#39d353" if cnt == max_m and cnt > 0 else "#26a641"
        delay = round(0.2 + idx * 0.05, 2)

        bars_svg.append(
            f'<g class="bar-group" style="animation-delay: {delay}s">'
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{h}" rx="4" fill="{fill}" />'
            f'<text x="{x + bar_w/2}" y="{y - 8}" text-anchor="middle" class="bar-val">{cnt}</text>'
            f'<text x="{x + bar_w/2}" y="{bar_y_bottom + 20}" text-anchor="middle" class="bar-lbl">{m_lbl}</text>'
            f'</g>'
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="880" viewBox="0 0 840 880">
  <style>
    .win {{ fill: #0d1117; stroke: #30363d; stroke-width: 2px; }}
    .hdr {{ fill: #161b22; }}
    .title {{ fill: #8b949e; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 16px; }}
    .card {{ fill: #161b22; stroke: #21262d; stroke-width: 1.5px; }}
    .k-green {{ fill: #39d353; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 16px; font-weight: 600; }}
    .k-muted {{ fill: #8b949e; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 15px; font-weight: 600; letter-spacing: 0.5px; }}
    .v-green {{ fill: #39d353; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 48px; font-weight: 700; }}
    .v-white {{ fill: #f0f6fc; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 44px; font-weight: 700; }}
    .unit {{ fill: #8b949e; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 20px; }}
    .sub {{ fill: #8b949e; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 16px; }}
    .bar-val {{ fill: #c9d1d9; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }}
    .bar-lbl {{ fill: #8b949e; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }}
    .bar-group {{ opacity: 0; animation: fadeIn 0.4s ease forwards; }}
    @keyframes fadeIn {{ to {{ opacity: 1; }} }}
  </style>

  <rect x="1" y="1" width="838" height="878" rx="14" class="win" />
  <path d="M 15 1 H 825 A 14 14 0 0 1 839 15 V 48 H 1 V 15 A 14 14 0 0 1 15 1 Z" class="hdr" />
  <line x1="1" y1="48" x2="839" y2="48" stroke="#30363d" stroke-width="1.5" />
  <circle cx="26" cy="24" r="7" fill="#ff5f56" />
  <circle cx="50" cy="24" r="7" fill="#ffbd2e" />
  <circle cx="74" cy="24" r="7" fill="#27c93f" />
  <text x="420" y="30" text-anchor="middle" class="title">{d["username"]}@github — stats</text>

  <rect x="40" y="75" width="365" height="150" rx="10" class="card" />
  <text x="65" y="110" class="k-green">⚡ current streak</text>
  <text x="65" y="168" class="v-green">{cur_s}</text>
  <text x="175" y="168" class="unit">days</text>
  <text x="65" y="202" class="sub">{cur_range}</text>

  <rect x="435" y="75" width="365" height="150" rx="10" class="card" />
  <text x="460" y="110" class="k-muted"># longest streak</text>
  <text x="460" y="168" class="v-white">{long_s}</text>
  <text x="570" y="168" class="unit">days</text>
  <text x="460" y="202" class="sub">{long_range}</text>

  <rect x="40" y="245" width="365" height="150" rx="10" class="card" />
  <text x="65" y="280" class="k-muted">COMMITS (1Y)</text>
  <text x="65" y="338" class="v-white">{total_c}</text>
  <text x="65" y="372" class="sub">last 12 months</text>

  <rect x="435" y="245" width="365" height="150" rx="10" class="card" />
  <text x="460" y="280" class="k-muted">ACTIVE DAYS</text>
  <text x="460" y="338" class="v-white">{active_d}</text>
  <text x="570" y="338" class="unit">/ {total_d}</text>
  <text x="460" y="372" class="sub">{int(round(active_d / max(total_d,1) * 100))}% of the year</text>

  <rect x="40" y="415" width="365" height="140" rx="10" class="card" />
  <text x="65" y="450" class="k-muted">BEST DAY</text>
  <text x="65" y="505" class="v-white">{best_c}</text>
  <text x="175" y="505" class="unit">commits</text>
  <text x="65" y="537" class="sub">{best_dt}</text>

  <rect x="435" y="415" width="365" height="140" rx="10" class="card" />
  <text x="460" y="450" class="k-muted">Ø PER DAY</text>
  <text x="460" y="505" class="v-white">{avg_c}</text>
  <text x="585" y="505" class="unit">/ day</text>
  <text x="460" y="537" class="sub">across {total_d} days</text>

  <text x="54" y="595" class="k-muted">CONTRIBUTIONS / MONTH</text>
  <text x="786" y="595" text-anchor="end" class="sub">peak {max_m}</text>
  {"".join(bars_svg)}
</svg>'''

    with open("stats.svg", "w", encoding="utf-8") as f:
        f.write(svg)

if __name__ == "__main__":
    data = fetch_data()
    render_heatmap(data)
    render_stats(data)
    refresh_readme_heatmap_url()
