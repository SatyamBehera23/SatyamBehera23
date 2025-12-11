#!/usr/bin/env python3
"""
generate_streak_svg.py

- Fetches the contributions calendar via GitHub GraphQL for a given user.
- Computes the current contribution streak (consecutive days up to today with > 0 contributions).
- Generates a simple SVG card and writes `streak.svg`.
"""

import os
import sys
import requests
import datetime
from typing import List, Dict

GITHUB_API = "https://api.github.com/graphql"
USER = (
    os.environ.get("GITHUB_USER")
    or os.environ.get("INPUT_USER")
    or os.environ.get("REPO_OWNER")
)
TOKEN = os.environ.get("GITHUB_TOKEN")  # provided by GitHub Actions

if not TOKEN:
    print("Error: GITHUB_TOKEN environment variable is required.", file=sys.stderr)
    sys.exit(2)

if not USER:
    USER = os.environ.get("GITHUB_REPOSITORY_OWNER")
    if not USER:
        print("Error: Could not determine GitHub user. Set GITHUB_USER env var.", file=sys.stderr)
        sys.exit(2)


def run_graphql(query: str, variables: dict = None) -> dict:
    headers = {
        "Authorization": f"bearer {TOKEN}",
        "Accept": "application/vnd.github.everest-preview+json",
    }
    json_data = {"query": query}
    if variables:
        json_data["variables"] = variables

    r = requests.post(GITHUB_API, json=json_data, headers=headers, timeout=30)
    r.raise_for_status()

    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def fetch_contribution_days(user: str) -> List[Dict]:
    query = """
    query ($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    res = run_graphql(query, {"login": user})
    weeks = res["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

    days = []
    for week in weeks:
        for d in week["contributionDays"]:
            days.append({"date": d["date"], "count": d["contributionCount"]})

    days.sort(key=lambda x: x["date"])  # sort ascending
    return days


def compute_current_streak(days: List[Dict]) -> int:
    if not days:
        return 0

    day_map = {d["date"]: d["count"] for d in days}

    last_date_str = days[-1]["date"]
    last_date = datetime.datetime.strptime(last_date_str, "%Y-%m-%d").date()
    today = datetime.date.today()

    cursor = min(today, last_date)
    streak = 0

    while True:
        key = cursor.strftime("%Y-%m-%d")
        count = day_map.get(key, 0)

        if count > 0:
            streak += 1
            cursor -= datetime.timedelta(days=1)
        else:
            break

    return streak


def generate_svg(streak: int, total_last_year: int = None, username: str = "") -> str:
    title = "GitHub Contribution Streak"
    subtitle = f"{streak} day" + ("s" if streak != 1 else "")
    date_str = datetime.date.today().strftime("%b %d, %Y")

    width = 540
    height = 110

    if streak >= 30:
        accent = "#FF6B6B"
    elif streak >= 7:
        accent = "#FFB86B"
    elif streak >= 1:
        accent = "#66ccff"
    else:
        accent = "#888888"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" 
    viewBox="0 0 {width} {height}" preserveAspectRatio="xMinYMin">
  <defs>
    <linearGradient id="g" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="#0f1724" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="#071029" stop-opacity="0.95"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" 
      flood-color="#000" flood-opacity="0.5"/>
    </filter>
  </defs>

  <rect rx="12" ry="12" width="100%" height="100%" fill="url(#g)" filter="url(#shadow)"/>

  <g transform="translate(22,20)">
    <g transform="translate(0,0)">
      <g transform="scale(0.9)">
        <path d="M18 2s-2 3-2.5 5c-.5 2-2.2 3-2.2 5 0 2.8 
        2.2 5 5 5s5-2.2 5-5c0-3-2-5.5-2-8S25 2 25 2 
        22 6 21 6c-1 0-3-3-3-3S18 2 18 2z" fill="{accent}" />
      </g>
    </g>

    <g transform="translate(60,6)">
      <text x="0" y="18" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" 
      font-size="15" fill="#E6EEF6" font-weight="700">{title}</text>

      <text x="0" y="42" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" 
      font-size="28" fill="{accent}" font-weight="800">{subtitle}</text>

      <text x="0" y="66" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" 
      font-size="11" fill="#9FB4C8">Updated: {date_str}</text>
    </g>
  </g>
</svg>'''
    return svg


def main():
    try:
        days = fetch_contribution_days(USER)
    except Exception as e:
        print(f"Error fetching contributions: {e}", file=sys.stderr)
        sys.exit(3)

    streak = compute_current_streak(days)
    total = sum(d["count"] for d in days) if days else 0

    svg = generate_svg(streak, total_last_year=total, username=USER)

    out_path = "streak.svg"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Wrote {out_path} (current streak: {streak})")


if __name__ == "__main__":
    main()
