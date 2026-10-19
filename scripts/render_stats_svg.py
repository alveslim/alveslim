import json
from datetime import datetime

MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

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

def render():
    with open("data/contributions.json", "r", encoding="utf-8") as f:
        d = json.load(f)

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
    bar_x_start = 54
    bar_y_bottom = 815
    bar_max_h = 195
    bar_w = 44
    bar_gap = 18

    for idx, m in enumerate(monthly):
        cnt = m["count"]
        h = max(int((cnt / max_m) * bar_max_h), 8)
        x = bar_x_start + idx * (bar_w + bar_gap)
        y = bar_y_bottom - h
        m_num = int(m["month"].split("-")[1])
        m_lbl = MONTH_SHORT[m_num - 1]
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

  <!-- Row 1 -->
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

  <!-- Row 2 -->
  <rect x="40" y="245" width="365" height="150" rx="10" class="card" />
  <text x="65" y="280" class="k-muted">COMMITS (1Y)</text>
  <text x="65" y="338" class="v-white">{total_c}</text>
  <text x="65" y="372" class="sub">last 12 months</text>

  <rect x="435" y="245" width="365" height="150" rx="10" class="card" />
  <text x="460" y="280" class="k-muted">ACTIVE DAYS</text>
  <text x="460" y="338" class="v-white">{active_d}</text>
  <text x="570" y="338" class="unit">/ {total_d}</text>
  <text x="460" y="372" class="sub">{int(round(active_d / max(total_d,1) * 100))}% of the year</text>

  <!-- Row 3 -->
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

  <!-- Monthly Bar Chart -->
  <text x="54" y="595" class="k-muted">CONTRIBUTIONS / MONTH</text>
  <text x="786" y="595" text-anchor="end" class="sub">peak {max_m}</text>
  {"".join(bars_svg)}
</svg>'''

    with open("stats.svg", "w", encoding="utf-8") as f:
        f.write(svg)

if __name__ == "__main__":
    render()