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

from services.balldontlie_client import ApiResult, bdl_get, bdl_get_all
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

# ==================================================
# Page setup
# ==================================================
st.set_page_config(
    page_title="World Cup 2026 Match Centre",
    page_icon="WC",
    layout="wide",
)

DATA_DIR = "data"
FIXTURES_PATH = os.path.join(DATA_DIR, "fixtures.csv")
TEAMS_PATH = os.path.join(DATA_DIR, "teams.csv")
PLAYERS_PATH = os.path.join(DATA_DIR, "players.csv")
KNOCKOUT_PATH = os.path.join(DATA_DIR, "knockout.csv")

SOURCE_TIMEZONE = "America/New_York"  # local fixtures.csv kickoff times are stored as ET.

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

# ==================================================
# Styling
# ==================================================
st.markdown(
    """
    <style>
    html, body, [class*="css"] {font-family: Inter, Segoe UI, Arial, sans-serif;}
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    h1 {font-size: 2.05rem !important; line-height: 1.15 !important; margin-bottom: .25rem !important;}
    h2, h3 {letter-spacing: -0.015em;}
    .muted {color:#64748b; font-size:.88rem;}
    .status-card {border:1px solid #e2e8f0; border-radius:16px; padding:13px 15px; background:#fff; min-height:92px;}
    .status-label {color:#475569; font-size:.74rem; font-weight:800; text-transform:uppercase; letter-spacing:.04em; margin-bottom:6px;}
    .status-value {color:#111827; font-size:1.08rem; font-weight:800; line-height:1.25;}
    .status-sub {color:#64748b; font-size:.78rem; margin-top:4px;}
    .card-grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(245px,1fr)); gap:16px; margin-top:12px;}
    .feature-card {border:1px solid #dbe4f0; border-radius:16px; padding:18px; background:#fff; box-shadow:0 3px 12px rgba(15,23,42,.06); min-height:186px;}
    .feature-illustration {height:90px; border-radius:12px; background:linear-gradient(135deg,#f8fafc,#eef2ff); display:flex; align-items:center; justify-content:center; margin-bottom:14px;}
    .feature-icon {font-size:1.05rem; font-weight:900; background:white; border-radius:999px; width:58px; height:58px; display:flex; align-items:center; justify-content:center; box-shadow:0 8px 25px rgba(15,23,42,.12);}
    .pill {display:inline-block; padding:5px 10px; border-radius:999px; background:#ffe4e6; color:#111827; font-size:.78rem; font-weight:750; margin-right:6px; margin-bottom:8px;}
    .pill.alt {background:#f3e8ff;}
    .feature-title {font-size:1.13rem; font-weight:850; color:#020617; margin:6px 0 8px;}
    .feature-text {color:#475569; line-height:1.45; font-size:.92rem;}
    .scoreboard-card {border:1px solid #dbe4f0; border-radius:18px; overflow:hidden; background:#fff; box-shadow:0 3px 14px rgba(15,23,42,.08); margin-bottom:18px; max-width:840px;}
    .scoreboard-top {background:#16a34a; color:white; padding:12px 16px; display:flex; align-items:center; justify-content:space-between; gap:10px;}
    .scoreboard-league {font-weight:850; font-size:.98rem;}
    .scoreboard-live-pill {background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.35); border-radius:999px; padding:4px 10px; font-size:.78rem; font-weight:850;}
    .scoreboard-body {padding:16px 18px 14px;}
    .scoreboard-status-row {display:flex; justify-content:space-between; align-items:center; color:#64748b; font-size:.88rem; margin-bottom:12px;}
    .scoreboard-clock {color:#16a34a; font-weight:900; letter-spacing:.02em; font-size:1rem;}
    .scoreboard-main {display:grid; grid-template-columns:1fr 140px 1fr; align-items:center; gap:14px;}
    .scoreboard-team {text-align:center; min-width:0;}
    .scoreboard-team-name {font-size:1rem; font-weight:850; color:#111827; margin-top:6px; overflow-wrap:anywhere;}
    .scoreboard-flag {width:52px; height:52px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:2rem; background:#f8fafc; border:1px solid #e2e8f0;}
    .scoreboard-score {text-align:center; font-size:2.8rem; font-weight:950; color:#111827; letter-spacing:.02em; white-space:nowrap;}
    .scoreboard-goals {display:grid; grid-template-columns:1fr 1fr; gap:18px; border-top:1px solid #eef2f7; margin-top:14px; padding-top:10px; color:#475569; font-size:.86rem; min-height:34px;}
    .scoreboard-goals-right {text-align:right;}
    .scoreboard-footer {border-top:1px solid #eef2f7; color:#64748b; font-size:.82rem; padding-top:9px; margin-top:10px; display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap;}
    .bracket-board {display:grid; grid-template-columns:repeat(5,minmax(190px,1fr)); gap:14px; align-items:start; overflow-x:auto; padding-bottom:8px;}
    .bracket-stage {border:1px solid #dbe4f0; border-radius:14px; background:#f8fbff; padding:12px; min-height:250px;}
    .bracket-stage-title {font-weight:850; text-align:center; color:#102a56; margin-bottom:12px; font-size:.98rem;}
    .bracket-scroll {max-height:720px; overflow-y:auto; padding-right:4px;}
    .bracket-card {border:1px solid #cbd5e1; border-radius:12px; background:white; padding:10px; margin-bottom:10px; box-shadow:0 1px 3px rgba(15,23,42,.06);}
    .bracket-label {font-weight:850; color:#0f172a; font-size:.90rem;}
    .bracket-meta {color:#64748b; font-size:.76rem; margin-bottom:6px;}
    .bracket-team {display:flex; justify-content:space-between; gap:8px; padding:4px 0; border-top:1px solid #eef2f7;}
    .bracket-slot {color:#64748b; font-size:.72rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ==================================================
# Data loading
# ==================================================
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


fixtures, teams, players, knockout = normalize_dataframes(load_csv(FIXTURES_PATH), load_csv(TEAMS_PATH), load_csv(PLAYERS_PATH), load_csv(KNOCKOUT_PATH))

if fixtures.empty or teams.empty:
    st.error("Missing data files. Make sure data/fixtures.csv and data/teams.csv exist.")
    st.stop()

TEAM_LOOKUP: Dict[str, Dict[str, Any]] = teams.set_index("team_code").to_dict(orient="index") if not teams.empty else {}

# ==================================================
# Utility functions
# ==================================================
def read_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default) or default)
    except Exception:
        return default


def get_bdl_api_key() -> str:
    return (
        st.session_state.get("BDL_FIFA_API_KEY_SESSION", "")
        or read_secret("BDL_FIFA_API_KEY", "")
        or read_secret("BALLDONTLIE_API_KEY", "")
        or os.getenv("BDL_FIFA_API_KEY", "")
        or os.getenv("BALLDONTLIE_API_KEY", "")
    )


def pretty_dt(dt: datetime) -> str:
    """Cross-platform date/time formatter.

    Windows does not support strftime("%-I"), so build the non-padded
    12-hour value manually instead of relying on OS-specific format codes.
    """
    hour = dt.hour % 12 or 12
    return f"{dt.strftime('%b %d')}, {hour}:{dt.strftime('%M %p %Z')}"


def file_mtime(path: str, tz: str) -> str:
    if not os.path.exists(path):
        return "Not found"
    dt = datetime.fromtimestamp(os.path.getmtime(path), tz=ZoneInfo(tz))
    return pretty_dt(dt)


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


def code_for_team_name(name: str) -> str:
    if not name:
        return ""
    exact = teams[teams["team_name"].str.lower() == str(name).lower()]
    if not exact.empty:
        return exact.iloc[0]["team_code"]
    return ""


def fmt_score(value: Any) -> str:
    if value is None or value == "" or pd.isna(value):
        return "-"
    try:
        return str(int(float(value)))
    except Exception:
        return str(value)


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


def venue_tz(city: str) -> str:
    return VENUE_TIMEZONES.get(str(city), SOURCE_TIMEZONE)


def local_fixtures_display(df: pd.DataFrame, selected_tz: str, include_times: bool = True) -> pd.DataFrame:
    out = df.copy()
    out["Team A"] = out["team_a"].apply(lambda x: f"{flag_for_code(x)} {name_for_code(x)}")
    out["Team B"] = out["team_b"].apply(lambda x: f"{flag_for_code(x)} {name_for_code(x)}")
    out["Kickoff ET"] = out.apply(lambda r: format_dt(local_fixture_datetime(r), SOURCE_TIMEZONE), axis=1)
    if include_times:
        out["Venue Local Time"] = out.apply(lambda r: format_dt(local_fixture_datetime(r), venue_tz(r.get("city", ""))), axis=1)
        out["Your Time"] = out.apply(lambda r: format_dt(local_fixture_datetime(r), selected_tz), axis=1)
    out["Score"] = out.apply(lambda r: f"{fmt_score(r.get('score_a'))} - {fmt_score(r.get('score_b'))}", axis=1)
    out["Status"] = out["status"].str.title()
    cols = ["match_id", "stage", "group_name", "Kickoff ET"]
    if include_times:
        cols += ["Venue Local Time", "Your Time"]
    cols += ["city", "venue", "Team A", "Team B", "Status", "Score"]
    out = out[cols]
    return out.rename(
        columns={
            "match_id": "Match ID",
            "stage": "Stage",
            "group_name": "Group",
            "city": "City",
            "venue": "Venue",
        }
    )


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
    return out[cols].rename(
        columns={
            "match_number": "Match #",
            "match_id": "Match ID",
            "stage": "Stage",
            "group": "Group",
            "city": "City",
            "stadium": "Stadium",
            "status": "Status",
            "clock": "Clock",
        }
    )


def status_card(label: str, value: str, sub: str = "") -> str:
    return f"""
    <div class='status-card'>
      <div class='status-label'>{html.escape(label)}</div>
      <div class='status-value'>{html.escape(value)}</div>
      <div class='status-sub'>{html.escape(sub)}</div>
    </div>
    """


def render_scoreboard_from_api(match: Dict[str, Any], events_df: pd.DataFrame, selected_tz: str) -> None:
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

    html_block = f"""
    <div class='scoreboard-card'>
      <div class='scoreboard-top'>
        <div class='scoreboard-league'>FIFA World Cup 2026 {html.escape('• ' + group if group else '')}</div>
        <div class='scoreboard-live-pill'>{html.escape(live_text)}</div>
      </div>
      <div class='scoreboard-body'>
        <div class='scoreboard-status-row'>
          <div>{html.escape(stage)} • {html.escape(format_api_dt(dt, selected_tz))}</div>
          <div class='scoreboard-clock'>{html.escape(header_right)}</div>
        </div>
        <div class='scoreboard-main'>
          <div class='scoreboard-team'>
            <div class='scoreboard-flag'>{html.escape(flag_for_code(home_code))}</div>
            <div class='scoreboard-team-name'>{html.escape(home_name)}</div>
          </div>
          <div class='scoreboard-score'>{html.escape(score)}</div>
          <div class='scoreboard-team'>
            <div class='scoreboard-flag'>{html.escape(flag_for_code(away_code))}</div>
            <div class='scoreboard-team-name'>{html.escape(away_name)}</div>
          </div>
        </div>
        <div class='scoreboard-goals'>
          <div>{'<br>'.join(html.escape(x) for x in home_goals) if home_goals else '&nbsp;'}</div>
          <div class='scoreboard-goals-right'>{'<br>'.join(html.escape(x) for x in away_goals) if away_goals else '&nbsp;'}</div>
        </div>
        <div class='scoreboard-footer'>
          <div>{html.escape(venue)} • {html.escape(city)}</div>
          <div>Venue time: {html.escape(format_api_dt(dt, venue_tz(city)))}</div>
        </div>
      </div>
    </div>
    """
    st.markdown(html_block, unsafe_allow_html=True)


def render_demo_scoreboard() -> None:
    demo_match = {
        "datetime": "2026-06-13T22:00:00.000Z",
        "status": "in_progress",
        "clock_display": "54:01",
        "home_score": 1,
        "away_score": 0,
        "stage": {"name": "Group Stage"},
        "group": {"name": "Group C"},
        "stadium": {"name": "MetLife Stadium", "city": "East Rutherford", "country": "USA"},
        "home_team": {"name": "Brazil", "abbreviation": "BRA", "country_code": "BRA"},
        "away_team": {"name": "Morocco", "abbreviation": "MAR", "country_code": "MAR"},
    }
    events = pd.DataFrame(
        [
            {
                "Event ID": 1,
                "Match ID": 1,
                "Minute": "37'",
                "Minute Number": 37,
                "Type": "goal",
                "Class": "regular",
                "Side": "Home",
                "Player": "Vinícius Júnior",
                "Player Jersey": "7",
                "Assist": "Rodrygo",
                "Home Score": 1,
                "Away Score": 0,
            }
        ]
    )
    render_scoreboard_from_api(demo_match, events, selected_tz)
    st.caption("Demo card only. Real scores will come from BALLDONTLIE when a match is live or when your API tier can access matches/events.")


def render_feature_card(icon: str, title: str, tags: List[str], text: str) -> str:
    # Keep the HTML as a single compact line so Streamlit/Markdown does not
    # interpret indented lines as a code block on Windows/browser refreshes.
    tag_html = "".join(
        f"<span class=\"pill {'alt' if i % 2 else ''}\">{html.escape(t)}</span>"
        for i, t in enumerate(tags)
    )
    return (
        "<div class=\"feature-card\">"
        f"<div class=\"feature-illustration\"><div class=\"feature-icon\">{html.escape(icon)}</div></div>"
        f"{tag_html}"
        f"<div class=\"feature-title\">{html.escape(title)}</div>"
        f"<div class=\"feature-text\">{html.escape(text)}</div>"
        "</div>"
    )

# ==================================================
# Sidebar controls
# ==================================================
st.sidebar.header("Dashboard Controls")
show_times = st.sidebar.checkbox("Show venue local time and my time", value=True)
auto_refresh = st.sidebar.checkbox("Auto-refresh Match Centre every 60 seconds", value=False)
demo_mode = st.sidebar.checkbox("Demo live score mode", value=False)

bdl_key_input = st.sidebar.text_input("BALLDONTLIE FIFA API key for this session", type="password", help="Stored only in the current Streamlit session unless you save it in .streamlit/secrets.toml.")
if bdl_key_input:
    st.session_state["BDL_FIFA_API_KEY_SESSION"] = bdl_key_input.strip()

bdl_key = get_bdl_api_key()
st.sidebar.write(f"BALLDONTLIE API: {'Connected' if bdl_key else 'Not connected'}")
st.sidebar.caption("Secret names supported: BDL_FIFA_API_KEY or BALLDONTLIE_API_KEY")
if st.sidebar.button("Clear API cache / refresh data"):
    st.cache_data.clear()
    st.rerun()

if auto_refresh and st_autorefresh is not None:
    st_autorefresh(interval=60_000, key="bdl_live_refresh")

# ==================================================
# Header and timezone selector
# ==================================================
st.title("FIFA World Cup 2026 Match Centre")
st.caption("Card-based match hub using BALLDONTLIE FIFA World Cup API, with local CSV fallback.")

h1, h2, h3 = st.columns([1.15, 1.15, 1.4])
with h3:
    tz_label = st.selectbox("Select your city / time zone", list(USER_TIMEZONES.keys()), index=0)
selected_tz = USER_TIMEZONES[tz_label]
with h1:
    st.markdown(status_card("Data file last updated", file_mtime(FIXTURES_PATH, selected_tz), "Based on selected time zone"), unsafe_allow_html=True)
with h2:
    st.markdown(status_card("Screen refreshed", now_text(selected_tz), tz_label), unsafe_allow_html=True)

# ==================================================
# Shared API helpers
# ==================================================
@st.cache_data(show_spinner=False, ttl=120)
def cached_bdl_get_all(endpoint: str, api_key: str, params_tuple: Tuple[Tuple[str, Any], ...]) -> ApiResult:
    params = {k: v for k, v in params_tuple}
    return bdl_get_all(endpoint, api_key, params=params, max_pages=5)


def params_tuple(params: Dict[str, Any]) -> Tuple[Tuple[str, Any], ...]:
    return tuple(sorted(params.items(), key=lambda x: x[0]))


def fetch_bdl_matches() -> ApiResult:
    return cached_bdl_get_all("matches", bdl_key, params_tuple({"seasons[]": 2026, "per_page": 100}))


def fetch_bdl_teams() -> ApiResult:
    return cached_bdl_get_all("teams", bdl_key, params_tuple({"seasons[]": 2026, "per_page": 100}))

# ==================================================
# Tabs
# ==================================================
tabs = st.tabs(["Home", "Fixtures", "Match Centre", "Teams & Players", "Top Scorers", "Standings", "Knockout Bracket", "API Debug"])

# ==================================================
# Home
# ==================================================
with tabs[0]:
    st.subheader("World Cup Dashboard Modules")
    st.markdown("The app now uses BALLDONTLIE as the primary provider and keeps your local wall-chart schedule as fallback.")
    cards = [
        render_feature_card("MC", "Match Centre", ["Live Scores", "Events"], "Google-style scoreboard, match clock, scorers, events, lineups, and venue details."),
        render_feature_card("FX", "Fixtures", ["Schedule", "Export"], "Filter matches by team, group, city, stage, and export the table to CSV."),
        render_feature_card("SQ", "Team Squad", ["Rosters", "Jersey #"], "Team profiles and player rosters with jersey numbers when the API tier allows rosters."),
        render_feature_card("ST", "Standings", ["Groups"], "Local standings fallback plus BALLDONTLIE group standings when available."),
        render_feature_card("KO", "Knockout Bracket", ["Bracket"], "Cleaner bracket layout using local placeholders or API knockout source descriptions."),
        render_feature_card("API", "API Debug", ["Testing"], "Test your API key and endpoint access without guessing what failed."),
    ]
    st.markdown("<div class='card-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)
    st.info("GOAT subscription active: after you add the API key and restart the app, Matches, Rosters, Match Lineups, Match Events, Player Match Stats, Team Match Stats, Shots, Momentum, Best Players, Avg Positions, and Team Form should be available. Use API Debug first to confirm each endpoint returns 200.")

# ==================================================
# Fixtures
# ==================================================
with tabs[1]:
    st.subheader("Fixtures")
    source = st.radio("Fixture source", ["Local CSV fallback", "BALLDONTLIE API"], horizontal=True)

    if source == "BALLDONTLIE API":
        if not bdl_key:
            st.warning("Add your BALLDONTLIE FIFA API key in the sidebar or .streamlit/secrets.toml.")
        else:
            with st.spinner("Fetching BALLDONTLIE matches..."):
                result = fetch_bdl_matches()
            if not result.ok:
                st.error(result.error)
                st.caption(result.url)
                st.info("If this is 401, your key is valid/missing or your account tier may not include the Matches endpoint. Use Local CSV fallback until access is enabled.")
            else:
                api_df = parse_matches(result.data or [])
                team_filter = st.selectbox("Team", ["All Teams"] + sorted(set(api_df["home_team"]).union(api_df["away_team"]))) if not api_df.empty else "All Teams"
                stage_filter = st.selectbox("Stage", ["All Stages"] + sorted([x for x in api_df["stage"].dropna().unique() if x])) if not api_df.empty else "All Stages"
                view = api_df.copy()
                if team_filter != "All Teams":
                    view = view[(view["home_team"] == team_filter) | (view["away_team"] == team_filter)]
                if stage_filter != "All Stages":
                    view = view[view["stage"] == stage_filter]
                display = api_matches_display(view, selected_tz, show_times)
                st.dataframe(display, use_container_width=True, hide_index=True, height=620)
                st.download_button("Export API fixtures CSV", display.to_csv(index=False).encode("utf-8"), "balldontlie_fixtures.csv", "text/csv")
                st.caption(f"Rows returned: {len(api_df)}")
    else:
        all_team_codes = sorted(set(fixtures["team_a"]).union(fixtures["team_b"]))
        all_teams = [f"{flag_for_code(c)} {name_for_code(c)} ({c})" for c in all_team_codes]
        team_map = {f"{flag_for_code(c)} {name_for_code(c)} ({c})": c for c in all_team_codes}
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            team_filter_label = st.selectbox("Team", ["All Teams"] + all_teams)
        with c2:
            group_filter = st.selectbox("Group", ["All Groups"] + sorted(fixtures["group_name"].unique()))
        with c3:
            city_filter = st.selectbox("City", ["All Cities"] + sorted(fixtures["city"].unique()))
        with c4:
            stage_filter = st.selectbox("Stage", ["All Stages"] + sorted(fixtures["stage"].unique()))
        filtered = fixtures.copy()
        if team_filter_label != "All Teams":
            code = team_map[team_filter_label]
            filtered = filtered[(filtered["team_a"] == code) | (filtered["team_b"] == code)]
        if group_filter != "All Groups":
            filtered = filtered[filtered["group_name"] == group_filter]
        if city_filter != "All Cities":
            filtered = filtered[filtered["city"] == city_filter]
        if stage_filter != "All Stages":
            filtered = filtered[filtered["stage"] == stage_filter]
        display = local_fixtures_display(filtered, selected_tz, show_times)
        st.dataframe(display, use_container_width=True, hide_index=True, height=620)
        st.download_button("Export filtered fixtures CSV", display.to_csv(index=False).encode("utf-8"), "worldcup_filtered_fixtures.csv", "text/csv")

# ==================================================
# Match Centre
# ==================================================
with tabs[2]:
    st.subheader("Match Centre")
    if demo_mode:
        render_demo_scoreboard()
    source = st.radio("Match data source", ["BALLDONTLIE API", "Local scheduled fixture", "Demo only"], horizontal=True)

    if source == "Demo only":
        render_demo_scoreboard()

    elif source == "Local scheduled fixture":
        options = fixtures.apply(lambda r: f"{r['match_id']} • {flag_for_code(r['team_a'])} {name_for_code(r['team_a'])} vs {flag_for_code(r['team_b'])} {name_for_code(r['team_b'])} • {r['city']}", axis=1).tolist()
        choice = st.selectbox("Select local fixture", options)
        match_id = int(choice.split(" • ")[0])
        row = fixtures[fixtures["match_id"] == match_id].iloc[0]
        api_like = {
            "datetime": local_fixture_datetime(row).astimezone(timezone.utc).isoformat() if local_fixture_datetime(row) else None,
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
        render_scoreboard_from_api(api_like, pd.DataFrame(), selected_tz)
        st.info("This is the local schedule fallback. It will not show live scorers or lineups unless you update the CSV manually or fetch API data.")

    elif source == "BALLDONTLIE API":
        if not bdl_key:
            st.warning("Add your BALLDONTLIE FIFA API key first.")
        else:
            result = fetch_bdl_matches()
            if not result.ok:
                st.error(result.error)
                st.caption(result.url)
            else:
                matches = result.data or []
                api_df = parse_matches(matches)
                if api_df.empty:
                    st.warning("No matches returned.")
                else:
                    live_df = api_df[api_df["status"].astype(str).str.lower().eq("in_progress")]
                    default_idx = int(live_df.index[0]) if not live_df.empty else 0
                    labels = []
                    match_by_label = {}
                    for m in matches:
                        home = team_label(m.get("home_team"), m.get("home_team_source"))
                        away = team_label(m.get("away_team"), m.get("away_team_source"))
                        label = f"Match {m.get('match_number') or m.get('id')} • {home} vs {away} • {m.get('status')}"
                        labels.append(label)
                        match_by_label[label] = m
                    choice = st.selectbox("Select match", labels, index=min(default_idx, len(labels) - 1))
                    match = match_by_label[choice]
                    match_id = match.get("id")

                    events_df = pd.DataFrame()
                    lineups_df = pd.DataFrame()
                    e_col, l_col = st.columns(2)
                    with e_col:
                        fetch_events = st.button("Fetch match events / scorers", use_container_width=True)
                    with l_col:
                        fetch_lineups = st.button("Fetch lineups / jersey numbers", use_container_width=True)

                    if fetch_events:
                        ev = bdl_get_all("match_events", bdl_key, params={"match_ids[]": match_id, "per_page": 100})
                        if ev.ok:
                            events_df = parse_events(ev.data or [])
                            st.session_state["last_events_df"] = events_df
                        else:
                            st.error(ev.error)
                            st.caption(ev.url)
                    elif isinstance(st.session_state.get("last_events_df"), pd.DataFrame):
                        events_df = st.session_state["last_events_df"]

                    render_scoreboard_from_api(match, events_df, selected_tz)

                    if fetch_lineups:
                        lu = bdl_get_all("match_lineups", bdl_key, params={"match_ids[]": match_id, "per_page": 100})
                        if lu.ok:
                            lineups_df = parse_lineups(lu.data or [])
                            st.session_state["last_lineups_df"] = lineups_df
                        else:
                            st.error(lu.error)
                            st.caption(lu.url)
                    elif isinstance(st.session_state.get("last_lineups_df"), pd.DataFrame):
                        lineups_df = st.session_state["last_lineups_df"]

                    if not events_df.empty:
                        st.subheader("Events Timeline")
                        st.dataframe(events_df, use_container_width=True, hide_index=True, height=260)
                    else:
                        st.caption("No event/scorer data loaded yet. Click Fetch match events / scorers. This endpoint requires the correct API tier.")

                    if not lineups_df.empty:
                        st.subheader("Lineups and Bench")
                        st.dataframe(lineups_df, use_container_width=True, hide_index=True, height=360)
                    else:
                        st.caption("No lineup data loaded yet. Click Fetch lineups / jersey numbers. This endpoint requires the correct API tier and is usually populated close to kickoff.")

# ==================================================
# Teams and Players
# ==================================================
with tabs[3]:
    st.subheader("Team Profiles and Player Rosters")
    source = st.radio("Team source", ["Local CSV fallback", "BALLDONTLIE teams/rosters"], horizontal=True)

    if source == "BALLDONTLIE teams/rosters" and bdl_key:
        teams_result = fetch_bdl_teams()
        if teams_result.ok:
            api_teams = parse_teams(teams_result.data or [])
            team_options = api_teams.apply(lambda r: f"{flag_for_code(r['team_code'])} {r['team_name']} ({r['team_code']}) • ID {r['team_id']}", axis=1).tolist()
            choice = st.selectbox("Select team", team_options)
            selected_id = int(choice.split("ID ")[-1])
            selected_row = api_teams[api_teams["team_id"] == selected_id].iloc[0]
            c1, c2, c3 = st.columns(3)
            c1.metric("Team", f"{flag_for_code(selected_row['team_code'])} {selected_row['team_name']}")
            c2.metric("Code", selected_row["team_code"])
            c3.metric("Confederation", selected_row["confederation"])

            if st.button("Fetch roster with jersey numbers"):
                roster_result = bdl_get_all("rosters", bdl_key, params={"seasons[]": 2026, "team_ids[]": selected_id, "per_page": 100})
                if roster_result.ok:
                    roster_df = parse_rosters(roster_result.data or [])
                    if roster_df.empty:
                        st.warning("Roster endpoint returned no rows for this team.")
                    else:
                        st.dataframe(roster_df, use_container_width=True, hide_index=True, height=560)
                        st.download_button("Export selected API roster CSV", roster_df.to_csv(index=False).encode("utf-8"), f"{selected_row['team_code']}_bdl_roster.csv", "text/csv")
                else:
                    st.error(roster_result.error)
                    st.caption(roster_result.url)
                    st.info("Rosters require the GOAT tier in the BALLDONTLIE FIFA docs. Use the local placeholder roster until that access is active.")
        else:
            st.error(teams_result.error)
            st.caption(teams_result.url)
    else:
        if source == "BALLDONTLIE teams/rosters" and not bdl_key:
            st.warning("Add your BALLDONTLIE API key to use API teams/rosters. Showing local fallback.")
        team_labels = teams.apply(lambda r: f"{r['flag']} {r['team_name']} ({r['team_code']})", axis=1).tolist()
        selected_label = st.selectbox("Select a team", team_labels)
        selected_code = selected_label.split("(")[-1].replace(")", "")
        selected_team = teams[teams["team_code"] == selected_code].iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Team", f"{selected_team['flag']} {selected_team['team_name']}")
        c2.metric("Group", selected_team["group_name"])
        c3.metric("Confederation", selected_team["confederation"])
        c4.metric("BDL Team ID", selected_team.get("balldontlie_team_id", "Not set") or "Not set")

        st.subheader("Fixtures for Selected Team")
        team_fix = fixtures[(fixtures["team_a"] == selected_code) | (fixtures["team_b"] == selected_code)]
        st.dataframe(local_fixtures_display(team_fix, selected_tz, show_times), use_container_width=True, hide_index=True, height=240)

        st.subheader("Player Roster with Jersey Numbers")
        roster = players[players["team_code"] == selected_code].copy()
        roster_display = roster[["jersey_number", "player_name", "position", "club", "age", "status"]].rename(columns={"jersey_number": "Jersey #", "player_name": "Player", "position": "Position", "club": "Club", "age": "Age", "status": "Roster Status"})
        st.dataframe(roster_display, use_container_width=True, hide_index=True, height=560)
        st.download_button("Export selected team roster CSV", roster_display.to_csv(index=False).encode("utf-8"), f"{selected_code}_roster.csv", "text/csv")

# ==================================================
# Top Scorers
# ==================================================
with tabs[4]:
    st.subheader("Top Scorers")
    st.markdown("Use match events when your API tier allows the Match Events endpoint. For now, you can test with one match ID.")
    if not bdl_key:
        st.warning("Add your BALLDONTLIE API key first.")
    else:
        match_ids_text = st.text_input("Match IDs to pull events from", value="1", help="Comma-separated match IDs, e.g. 1,2,3. Avoid too many calls during trial limits.")
        if st.button("Fetch events and calculate top scorers"):
            all_events: List[pd.DataFrame] = []
            for raw in [x.strip() for x in match_ids_text.split(",") if x.strip()]:
                result = bdl_get_all("match_events", bdl_key, params={"match_ids[]": int(raw), "per_page": 100})
                if result.ok:
                    all_events.append(parse_events(result.data or []))
                else:
                    st.error(f"Match {raw}: {result.error}")
            if all_events:
                events_df = pd.concat(all_events, ignore_index=True)
                scorers_df = top_scorers_from_events(events_df)
                st.dataframe(scorers_df, use_container_width=True, hide_index=True)
                with st.expander("Events used"):
                    st.dataframe(events_df, use_container_width=True, hide_index=True)
            else:
                st.warning("No events loaded.")

# ==================================================
# Standings
# ==================================================
with tabs[5]:
    st.subheader("Group Standings")
    source = st.radio("Standings source", ["Local fixtures.csv", "BALLDONTLIE group standings"], horizontal=True)
    if source == "BALLDONTLIE group standings":
        if not bdl_key:
            st.warning("Add your BALLDONTLIE API key first.")
        elif st.button("Fetch BALLDONTLIE group standings"):
            result = bdl_get_all("group_standings", bdl_key, params={"seasons[]": 2026, "per_page": 100})
            if result.ok:
                standings_df = parse_standings(result.data or [])
                st.dataframe(standings_df, use_container_width=True, hide_index=True, height=620)
                st.download_button("Export API standings CSV", standings_df.to_csv(index=False).encode("utf-8"), "bdl_group_standings.csv", "text/csv")
            else:
                st.error(result.error)
                st.caption(result.url)
                st.info("BALLDONTLIE group standings require ALL-STAR or GOAT according to the FIFA docs.")
    else:
        # Pre-tournament table from local groups. Scores are blank so all teams start at 0.
        rows = []
        for _, row in teams.sort_values(["group_name", "team_name"]).iterrows():
            rows.append({"Group": f"Group {row['group_name']}", "Team": f"{row['flag']} {row['team_name']}", "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0})
        local_standings = pd.DataFrame(rows)
        st.dataframe(local_standings, use_container_width=True, hide_index=True, height=620)
        st.download_button("Export local standings CSV", local_standings.to_csv(index=False).encode("utf-8"), "local_group_standings.csv", "text/csv")

# ==================================================
# Knockout Bracket
# ==================================================
with tabs[6]:
    st.subheader("Knockout Bracket")
    source = st.radio("Bracket source", ["Local bracket placeholders", "BALLDONTLIE knockout matches"], horizontal=True)

    if source == "BALLDONTLIE knockout matches" and bdl_key:
        result = fetch_bdl_matches()
        if result.ok:
            api_df = parse_matches(result.data or [])
            bracket_df = api_df[~api_df["stage"].str.lower().eq("group stage")].copy()
            if bracket_df.empty:
                st.info("No knockout matches returned yet.")
            else:
                stages = ["Round of 32", "Round of 16", "Quarter-finals", "Quarterfinals", "Semi-finals", "Semifinals", "Third Place", "Final"]
                stage_groups = []
                for s in stages:
                    part = bracket_df[bracket_df["stage"].str.lower() == s.lower()]
                    if not part.empty:
                        stage_groups.append((s, part))
                if not stage_groups:
                    stage_groups = list(bracket_df.groupby("stage"))
                html_cols = []
                for stage, part in stage_groups:
                    cards = []
                    for _, r in part.sort_values("match_number").iterrows():
                        home = r["home_team"] if r["home_team"] != "TBD" else r["home_source"] or "TBD"
                        away = r["away_team"] if r["away_team"] != "TBD" else r["away_source"] or "TBD"
                        cards.append(f"""
                        <div class='bracket-card'>
                          <div class='bracket-label'>Match {html.escape(str(r['match_number']))}</div>
                          <div class='bracket-meta'>{html.escape(format_api_dt(r['datetime_utc_dt'], selected_tz))}</div>
                          <div class='bracket-team'><span>{html.escape(str(home))}</span><strong>{html.escape(fmt_score(r['home_score']))}</strong></div>
                          <div class='bracket-team'><span>{html.escape(str(away))}</span><strong>{html.escape(fmt_score(r['away_score']))}</strong></div>
                        </div>
                        """)
                    html_cols.append(f"<div class='bracket-stage'><div class='bracket-stage-title'>{html.escape(stage)}</div><div class='bracket-scroll'>{''.join(cards)}</div></div>")
                st.markdown("<div class='bracket-board'>" + "".join(html_cols) + "</div>", unsafe_allow_html=True)
                with st.expander("API knockout data table / export"):
                    display = api_matches_display(bracket_df, selected_tz, show_times)
                    st.dataframe(display, use_container_width=True, hide_index=True)
                    st.download_button("Export API knockout CSV", display.to_csv(index=False).encode("utf-8"), "api_knockout.csv", "text/csv")
        else:
            st.error(result.error)
            st.caption(result.url)
    else:
        if source == "BALLDONTLIE knockout matches" and not bdl_key:
            st.warning("Add your BALLDONTLIE key first. Showing local placeholder bracket.")
        if knockout.empty:
            st.warning("No knockout.csv found.")
        else:
            stages = ["Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "Third-Place", "Final"]
            html_cols = []
            for stage in stages:
                part = knockout[knockout["stage"] == stage]
                if part.empty:
                    continue
                cards = []
                for _, r in part.iterrows():
                    cards.append(f"""
                    <div class='bracket-card'>
                      <div class='bracket-label'>{html.escape(str(r['match_label']))}</div>
                      <div class='bracket-meta'>{html.escape(str(r.get('city','')))} {html.escape(str(r.get('venue','')))}</div>
                      <div class='bracket-team'><span>{html.escape(str(r.get('team_a_slot') or r.get('team_a')))}</span><strong>{html.escape(fmt_score(r.get('score_a')))}</strong></div>
                      <div class='bracket-team'><span>{html.escape(str(r.get('team_b_slot') or r.get('team_b')))}</span><strong>{html.escape(fmt_score(r.get('score_b')))}</strong></div>
                    </div>
                    """)
                html_cols.append(f"<div class='bracket-stage'><div class='bracket-stage-title'>{html.escape(stage)}</div><div class='bracket-scroll'>{''.join(cards)}</div></div>")
            st.markdown("<div class='bracket-board'>" + "".join(html_cols) + "</div>", unsafe_allow_html=True)
            with st.expander("Knockout data table / export"):
                st.dataframe(knockout, use_container_width=True, hide_index=True)
                st.download_button("Export local knockout CSV", knockout.to_csv(index=False).encode("utf-8"), "local_knockout.csv", "text/csv")

# ==================================================
# API Debug
# ==================================================
with tabs[7]:
    st.subheader("BALLDONTLIE API Debug")
    st.markdown("Use this tab to verify your key and which FIFA endpoints your tier can access.")

    if not bdl_key:
        st.warning("No BALLDONTLIE key detected. Enter it in the sidebar or save it in .streamlit/secrets.toml.")

    tests = [
        ("Teams", "teams", {"seasons[]": 2026, "per_page": 100}),
        ("Stadiums", "stadiums", {"seasons[]": 2026, "per_page": 100}),
        ("Group standings", "group_standings", {"seasons[]": 2026, "per_page": 100}),
        ("Matches", "matches", {"seasons[]": 2026, "per_page": 100}),
        ("Players", "players", {"seasons[]": 2026, "per_page": 25}),
        ("Rosters sample team ID 12", "rosters", {"seasons[]": 2026, "team_ids[]": 12, "per_page": 25}),
        ("Match events sample match ID 1", "match_events", {"match_ids[]": 1, "per_page": 25}),
        ("Match lineups sample match ID 1", "match_lineups", {"match_ids[]": 1, "per_page": 25}),
        ("Player match stats sample match ID 1", "player_match_stats", {"match_ids[]": 1, "per_page": 25}),
        ("Team match stats sample match ID 1", "team_match_stats", {"match_ids[]": 1, "per_page": 25}),
        ("Match shots sample match ID 1", "match_shots", {"match_ids[]": 1, "per_page": 25}),
        ("Match momentum sample match ID 1", "match_momentum", {"match_ids[]": 1, "per_page": 25}),
    ]

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Run common endpoint tests", use_container_width=True):
            st.session_state["debug_results"] = []
            for label, endpoint, params in tests:
                result = bdl_get(endpoint, bdl_key, params=params)
                count = len(result.data) if isinstance(result.data, list) else "n/a"
                st.session_state["debug_results"].append(
                    {
                        "Test": label,
                        "Endpoint": endpoint,
                        "Status": result.status_code,
                        "OK": result.ok,
                        "Rows": count,
                        "Message": "OK" if result.ok else result.error,
                        "URL": result.url,
                    }
                )
    with c2:
        custom_endpoint = st.text_input("Custom endpoint", value="teams")
        custom_params = st.text_input("Custom params", value="seasons[]=2026&per_page=5", help="Example: seasons[]=2026&per_page=5")
        if st.button("Run custom test", use_container_width=True):
            params: Dict[str, Any] = {}
            for piece in custom_params.split("&"):
                if "=" in piece:
                    k, v = piece.split("=", 1)
                    params[k] = int(v) if v.isdigit() else v
            result = bdl_get(custom_endpoint, bdl_key, params=params)
            if result.ok:
                st.success(f"OK — {len(result.data) if isinstance(result.data, list) else 'data returned'} rows/items")
            else:
                st.error(result.error)
            st.caption(result.url)
            st.json(result.data if result.data is not None else {"error": result.error})

    if isinstance(st.session_state.get("debug_results"), list):
        debug_df = pd.DataFrame(st.session_state["debug_results"])
        st.dataframe(debug_df, use_container_width=True, hide_index=True)

    st.markdown("""
    **How to read results:**
    - `200` = endpoint worked.
    - `401` = missing/invalid key, the old key is still cached, or your BALLDONTLIE FIFA tier has not activated for that endpoint yet.
    - `404` = the sample match/team ID is not available yet or the endpoint name differs.
    - Teams and Stadiums should work on every tier.
    - Group Standings require ALL-STAR or GOAT.
    - Matches, Rosters, Match Lineups, Match Events, and Match Stats require GOAT.
    - If you just upgraded, click Clear API cache / refresh data in the sidebar, restart Streamlit, and retest.
    """)
