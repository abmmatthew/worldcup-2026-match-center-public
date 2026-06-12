from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd


def get_nested(obj: Dict[str, Any], path: str, default: Any = "") -> Any:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part)
        if cur is None:
            return default
    return cur


def team_label(team: Dict[str, Any] | None, source: Dict[str, Any] | None = None) -> str:
    if team:
        return team.get("name") or team.get("abbreviation") or "TBD"
    if source:
        return source.get("placeholder") or source.get("description") or "TBD"
    return "TBD"


def team_code(team: Dict[str, Any] | None) -> str:
    if not team:
        return ""
    return team.get("abbreviation") or team.get("country_code") or ""


def parse_matches(matches: List[Dict[str, Any]]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for m in matches or []:
        home = m.get("home_team") or None
        away = m.get("away_team") or None
        stadium = m.get("stadium") or {}
        stage = m.get("stage") or {}
        group = m.get("group") or {}
        rows.append(
            {
                "match_id": m.get("id"),
                "match_number": m.get("match_number"),
                "datetime_utc": m.get("datetime"),
                "status": m.get("status") or "",
                "clock": m.get("clock_display") or "",
                "stage": stage.get("name") or "",
                "stage_order": stage.get("order"),
                "group": group.get("name") or "",
                "round_number": m.get("round_number"),
                "round_name": m.get("round_name") or "",
                "stadium": stadium.get("name") or "",
                "city": stadium.get("city") or "",
                "country": stadium.get("country") or "",
                "home_team": team_label(home, m.get("home_team_source")),
                "away_team": team_label(away, m.get("away_team_source")),
                "home_code": team_code(home),
                "away_code": team_code(away),
                "home_team_id": home.get("id") if home else None,
                "away_team_id": away.get("id") if away else None,
                "home_score": m.get("home_score"),
                "away_score": m.get("away_score"),
                "home_pen": m.get("home_score_penalties"),
                "away_pen": m.get("away_score_penalties"),
                "home_formation": m.get("home_formation") or "",
                "away_formation": m.get("away_formation") or "",
                "home_source": get_nested(m, "home_team_source.description", ""),
                "away_source": get_nested(m, "away_team_source.description", ""),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["datetime_utc_dt"] = pd.to_datetime(df["datetime_utc"], errors="coerce", utc=True)
    return df


def parse_teams(teams: List[Dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "team_id": t.get("id"),
                "team_name": t.get("name"),
                "team_code": t.get("abbreviation") or t.get("country_code"),
                "country_code": t.get("country_code"),
                "confederation": t.get("confederation"),
            }
            for t in teams or []
        ]
    )


def parse_standings(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    parsed: List[Dict[str, Any]] = []
    for r in rows or []:
        team = r.get("team") or {}
        group = r.get("group") or {}
        parsed.append(
            {
                "Group": group.get("name") or "",
                "Pos": r.get("position"),
                "Team": team.get("name") or "",
                "Code": team.get("abbreviation") or team.get("country_code") or "",
                "P": r.get("played"),
                "W": r.get("won"),
                "D": r.get("drawn"),
                "L": r.get("lost"),
                "GF": r.get("goals_for"),
                "GA": r.get("goals_against"),
                "GD": r.get("goal_difference"),
                "Pts": r.get("points"),
            }
        )
    df = pd.DataFrame(parsed)
    if not df.empty:
        df = df.sort_values(["Group", "Pos"], na_position="last")
    return df


def parse_rosters(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    parsed: List[Dict[str, Any]] = []
    for r in rows or []:
        player = r.get("player") or {}
        parsed.append(
            {
                "Jersey #": player.get("jersey_number") or "",
                "Player": player.get("name") or "",
                "Short Name": player.get("short_name") or "",
                "Position": r.get("position") or player.get("position") or "",
                "Team ID": r.get("team_id") or "",
                "Country": player.get("country_name") or player.get("country_code") or "",
                "Apps": r.get("appearances"),
                "Starts": r.get("starts"),
                "Min": r.get("minutes_played"),
                "Goals": r.get("goals"),
                "Assists": r.get("assists"),
                "YC": r.get("yellow_cards"),
                "RC": r.get("red_cards"),
                "Avg Rating": r.get("avg_rating"),
                "Player ID": player.get("id") or "",
            }
        )
    df = pd.DataFrame(parsed)
    if not df.empty:
        df["Jersey Sort"] = pd.to_numeric(df["Jersey #"], errors="coerce")
        df = df.sort_values(["Jersey Sort", "Player"], na_position="last").drop(columns=["Jersey Sort"])
    return df


def parse_events(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    parsed: List[Dict[str, Any]] = []
    for e in rows or []:
        player = e.get("player") or {}
        assist = e.get("assist_player") or {}
        minute = e.get("time_minute")
        added = e.get("added_time")
        minute_text = ""
        if minute is not None:
            minute_text = f"{minute}'" if not added else f"{minute}+{added}'"
        parsed.append(
            {
                "Event ID": e.get("id"),
                "Match ID": e.get("match_id"),
                "Minute": minute_text,
                "Minute Number": minute,
                "Type": e.get("incident_type") or "",
                "Class": e.get("incident_class") or "",
                "Side": "Home" if e.get("is_home") is True else "Away" if e.get("is_home") is False else "",
                "Player": player.get("name") or "",
                "Player Jersey": player.get("jersey_number") or "",
                "Assist": assist.get("name") or "",
                "Home Score": e.get("home_score"),
                "Away Score": e.get("away_score"),
                "Reason": e.get("reason") or "",
            }
        )
    df = pd.DataFrame(parsed)
    if not df.empty:
        df = df.sort_values(["Match ID", "Minute Number", "Event ID"], na_position="last")
    return df


def parse_lineups(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    parsed: List[Dict[str, Any]] = []
    for r in rows or []:
        player = r.get("player") or {}
        parsed.append(
            {
                "Match ID": r.get("match_id"),
                "Team ID": r.get("team_id"),
                "Shirt #": r.get("shirt_number") or player.get("jersey_number") or "",
                "Player": player.get("name") or "",
                "Position": r.get("position") or player.get("position") or "",
                "Starter": bool(r.get("is_starter")),
                "Substitute": bool(r.get("is_substitute")),
                "Formation": r.get("formation") or "",
                "Player ID": player.get("id") or "",
            }
        )
    df = pd.DataFrame(parsed)
    if not df.empty:
        df["Starter Rank"] = df["Starter"].apply(lambda x: 0 if x else 1)
        df["Shirt Sort"] = pd.to_numeric(df["Shirt #"], errors="coerce")
        df = df.sort_values(["Team ID", "Starter Rank", "Shirt Sort", "Player"], na_position="last").drop(columns=["Starter Rank", "Shirt Sort"])
    return df


def goal_scorers_by_side(events_df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    home: List[str] = []
    away: List[str] = []
    if events_df.empty:
        return home, away
    goals = events_df[events_df["Type"].str.lower().eq("goal")].copy()
    for _, row in goals.iterrows():
        text = str(row.get("Player") or "Goal")
        minute = row.get("Minute") or ""
        jersey = row.get("Player Jersey") or ""
        if jersey:
            text = f"#{jersey} {text} {minute}".strip()
        else:
            text = f"{text} {minute}".strip()
        if row.get("Side") == "Home":
            home.append(text)
        elif row.get("Side") == "Away":
            away.append(text)
    return home, away


def top_scorers_from_events(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame(columns=["Player", "Goals"])
    goals = events_df[events_df["Type"].str.lower().eq("goal")]
    counts = Counter(goals["Player"].dropna())
    return pd.DataFrame([{"Player": k, "Goals": v} for k, v in counts.most_common()])
