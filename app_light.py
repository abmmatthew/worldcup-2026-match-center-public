from __future__ import annotations

import html
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

from services.balldontlie_client import ApiResult, bdl_get_all
from services.balldontlie_parser import (
    goal_scorers_by_side,
    parse_events,
    parse_lineups,
    parse_matches,
    parse_rosters,
    parse_standings,
    parse_teams,
    team_label,
    top_scorers_from_events,
)

st.set_page_config(
    page_title="World Cup 2026 Match Centre",
    page_icon="WC",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_DIR = "data"
FIXTURES_PATH = os.path.join(DATA_DIR, "fixtures.csv")
TEAMS_PATH = os.path.join(DATA_DIR, "teams.csv")
PLAYERS_PATH = os.path.join(DATA_DIR, "players.csv")
KNOCKOUT_PATH = os.path.join(DATA_DIR, "knockout.csv")

SOURCE_TIMEZONE = "America/New_York"

VENUE_TIMEZONES = {
    "Atlanta": "America/New_York",
    "Boston": "America/New_York",
    "Dallas": "America/Chicago",
    "East Rutherford": "America/New_York",
    "Guadalajara": "America/Mexico_City",
    "Houston": "America/Chicago",
    "Kansas City": "America/Chicago",
    "Los Angeles": "America/Los_Angeles",
    "Mexico City": "America/Mexico_City",
    "Miami": "America/New_York",
    "Monterrey": "America/Monterrey",
    "Philadelphia": "America/New_York",
    "San Francisco": "America/Los_Angeles",
    "Seattle": "America/Los_Angeles",
    "Toronto": "America/Toronto",
    "Vancouver": "America/Vancouver",
}

USER_TIMEZONES = {
    "Houston, TX": "America/Chicago",
    "Dallas, TX": "America/Chicago",
    "Chicago, IL": "America/Chicago",
    "New York / New Jersey": "America/New_York",
    "Miami, FL": "America/New_York",
    "Atlanta, GA": "America/New_York",
    "Los Angeles, CA": "America/Los_Angeles",
    "San Francisco, CA": "America/Los_Angeles",
    "Seattle, WA": "America/Los_Angeles",
    "Toronto, Canada": "America/Toronto",
    "Vancouver, Canada": "America/Vancouver",
    "Mexico City, Mexico": "America/Mexico_City",
    "Monterrey, Mexico": "America/Monterrey",
    "London, UK": "Europe/London",
    "Kochi / Bengaluru, India": "Asia/Kolkata",
}

st.markdown(
    """
    <style>
    html, body, [class*="css"] {font-family: Inter, Segoe UI, Arial, sans-serif;}
    .block-container {padding-top: 1rem; padding-bottom: 2.25rem; max-width: 1220px;}
    section[data-testid="stSidebar"] {display:none;}
    h1 {font-size: clamp(1.8rem, 4vw, 2.65rem) !important; line-height:1.05 !important; letter-spacing:-.035em; margin-bottom:.25rem !important;}
    h2 {letter-spacing:-.025em;}
    .muted {color:#64748b; font-size:.92rem;}
    .topbar {display:flex; align-items:flex-end; justify-content:space-between; gap:18px; flex-wrap:wrap; margin-bottom:18px;}
    .status-grid {display:grid; grid-template-columns:repeat(2,minmax(190px,1fr)); gap:14px; margin:14px 0 12px;}
    .status-card {border:1px solid #e2e8f0; border-radius:18px; padding:14px 16px; background:#fff; box-shadow:0 2px 12px rgba(15,23,42,.04);}
    .status-label {color:#475569; font-size:.74rem; font-weight:850; text-transform:uppercase; letter-spacing:.05em; margin-bottom:7px;}
    .status-value {color:#111827; font-size:1.08rem; font-weight:850; line-height:1.25;}
    .status-sub {color:#64748b; font-size:.80rem; margin-top:5px;}
    .home-grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(245px,1fr)); gap:16px; margin-top:18px;}
    .home-card {border:1px solid #dbe4f0; border-radius:18px; padding:18px; background:#fff; box-shadow:0 4px 18px rgba(15,23,42,.055); min-height:170px;}
    .home-card-top {height:58px; border-radius:14px; background:linear-gradient(135deg,#f8fafc,#eff6ff); display:flex; align-items:center; justify-content:center; color:#0f172a; font-weight:900; font-size:1.1rem; margin-bottom:14px;}
    .pill {display:inline-block; padding:4px 9px; border-radius:999px; background:#fee2e2; color:#111827; font-size:.76rem; font-weight:750; margin-right:6px; margin-bottom:8px;}
    .pill.alt {background:#ede9fe;}
    .home-title {font-size:1.12rem; font-weight:850; color:#020617; margin:5px 0 8px;}
    .home-text {color:#475569; line-height:1.45; font-size:.92rem;}
    .scoreboard-card {border:1px solid #dbe4f0; border-radius:20px; overflow:hidden; background:#fff; box-shadow:0 6px 22px rgba(15,23,42,.08); margin:10px 0 20px; max-width:900px;}
    .scoreboard-top {background:#16a34a; color:white; padding:12px 16px; display:flex; align-items:center; justify-content:space-between; gap:10px;}
    .scoreboard-league {font-weight:850; font-size:.98rem;}
    .scoreboard-live-pill {background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.35); border-radius:999px; padding:4px 10px; font-size:.78rem; font-weight:850;}
    .scoreboard-body {padding:16px 18px 14px;}
    .scoreboard-status-row {display:flex; justify-content:space-between; align-items:center; color:#64748b; font-size:.88rem; margin-bottom:12px; gap:12px;}
    .scoreboard-clock {color:#16a34a; font-weight:900; letter-spacing:.02em; font-size:1rem; white-space:nowrap;}
    .scoreboard-main {display:grid; grid-template-columns:1fr 142px 1fr; align-items:center; gap:14px;}
    .scoreboard-team {text-align:center; min-width:0;}
    .scoreboard-team-name {font-size:1rem; font-weight:850; color:#111827; margin-top:6px; overflow-wrap:anywhere;}
    .scoreboard-flag {width:52px; height:52px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:2rem; background:#f8fafc; border:1px solid #e2e8f0;}
    .scoreboard-score {text-align:center; font-size:2.7rem; font-weight:950; color:#111827; letter-spacing:.02em; white-space:nowrap;}
    .scoreboard-goals {display:grid; grid-template-columns:1fr 1fr; gap:18px; border-top:1px solid #eef2f7; margin-top:14px; padding-top:10px; color:#475569; font-size:.86rem; min-height:34px;}
    .scoreboard-goals-right {text-align:right;}
    .scoreboard-footer {border-top:1px solid #eef2f7; color:#64748b; font-size:.82rem; padding-top:9px; margin-top:10px; display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap;}
    .notice {border:1px solid #dbeafe; background:#eff6ff; color:#334155; border-radius:14px; padding:12px 14px; margin:12px 0; font-size:.92rem;}
    .bracket-board {display:grid; grid-template-columns:repeat(5,minmax(190px,1fr)); gap:14px; align-items:start; overflow-x:auto; padding-bottom:8px;}
    .bracket-stage {border:1px solid #dbe4f0; border-radius:14px; background:#f8fbff; padding:12px; min-height:250px;}
    .bracket-stage-title {font-weight:850; text-align:center; color:#102a56; margin-bottom:12px; font-size:.98rem;}
    .bracket-scroll {max-height:720px; overflow-y:auto; padding-right:4px;}
    .bracket-card {border:1px solid #cbd5e1; border-radius:12px; background:white; padding:10px; margin-bottom:10px; box-shadow:0 1px 3px rgba(15,23,42,.06);}
    .bracket-label {font-weight:850; color:#0f172a; font-size:.90rem;}
    .bracket-meta {color:#64748b; font-size:.76rem; margin-bottom:6px;}
    .bracket-team {display:flex; justify-content:space-between; gap:8px; padding:4px 0; border-top:1px solid #eef2f7;}
    .footer-note {color:#64748b; font-size:.82rem; margin-top:18px;}
    @media (max-width: 760px) {
      .block-container {padding-left: .85rem; padding-right: .85rem;}
      .status-grid {grid-template-columns:1fr;}
      .scoreboard-main {grid-template-columns:1fr 88px 1fr; gap:8px;}
      .scoreboard-score {font-size:1.8rem;}
      .scoreboard-flag {width:40px; height:40px; font-size:1.55rem;}
      .scoreboard-team-name {font-size:.84rem;}
      .scoreboard-status-row {font-size:.78rem; align-items:flex-start;}
      .scoreboard-goals {font-size:.78rem; gap:10px;}
      .home-card {min-height:150px;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, keep_default_na=False)


def normalize_dataframes(fixtures: pd.DataFrame, teams: pd.DataFrame, players: pd.DataFrame, knockout: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not fixtures.empty:
        fixtures = fixtures.copy()
        fixtures["match_date"] = pd.to_datetime(fixtures["match_date"], errors="coerce")
        fixtures["status"] = fixtures.get("status", "scheduled").replace("", "scheduled").astype(str).str.lower()
        for col in ["score_a", "score_b", "minute", "api_fixture_id"]:
            if col not in fixtures.columns:
                fixtures[col] = ""
            fixtures[col] = fixtures[col].astype("object")
    if not teams.empty:
        teams = teams.copy()
        for col in ["balldontlie_team_id", "coach", "fifa_rank", "notes"]:
            if col not in teams.columns:
                teams[col] = ""
    if not players.empty:
        players = players.copy()
        for col in ["api_player_id", "club", "age", "status"]:
            if col not in players.columns:
                players[col] = ""
    if not knockout.empty:
        knockout = knockout.copy()
        knockout["match_date"] = pd.to_datetime(knockout["match_date"], errors="coerce")
        knockout["status"] = knockout.get("status", "scheduled").replace("", "scheduled").astype(str).str.lower()
    return fixtures, teams, players, knockout


fixtures, teams, players, knockout = normalize_dataframes(
    load_csv(FIXTURES_PATH), load_csv(TEAMS_PATH), load_csv(PLAYERS_PATH), load_csv(KNOCKOUT_PATH)
)

if fixtures.empty or teams.empty:
    st.error("Missing data files. Make sure data/fixtures.csv and data/teams.csv exist.")
    st.stop()

TEAM_LOOKUP: Dict[str, Dict[str, Any]] = teams.set_index("team_code").to_dict(orient="index") if not teams.empty else {}


def read_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default) or default)
    except Exception:
        return default


def get_bdl_api_key() -> str:
    return (
        read_secret("BDL_FIFA_API_KEY", "")
        or read_secret("BALLDONTLIE_API_KEY", "")
        or os.getenv("BDL_FIFA_API_KEY", "")
        or os.getenv("BALLDONTLIE_API_KEY", "")
    )


def pretty_dt(dt: datetime) -> str:
    hour = dt.hour % 12 or 12
    return f"{dt.strftime('%b %d')}, {hour}:{dt.strftime('%M %p %Z')}"


def file_mtime(path: str, tz: str) -> str:
    if not os.path.exists(path):
        return "Not found"
    return pretty_dt(datetime.fromtimestamp(os.path.getmtime(path), tz=ZoneInfo(tz)))


def now_text(tz: str) -> str:
    return pretty_dt(datetime.now(ZoneInfo(tz)))


def flag_for_code(code: str) -> str:
    if not code:
        return ""
    row = TEAM_LOOKUP.get(str(code).upper(), {})
    return row.get("flag", "")


def name_for_code(code: str) -> str:
    if not code:
        return "TBD"
    row = TEAM_LOOKUP.get(str(code).upper(), {})
    return row.get("team_name", code)


def fmt_score(value: Any) -> str:
    if value is None or value == "":
        return "-"
    try:
        if pd.isna(value):
            return "-"
    except Exception:
        pass
    try:
        return str(int(float(value)))
    except Exception:
        return str(value)


def venue_tz(city: str) -> str:
    return VENUE_TIMEZONES.get(str(city), SOURCE_TIMEZONE)


def local_fixture_datetime(row: pd.Series) -> Optional[datetime]:
    try:
        if pd.isna(row.get("match_date")) or not row.get("time_et"):
            return None
        raw = f"{row['match_date'].strftime('%Y-%m-%d')} {row['time_et']}"
        naive = datetime.strptime(raw, "%Y-%m-%d %H:%M")
        return naive.replace(tzinfo=ZoneInfo(SOURCE_TIMEZONE))
    except Exception:
        return None


def format_dt(dt: Optional[datetime], tz_name: str) -> str:
    if not dt:
        return ""
    return pretty_dt(dt.astimezone(ZoneInfo(tz_name)))


def format_api_dt(dt: Any, tz_name: str) -> str:
    if pd.isna(dt):
        return ""
    try:
        if not isinstance(dt, pd.Timestamp):
            dt = pd.to_datetime(dt, utc=True)
        if dt.tzinfo is None:
            dt = dt.tz_localize("UTC")
        return pretty_dt(dt.tz_convert(tz_name).to_pydatetime())
    except Exception:
        return ""


def status_card(label: str, value: str, sub: str = "") -> str:
    return f"<div class='status-card'><div class='status-label'>{html.escape(label)}</div><div class='status-value'>{html.escape(value)}</div><div class='status-sub'>{html.escape(sub)}</div></div>"


def home_card(code: str, title: str, tags: List[str], text: str) -> str:
    tag_html = "".join(f"<span class=\"pill {'alt' if i % 2 else ''}\">{html.escape(t)}</span>" for i, t in enumerate(tags))
    return f"<div class='home-card'><div class='home-card-top'>{html.escape(code)}</div>{tag_html}<div class='home-title'>{html.escape(title)}</div><div class='home-text'>{html.escape(text)}</div></div>"


def local_fixtures_display(df: pd.DataFrame, selected_tz: str, include_times: bool = True) -> pd.DataFrame:
    out = df.copy()
    out["Team A"] = out["team_a"].apply(lambda x: f"{flag_for_code(x)} {name_for_code(x)}")
    out["Team B"] = out["team_b"].apply(lambda x: f"{flag_for_code(x)} {name_for_code(x)}")
    out["Kickoff ET"] = out.apply(lambda r: format_dt(local_fixture_datetime(r), SOURCE_TIMEZONE), axis=1)
    if include_times:
        out["Venue Local Time"] = out.apply(lambda r: format_dt(local_fixture_datetime(r), venue_tz(r.get("city", ""))), axis=1)
        out["Your Time"] = out.apply(lambda r: format_dt(local_fixture_datetime(r), selected_tz), axis=1)
    out["Score"] = out.apply(lambda r: f"{fmt_score(r.get('score_a'))} - {fmt_score(r.get('score_b'))}", axis=1)
    out["Status"] = out["status"].astype(str).str.title()
    cols = ["match_id", "stage", "group_name", "Kickoff ET"]
    if include_times:
        cols += ["Venue Local Time", "Your Time"]
    cols += ["city", "venue", "Team A", "Team B", "Status", "Score"]
    out = out[cols]
    return out.rename(columns={"match_id": "Match ID", "stage": "Stage", "group_name": "Group", "city": "City", "venue": "Venue"})


def api_matches_display(df: pd.DataFrame, selected_tz: str, include_times: bool = True) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["Home"] = out.apply(lambda r: f"{flag_for_code(r.get('home_code'))} {r.get('home_team')}", axis=1)
    out["Away"] = out.apply(lambda r: f"{flag_for_code(r.get('away_code'))} {r.get('away_team')}", axis=1)
    out["Kickoff UTC"] = out["datetime_utc_dt"].apply(lambda x: format_api_dt(x, "UTC"))
    if include_times:
        out["Venue Local Time"] = out.apply(lambda r: format_api_dt(r.get("datetime_utc_dt"), venue_tz(r.get("city", ""))), axis=1)
        out["Your Time"] = out["datetime_utc_dt"].apply(lambda x: format_api_dt(x, selected_tz))
    out["Score"] = out.apply(lambda r: f"{fmt_score(r.get('home_score'))} - {fmt_score(r.get('away_score'))}", axis=1)
    cols = ["match_number", "match_id", "stage", "group", "Kickoff UTC"]
    if include_times:
        cols += ["Venue Local Time", "Your Time"]
    cols += ["city", "stadium", "Home", "Away", "status", "clock", "Score"]
    return out[cols].rename(columns={"match_number": "Match #", "match_id": "Match ID", "stage": "Stage", "group": "Group", "city": "City", "stadium": "Stadium", "status": "Status", "clock": "Clock"})


@st.cache_data(show_spinner=False, ttl=120)
def cached_bdl_get_all(endpoint: str, api_key: str, params_tuple: Tuple[Tuple[str, Any], ...]) -> ApiResult:
    params = {k: v for k, v in params_tuple}
    return bdl_get_all(endpoint, api_key, params=params, max_pages=5)


def params_tuple(params: Dict[str, Any]) -> Tuple[Tuple[str, Any], ...]:
    return tuple(sorted(params.items(), key=lambda x: x[0]))


bdl_key = get_bdl_api_key()


def fetch_bdl_matches() -> ApiResult:
    return cached_bdl_get_all("matches", bdl_key, params_tuple({"seasons[]": 2026, "per_page": 100}))


def fetch_bdl_teams() -> ApiResult:
    return cached_bdl_get_all("teams", bdl_key, params_tuple({"seasons[]": 2026, "per_page": 100}))


def fetch_bdl_standings() -> ApiResult:
    return cached_bdl_get_all("group_standings", bdl_key, params_tuple({"seasons[]": 2026, "per_page": 100}))


def fetch_bdl_events(match_id: int) -> ApiResult:
    return cached_bdl_get_all("match_events", bdl_key, params_tuple({"match_ids[]": int(match_id), "per_page": 100}))


def fetch_bdl_lineups(match_id: int) -> ApiResult:
    return cached_bdl_get_all("match_lineups", bdl_key, params_tuple({"match_ids[]": int(match_id), "per_page": 100}))


def fetch_bdl_roster(team_id: int) -> ApiResult:
    return cached_bdl_get_all("rosters", bdl_key, params_tuple({"seasons[]": 2026, "team_ids[]": int(team_id), "per_page": 100}))


def get_api_matches_df() -> Tuple[pd.DataFrame, List[Dict[str, Any]], bool]:
    if not bdl_key:
        return pd.DataFrame(), [], False
    result = fetch_bdl_matches()
    if not result.ok:
        return pd.DataFrame(), [], False
    data = result.data or []
    return parse_matches(data), data, True


api_matches_df, api_matches_raw, api_matches_ok = get_api_matches_df()


def render_notice(text: str) -> None:
    st.markdown(f"<div class='notice'>{html.escape(text)}</div>", unsafe_allow_html=True)


def render_scoreboard(match: Dict[str, Any], events_df: pd.DataFrame, selected_tz: str) -> None:
    home = match.get("home_team") or {}
    away = match.get("away_team") or {}
    home_name = team_label(home, match.get("home_team_source"))
    away_name = team_label(away, match.get("away_team_source"))
    home_code = home.get("abbreviation") or home.get("country_code") or ""
    away_code = away.get("abbreviation") or away.get("country_code") or ""
    stage = (match.get("stage") or {}).get("name", "World Cup")
    group = (match.get("group") or {}).get("name", "")
    stadium = match.get("stadium") or {}
    city = stadium.get("city") or ""
    venue = stadium.get("name") or ""
    dt = pd.to_datetime(match.get("datetime"), utc=True, errors="coerce")
    home_goals, away_goals = goal_scorers_by_side(events_df)
    status = str(match.get("status") or "scheduled").replace("_", " ").title()
    clock = match.get("clock_display") or ""
    header_right = clock if clock else status
    live_text = "LIVE" if str(match.get("status")).lower() == "in_progress" else status
    score = f"{fmt_score(match.get('home_score'))} - {fmt_score(match.get('away_score'))}"
    if match.get("has_penalty_shootout") and match.get("home_score_penalties") is not None:
        score += f" ({fmt_score(match.get('home_score_penalties'))}-{fmt_score(match.get('away_score_penalties'))} pens)"
    venue_time_text = format_api_dt(dt, venue_tz(city))
    user_time_text = format_api_dt(dt, selected_tz)
    home_goal_html = "<br>".join(html.escape(x) for x in home_goals) if home_goals else "&nbsp;"
    away_goal_html = "<br>".join(html.escape(x) for x in away_goals) if away_goals else "&nbsp;"
    block = f"<div class='scoreboard-card'><div class='scoreboard-top'><div class='scoreboard-league'>FIFA World Cup 2026 {html.escape('• ' + group if group else '')}</div><div class='scoreboard-live-pill'>{html.escape(live_text)}</div></div><div class='scoreboard-body'><div class='scoreboard-status-row'><div>{html.escape(stage)} • {html.escape(user_time_text)}</div><div class='scoreboard-clock'>{html.escape(header_right)}</div></div><div class='scoreboard-main'><div class='scoreboard-team'><div class='scoreboard-flag'>{html.escape(flag_for_code(home_code))}</div><div class='scoreboard-team-name'>{html.escape(home_name)}</div></div><div class='scoreboard-score'>{html.escape(score)}</div><div class='scoreboard-team'><div class='scoreboard-flag'>{html.escape(flag_for_code(away_code))}</div><div class='scoreboard-team-name'>{html.escape(away_name)}</div></div></div><div class='scoreboard-goals'><div>{home_goal_html}</div><div class='scoreboard-goals-right'>{away_goal_html}</div></div><div class='scoreboard-footer'><div>{html.escape(venue)} • {html.escape(city)}</div><div>Venue time: {html.escape(venue_time_text)}</div></div></div></div>"
    st.markdown(block, unsafe_allow_html=True)


def render_local_scoreboard(row: pd.Series, selected_tz: str) -> None:
    dt = local_fixture_datetime(row)
    api_like = {
        "datetime": dt.astimezone(timezone.utc).isoformat() if dt else None,
        "status": row.get("status", "scheduled"),
        "clock_display": row.get("minute", ""),
        "home_score": row.get("score_a", ""),
        "away_score": row.get("score_b", ""),
        "stage": {"name": row.get("stage", "")},
        "group": {"name": f"Group {row.get('group_name', '')}"},
        "stadium": {"name": row.get("venue", ""), "city": row.get("city", ""), "country": row.get("country", "")},
        "home_team": {"name": name_for_code(row.get("team_a")), "abbreviation": row.get("team_a"), "country_code": row.get("team_a")},
        "away_team": {"name": name_for_code(row.get("team_b")), "abbreviation": row.get("team_b"), "country_code": row.get("team_b")},
    }
    render_scoreboard(api_like, pd.DataFrame(), selected_tz)


def local_group_standings() -> pd.DataFrame:
    rows = []
    for _, row in teams.sort_values(["group_name", "team_name"]).iterrows():
        rows.append({"Group": f"Group {row['group_name']}", "Team": f"{row['flag']} {row['team_name']}", "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0})
    return pd.DataFrame(rows)


def render_bracket_from_api(api_df: pd.DataFrame, selected_tz: str) -> bool:
    if api_df.empty:
        return False
    bracket_df = api_df[~api_df["stage"].str.lower().eq("group stage")].copy()
    if bracket_df.empty:
        return False
    stages = ["Round of 32", "Round of 16", "Quarter-finals", "Quarterfinals", "Semi-finals", "Semifinals", "Third Place", "Final"]
    stage_groups = []
    for stage in stages:
        part = bracket_df[bracket_df["stage"].str.lower() == stage.lower()]
        if not part.empty:
            stage_groups.append((stage, part))
    if not stage_groups:
        stage_groups = list(bracket_df.groupby("stage"))
    html_cols = []
    for stage, part in stage_groups:
        cards = []
        for _, r in part.sort_values("match_number").iterrows():
            home = r["home_team"] if r["home_team"] != "TBD" else r["home_source"] or "TBD"
            away = r["away_team"] if r["away_team"] != "TBD" else r["away_source"] or "TBD"
            cards.append(f"<div class='bracket-card'><div class='bracket-label'>Match {html.escape(str(r['match_number']))}</div><div class='bracket-meta'>{html.escape(format_api_dt(r['datetime_utc_dt'], selected_tz))}</div><div class='bracket-team'><span>{html.escape(str(home))}</span><strong>{html.escape(fmt_score(r['home_score']))}</strong></div><div class='bracket-team'><span>{html.escape(str(away))}</span><strong>{html.escape(fmt_score(r['away_score']))}</strong></div></div>")
        html_cols.append(f"<div class='bracket-stage'><div class='bracket-stage-title'>{html.escape(str(stage))}</div><div class='bracket-scroll'>{''.join(cards)}</div></div>")
    st.markdown("<div class='bracket-board'>" + "".join(html_cols) + "</div>", unsafe_allow_html=True)
    return True


def render_local_bracket(selected_tz: str) -> None:
    if knockout.empty:
        render_notice("Knockout bracket will populate once the knockout schedule is available.")
        return
    stages = ["Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "Third-Place", "Final"]
    html_cols = []
    for stage in stages:
        part = knockout[knockout["stage"] == stage]
        cards = []
        for _, r in part.iterrows():
            dt_text = format_dt(local_fixture_datetime(r), selected_tz) if "time_et" in r else ""
            t1 = r.get("team_a", "TBD") or "TBD"
            t2 = r.get("team_b", "TBD") or "TBD"
            cards.append(f"<div class='bracket-card'><div class='bracket-label'>{html.escape(str(r.get('match_id', '')))}</div><div class='bracket-meta'>{html.escape(dt_text)} • {html.escape(str(r.get('city', '')))}</div><div class='bracket-team'><span>{html.escape(str(t1))}</span><strong>{html.escape(fmt_score(r.get('score_a', '')))}</strong></div><div class='bracket-team'><span>{html.escape(str(t2))}</span><strong>{html.escape(fmt_score(r.get('score_b', '')))}</strong></div></div>")
        html_cols.append(f"<div class='bracket-stage'><div class='bracket-stage-title'>{html.escape(stage)}</div><div class='bracket-scroll'>{''.join(cards)}</div></div>")
    st.markdown("<div class='bracket-board'>" + "".join(html_cols) + "</div>", unsafe_allow_html=True)


# Header
st.title("FIFA World Cup 2026 Match Centre")
st.caption("Fixtures, live match centre, team rosters, standings, and knockout bracket.")

h1, h2, h3 = st.columns([1.05, 1.05, 1.25])
with h3:
    tz_label = st.selectbox("Select your city / time zone", list(USER_TIMEZONES.keys()), index=0)
selected_tz = USER_TIMEZONES[tz_label]
with h1:
    st.markdown(status_card("Schedule updated", file_mtime(FIXTURES_PATH, selected_tz), "Based on selected time zone"), unsafe_allow_html=True)
with h2:
    st.markdown(status_card("Page refreshed", now_text(selected_tz), tz_label), unsafe_allow_html=True)

if st_autorefresh is not None:
    st_autorefresh(interval=60_000, key="public_refresh")

tabs = st.tabs(["Home", "Fixtures", "Match Centre", "Teams", "Standings", "Knockout", "Top Scorers"])

with tabs[0]:
    st.subheader("World Cup dashboard")
    st.markdown("A public-friendly version with no admin controls, no debug page, and no API settings visible to users.")
    cards = [
        home_card("MC", "Match Centre", ["Live score", "Events"], "Scoreboard view with match clock, scorers, venue, events, and lineups when available."),
        home_card("FX", "Fixtures", ["Schedule", "Times"], "Filter matches by team, group, city, and stage. Times are shown for the venue and your selected city."),
        home_card("TM", "Teams", ["Rosters", "Jersey numbers"], "Team pages with fixtures and player rosters when the API provides them."),
        home_card("ST", "Standings", ["Groups"], "Group standings from the API when available, with a local pre-tournament fallback."),
        home_card("KO", "Knockout", ["Bracket"], "A simplified bracket view that fills in as knockout match data becomes available."),
        home_card("TS", "Top Scorers", ["Goals"], "Top scorer table calculated from match events when event data is available."),
    ]
    st.markdown("<div class='home-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)
    st.markdown("<div class='footer-note'>Live data is powered by BALLDONTLIE when available. The local schedule is used as a fallback.</div>", unsafe_allow_html=True)

with tabs[1]:
    st.subheader("Fixtures")
    using_api = api_matches_ok and not api_matches_df.empty
    if using_api:
        source_df = api_matches_df.copy()
        team_options = ["All Teams"] + sorted(set(source_df["home_team"]).union(source_df["away_team"]))
        c1, c2, c3 = st.columns(3)
        with c1:
            team_filter = st.selectbox("Team", team_options)
        with c2:
            group_filter = st.selectbox("Group", ["All Groups"] + sorted([x for x in source_df["group"].dropna().unique() if x]))
        with c3:
            city_filter = st.selectbox("City", ["All Cities"] + sorted([x for x in source_df["city"].dropna().unique() if x]))
        view = source_df.copy()
        if team_filter != "All Teams":
            view = view[(view["home_team"] == team_filter) | (view["away_team"] == team_filter)]
        if group_filter != "All Groups":
            view = view[view["group"] == group_filter]
        if city_filter != "All Cities":
            view = view[view["city"] == city_filter]
        display = api_matches_display(view, selected_tz, include_times=True)
    else:
        render_notice("Live fixture data is temporarily unavailable. Showing the local published schedule.")
        all_team_codes = sorted(set(fixtures["team_a"]).union(fixtures["team_b"]))
        team_map = {f"{flag_for_code(c)} {name_for_code(c)} ({c})": c for c in all_team_codes}
        c1, c2, c3 = st.columns(3)
        with c1:
            team_filter_label = st.selectbox("Team", ["All Teams"] + list(team_map.keys()))
        with c2:
            group_filter = st.selectbox("Group", ["All Groups"] + sorted(fixtures["group_name"].unique()))
        with c3:
            city_filter = st.selectbox("City", ["All Cities"] + sorted(fixtures["city"].unique()))
        view = fixtures.copy()
        if team_filter_label != "All Teams":
            code = team_map[team_filter_label]
            view = view[(view["team_a"] == code) | (view["team_b"] == code)]
        if group_filter != "All Groups":
            view = view[view["group_name"] == group_filter]
        if city_filter != "All Cities":
            view = view[view["city"] == city_filter]
        display = local_fixtures_display(view, selected_tz, include_times=True)
    st.dataframe(display, use_container_width=True, hide_index=True, height=560)
    st.download_button("Export fixtures CSV", display.to_csv(index=False).encode("utf-8"), "worldcup_fixtures.csv", "text/csv")

with tabs[2]:
    st.subheader("Match Centre")
    if api_matches_ok and api_matches_raw:
        matches = api_matches_raw
        labels = []
        match_by_label: Dict[str, Dict[str, Any]] = {}
        for m in matches:
            home = team_label(m.get("home_team"), m.get("home_team_source"))
            away = team_label(m.get("away_team"), m.get("away_team_source"))
            status = str(m.get("status") or "scheduled").replace("_", " ").title()
            label = f"Match {m.get('match_number') or m.get('id')} - {home} vs {away} - {status}"
            labels.append(label)
            match_by_label[label] = m
        default_index = 0
        parsed = api_matches_df.copy()
        live = parsed[parsed["status"].astype(str).str.lower().eq("in_progress")]
        if not live.empty:
            live_id = live.iloc[0]["match_id"]
            for idx, label in enumerate(labels):
                if str(match_by_label[label].get("id")) == str(live_id):
                    default_index = idx
                    break
        choice = st.selectbox("Select match", labels, index=default_index)
        match = match_by_label[choice]
        match_id = int(match.get("id"))
        events_df = pd.DataFrame()
        lineups_df = pd.DataFrame()
        with st.spinner("Loading match details..."):
            events_result = fetch_bdl_events(match_id)
            if events_result.ok:
                events_df = parse_events(events_result.data or [])
            lineups_result = fetch_bdl_lineups(match_id)
            if lineups_result.ok:
                lineups_df = parse_lineups(lineups_result.data or [])
        render_scoreboard(match, events_df, selected_tz)
        if not events_df.empty:
            st.subheader("Events")
            st.dataframe(events_df, use_container_width=True, hide_index=True, height=260)
        if not lineups_df.empty:
            st.subheader("Lineups and bench")
            st.dataframe(lineups_df, use_container_width=True, hide_index=True, height=360)
        if events_df.empty and lineups_df.empty:
            render_notice("Match events and lineups usually populate closer to kickoff or after the match starts.")
    else:
        render_notice("Live match data is not available right now. Showing a scheduled match from the local fixture file.")
        options = fixtures.apply(lambda r: f"{r['match_id']} - {flag_for_code(r['team_a'])} {name_for_code(r['team_a'])} vs {flag_for_code(r['team_b'])} {name_for_code(r['team_b'])} - {r['city']}", axis=1).tolist()
        choice = st.selectbox("Select match", options)
        match_id = int(choice.split(" - ")[0])
        row = fixtures[fixtures["match_id"] == match_id].iloc[0]
        render_local_scoreboard(row, selected_tz)

with tabs[3]:
    st.subheader("Teams")
    api_teams = pd.DataFrame()
    if bdl_key:
        teams_result = fetch_bdl_teams()
        if teams_result.ok:
            api_teams = parse_teams(teams_result.data or [])
    if not api_teams.empty:
        team_options = api_teams.apply(lambda r: f"{flag_for_code(r['team_code'])} {r['team_name']} ({r['team_code']})", axis=1).tolist()
        selected_label = st.selectbox("Select team", team_options)
        selected_code = selected_label.split("(")[-1].replace(")", "")
        selected_row = api_teams[api_teams["team_code"] == selected_code].iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Team", f"{flag_for_code(selected_code)} {selected_row['team_name']}")
        c2.metric("Code", selected_row["team_code"])
        c3.metric("Confederation", selected_row["confederation"])
        roster_df = pd.DataFrame()
        with st.spinner("Loading roster..."):
            roster_result = fetch_bdl_roster(int(selected_row["team_id"]))
            if roster_result.ok:
                roster_df = parse_rosters(roster_result.data or [])
        if roster_df.empty:
            render_notice("Official roster data is not available yet for this team. Showing local roster placeholders.")
            local_code = selected_code
            roster = players[players["team_code"] == local_code].copy()
            roster_df = roster[["jersey_number", "player_name", "position", "club", "age", "status"]].rename(columns={"jersey_number": "Jersey #", "player_name": "Player", "position": "Position", "club": "Club", "age": "Age", "status": "Roster Status"})
        st.dataframe(roster_df, use_container_width=True, hide_index=True, height=560)
        st.download_button("Export roster CSV", roster_df.to_csv(index=False).encode("utf-8"), f"{selected_code}_roster.csv", "text/csv")
    else:
        render_notice("Team API data is temporarily unavailable. Showing local team profiles.")
        team_labels = teams.apply(lambda r: f"{r['flag']} {r['team_name']} ({r['team_code']})", axis=1).tolist()
        selected_label = st.selectbox("Select team", team_labels)
        selected_code = selected_label.split("(")[-1].replace(")", "")
        selected_team = teams[teams["team_code"] == selected_code].iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Team", f"{selected_team['flag']} {selected_team['team_name']}")
        c2.metric("Group", selected_team["group_name"])
        c3.metric("Confederation", selected_team["confederation"])
        team_fix = fixtures[(fixtures["team_a"] == selected_code) | (fixtures["team_b"] == selected_code)]
        st.subheader("Fixtures")
        st.dataframe(local_fixtures_display(team_fix, selected_tz, True), use_container_width=True, hide_index=True, height=240)
        st.subheader("Roster")
        roster = players[players["team_code"] == selected_code].copy()
        roster_display = roster[["jersey_number", "player_name", "position", "club", "age", "status"]].rename(columns={"jersey_number": "Jersey #", "player_name": "Player", "position": "Position", "club": "Club", "age": "Age", "status": "Roster Status"})
        st.dataframe(roster_display, use_container_width=True, hide_index=True, height=560)

with tabs[4]:
    st.subheader("Standings")
    standings_df = pd.DataFrame()
    if bdl_key:
        with st.spinner("Loading standings..."):
            result = fetch_bdl_standings()
        if result.ok:
            standings_df = parse_standings(result.data or [])
    if standings_df.empty:
        render_notice("Official group standings are not available yet. Showing the pre-tournament group table.")
        standings_df = local_group_standings()
    st.dataframe(standings_df, use_container_width=True, hide_index=True, height=620)
    st.download_button("Export standings CSV", standings_df.to_csv(index=False).encode("utf-8"), "worldcup_standings.csv", "text/csv")

with tabs[5]:
    st.subheader("Knockout")
    if not render_bracket_from_api(api_matches_df, selected_tz):
        render_notice("The bracket will update as knockout match data becomes available. Showing the local bracket layout for now.")
        render_local_bracket(selected_tz)

with tabs[6]:
    st.subheader("Top Scorers")
    if api_matches_ok and not api_matches_df.empty:
        completed_or_live = api_matches_df[api_matches_df["status"].astype(str).str.lower().isin(["finished", "completed", "in_progress", "full_time"])]
        sample_df = completed_or_live if not completed_or_live.empty else api_matches_df.head(8)
        sample_df = sample_df.head(12)
        render_notice("Top scorers are calculated from match events that are available through the live data provider.")
        all_events: List[pd.DataFrame] = []
        with st.spinner("Loading available goal events..."):
            for match_id in sample_df["match_id"].dropna().astype(int).tolist():
                result = fetch_bdl_events(match_id)
                if result.ok:
                    parsed = parse_events(result.data or [])
                    if not parsed.empty:
                        all_events.append(parsed)
        if all_events:
            events_df = pd.concat(all_events, ignore_index=True)
            scorers_df = top_scorers_from_events(events_df)
            st.dataframe(scorers_df, use_container_width=True, hide_index=True, height=420)
            with st.expander("Events used"):
                st.dataframe(events_df, use_container_width=True, hide_index=True, height=320)
        else:
            render_notice("No goal events are available yet. This table will populate after matches have event data.")
    else:
        render_notice("Top scorer data will populate when live match event data is available.")
