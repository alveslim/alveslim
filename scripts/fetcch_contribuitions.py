import os
import re
import json
from datetime import datetime, date
import requests
from bs4 import BeautifulSoup

USERNAME = os.getenv("GITHUB_USER", "alveslim")
URL = f"https://github.com/users/{USERNAME}/contributions"

def fetch():
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "text/html",
    }
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Mapeia os tooltips para obter a contagem exata de cada dia
    tooltips = {}
    for tip in soup.find_all("tool-tip"):
        for_id = tip.get("for")
        text = tip.get_text(strip=True)
        m = re.search(r"(\d+)\s+contribution", text)
        count = int(m.group(1)) if m else 0
        if for_id:
            tooltips[for_id] = count

    days = []
    cells = soup.select("td.ContributionCalendar-day")
    for cell in cells:
        d_str = cell.get("data-date")
        if not d_str:
            continue
        level = int(cell.get("data-level", "0"))
        cell_id = cell.get("id")
        count = tooltips.get(cell_id, 0)
        if count == 0 and level > 0:
            # Fallback caso o GitHub mude o formato do tool-tip
            count = {1: 1, 2: 3, 3: 6, 4: 10}.get(level, 1)
        days.append({"date": d_str, "count": count, "level": level})

    days.sort(key=lambda x: x["date"])

    # Organiza em colunas de semanas (Domingo = 0 ... Sábado = 6)
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

    # Cálculo de Longest Streak e Current Streak
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

    # Streak atual (contando de hoje/ontem para trás)
    current_streak = 0
    current_start = current_end = None
    reversed_days = list(reversed(days))
    for i, d in enumerate(reversed_days):
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

    # Agrupamento mensal (últimos 12 meses)
    monthly = {}
    for d in days:
        ym = d["date"][:7]
        monthly[ym] = monthly.get(ym, 0) + d["count"]
    monthly_list = [{"month": k, "count": v} for k, v in sorted(monthly.items())][-12:]

    os.makedirs("data", exist_ok=True)
    out = {
        "username": USERNAME,
        "total_contributions": total_contributions,
        "active_days": active_days,
        "total_days": total_days,
        "current_streak": {
            "days": current_streak,
            "start": current_start,
            "end": current_end,
        },
        "longest_streak": {
            "days": longest_streak,
            "start": longest_start,
            "end": longest_end,
        },
        "best_day": best_day,
        "avg_per_day": avg_per_day,
        "monthly": monthly_list,
        "weeks": weeks,
    }

    with open("data/contributions.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    fetch()