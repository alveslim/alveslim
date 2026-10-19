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

    total_contributions = sum(d["count"] for d in days)
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

    rects, month_labels = [], []
    last_month = None

    for w_idx, week in enumerate(weeks):
        for d in week:
            if d:
                dt = datetime.strptime(d["date"], "%Y-%m-%d")
                if dt.day <= 7 and dt.month != last_month:
                    m_name = MONTH_NAMES[dt.month - 1]
                    mx = grid_x + w_idx * step
                    month_labels.append(f'<text x="{mx}" y="{grid_y - 10}" class="label">{m_name}</text>')
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

    legend_x, legend_y = width - 155, height - 24
    legend_items = [f'<text x="{legend_x - 32}" y="{legend_y + 9}" class="label">Less</text>']
    for lvl in range(5):
        lx = legend_x + lvl * (cell_size + 3)
        legend_items.append(f'<rect x="{lx}" y="{legend_y}" width="{cell_size}" height="{cell_size}" rx="2.5" ry="2.5" fill="{COLORS[lvl]}" />')
    legend_items.append(f'<text x="{legend_x + 5 * (cell_size + 3) + 4}" y="{legend_y + 9}" class="label">More</text>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; }}
    .label {{ fill: #8b949e; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 10px; }}
    .footer {{ fill: #c9d1d9; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; font-weight: 600; }}
    .cell {{ opacity: 0; transform: translateY(-6px); animation: popIn 0.35s cubic-bezier(0.22, 1, 0.36, 1) forwards; }}
    @keyframes popIn {{ to {{ opacity: 1; transform: translateY(0); }} }}
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
