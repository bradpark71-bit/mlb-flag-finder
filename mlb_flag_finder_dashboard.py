"""
⚡ MLB Flag Finder Dashboard — Streamlit Cloud Edition
Pulls all data files from Google Drive "MLB 2026" folder via service account.
Local path references replaced with Drive API calls.
"""
import streamlit as st
import pandas as pd
import json
import io
import os
from datetime import datetime
import pytz

# ── GOOGLE DRIVE IMPORTS ───────────────────────────────────────────────────────
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ── CONFIG ─────────────────────────────────────────────────────────────────────
DRIVE_FOLDER_NAME = "MLB 2026"   # Exact folder name shared with service account
HST = pytz.timezone("Pacific/Honolulu")

st.set_page_config(
    page_title="⚡ MLB Flag Finder",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── GOOGLE DRIVE AUTH ──────────────────────────────────────────────────────────
@st.cache_resource
def get_drive_service():
    """Build Drive service from Streamlit secrets (service account JSON)."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    return build("drive", "v3", credentials=creds)


@st.cache_data(ttl=300)
def get_folder_id(folder_name: str) -> str | None:
    """Find the Drive folder ID by name."""
    service = get_drive_service()
    resp = service.files().list(
        q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        pageSize=5,
    ).execute()
    files = resp.get("files", [])
    return files[0]["id"] if files else None


@st.cache_data(ttl=300)
def list_folder_files(folder_id: str) -> list[dict]:
    """Return all files in a Drive folder (non-trashed)."""
    service = get_drive_service()
    results = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType, modifiedTime)",
            pageSize=100,
            pageToken=page_token,
        ).execute()
        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


def find_file(files: list[dict], name: str) -> dict | None:
    """Exact filename match."""
    for f in files:
        if f["name"] == name:
            return f
    return None


def find_file_contains(files: list[dict], substring: str) -> dict | None:
    """First file whose name contains substring."""
    for f in files:
        if substring in f["name"]:
            return f
    return None


def find_files_contains(files: list[dict], substring: str) -> list[dict]:
    """All files whose name contains substring, sorted desc by name."""
    matches = [f for f in files if substring in f["name"]]
    return sorted(matches, key=lambda x: x["name"], reverse=True)


def download_bytes(file_id: str) -> bytes:
    """Download a file from Drive as raw bytes."""
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    return buf.read()


def read_excel_from_drive(file_id: str, sheet_name=0) -> pd.DataFrame:
    raw = download_bytes(file_id)
    return pd.read_excel(io.BytesIO(raw), sheet_name=sheet_name)


def read_excel_file_from_drive(file_id: str) -> pd.ExcelFile:
    raw = download_bytes(file_id)
    return pd.ExcelFile(io.BytesIO(raw))


def read_json_from_drive(file_id: str) -> dict:
    raw = download_bytes(file_id)
    return json.loads(raw.decode("utf-8"))


# ── CSS — matches play card exactly ────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
html, body, [class*="css"] {
    font-family: 'Share Tech Mono', monospace !important;
    background-color: #0a0a12 !important;
    color: #e0e0ff !important;
}
.stApp { background: linear-gradient(135deg, #0a0a12 0%, #1a1a2e 100%) !important; }
.block-container { padding: 1.5rem 2rem !important; max-width: 1200px; }
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        linear-gradient(rgba(0,229,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,229,255,0.025) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 8px; background: transparent;
    border-bottom: 2px solid #00e5ff40; padding-bottom: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: #12121f; border: 1px solid #1a1a2e;
    border-radius: 4px 4px 0 0; padding: 8px 20px;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 0.7em; font-weight: 700; color: #546e7a; letter-spacing: 1px;
}
.stTabs [aria-selected="true"] {
    background: #0d0d18 !important; color: #00e5ff !important;
    border-color: #00e5ff !important; border-bottom-color: #0a0a12 !important;
}
.stTabs [data-baseweb="tab-panel"] { background: transparent; padding-top: 1rem; }
[data-testid="metric-container"] {
    background: #12121f !important; border: 1px solid #1a1a2e !important;
    border-radius: 6px !important; padding: 12px !important;
}
[data-testid="metric-container"] label {
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.65em !important; color: #888 !important;
    text-transform: uppercase; letter-spacing: 1px;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'Orbitron', sans-serif !important;
    font-size: 1.6em !important; color: #00e5ff;
}
.stButton button {
    background: #12121f !important; border: 1px solid #00e5ff40 !important;
    color: #00e5ff !important; font-family: 'Orbitron', sans-serif !important;
    font-size: 0.7em !important; font-weight: 700 !important;
    letter-spacing: 1px !important; border-radius: 4px !important;
    padding: 6px 16px !important;
}
.stButton button:hover {
    border-color: #00e5ff !important;
    box-shadow: 0 0 12px rgba(0,229,255,0.2) !important;
}
.stDataFrame { border: 1px solid #1a1a2e !important; border-radius: 6px !important; }
[data-testid="stDataFrame"] th {
    background: #0d0d18 !important; color: #888 !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.72em !important; text-transform: uppercase;
}
hr { border-color: #1a1a2e !important; }
.stSelectbox select, .stSelectbox div[data-baseweb="select"] {
    background: #12121f !important; border-color: #1a1a2e !important;
    color: #e0e0ff !important; font-family: 'Share Tech Mono', monospace !important;
}
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0a0a12; }
::-webkit-scrollbar-thumb { background: #1a1a2e; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #00e5ff40; }
</style>
""", unsafe_allow_html=True)

# ── HTML COMPONENTS ─────────────────────────────────────────────────────────────
def header_html(today_str, window, version="v1.1g6a"):
    accent = "#00e5ff" if window == "T1" else "#ffab00"
    badge_class = "t1" if window == "T1" else "t2"
    now_hst = datetime.now(HST).strftime("%I:%M %p HST")
    return f"""
<style>
.ff-header {{ text-align:center; margin-bottom:24px; border-bottom:2px solid {accent}; padding-bottom:16px; }}
.ff-title {{ font-family:'Orbitron',sans-serif; font-size:1.9em; font-weight:900;
             color:{accent}; text-shadow:0 0 20px {accent}80; letter-spacing:2px; }}
.ff-subtitle {{ color:#888; font-size:0.82em; margin-top:6px; letter-spacing:1px; font-family:'Share Tech Mono',monospace; }}
.ff-badge {{ display:inline-block; padding:4px 14px; border-radius:20px; font-size:0.75em; margin:0 4px;
             font-family:'Share Tech Mono',monospace; }}
.ff-badge-date {{ background:rgba(0,229,255,0.1); border:1px solid #00e5ff; color:#00e5ff; }}
.ff-badge-t1 {{ background:rgba(0,229,255,0.1); border:1px solid #00e5ff; color:#00e5ff; }}
.ff-badge-t2 {{ background:rgba(255,171,0,0.12); border:1px solid #ffab00; color:#ffab00; }}
.ff-badge-eng {{ background:rgba(156,39,176,0.15); border:1px solid #ab47bc; color:#ab47bc; }}
.ff-meta {{ font-size:0.72em; color:#546e7a; margin-top:8px; font-family:'Share Tech Mono',monospace; }}
</style>
<div class="ff-header">
  <div class="ff-title">⚡ MLB FLAG FINDER {version}</div>
  <div class="ff-subtitle">PLAY CARD &nbsp;|&nbsp; ENGINE A (SIDES/ML) + ENGINE B (TOTALS)</div>
  <div style="margin-top:10px;">
    <span class="ff-badge ff-badge-date">{today_str}</span>
    <span class="ff-badge ff-badge-{badge_class}">{"TIER 1 — T1 CAPTURE" if window == "T1" else "TIER 2 — T2 CAPTURE"}</span>
    <span class="ff-badge ff-badge-eng">{version}</span>
  </div>
  <div class="ff-meta">Last refresh: {now_hst}</div>
</div>
"""

def alert_html(label, detail, color="#ffab00"):
    bg = color.replace("#", "")
    return f"""
<div style="background:linear-gradient(90deg,rgba({int(bg[0:2],16)},{int(bg[2:4],16)},{int(bg[4:6],16)},0.10),rgba({int(bg[0:2],16)},{int(bg[2:4],16)},{int(bg[4:6],16)},0.02));
     border:1px solid {color}; border-radius:8px; padding:12px 18px; margin-bottom:12px; text-align:center;">
  <div style="font-family:'Orbitron',sans-serif; font-size:0.9em; font-weight:700; color:{color};">{label}</div>
  <div style="font-size:0.76em; color:#888; margin-top:4px; font-family:'Share Tech Mono',monospace;">{detail}</div>
</div>
"""

def kpi_html(items):
    color_map = {
        "cyan": "#00e5ff", "green": "#4caf50", "amber": "#ffab00",
        "muted": "#546e7a", "red": "#f44336", "purple": "#ce93d8", "white": "#fff"
    }
    cols = "".join([
        f"""<div style="background:#12121f; border:1px solid #1a1a2e; border-radius:6px; padding:12px; text-align:center;">
<div style="font-size:0.68em; color:#888; text-transform:uppercase; letter-spacing:1px; font-family:'Share Tech Mono',monospace;">{label}</div>
<div style="font-family:'Orbitron',sans-serif; font-size:1.5em; font-weight:700; color:{color_map.get(clr,'#aaa')};">{val}</div>
</div>"""
        for label, val, clr in items
    ])
    return f"""<div style="display:grid; grid-template-columns:repeat({len(items)},1fr); gap:10px; margin-bottom:20px;">{cols}</div>"""

def no_plays_html(msg, detail=""):
    return f"""<div style="background:#12121f; border:1px dashed #546e7a40; border-radius:8px; padding:22px; text-align:center; margin-bottom:18px;">
<div style="font-family:'Orbitron',sans-serif; font-size:1.05em; color:#546e7a; font-weight:700; letter-spacing:2px;">{msg}</div>
<div style="font-size:0.78em; color:#546e7a; margin-top:6px; font-family:'Share Tech Mono',monospace;">{detail}</div>
</div>"""

def play_card_html(matchup, time_venue, tier, play_line, units, meta, flags_html, note="", accent="#ffab00"):
    tier_colors = {
        "LEAN":   ("#80d8ff", "rgba(128,216,255,0.12)", "#80d8ff40"),
        "STRONG": ("#4caf50", "rgba(76,175,80,0.15)",   "#4caf5040"),
        "ELITE":  ("#00e5ff", "rgba(0,229,255,0.12)",   "#00e5ff40"),
    }
    tc, tbg, tborder = tier_colors.get(tier.upper(), ("#888", "rgba(136,136,136,0.1)", "#88888840"))
    note_html = f'<div style="font-size:0.74em; color:#546e7a; padding:8px 16px; background:#0a0a12; border-top:1px solid #1a1a2e20; font-style:italic; font-family:\'Share Tech Mono\',monospace;">{note}</div>' if note else ""
    return f"""
<div style="background:#12121f; border:2px solid {accent}; border-radius:8px; margin-bottom:14px;
     overflow:hidden; box-shadow:0 0 20px {accent}30;">
  <div style="padding:12px 16px; background:#0d0d18; border-bottom:1px solid #1a1a2e;
       display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
    <span style="font-family:'Orbitron',sans-serif; font-size:1.2em; font-weight:700; color:#fff;">{matchup}</span>
    <span style="font-family:'Orbitron',sans-serif; font-size:0.65em; font-weight:700; padding:3px 10px;
          border-radius:4px; background:{tbg}; border:1px solid {tborder}; color:{tc};">{tier} {units}</span>
    <span style="font-size:0.73em; color:#888; font-family:'Share Tech Mono',monospace;">{time_venue}</span>
  </div>
  <div style="padding:12px 16px;">
    <div style="font-family:'Orbitron',sans-serif; font-size:1.3em; font-weight:700; color:{accent}; margin-bottom:6px;">⚾ {play_line}</div>
    <div style="font-size:0.78em; color:#888; margin-bottom:8px; font-family:'Share Tech Mono',monospace;">{meta}</div>
    <div style="font-size:0.79em; line-height:1.9; font-family:'Share Tech Mono',monospace;">{flags_html}</div>
  </div>
  {note_html}
</div>"""

def section_title_html(text, color="#00e5ff"):
    return f"""<div style="font-family:'Orbitron',sans-serif; font-size:0.88em; font-weight:700; color:{color}; margin:22px 0 10px; padding-bottom:5px; border-bottom:1px solid {color}20; letter-spacing:1px;">{text}</div>"""

def sharp_row_html(title, mtype, direction, signal_type, divergence, big_money, dollars):
    dir_color = "#4caf50" if direction == "YES" else "#f44336"
    type_color = "#4caf50" if "CONFIRM" in signal_type else "#ffab00"
    bm_badge = '<span style="background:rgba(76,175,80,0.15); border:1px solid #4caf50; color:#4caf50; padding:1px 6px; border-radius:3px; font-size:0.8em;">BIG$</span>' if big_money else '<span style="background:rgba(84,110,122,0.12); border:1px solid #546e7a; color:#546e7a; padding:1px 6px; border-radius:3px; font-size:0.8em;">reg</span>'
    return f"""<tr style="border-bottom:1px solid #1a1a2e20;">
  <td style="padding:5px 10px; color:#e0e0ff;">{title[:55]}</td>
  <td style="padding:5px 10px; color:#888; text-transform:uppercase; font-size:0.8em;">{mtype}</td>
  <td style="padding:5px 10px; text-align:center;">{bm_badge}</td>
  <td style="padding:5px 10px; color:{dir_color}; font-weight:700;">{direction}</td>
  <td style="padding:5px 10px; color:{type_color}; font-size:0.82em;">{signal_type}</td>
  <td style="padding:5px 10px; color:#888; text-align:right;">{divergence:.1%}</td>
  <td style="padding:5px 10px; color:#888; text-align:right;">${dollars:,.0f}</td>
</tr>"""

# ── HELPERS ─────────────────────────────────────────────────────────────────────
def classify_window(game_time_hst):
    try:
        hour = int(str(game_time_hst).split(":")[0])
        return "T1" if hour < 13 else "T2"
    except:
        return "T2"

def fmt_ml(val):
    try:
        v = int(float(val))
        return f"+{v}" if v > 0 else str(v)
    except:
        return "—"

def safe(val, default="—"):
    if not isinstance(val, str) and pd.isna(val):
        return default
    return val if str(val) not in ("nan", "None", "") else default

# ── DATA LOADERS (Drive-backed) ─────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_all(today_str: str, today_sheet: str) -> dict:
    results = {}

    # ── Get folder listing ──
    folder_id = get_folder_id(DRIVE_FOLDER_NAME)
    if not folder_id:
        results["_folder_error"] = f"Drive folder '{DRIVE_FOLDER_NAME}' not found. Check folder sharing."
        return results

    files = list_folder_files(folder_id)
    results["_file_count"] = len(files)

    # ── Daily Outlook ──
    f_out = find_file(files, "MLB_Daily_Outlook.xlsx")
    if f_out:
        try:
            xl = read_excel_file_from_drive(f_out["id"])
            sheet = today_sheet if today_sheet in xl.sheet_names else xl.sheet_names[0]
            df = pd.read_excel(io.BytesIO(download_bytes(f_out["id"])), sheet_name=sheet).dropna(subset=["away_team"])
            results["outlook"] = (df, None, sheet)
        except Exception as e:
            results["outlook"] = (None, str(e), None)
    else:
        results["outlook"] = (None, "MLB_Daily_Outlook.xlsx not found in Drive folder.", None)

    # ── Trade Flow ──
    tf_files = find_files_contains(files, f"trade_flow_{today_str}_")
    results["trade_flows"] = []
    for f in tf_files:
        try:
            results["trade_flows"].append((read_json_from_drive(f["id"]), f["name"]))
        except:
            pass

    # ── Kalshi Depth ──
    results["kalshi_depth"] = (None, None)
    for suffix in ["close", "open"]:
        f_kd = find_file(files, f"kalshi_depth_{today_str}_{suffix}.json")
        if f_kd:
            try:
                results["kalshi_depth"] = (read_json_from_drive(f_kd["id"]), f_kd["name"])
                break
            except:
                pass

    # ── God Mode — prefer PM ──
    results["god_mode"] = (None, None)
    for pattern in [f"MLB_God_Mode_{today_str}_PM.xlsx", f"MLB_God_Mode_{today_str}.xlsx"]:
        f_gm = find_file(files, pattern)
        if not f_gm:
            # fallback: contains match
            f_gm = find_file_contains(files, f"MLB_God_Mode_{today_str}")
        if f_gm:
            try:
                xl_gm = read_excel_file_from_drive(f_gm["id"])
                raw = download_bytes(f_gm["id"])
                gm = {sn: pd.read_excel(io.BytesIO(raw), sheet_name=sn) for sn in xl_gm.sheet_names}
                results["god_mode"] = (gm, f_gm["name"])
                break
            except:
                pass

    # ── Wx Pressure ──
    f_px = find_file(files, f"game_day_pressure_{today_str}.json")
    if f_px:
        try:
            results["pressure"] = read_json_from_drive(f_px["id"])
        except:
            results["pressure"] = None
    else:
        results["pressure"] = None

    # ── Master DB ──
    f_mdb = find_file(files, "MLB_Master_DB.xlsx")
    if f_mdb:
        try:
            results["master_db"] = read_excel_from_drive(f_mdb["id"])
        except:
            results["master_db"] = None
    else:
        results["master_db"] = None

    # ── Futures Tracker ──
    f_fut = find_file(files, "MLB_Futures_Tracker.xlsx")
    results["futures_file_id"] = f_fut["id"] if f_fut else None

    return results


# ── MAIN ────────────────────────────────────────────────────────────────────────
def main():
    now_hst = datetime.now(HST)
    today_str = now_hst.strftime("%Y-%m-%d")
    today_sheet = now_hst.strftime("%m-%d")
    current_window = "T1" if now_hst.hour < 13 else "T2"

    # ── TOP BAR ──
    st.markdown(header_html(today_str, current_window), unsafe_allow_html=True)
    col_w, col_r, _ = st.columns([1, 1, 4])
    with col_w:
        window_override = st.selectbox("Window", ["Auto", "T1", "T2"], label_visibility="collapsed")
        if window_override != "Auto":
            current_window = window_override
    with col_r:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()

    # ── LOAD DATA ──
    data = load_all(today_str, today_sheet)

    if "_folder_error" in data:
        st.error(f"🔴 Drive Error: {data['_folder_error']}")
        st.stop()

    df_out, out_err, loaded_sheet = data.get("outlook", (None, "Not loaded", None))
    trade_flows = data.get("trade_flows", [])
    kd_data, kd_file = data.get("kalshi_depth", (None, None))
    gm_data, gm_file = data.get("god_mode", (None, None))
    px_data = data.get("pressure", None)
    mdb = data.get("master_db", None)
    futures_file_id = data.get("futures_file_id", None)

    tf_data = trade_flows[0][0] if trade_flows else None
    tf_file = trade_flows[0][1] if trade_flows else None

    # ── FILE STATUS ROW ──
    def status(ok, label):
        icon = "🟢" if ok else "🔴"
        color = "#4caf50" if ok else "#f44336"
        return f'<span style="font-family:\'Share Tech Mono\',monospace; font-size:0.75em; color:{color};">{icon} {label}</span>'

    st.markdown(f"""
    <div style="display:flex; gap:20px; background:#12121f; border:1px solid #1a1a2e;
         border-radius:6px; padding:8px 16px; margin-bottom:18px; flex-wrap:wrap;">
      {status(df_out is not None, "Daily Outlook")}
      {status(tf_data is not None, f"Trade Flow ({tf_file or 'missing'})")}
      {status(kd_data is not None, f"Kalshi Depth ({kd_file or 'missing'})")}
      {status(gm_data is not None, f"God Mode ({gm_file or 'missing'})")}
      {status(px_data is not None, "Wx Pressure")}
    </div>
    """, unsafe_allow_html=True)

    if out_err:
        st.markdown(alert_html("⚠️ DAILY OUTLOOK ERROR", out_err, "#f44336"), unsafe_allow_html=True)

    # ── TABS ──
    tabs = st.tabs([
        "📡 TODAY'S PLAYS",
        "📋 FULL SLATE",
        "⚡ SHARP MONEY",
        "📊 KALSHI DEPTH",
        "⛽ GOD MODE",
        "🌪️ WX PRESSURE",
        "📈 FUTURES",
    ])

    # ═══════════════════════════════════════════════════════
    # TAB 0 — TODAY'S PLAYS
    # ═══════════════════════════════════════════════════════
    with tabs[0]:
        if df_out is None:
            st.markdown(no_plays_html("NO DATA — OUTLOOK NOT LOADED", out_err or ""), unsafe_allow_html=True)
        else:
            df_window = df_out.copy()
            df_window["_window"] = df_window["game_time_hst"].apply(classify_window)
            df_t = df_window[df_window["_window"] == current_window].copy()

            plays_a = df_t[df_t["engine_a_tier"].isin(["PLAY", "ELITE", "STRONG", "LEAN"])].copy()
            plays_b = df_t[df_t["engine_b_tier"].isin(["PLAY", "ELITE", "STRONG", "LEAN"])].copy()
            killed = df_t[df_t["engine_b_tier"] == "KILLED"].copy()
            total_plays = len(plays_a) + len(plays_b)
            total_units = plays_a["engine_a_units"].sum() + plays_b["engine_b_units"].sum()

            accent = "#00e5ff" if current_window == "T1" else "#ffab00"
            st.markdown(kpi_html([
                (f"{current_window} Games", len(df_t), "cyan"),
                ("Engine A Plays", len(plays_a), "green" if len(plays_a) > 0 else "muted"),
                ("Engine B Plays", len(plays_b), "green" if len(plays_b) > 0 else "muted"),
                ("Total Units", f"{total_units:.1f}u", "amber" if total_units > 0 else "muted"),
                ("Sharp Tickers", tf_data["sharp_count"] if tf_data else "—", "purple"),
            ]), unsafe_allow_html=True)

            if total_plays == 0:
                st.markdown(no_plays_html(
                    f"NO {current_window} PLAYS — SIGNAL WATCH ONLY",
                    f"All {len(df_t)} {current_window} games below threshold."
                ), unsafe_allow_html=True)

            # ENGINE A
            if len(plays_a) > 0:
                st.markdown(section_title_html(f"🎯 ENGINE A — SIDES/ML ({current_window})", accent), unsafe_allow_html=True)
                for _, row in plays_a.iterrows():
                    side = safe(row["engine_a_play_side"], "—").split()[-1]
                    ml_col = "close_home_ml" if row["engine_a_play_side"] == row["home_team"] else "close_away_ml"
                    ml_val = fmt_ml(row.get(ml_col, "—"))
                    tier = str(row["engine_a_tier"])
                    play_line = f"{side} ML {ml_val} &nbsp;→&nbsp; {row['engine_a_units']}u"
                    flags_html = ""
                    for f in safe(row["engine_a_flags_for"], "").split(","):
                        if f.strip():
                            flags_html += f'<div><span style="color:#4caf50;">✅ {f.strip()}</span></div>'
                    for f in safe(row["engine_a_flags_against"], "").split(","):
                        if f.strip():
                            flags_html += f'<div><span style="color:#f44336;">❌ {f.strip()}</span></div>'
                    meta = f"Engine A {tier} +{row['engine_a_net_score']:.2f} &nbsp;|&nbsp; {row['game_time_hst']} &nbsp;|&nbsp; {safe(row['venue'], '')}"
                    st.markdown(play_card_html(
                        matchup=f"{row['away_team'].split()[-1]} @ {row['home_team'].split()[-1]}",
                        time_venue=f"{row['game_time_hst']} · {safe(row['venue'], 'TBD')} · Total {safe(row['close_total'], safe(row['open_total'], '—'))}",
                        tier=tier, play_line=play_line,
                        units=f"→ {row['engine_a_units']}u", meta=meta,
                        flags_html=flags_html, accent=accent,
                    ), unsafe_allow_html=True)

            # ENGINE B
            if len(plays_b) > 0:
                st.markdown(section_title_html(f"🎯 ENGINE B — TOTALS ({current_window})", accent), unsafe_allow_html=True)
                for _, row in plays_b.iterrows():
                    direction = safe(row["engine_b_play_dir"], "—")
                    total = safe(row["close_total"], safe(row["open_total"], "—"))
                    tier = str(row["engine_b_tier"])
                    play_line = f"{direction} {total} &nbsp;→&nbsp; {row['engine_b_units']}u"
                    flags_html = ""
                    for f in safe(row["engine_b_flags_for"], "").split(","):
                        if f.strip():
                            flags_html += f'<div><span style="color:#4caf50;">✅ {f.strip()}</span></div>'
                    for f in safe(row["engine_b_flags_against"], "").split(","):
                        if f.strip():
                            flags_html += f'<div><span style="color:#f44336;">❌ {f.strip()}</span></div>'
                    kill = safe(row["engine_b_kill"], "")
                    if kill:
                        flags_html += f'<div><span style="color:#f44336;">🔴 KILL: {kill}</span></div>'
                    meta = f"Engine B {tier} +{row['engine_b_net_score']:.2f} &nbsp;|&nbsp; {row['game_time_hst']} &nbsp;|&nbsp; {safe(row['venue'], '')}"
                    st.markdown(play_card_html(
                        matchup=f"{row['away_team'].split()[-1]} @ {row['home_team'].split()[-1]}",
                        time_venue=f"{row['game_time_hst']} · {safe(row['venue'], 'TBD')} · Total {total}",
                        tier=tier, play_line=play_line,
                        units=f"→ {row['engine_b_units']}u", meta=meta,
                        flags_html=flags_html, accent=accent,
                    ), unsafe_allow_html=True)

            # KILLED
            if len(killed) > 0:
                st.markdown(section_title_html("🔴 KILLED PLAYS", "#f44336"), unsafe_allow_html=True)
                for _, row in killed.iterrows():
                    st.markdown(f"""
                    <div style="background:#12121f; border:1px solid #f4433640; border-radius:6px;
                         padding:10px 14px; margin-bottom:8px; font-family:'Share Tech Mono',monospace; font-size:0.8em;">
                      <span style="color:#f44336; font-family:'Orbitron',sans-serif; font-size:0.85em; font-weight:700;">
                        {row['away_team'].split()[-1]} @ {row['home_team'].split()[-1]}
                      </span>
                      <span style="color:#546e7a; margin-left:10px;">{row['game_time_hst']}</span>
                      <span style="color:#f44336; margin-left:10px;">KILL: {safe(row['engine_b_kill'], '—')}</span>
                    </div>
                    """, unsafe_allow_html=True)

            # SIGNAL WATCH
            st.markdown(section_title_html(f"📡 {current_window} SIGNAL WATCH — ALL GAMES", "#546e7a"), unsafe_allow_html=True)
            rows_html = ""
            for _, row in df_t.iterrows():
                ea_score = row.get("engine_a_net_score", 0) or 0
                eb_score = row.get("engine_b_net_score", 0) or 0
                ea_tier = safe(row["engine_a_tier"], "PASS")
                eb_tier = safe(row["engine_b_tier"], "PASS")
                a_color = "#4caf50" if ea_tier not in ["PASS", "KILLED"] else ("#f44336" if ea_tier == "KILLED" else "#546e7a")
                b_color = "#4caf50" if eb_tier not in ["PASS", "KILLED"] else ("#f44336" if eb_tier == "KILLED" else "#546e7a")
                rows_html += f"""<tr style="border-bottom:1px solid #1a1a2e20;">
                  <td style="padding:5px 10px; color:#fff; font-family:'Share Tech Mono',monospace; white-space:nowrap;">{safe(row['away_team'],'').split()[-1]} @ {safe(row['home_team'],'').split()[-1]}</td>
                  <td style="padding:5px 10px; color:#546e7a; font-family:'Share Tech Mono',monospace;">{safe(row['game_time_hst'],'—')}</td>
                  <td style="padding:5px 10px; color:#888; font-family:'Share Tech Mono',monospace;">{fmt_ml(row.get('close_away_ml',''))} / {fmt_ml(row.get('close_home_ml',''))}</td>
                  <td style="padding:5px 10px; color:#888; font-family:'Share Tech Mono',monospace;">{safe(row.get('close_total',''),safe(row.get('open_total',''),'—'))}</td>
                  <td style="padding:5px 10px; color:{a_color}; font-family:'Orbitron',sans-serif; font-size:0.75em; font-weight:700;">{ea_tier} {ea_score:+.2f}</td>
                  <td style="padding:5px 10px; color:{b_color}; font-family:'Orbitron',sans-serif; font-size:0.75em; font-weight:700;">{eb_tier} {eb_score:+.2f}</td>
                  <td style="padding:5px 10px; color:#546e7a; font-family:'Share Tech Mono',monospace; font-size:0.75em;">{safe(row.get('engine_a_flags_for',''), safe(row.get('engine_b_flags_for',''),'—'))[:60]}</td>
                </tr>"""
            st.markdown(f"""
            <div style="overflow-x:auto; background:#12121f; border:1px solid #1a1a2e; border-radius:8px;">
            <table style="width:100%; border-collapse:collapse; font-size:0.78em;">
              <thead><tr style="background:#0d0d18;">
                <th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">Game</th>
                <th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">Time</th>
                <th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">ML (A/H)</th>
                <th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">Total</th>
                <th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">Engine A</th>
                <th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">Engine B</th>
                <th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">Top Flag</th>
              </tr></thead>
              <tbody>{rows_html}</tbody>
            </table>
            </div>
            """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # TAB 1 — FULL SLATE
    # ═══════════════════════════════════════════════════════
    with tabs[1]:
        if df_out is None:
            st.error("Daily Outlook not loaded.")
        else:
            st.markdown(section_title_html(f"📋 FULL SLATE — {today_sheet} ({len(df_out)} games)", "#00e5ff"), unsafe_allow_html=True)
            col_f1, _ = st.columns([2, 4])
            with col_f1:
                w_filter = st.selectbox("Filter", ["All Games", "T1 Only (< 13:00 HST)", "T2 Only (13:00+ HST)"])
            df_display = df_out.copy()
            df_display["_window"] = df_display["game_time_hst"].apply(classify_window)
            if "T1" in w_filter:
                df_display = df_display[df_display["_window"] == "T1"]
            elif "T2" in w_filter:
                df_display = df_display[df_display["_window"] == "T2"]
            cols_show = [
                "game_time_hst", "away_team", "home_team",
                "away_starter", "home_starter",
                "open_away_ml", "open_home_ml", "close_away_ml", "close_home_ml",
                "open_total", "close_total", "total_change", "ml_fav_move_dir",
                "engine_a_tier", "engine_a_net_score", "engine_a_play_side",
                "engine_b_tier", "engine_b_net_score", "engine_b_play_dir",
                "engine_a_flags_for", "engine_b_flags_for",
                "weather_temp", "weather_wind", "park_factor",
            ]
            df_show = df_display[[c for c in cols_show if c in df_display.columns]].copy()
            df_show.columns = [c.replace("_", " ").upper() for c in df_show.columns]
            st.dataframe(df_show, use_container_width=True, height=500)

    # ═══════════════════════════════════════════════════════
    # TAB 2 — SHARP MONEY
    # ═══════════════════════════════════════════════════════
    with tabs[2]:
        if not trade_flows:
            st.markdown(alert_html("⚠️ NO TRADE FLOW DATA", f"No trade_flow_{today_str}_*.json found in Drive folder."), unsafe_allow_html=True)
        else:
            for tf_d, tf_fname in trade_flows:
                capture_time = tf_d.get("capture_time", "—")
                sharp_count = tf_d.get("sharp_count", 0)
                market_count = tf_d.get("market_count", 0)
                markets_with_trades = tf_d.get("markets_with_trades", 0)
                window_h = tf_d.get("lookback_hours", "—")
                st.markdown(section_title_html(f"⚡ {tf_fname} — {sharp_count} SHARP SIGNALS", "#ffab00"), unsafe_allow_html=True)
                st.markdown(kpi_html([
                    ("Sharp Signals", sharp_count, "amber" if sharp_count > 0 else "muted"),
                    ("Markets Scanned", market_count, "cyan"),
                    ("Markets w/ Trades", markets_with_trades, "cyan"),
                    ("Lookback Window", f"{window_h}h", "muted"),
                    ("Capture", capture_time[:16].replace("T", " "), "muted"),
                ]), unsafe_allow_html=True)
                sharp_markets = [m for m in tf_d.get("markets", []) if m["sharp_signal"]["triggered"]]
                if not sharp_markets:
                    st.markdown(no_plays_html("NO SHARP SIGNALS TRIGGERED"), unsafe_allow_html=True)
                    continue
                from collections import defaultdict
                by_type = defaultdict(list)
                for m in sharp_markets:
                    by_type[m["market_type"]].append(m)
                for mtype in ["moneyline", "spread", "total"]:
                    if mtype not in by_type:
                        continue
                    markets = by_type[mtype]
                    st.markdown(section_title_html(f"{mtype.upper()} ({len(markets)} signals)", "#00e5ff"), unsafe_allow_html=True)
                    rows = ""
                    for m in sorted(markets, key=lambda x: -abs(x["sharp_signal"]["divergence"])):
                        ss = m["sharp_signal"]
                        df_info = m["dollar_flow"]
                        ts = m["trade_size"]
                        rows += sharp_row_html(
                            title=m["title"], mtype=mtype,
                            direction=ss["direction"] or "—",
                            signal_type=ss["signal_type"],
                            divergence=ss["divergence"],
                            big_money=ts["big_money_flag"],
                            dollars=df_info["total"],
                        )
                    st.markdown(f"""
                    <div style="overflow-x:auto; background:#12121f; border:1px solid #1a1a2e; border-radius:8px; margin-bottom:16px;">
                    <table style="width:100%; border-collapse:collapse; font-size:0.77em; font-family:'Share Tech Mono',monospace;">
                      <thead><tr style="background:#0d0d18;">
                        <th style="padding:5px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em;">Market</th>
                        <th style="padding:5px 10px; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em;">Type</th>
                        <th style="padding:5px 10px; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em;">Size</th>
                        <th style="padding:5px 10px; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em;">Dir</th>
                        <th style="padding:5px 10px; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em;">Signal</th>
                        <th style="padding:5px 10px; text-align:right; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em;">Gap</th>
                        <th style="padding:5px 10px; text-align:right; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em;">$ Flow</th>
                      </tr></thead>
                      <tbody>{rows}</tbody>
                    </table>
                    </div>
                    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # TAB 3 — KALSHI DEPTH
    # ═══════════════════════════════════════════════════════
    with tabs[3]:
        if kd_data is None:
            st.markdown(alert_html("⚠️ NO KALSHI DEPTH DATA", f"No kalshi_depth_{today_str}_close/open.json found."), unsafe_allow_html=True)
        else:
            meta = kd_data.get("metadata", {})
            games = kd_data.get("games", [])
            st.markdown(kpi_html([
                ("Games Captured", meta.get("games_captured", len(games)), "cyan"),
                ("Snapshot", meta.get("phase", "—").upper(), "amber"),
                ("Version", meta.get("script_version", "—"), "muted"),
                ("Snapshot Time", meta.get("snapshot_time", "—")[:16].replace("T", " "), "muted"),
                ("File", kd_file or "—", "muted"),
            ]), unsafe_allow_html=True)
            for game in games:
                away = game.get("away_team", "—")
                home = game.get("home_team", "—")
                game_time = game.get("game_time_et", "—")
                ml = game.get("moneyline", {})
                spread = game.get("spread", {})
                total = game.get("total", {})
                rfi = game.get("rfi", {})
                home_ml = ml.get("home", {})
                away_ml = ml.get("away", {})
                home_prob = home_ml.get("last_price", "—")
                away_prob = away_ml.get("last_price", "—")
                total_line = total.get("primary_line", "—")
                total_over = total.get("yes_bid", "—")
                spread_line = spread.get("primary_line", "—") if spread.get("available") else "N/A"
                hp_str = f"{home_prob:.0%}" if isinstance(home_prob, float) else "—"
                ap_str = f"{away_prob:.0%}" if isinstance(away_prob, float) else "—"
                to_str = f"{total_over:.0%}" if isinstance(total_over, float) else "—"
                tf_game = game.get("trade_flow", {})
                ml_tf = tf_game.get("moneyline", {})
                ml_sharp = ml_tf.get("sharp_signal", {})
                sharp_triggered = ml_sharp.get("triggered", False)
                sharp_dir = ml_sharp.get("direction", "—")
                sharp_badge = ""
                if sharp_triggered:
                    sc = "#4caf50" if sharp_dir == "YES" else "#f44336"
                    sharp_badge = f'<span style="background:rgba(76,175,80,0.15); border:1px solid {sc}; color:{sc}; padding:2px 8px; border-radius:3px; font-size:0.72em; font-family:\'Orbitron\',sans-serif; font-weight:700;">⚡ SHARP {sharp_dir}</span>'
                st.markdown(f"""
                <div style="background:#12121f; border:1px solid #1a1a2e; border-radius:8px;
                     padding:10px 16px; margin-bottom:8px; font-family:'Share Tech Mono',monospace;">
                  <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom:6px;">
                    <span style="font-family:'Orbitron',sans-serif; font-size:1.0em; font-weight:700; color:#fff;">{away} @ {home}</span>
                    <span style="color:#546e7a; font-size:0.75em;">{game_time} ET</span>
                    {sharp_badge}
                  </div>
                  <div style="display:grid; grid-template-columns:repeat(5,1fr); gap:8px; font-size:0.76em;">
                    <div><div style="color:#888; font-size:0.75em; text-transform:uppercase; margin-bottom:2px;">ML {away}</div><div style="color:#00e5ff;">{ap_str}</div></div>
                    <div><div style="color:#888; font-size:0.75em; text-transform:uppercase; margin-bottom:2px;">ML {home}</div><div style="color:#00e5ff;">{hp_str}</div></div>
                    <div><div style="color:#888; font-size:0.75em; text-transform:uppercase; margin-bottom:2px;">Spread</div><div style="color:#888;">{home} {spread_line}</div></div>
                    <div><div style="color:#888; font-size:0.75em; text-transform:uppercase; margin-bottom:2px;">Total O {total_line}</div><div style="color:#888;">{to_str}</div></div>
                    <div><div style="color:#888; font-size:0.75em; text-transform:uppercase; margin-bottom:2px;">RFI Yes</div><div style="color:#888;">{f"{rfi['yes_bid']:.0%}" if rfi.get("available") and isinstance(rfi.get("yes_bid"), float) else "N/A"}</div></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # TAB 4 — GOD MODE
    # ═══════════════════════════════════════════════════════
    with tabs[4]:
        if gm_data is None:
            st.markdown(alert_html("⚠️ GOD MODE NOT LOADED", f"No MLB_God_Mode_{today_str}*.xlsx found in Drive folder."), unsafe_allow_html=True)
        else:
            gm_tab_names = list(gm_data.keys())
            gm_tabs = st.tabs(gm_tab_names)
            for i, sname in enumerate(gm_tab_names):
                with gm_tabs[i]:
                    st.dataframe(gm_data[sname], use_container_width=True, height=500)

    # ═══════════════════════════════════════════════════════
    # TAB 5 — WX PRESSURE
    # ═══════════════════════════════════════════════════════
    with tabs[5]:
        if px_data is None:
            st.markdown(alert_html("⚠️ NO PRESSURE DATA", f"No game_day_pressure_{today_str}.json found."), unsafe_allow_html=True)
        else:
            summary = px_data.get("summary", {})
            st.markdown(kpi_html([
                ("Hitter Boost", summary.get("hitter_boost", 0), "green"),
                ("Pitcher Boost", summary.get("pitcher_boost", 0), "red"),
                ("Neutral", summary.get("neutral", 0), "muted"),
                ("Dome Skip", summary.get("dome_skip", 0), "muted"),
                ("Errors", summary.get("errors", 0), "red" if summary.get("errors", 0) > 0 else "muted"),
            ]), unsafe_allow_html=True)
            for r in px_data.get("results", []):
                team = r.get("team", "—")
                park = r.get("park", "—")
                classification = r.get("classification", "NEUTRAL")
                anomaly = r.get("anomaly_hpa", 0)
                sigma = r.get("anomaly_sigma", 0)
                avg_hpa = r.get("game_window_avg_hpa", 0)
                cls_color = {"HITTER_BOOST": "#4caf50", "PITCHER_BOOST": "#f44336", "NEUTRAL": "#546e7a"}.get(classification, "#546e7a")
                roof = r.get("roof_warning", "")
                st.markdown(f"""
                <div style="background:#12121f; border:1px solid #1a1a2e; border-radius:6px;
                     padding:8px 14px; margin-bottom:6px; font-family:'Share Tech Mono',monospace; font-size:0.78em;
                     display:flex; align-items:center; gap:16px; flex-wrap:wrap;">
                  <span style="font-family:'Orbitron',sans-serif; font-size:0.9em; font-weight:700; color:#fff; min-width:50px;">{team}</span>
                  <span style="color:#888;">{park}</span>
                  <span style="font-family:'Orbitron',sans-serif; font-size:0.7em; font-weight:700; color:{cls_color};
                       padding:2px 8px; border:1px solid {cls_color}40; border-radius:4px;">{classification}</span>
                  <span style="color:#888;">Anomaly: <span style="color:#00e5ff;">{anomaly:+.2f} hPa</span></span>
                  <span style="color:#888;">σ: {sigma:.2f}</span>
                  <span style="color:#888;">Avg: {avg_hpa:.1f} hPa</span>
                  {"<span style='color:#ffab00; font-size:0.72em;'>⚠️ RETRACTABLE</span>" if "RETRACTABLE" in roof else ""}
                </div>
                """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # TAB 6 — FUTURES
    # ═══════════════════════════════════════════════════════
    with tabs[6]:
        if not futures_file_id:
            st.markdown(alert_html("⚠️ FUTURES TRACKER NOT FOUND", "MLB_Futures_Tracker.xlsx not found in Drive folder."), unsafe_allow_html=True)
        else:
            try:
                raw_fut = download_bytes(futures_file_id)
                xl_fut = pd.ExcelFile(io.BytesIO(raw_fut))
                sheet_names = xl_fut.sheet_names
                sel_sheet = st.selectbox("Snapshot", sheet_names)
                df_fut = pd.read_excel(io.BytesIO(raw_fut), sheet_name=sel_sheet)
                if "WS %" in df_fut.columns:
                    df_fut_sorted = df_fut.sort_values("WS %", ascending=False).head(15)
                    st.markdown(section_title_html(f"🏆 WORLD SERIES ODDS — {sel_sheet}", "#ffab00"), unsafe_allow_html=True)
                    rows_f = ""
                    for _, row in df_fut_sorted.iterrows():
                        ws_pct = float(row.get("WS %", 0) or 0)
                        pl_pct = float(row.get("Playoff %", 0) or 0)
                        bar_w = int(ws_pct * 2)
                        rows_f += f"""<tr style="border-bottom:1px solid #1a1a2e20;">
<td style="padding:6px 10px; color:#fff; font-family:'Share Tech Mono',monospace;">{row.get('Team','—')}</td>
<td style="padding:6px 10px;"><div style="display:flex; align-items:center; gap:8px;"><div style="width:{bar_w}px; height:8px; background:#ffab00; border-radius:2px; min-width:2px;"></div><span style="color:#ffab00; font-family:'Orbitron',sans-serif; font-size:0.85em; font-weight:700;">{ws_pct:.0f}%</span></div></td>
<td style="padding:6px 10px; color:#888; font-family:'Share Tech Mono',monospace;">{row.get('Pennant %','—')}%</td>
<td style="padding:6px 10px; color:#888; font-family:'Share Tech Mono',monospace;">{row.get('Div %','—')}%</td>
<td style="padding:6px 10px; color:#888; font-family:'Share Tech Mono',monospace;">{"—" if not pl_pct else f"{pl_pct:.0f}%"}</td>
<td style="padding:6px 10px; color:#546e7a; font-family:'Share Tech Mono',monospace; font-size:0.8em;">${float(row.get('WS Vol ($)', 0) or 0):,.0f}</td>
</tr>"""
                    st.markdown(f"""<div style="overflow-x:auto; background:#12121f; border:1px solid #1a1a2e; border-radius:8px;">
<table style="width:100%; border-collapse:collapse; font-size:0.8em;">
<thead><tr style="background:#0d0d18;">
<th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">Team</th>
<th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">WS %</th>
<th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">Pennant</th>
<th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">Division</th>
<th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">Playoff</th>
<th style="padding:6px 10px; text-align:left; color:#888; font-weight:400; text-transform:uppercase; font-size:0.7em; font-family:'Share Tech Mono',monospace;">WS Volume</th>
</tr></thead>
<tbody>{rows_f}</tbody>
</table></div>""", unsafe_allow_html=True)
                else:
                    st.markdown(section_title_html(f"📊 {sel_sheet}", "#ffab00"), unsafe_allow_html=True)
                    st.dataframe(df_fut, use_container_width=True, height=400)
            except Exception as e:
                st.error(f"Futures load error: {e}")

    # ── FOOTER ──
    st.markdown(f"""
    <div style="text-align:center; margin-top:30px; padding-top:16px; border-top:1px solid #1a1a2e;
         font-size:0.7em; color:#546e7a; font-family:'Share Tech Mono',monospace;">
      MLB Flag Finder &nbsp;|&nbsp; Play Card &nbsp;|&nbsp; {today_str} {current_window}<br>
      Data: Google Drive / {DRIVE_FOLDER_NAME} &nbsp;|&nbsp; Outlook: {loaded_sheet or '—'} &nbsp;|&nbsp; Trade Flow: {tf_file or '—'}<br>
      For internal use only. Not financial advice.
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
