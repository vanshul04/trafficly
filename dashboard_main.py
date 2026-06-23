"""
Trafficly — Smart Traffic Enforcement Platform
Automated violation detection, ANPR, e-challan generation
Engineered by Vanshul Lalwani
"""

import os
import base64
import datetime
import cv2
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
import requests

from src.challan_pdf import create_official_pdf

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Trafficly — Smart Traffic Enforcement",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & PATHS
# ═══════════════════════════════════════════════════════════════════════════════
PROJECT_ROOT = r"C:\Users\Vansh\gridlock_hackathon"
ASSETS_DIR   = os.path.join(PROJECT_ROOT, "assets")
CROPS_DIR    = os.path.join(PROJECT_ROOT, "output", "crops")
CHALLANS_DIR = os.path.join(PROJECT_ROOT, "output", "challans")
os.makedirs(CROPS_DIR,    exist_ok=True)
os.makedirs(CHALLANS_DIR, exist_ok=True)

# Junction coordinates for real map markers
JUNCTION_COORDS = {
    "Hebbal Flyover Junction":  (13.0359, 77.5970),
    "Silk Board Junction":      (12.9176, 77.6229),
    "MG Road Intersection":     (12.9716, 77.6099),
    "Marathahalli Bridge":      (12.9563, 77.7010),
    "Whitefield Main Road":     (12.9698, 77.7499),
    "KR Puram Bridge":          (13.0035, 77.6950),
}
DEFAULT_COORDS = (12.9716, 77.5946)  # Bengaluru city centre


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE UTILITY
# ═══════════════════════════════════════════════════════════════════════════════
def img_b64(path: str) -> str:
    if not os.path.exists(path):
        return ""
    ext  = os.path.splitext(path)[1].lstrip(".").lower()
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    try:
        with open(path, "rb") as fh:
            return f"data:image/{mime};base64,{base64.b64encode(fh.read()).decode()}"
    except Exception:
        return ""


_hero_uri  = img_b64(os.path.join(ASSETS_DIR, "traffic_hero.jpg"))
_cctv_uri  = img_b64(os.path.join(ASSETS_DIR, "cctv_card.jpg"))
_badge_uri = img_b64(os.path.join(ASSETS_DIR, "badge.jpg"))
_helm_uri  = img_b64(os.path.join(ASSETS_DIR, "helmet_scene.jpg"))
_dev_uri   = img_b64(os.path.join(ASSETS_DIR, "dev_bg.jpg"))


# ═══════════════════════════════════════════════════════════════════════════════
# CSS — DESIGN SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700;14..32,800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg0:    #070809;
  --bg1:    #0D1117;
  --bg2:    #161C26;
  --bg3:    #1C2333;
  --bg4:    #242D3E;

  --border0: rgba(255,255,255,0.04);
  --border1: rgba(255,255,255,0.08);
  --border2: rgba(255,255,255,0.14);
  --border3: rgba(255,255,255,0.22);

  --tx0: #F0F4FA;
  --tx1: #8C98AC;
  --tx2: #4E5A6B;
  --tx3: #2E3847;

  --red:    #FF3D3D;
  --red-bg: rgba(255,61,61,0.08);
  --red-bd: rgba(255,61,61,0.20);
  --green:    #00D47E;
  --green-bg: rgba(0,212,126,0.08);
  --amber:    #F5A623;
  --amber-bg: rgba(245,166,35,0.08);
  --blue:     #3B82F6;
  --blue-bg:  rgba(59,130,246,0.08);
  --violet:   #8B5CF6;
  --violet-bg: rgba(139,92,246,0.08);

  --r-sm: 6px;
  --r-md: 10px;
  --r-lg: 16px;
  --r-xl: 22px;

  --ease: cubic-bezier(0.4,0,0.2,1);
  --t1: 0.12s;
  --t2: 0.22s;
  --t3: 0.38s;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, .stApp {
  background: var(--bg0) !important;
  color: var(--tx0) !important;
  font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
.stDeployButton,
section[data-testid="stSidebar"] { display:none!important; visibility:hidden!important; }

.block-container { padding: 0!important; max-width: 100%!important; }

/* ── Topbar ── */
.nav {
  position: sticky; top: 0; z-index: 999;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 32px; height: 54px;
  background: rgba(7,8,9,0.85);
  border-bottom: 1px solid var(--border0);
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
}
.nav-left  { display:flex; align-items:center; gap:16px; }
.nav-right { display:flex; align-items:center; gap:12px; }
.nav-logo  {
  width:30px; height:30px; border-radius:7px;
  overflow:hidden; flex-shrink:0; background:var(--bg2);
}
.nav-logo img { width:100%; height:100%; object-fit:cover; }
.nav-brand {
  font-size:15px; font-weight:700; color:var(--tx0);
  letter-spacing:-0.4px;
}
.nav-sep {
  width:1px; height:18px; background:var(--border1); margin:0 2px;
}
.nav-sub {
  font-size:11px; color:var(--tx2); font-weight:400;
}
.chip {
  display:inline-flex; align-items:center; gap:5px;
  padding:4px 10px;
  background:var(--bg1); border:1px solid var(--border0);
  border-radius:999px;
  font-size:11px; color:var(--tx1); font-weight:500;
  white-space:nowrap;
}
.live-pill {
  display:inline-flex; align-items:center; gap:5px;
  padding:4px 12px;
  background:var(--green-bg); border:1px solid rgba(0,212,126,0.22);
  border-radius:999px;
  font-size:10px; color:var(--green); font-weight:700; letter-spacing:0.6px;
  text-transform:uppercase;
}
.preview-pill {
  display:inline-flex; align-items:center; gap:5px;
  padding:4px 12px;
  background:var(--amber-bg); border:1px solid rgba(245,166,35,0.22);
  border-radius:999px;
  font-size:10px; color:var(--amber); font-weight:700; letter-spacing:0.6px;
  text-transform:uppercase;
}
.pulse-dot {
  width:5px; height:5px; border-radius:50%; background:currentColor;
  animation: blink 2.2s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.35} }

/* ── Hero ── */
.hero {
  position:relative; height:360px; overflow:hidden;
  background: var(--bg1);
}
.hero-img {
  position:absolute; inset:0;
  width:100%; height:100%;
  object-fit:cover; object-position:center 45%;
  filter: brightness(0.38) saturate(0.75);
  transition: transform 10s ease;
}
.hero-grad-bottom {
  position:absolute; inset:0;
  background: linear-gradient(180deg, transparent 30%, var(--bg0) 100%);
}
.hero-grad-left {
  position:absolute; inset:0;
  background: linear-gradient(90deg, rgba(7,8,9,0.85) 0%, transparent 65%);
}
.hero-body {
  position:relative; z-index:2;
  height:100%; display:flex; flex-direction:column; justify-content:flex-end;
  padding:40px 40px; max-width:700px;
}
.hero-tag {
  display:inline-flex; align-items:center; gap:7px;
  padding:4px 11px;
  background:rgba(255,61,61,0.10); border:1px solid rgba(255,61,61,0.24);
  border-radius:999px;
  font-size:10px; font-weight:700; color:#FF6E6E;
  letter-spacing:1.2px; text-transform:uppercase;
  margin-bottom:14px; width:fit-content;
}
.hero-h1 {
  font-size:40px; font-weight:800; color:#fff;
  letter-spacing:-1.8px; line-height:1.08; margin-bottom:12px;
}
.hero-h1 em { color:var(--red); font-style:normal; }
.hero-desc {
  font-size:13px; color:rgba(255,255,255,0.48);
  line-height:1.75; max-width:520px; font-weight:400;
}
.hero-kpis {
  position:absolute; right:40px; bottom:40px; z-index:2;
  display:flex; flex-direction:column; gap:8px; align-items:flex-end;
}
.hero-kpi {
  display:flex; align-items:center; gap:12px;
  padding:10px 18px;
  background:rgba(7,8,9,0.6); border:1px solid rgba(255,255,255,0.07);
  border-radius:var(--r-md);
  backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
}
.hero-kpi-n {
  font-size:22px; font-weight:800; color:#fff;
  letter-spacing:-0.8px; font-variant-numeric:tabular-nums; line-height:1;
}
.hero-kpi-l {
  font-size:10px; color:rgba(255,255,255,0.38);
  text-transform:uppercase; letter-spacing:0.5px; margin-top:2px;
  font-weight:600;
}

/* ── KPI Strip ── */
.kpis {
  display:grid; grid-template-columns:repeat(4,1fr);
  background:var(--bg1); border-bottom:1px solid var(--border0);
}
.kpi {
  padding:22px 28px; border-right:1px solid var(--border0);
  position:relative; overflow:hidden;
}
.kpi:last-child { border-right:none; }
.kpi::after {
  content:''; position:absolute; top:0; left:0; right:0; height:2px;
}
.kpi.r::after { background:var(--red); }
.kpi.g::after { background:var(--green); }
.kpi.a::after { background:var(--amber); }
.kpi.b::after { background:var(--blue); }
.kpi-lbl {
  font-size:9px; font-weight:700; color:var(--tx2);
  text-transform:uppercase; letter-spacing:1.1px; margin-bottom:8px;
}
.kpi-n {
  font-size:34px; font-weight:800; letter-spacing:-1.8px;
  color:var(--tx0); font-variant-numeric:tabular-nums;
  line-height:1; margin-bottom:6px;
}
.kpi-n.r { color:var(--red); }
.kpi-n.g { color:var(--green); }
.kpi-n.a { color:var(--amber); }
.kpi-sub { font-size:11px; color:var(--tx2); font-weight:500; }

/* ── Content wrapper ── */
.wrap { padding:28px 32px 52px; }

/* ── Section label ── */
.slabel {
  font-size:9px; font-weight:700; color:var(--tx2);
  text-transform:uppercase; letter-spacing:1.3px;
  padding-bottom:10px; margin-bottom:14px;
  border-bottom:1px solid var(--border0);
}

/* ── Card ── */
.card {
  background:var(--bg1); border:1px solid var(--border0);
  border-radius:var(--r-lg); overflow:hidden;
  transition:border-color var(--t1) var(--ease);
}
.card:hover { border-color:var(--border1); }

/* ── Stream wrapper ── */
.stream-card {
  background:var(--bg1); border:1px solid var(--border0);
  border-radius:var(--r-lg); overflow:hidden; margin-bottom:22px;
}
.stream-hdr {
  display:flex; align-items:center; justify-content:space-between;
  padding:11px 18px; border-bottom:1px solid var(--border0);
}
.stream-title { font-size:12px; font-weight:600; color:var(--tx1); }
.stream-meta  { font-family:'JetBrains Mono',monospace; font-size:10px; color:var(--tx2); }
.stream-offline {
  height:260px; display:flex; flex-direction:column;
  align-items:center; justify-content:center; gap:10px;
  background: repeating-linear-gradient(
    45deg, var(--bg1), var(--bg1) 8px, var(--bg2) 8px, var(--bg2) 16px
  );
}

/* ── Table row ── */
.trow-plate {
  font-family:'JetBrains Mono',monospace;
  font-size:13px; font-weight:600; color:var(--tx0); letter-spacing:0.5px;
}
.trow-meta { font-size:11px; color:var(--tx2); font-weight:500; margin-top:2px; }

/* ── Badge ── */
.badge-r {
  display:inline-block; padding:2px 9px;
  background:var(--red-bg); border:1px solid var(--red-bd);
  border-radius:4px; font-size:9px; font-weight:700;
  color:var(--red); text-transform:uppercase; letter-spacing:0.7px;
}
.badge-g {
  display:inline-block; padding:2px 9px;
  background:var(--green-bg); border:1px solid rgba(0,212,126,0.25);
  border-radius:4px; font-size:9px; font-weight:700;
  color:var(--green); text-transform:uppercase; letter-spacing:0.7px;
}
.badge-a {
  display:inline-block; padding:2px 9px;
  background:var(--amber-bg); border:1px solid rgba(245,166,35,0.25);
  border-radius:4px; font-size:9px; font-weight:700;
  color:var(--amber); text-transform:uppercase; letter-spacing:0.7px;
}
.badge-b {
  display:inline-block; padding:2px 9px;
  background:var(--blue-bg); border:1px solid rgba(59,130,246,0.25);
  border-radius:4px; font-size:9px; font-weight:700;
  color:var(--blue); text-transform:uppercase; letter-spacing:0.7px;
}

/* ── Spotlight ── */
.spotlight {
  background:var(--bg1); border:1px solid var(--border0);
  border-radius:var(--r-lg); overflow:hidden; margin-bottom:14px;
}
.spotlight img.scene {
  width:100%; height:130px; object-fit:cover;
  filter:brightness(0.55); display:block;
}
.spotlight-body { padding:15px 18px; }
.spotlight-plate {
  font-family:'JetBrains Mono',monospace;
  font-size:18px; font-weight:700; color:var(--tx0);
  letter-spacing:1px; margin:8px 0 4px;
}
.spotlight-row {
  display:flex; align-items:center; justify-content:space-between;
  font-size:11px; color:var(--tx2); margin-top:5px;
}

/* ── Map container ── */
.map-wrap {
  background:var(--bg1); border:1px solid var(--border0);
  border-radius:var(--r-lg); overflow:hidden; margin-bottom:14px;
}
.map-hdr {
  display:flex; align-items:center; justify-content:space-between;
  padding:11px 18px; border-bottom:1px solid var(--border0);
}

/* ── Stat row ── */
.stat-row { display:flex; gap:10px; margin-bottom:14px; }
.stat-item {
  flex:1; background:var(--bg1); border:1px solid var(--border0);
  border-radius:var(--r-md); padding:13px 16px; text-align:center;
}
.stat-n {
  font-size:24px; font-weight:800; color:var(--tx0);
  letter-spacing:-0.8px; font-variant-numeric:tabular-nums;
}
.stat-n.r { color:var(--red); }
.stat-n.g { color:var(--green); }
.stat-l  { font-size:9px; color:var(--tx2); font-weight:700; text-transform:uppercase; letter-spacing:0.6px; margin-top:3px; }

/* ── Developer card ── */
.dev-hero {
  position:relative; border-radius:var(--r-xl);
  overflow:hidden; margin-bottom:24px;
}
.dev-hero-img {
  width:100%; height:220px; object-fit:cover;
  filter:brightness(0.4) saturate(0.6);
  display:block;
}
.dev-hero-overlay {
  position:absolute; inset:0;
  background:linear-gradient(135deg, rgba(7,8,9,0.75) 0%, transparent 80%);
  display:flex; flex-direction:column; justify-content:flex-end;
  padding:28px 32px;
}
.dev-name {
  font-size:28px; font-weight:800; color:#fff;
  letter-spacing:-1px; margin-bottom:4px;
}
.dev-role { font-size:13px; color:rgba(255,255,255,0.5); font-weight:500; }
.dev-card {
  background:var(--bg1); border:1px solid var(--border0);
  border-radius:var(--r-lg); padding:24px 28px; margin-bottom:16px;
}
.dev-section-title {
  font-size:9px; font-weight:700; color:var(--tx2);
  text-transform:uppercase; letter-spacing:1.2px; margin-bottom:14px;
  padding-bottom:8px; border-bottom:1px solid var(--border0);
}
.dev-link {
  display:flex; align-items:center; gap:14px;
  padding:12px 16px;
  background:var(--bg2); border:1px solid var(--border0);
  border-radius:var(--r-md); text-decoration:none;
  transition:border-color var(--t1) var(--ease), background var(--t1) var(--ease);
  margin-bottom:10px;
}
.dev-link:hover { background:var(--bg3); border-color:var(--border2); }
.dev-link-icon {
  width:36px; height:36px; border-radius:8px;
  background:var(--bg3); display:flex; align-items:center;
  justify-content:center; flex-shrink:0;
}
.dev-link-label { font-size:11px; color:var(--tx2); font-weight:500; margin-bottom:2px; }
.dev-link-val { font-size:13px; font-weight:600; color:var(--tx0); }
.tech-pill {
  display:inline-block; padding:4px 12px;
  background:var(--bg2); border:1px solid var(--border0);
  border-radius:999px; font-size:11px; font-weight:500; color:var(--tx1);
  margin:4px; transition:border-color var(--t1) var(--ease);
}
.tech-pill:hover { border-color:var(--border2); }

/* ── Streamlit overrides ── */
[data-testid="stTabs"] button[role="tab"] {
  background:none!important; color:var(--tx2)!important;
  font-size:13px!important; font-weight:600!important;
  padding:11px 22px!important; border:none!important;
  border-bottom:2px solid transparent!important;
  font-family:'Inter',sans-serif!important;
  transition:color var(--t1) var(--ease)!important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  color:var(--tx0)!important;
  border-bottom:2px solid var(--tx0)!important;
  background:none!important;
}
[data-testid="stTabs"] div[role="tablist"] {
  border-bottom:1px solid var(--border0)!important;
  margin-bottom:26px!important; padding:0!important; gap:0!important;
}
[data-testid="stTabs"] div[data-testid="stTabContent"] { padding:0!important; }

[data-testid="stTextInput"] input {
  background:var(--bg1)!important; border:1px solid var(--border1)!important;
  color:var(--tx0)!important; border-radius:var(--r-md)!important;
  font-family:'JetBrains Mono',monospace!important;
  font-size:13px!important; padding:10px 14px!important; height:42px!important;
  transition:border-color var(--t1) var(--ease)!important;
}
[data-testid="stTextInput"] input:focus {
  border-color:var(--border3)!important;
  box-shadow:0 0 0 3px rgba(255,255,255,0.03)!important; outline:none!important;
}
[data-testid="stTextInput"] input::placeholder { color:var(--tx2)!important; }
[data-testid="stTextInput"] label {
  color:var(--tx2)!important; font-size:9px!important; font-weight:700!important;
  text-transform:uppercase!important; letter-spacing:1.1px!important;
  font-family:'Inter',sans-serif!important;
}

[data-testid="stSelectbox"] > div > div {
  background:var(--bg1)!important; border:1px solid var(--border1)!important;
  color:var(--tx0)!important; border-radius:var(--r-md)!important;
  font-family:'Inter',sans-serif!important; font-size:13px!important; min-height:42px!important;
}
[data-testid="stSelectbox"] label {
  color:var(--tx2)!important; font-size:9px!important; font-weight:700!important;
  text-transform:uppercase!important; letter-spacing:1.1px!important;
}

div.stDownloadButton > button {
  background:var(--bg2)!important; color:var(--tx1)!important;
  border:1px solid var(--border1)!important; border-radius:var(--r-sm)!important;
  font-size:11px!important; font-weight:600!important; padding:6px 14px!important;
  font-family:'Inter',sans-serif!important; width:100%!important;
  transition:all var(--t1) var(--ease)!important;
}
div.stDownloadButton > button:hover {
  background:var(--bg3)!important; color:var(--tx0)!important;
  border-color:var(--border2)!important;
  transform:translateY(-1px)!important;
  box-shadow:0 4px 14px rgba(0,0,0,0.35)!important;
}
div.stDownloadButton > button:active { transform:translateY(0)!important; }

[data-testid="stImage"] img { border-radius:var(--r-md)!important; display:block; }
[data-testid="stAlert"] {
  background:var(--bg1)!important; border:1px solid var(--border0)!important;
  border-radius:var(--r-md)!important; color:var(--tx1)!important;
}

::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-track { background:var(--bg0); }
::-webkit-scrollbar-thumb { background:var(--border1); border-radius:2px; }
::-webkit-scrollbar-thumb:hover { background:var(--border2); }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def make_plate_crop(plate: str, track_id: int, out: str) -> None:
    img = np.full((80, 280, 3), 15, dtype=np.uint8)
    cv2.rectangle(img, (0, 0), (279, 79), (32, 36, 46), 1)
    cv2.rectangle(img, (2, 2), (33, 77), (18, 35, 110), -1)
    cv2.putText(img, "IND", (4, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (190, 200, 255), 1, cv2.LINE_AA)
    txt = plate if plate != "UNKNOWN" else f"TRF-{track_id:05d}"
    cv2.putText(img, txt, (42, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (230, 235, 245), 2, cv2.LINE_AA)
    cv2.rectangle(img, (0, 0), (279, 79), (50, 56, 70), 1)
    cv2.imwrite(out, img)


def get_pdf(row) -> tuple:
    fname = f"Notice_{row['track_id']}.pdf"
    data  = None
    url   = row.get("pdf_url", "")
    if isinstance(url, str) and url:
        bn = os.path.basename(url)
        bp = os.path.join(CHALLANS_DIR, bn)
        if os.path.exists(bp):
            fname = bn
            try:    data = open(bp, "rb").read()
            except: pass
    if data is None:
        pp = os.path.join(CHALLANS_DIR, fname)
        try:
            create_official_pdf(
                vehicle_no=row["license_plate"],
                violation_reason=row["violation_type"],
                track_id=row["track_id"],
                location=row.get("location", ""),
                output_path=pp,
            )
            data = open(pp, "rb").read()
        except Exception as e:
            data = f"PDF error: {e}".encode()
    return data, fname


def violation_badge(vtype: str) -> str:
    vtype_l = vtype.lower()
    if "helmet" in vtype_l:   return f'<span class="badge-r">{vtype}</span>'
    if "signal" in vtype_l:   return f'<span class="badge-a">{vtype}</span>'
    if "speed"  in vtype_l:   return f'<span class="badge-b">{vtype}</span>'
    return f'<span class="badge-a">{vtype}</span>'


def status_badge(status: str) -> str:
    return '<span class="badge-g">PAID</span>' if status.upper() == "PAID" \
        else '<span class="badge-r">UNPAID</span>'


def make_leaflet_map(df: pd.DataFrame, height: int = 520) -> str:
    """Build a dark-themed Leaflet map with violation markers."""
    markers_js = ""
    for _, row in df.iterrows():
        loc    = row.get("location", "")
        coords = JUNCTION_COORDS.get(loc, DEFAULT_COORDS)
        plate  = str(row["license_plate"]).replace("'", "\\'")
        vtype  = str(row["violation_type"]).replace("'", "\\'")
        ts     = str(row["timestamp"])[:16]
        status = str(row.get("status","UNPAID")).upper()
        color  = "#FF3D3D" if status == "UNPAID" else "#00D47E"
        markers_js += f"""
        L.circleMarker([{coords[0]}, {coords[1]}], {{
            radius: 9,
            fillColor: '{color}',
            color: '{color}',
            weight: 1.5,
            opacity: 0.9,
            fillOpacity: 0.55
        }}).addTo(map).bindPopup(
            '<div style="font-family:monospace;font-size:12px;line-height:1.6;min-width:180px;">' +
            '<strong style="font-size:14px;">{plate}</strong><br/>' +
            '<span style="color:#888;">{vtype}</span><br/>' +
            '<span style="color:#888;">{ts}</span><br/>' +
            '<span style="font-size:10px;color:{color};font-weight:700;">{status}</span>' +
            '</div>',
            {{ maxWidth: 220 }}
        );
        """

    # Zone markers for all junctions
    for name, (lat, lng) in JUNCTION_COORDS.items():
        jname = name.replace("'", "\\'")
        markers_js += f"""
        L.marker([{lat}, {lng}], {{
            icon: L.divIcon({{
                html: '<div style="width:10px;height:10px;border-radius:50%;background:#3B82F6;border:2px solid rgba(59,130,246,0.4);box-shadow:0 0 8px rgba(59,130,246,0.5);"></div>',
                iconSize:[10,10], iconAnchor:[5,5]
            }})
        }}).addTo(map).bindTooltip('{jname}', {{
            direction:'top', permanent:false,
            className:'map-tooltip'
        }});
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <style>
        body, html {{ margin:0; padding:0; background:#070809; }}
        #map {{ width:100%; height:{height}px; }}
        .leaflet-popup-content-wrapper {{
          background:#0D1117; color:#F0F4FA;
          border:1px solid rgba(255,255,255,0.08);
          border-radius:8px;
          box-shadow:0 8px 32px rgba(0,0,0,0.6);
        }}
        .leaflet-popup-tip {{ background:#0D1117; }}
        .leaflet-popup-close-button {{ color:#8C98AC!important; }}
        .leaflet-control-zoom a {{
          background:#0D1117!important; color:#8C98AC!important;
          border:1px solid rgba(255,255,255,0.08)!important;
        }}
        .leaflet-control-zoom a:hover {{ background:#161C26!important; color:#F0F4FA!important; }}
        .leaflet-control-attribution {{ background:rgba(7,8,9,0.75)!important; color:#4E5A6B!important; font-size:9px!important; }}
        .leaflet-control-attribution a {{ color:#4E5A6B!important; }}
        .map-tooltip {{
          background:#0D1117; border:1px solid rgba(255,255,255,0.08);
          border-radius:5px; color:#8C98AC; font-family:Inter,sans-serif;
          font-size:11px; font-weight:600; padding:4px 10px;
          box-shadow:0 4px 16px rgba(0,0,0,0.5);
        }}
        .map-tooltip::before {{ border-top-color:#0D1117!important; }}
      </style>
    </head>
    <body>
    <div id="map"></div>
    <script>
      var map = L.map('map', {{
        center: [12.9716, 77.5946],
        zoom: 12,
        zoomControl: true,
        attributionControl: true
      }});

      L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
        attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
      }}).addTo(map);

      {markers_js}
    </script>
    </body>
    </html>
    """


# ═══════════════════════════════════════════════════════════════════════════════
# SEED DATA
# ═══════════════════════════════════════════════════════════════════════════════
_MOCK = [
    {"timestamp":"2026-06-23 09:14:22","track_id":101,"license_plate":"KA-03-MH-2234","violation_type":"No Helmet",    "fine_amount":500,"location":"Hebbal Flyover Junction","status":"UNPAID"},
    {"timestamp":"2026-06-23 09:58:40","track_id":103,"license_plate":"KA-19-N-5598", "violation_type":"Signal Jump",  "fine_amount":1000,"location":"MG Road Intersection",   "status":"UNPAID"},
    {"timestamp":"2026-06-23 10:22:05","track_id":105,"license_plate":"KA-51-EF-8890","violation_type":"No Helmet",    "fine_amount":500,"location":"Hebbal Flyover Junction","status":"UNPAID"},
    {"timestamp":"2026-06-23 11:05:40","track_id":108,"license_plate":"KA-01-AB-1234","violation_type":"No Helmet",    "fine_amount":500,"location":"Silk Board Junction",    "status":"PAID"},
    {"timestamp":"2026-06-23 11:43:10","track_id":110,"license_plate":"MH-12-AJ-7731","violation_type":"Over Speeding","fine_amount":2000,"location":"Marathahalli Bridge",   "status":"UNPAID"},
    {"timestamp":"2026-06-23 12:40:15","track_id":112,"license_plate":"KA-04-PK-4567","violation_type":"No Helmet",    "fine_amount":500,"location":"Hebbal Flyover Junction","status":"UNPAID"},
    {"timestamp":"2026-06-23 14:15:30","track_id":115,"license_plate":"UNKNOWN",      "violation_type":"No Helmet",    "fine_amount":500,"location":"MG Road Intersection",   "status":"UNPAID"},
    {"timestamp":"2026-06-23 14:32:00","track_id":118,"license_plate":"MH-12-Q-4455", "violation_type":"Signal Jump",  "fine_amount":1000,"location":"Hebbal Flyover Junction","status":"UNPAID"},
    {"timestamp":"2026-06-23 15:08:11","track_id":122,"license_plate":"KA-09-N-7812", "violation_type":"No Helmet",    "fine_amount":500,"location":"Silk Board Junction",    "status":"PAID"},
    {"timestamp":"2026-06-23 16:47:30","track_id":130,"license_plate":"KA-02-AC-0093","violation_type":"No Helmet",    "fine_amount":500,"location":"Marathahalli Bridge",    "status":"UNPAID"},
]

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(_MOCK)


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE API POLL
# ═══════════════════════════════════════════════════════════════════════════════
compliance_rate = 82.5
total_scanned   = 0
live_active     = False
junction_name   = "Bengaluru Traffic Network"
camera_id       = "CAM-TRF-01"

try:
    r = requests.get("http://127.0.0.1:8000/api/stats", timeout=1.2)
    if r.status_code == 200:
        s               = r.json()
        compliance_rate = round(float(s.get("compliance_rate", compliance_rate)), 1)
        total_scanned   = int(s.get("total_vehicles", 0))
        live_active     = s.get("status") == "ONLINE"
        junction_name   = s.get("junction_name", junction_name)
        camera_id       = s.get("camera_id", camera_id)

        ch = requests.get("http://127.0.0.1:8000/api/challans", timeout=1.2)
        if ch.status_code == 200:
            live = ch.json()
            if live:
                mapped = [{
                    "timestamp":      v["timestamp"],
                    "track_id":       v["track_id"],
                    "license_plate":  v["license_plate"],
                    "violation_type": v["violation_type"],
                    "fine_amount":    int(v.get("fine_amount", 500)),
                    "location":       junction_name,
                    "pdf_url":        v.get("pdf_url", ""),
                    "status":         v.get("status", "UNPAID"),
                } for v in live]
                combined = pd.concat(
                    [pd.DataFrame(mapped), pd.DataFrame(_MOCK)]
                ).drop_duplicates(subset=["track_id", "violation_type"], keep="first")
                st.session_state.df = combined.reset_index(drop=True)
except Exception:
    pass

df = st.session_state.df
if total_scanned == 0:
    total_scanned = max(len(df) * 6, 64)

# Ensure crops exist
for _, row in df.iterrows():
    cp = os.path.join(CROPS_DIR, f"track_{row['track_id']}_No_Helmet.jpg")
    if not os.path.exists(cp):
        make_plate_crop(row["license_plate"], row["track_id"], cp)

# Derived
total_v   = len(df)
paid_n    = int((df["status"].str.upper() == "PAID").sum()) if "status" in df.columns else 0
unpaid_n  = total_v - paid_n
fine_due  = int(df.loc[df.get("status", pd.Series(["UNPAID"]*total_v)).str.upper() != "PAID", "fine_amount"].sum()) if "status" in df.columns else total_v * 500
now_str   = datetime.datetime.now().strftime("%d %b %Y  %H:%M")
comp_cls  = "g" if compliance_rate >= 85 else "a"


# ═══════════════════════════════════════════════════════════════════════════════
# TOPBAR
# ═══════════════════════════════════════════════════════════════════════════════
logo_html = f'<img src="{_badge_uri}" style="width:100%;height:100%;object-fit:cover;"/>' if _badge_uri else ""
pill_cls  = "live-pill"    if live_active else "preview-pill"
pill_txt  = "LIVE"         if live_active else "PREVIEW"

st.markdown(f"""
<div class="nav">
  <div class="nav-left">
    <div class="nav-logo">{logo_html}</div>
    <span class="nav-brand">Trafficly</span>
    <div class="nav-sep"></div>
    <span class="nav-sub">Smart Traffic Enforcement Platform</span>
    <div class="chip">
      <svg width="9" height="9" viewBox="0 0 12 12" fill="none">
        <circle cx="6" cy="6" r="5" stroke="#4E5A6B" stroke-width="1.5"/>
        <path d="M6 3v3l2 1.5" stroke="#4E5A6B" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      {now_str}
    </div>
  </div>
  <div class="nav-right">
    <div class="chip">
      <svg width="9" height="9" viewBox="0 0 12 12" fill="none">
        <path d="M6 1C4.07 1 2.5 2.57 2.5 4.5c0 2.76 3.5 6.5 3.5 6.5s3.5-3.74 3.5-6.5C9.5 2.57 7.93 1 6 1z" stroke="#4E5A6B" stroke-width="1.3"/>
        <circle cx="6" cy="4.5" r="1.2" fill="#4E5A6B"/>
      </svg>
      Bengaluru, India
    </div>
    <div class="{pill_cls}">
      <span class="pulse-dot"></span>{pill_txt}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HERO
# ═══════════════════════════════════════════════════════════════════════════════
hero_img = f'<img class="hero-img" src="{_hero_uri}" alt="Traffic"/>' if _hero_uri else \
           '<div style="position:absolute;inset:0;background:var(--bg2);"></div>'

st.markdown(f"""
<div class="hero">
  {hero_img}
  <div class="hero-grad-bottom"></div>
  <div class="hero-grad-left"></div>
  <div class="hero-body">
    <div class="hero-tag">
      <svg width="6" height="6" viewBox="0 0 6 6"><circle cx="3" cy="3" r="3" fill="#FF3D3D"/></svg>
      Bengaluru Traffic Police · Automated Enforcement
    </div>
    <div class="hero-h1">Smart <em>Traffic</em><br/>Enforcement System</div>
    <div class="hero-desc">
      Multi-class violation detection using YOLOv8 computer vision and ANPR plate recognition. 
      Covers helmet violations, signal jumps, over-speeding, and more — with automated 
      e-challan generation and UPI payment integration.
    </div>
  </div>
  <div class="hero-kpis">
    <div class="hero-kpi">
      <div>
        <div class="hero-kpi-n">{total_scanned:,}</div>
        <div class="hero-kpi-l">Vehicles Monitored</div>
      </div>
    </div>
    <div class="hero-kpi">
      <div>
        <div class="hero-kpi-n" style="color:var(--red);">{total_v}</div>
        <div class="hero-kpi-l">Violations Logged</div>
      </div>
    </div>
    <div class="hero-kpi">
      <div>
        <div class="hero-kpi-n" style="color:{'var(--green)' if compliance_rate>=85 else 'var(--amber)'};">{compliance_rate}%</div>
        <div class="hero-kpi-l">Compliance Rate</div>
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# KPI STRIP
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="kpis">
  <div class="kpi b">
    <div class="kpi-lbl">Total Vehicles Scanned</div>
    <div class="kpi-n">{total_scanned:,}</div>
    <div class="kpi-sub">All camera feeds · this session</div>
  </div>
  <div class="kpi r">
    <div class="kpi-lbl">Active Violations</div>
    <div class="kpi-n r">{total_v}</div>
    <div class="kpi-sub">{unpaid_n} unpaid · {paid_n} settled</div>
  </div>
  <div class="kpi a">
    <div class="kpi-lbl">Pending Fine Revenue</div>
    <div class="kpi-n a">&#8377;{fine_due:,}</div>
    <div class="kpi-sub">Across all violation types</div>
  </div>
  <div class="kpi {comp_cls}">
    <div class="kpi-lbl">Overall Compliance</div>
    <div class="kpi-n {comp_cls}">{compliance_rate}%</div>
    <div class="kpi-sub">Safety target &gt; 85% · {'On track' if compliance_rate >= 85 else 'Needs attention'}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="wrap">', unsafe_allow_html=True)

tab_live, tab_map, tab_archive, tab_dev = st.tabs([
    "Live Monitoring",
    "Violation Map",
    "Citation Archive",
    "About Developer",
])


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  TAB 1 — LIVE MONITORING                                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
with tab_live:
    col_l, col_r = st.columns([1.65, 1], gap="large")

    with col_l:
        # CCTV stream
        st.markdown('<div class="slabel">CCTV Inference Stream — YOLOv8 Multi-class Detection</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="stream-card">
          <div class="stream-hdr">
            <span class="stream-title">Live Camera Feed</span>
            <span class="stream-meta">MJPEG &nbsp;·&nbsp; 30 fps &nbsp;·&nbsp; YOLOv8s</span>
          </div>
        """, unsafe_allow_html=True)

        try:
            st.image("http://127.0.0.1:8000/api/stream", use_container_width=True, output_format="JPEG")
        except Exception:
            if _hero_uri:
                st.markdown(f"""
                <div style="position:relative;">
                  <img src="{_hero_uri}" style="width:100%;height:300px;object-fit:cover;
                    object-position:center;filter:brightness(0.4);display:block;"/>
                  <div style="position:absolute;inset:0;display:flex;flex-direction:column;
                    align-items:center;justify-content:center;gap:8px;">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
                      stroke="rgba(78,90,107,0.8)" stroke-width="1.5" stroke-linecap="round">
                      <path d="M23 7l-7 5 7 5V7z"/>
                      <rect x="1" y="5" width="15" height="14" rx="2"/>
                    </svg>
                    <span style="font-size:12px;color:#4E5A6B;font-weight:600;">
                      Backend stream unavailable — run: py main.py --web
                    </span>
                  </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="stream-offline"><span style="font-size:12px;color:var(--tx2);font-weight:600;">Stream offline</span></div>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # Infraction log
        st.markdown('<div class="slabel" style="margin-top:6px;">Infraction Log</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="display:grid;grid-template-columns:80px 1fr 1fr 90px 80px 80px;
          gap:12px;padding:7px 14px;background:var(--bg2);border:1px solid var(--border0);
          border-radius:var(--r-md) var(--r-md) 0 0;margin-bottom:2px;">
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Evidence</span>
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Plate / ID</span>
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Violation</span>
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Fine</span>
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Status</span>
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Challan</span>
        </div>
        """, unsafe_allow_html=True)

        for idx, row in df.iterrows():
            cp  = os.path.join(CROPS_DIR, f"track_{row['track_id']}_No_Helmet.jpg")
            pb, pf = get_pdf(row)
            rs  = str(row.get("status", "UNPAID")).upper()
            c1,c2,c3,c4,c5,c6 = st.columns([0.55, 1.1, 1.1, 0.6, 0.6, 0.6])
            with c1:
                if os.path.exists(cp): st.image(cp, use_container_width=True)
            with c2:
                st.markdown(f"""
                <div style="padding:5px 0;">
                  <div class="trow-plate">{row['license_plate']}</div>
                  <div class="trow-meta">#{row['track_id']} · {str(row['timestamp'])[:16]}</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div style="padding:5px 0;">{violation_badge(row["violation_type"])}</div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div style="padding:5px 0;font-size:13px;font-weight:700;color:var(--amber);">&#8377;{int(row.get("fine_amount",500))}</div>', unsafe_allow_html=True)
            with c5:
                st.markdown(f'<div style="padding:5px 0;">{status_badge(rs)}</div>', unsafe_allow_html=True)
            with c6:
                st.download_button("PDF", pb, pf, "application/pdf", key=f"dl_l_{idx}_{row['track_id']}")
            st.markdown('<div style="height:1px;background:var(--border0);margin:2px 0 6px;"></div>', unsafe_allow_html=True)

    with col_r:
        # Spotlight
        st.markdown('<div class="slabel">Latest Violation</div>', unsafe_allow_html=True)
        if not df.empty:
            lat  = df.iloc[0]
            cp   = os.path.join(CROPS_DIR, f"track_{lat['track_id']}_No_Helmet.jpg")
            pb_l, pf_l = get_pdf(lat)
            ls   = str(lat.get("status","UNPAID")).upper()

            scene = f'<img class="scene" src="{_helm_uri}" alt="Scene"/>' if _helm_uri else \
                    '<div style="height:130px;background:var(--bg2);"></div>'
            st.markdown(f"""
            <div class="spotlight">
              {scene}
              <div class="spotlight-body">
                {violation_badge(lat['violation_type'])}
                <div class="spotlight-plate">{lat['license_plate']}</div>
                <div class="spotlight-row">
                  <span>Track #{lat['track_id']}</span>
                  <span style="font-family:'JetBrains Mono',monospace;font-size:10px;">{str(lat['timestamp'])[:16]}</span>
                </div>
                <div style="margin-top:4px;font-size:11px;color:var(--tx2);">{lat.get('location','—')}</div>
                <div style="margin-top:8px;display:flex;align-items:center;justify-content:space-between;">
                  <span style="font-size:16px;font-weight:800;color:var(--amber);">&#8377;{int(lat.get('fine_amount',500))}</span>
                  {status_badge(ls)}
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if os.path.exists(cp):
                st.markdown('<div style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Plate Evidence</div>', unsafe_allow_html=True)
                st.image(cp, use_container_width=True)

            qr_url = lat.get("pdf_url","")
            if isinstance(qr_url, str) and qr_url:
                qr_p = os.path.join(CHALLANS_DIR, os.path.basename(qr_url).replace(".pdf","_qr.png"))
                if os.path.exists(qr_p):
                    st.markdown('<div style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:1px;margin:12px 0 8px;">UPI Payment QR</div>', unsafe_allow_html=True)
                    cq, _ = st.columns([1,1])
                    with cq: st.image(qr_p)

            st.markdown("<br/>", unsafe_allow_html=True)
            st.download_button(f"Download Challan — #{lat['track_id']}", pb_l, pf_l, "application/pdf", key="dl_spot")

        # Mini stats
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="stat-row">
          <div class="stat-item"><div class="stat-n r">{unpaid_n}</div><div class="stat-l">Unpaid</div></div>
          <div class="stat-item"><div class="stat-n g">{paid_n}</div><div class="stat-l">Settled</div></div>
          <div class="stat-item"><div class="stat-n">{total_v}</div><div class="stat-l">Total</div></div>
        </div>
        """, unsafe_allow_html=True)

        # Donut
        st.markdown('<div class="slabel">Compliance Breakdown</div>', unsafe_allow_html=True)
        compliant = max(0, total_scanned - total_v)
        fig = go.Figure(go.Pie(
            labels=["Compliant","Violation"],
            values=[compliant, total_v],
            hole=0.68,
            marker=dict(colors=["#00D47E","#FF3D3D"], line=dict(color="#070809",width=3)),
            textinfo="none",
            hovertemplate="%{label}: %{value}<extra></extra>",
        ))
        fig.add_annotation(text=f"<b>{compliance_rate}%</b>", x=0.5, y=0.56,
            font=dict(size=20,color="#F0F4FA",family="Inter"), showarrow=False)
        fig.add_annotation(text="compliant", x=0.5, y=0.39,
            font=dict(size=10,color="#4E5A6B",family="Inter"), showarrow=False)
        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=185,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=True,
            legend=dict(orientation="h",y=-0.06,x=0.5,xanchor="center",
                font=dict(size=10,color="#8C98AC",family="Inter"),bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, use_container_width=True, key="donut")

        # Violation type breakdown
        st.markdown('<div class="slabel">By Violation Type</div>', unsafe_allow_html=True)
        vtype_counts = df["violation_type"].value_counts().reset_index()
        vtype_counts.columns = ["type","count"]
        colors_map = {"No Helmet":"#FF3D3D","Signal Jump":"#F5A623","Over Speeding":"#3B82F6"}
        bar_colors = [colors_map.get(t,"#8B5CF6") for t in vtype_counts["type"]]
        fig2 = go.Figure(go.Bar(
            x=vtype_counts["count"], y=vtype_counts["type"],
            orientation="h",
            marker=dict(color=bar_colors, line=dict(width=0)),
            hovertemplate="%{y}: %{x}<extra></extra>",
        ))
        fig2.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=130,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickfont=dict(size=9,color="#4E5A6B",family="Inter"),showgrid=False,zeroline=False,fixedrange=True),
            yaxis=dict(tickfont=dict(size=10,color="#8C98AC",family="Inter"),showgrid=False,zeroline=False,fixedrange=True),
            bargap=0.3)
        st.plotly_chart(fig2, use_container_width=True, key="vtype_bar")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  TAB 2 — VIOLATION MAP                                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
with tab_map:
    mc1, mc2 = st.columns([1, 2.8], gap="large")

    with mc1:
        st.markdown('<div class="slabel">Map Controls</div>', unsafe_allow_html=True)
        map_vtype = st.selectbox("Filter Violation", ["All"] + sorted(df["violation_type"].unique().tolist()), key="map_vf")
        map_status = st.selectbox("Filter Status", ["All", "UNPAID", "PAID"], key="map_sf")

        map_df = df.copy()
        if map_vtype != "All":   map_df = map_df[map_df["violation_type"] == map_vtype]
        if map_status != "All":  map_df = map_df[map_df["status"].str.upper() == map_status]

        st.markdown(f"""
        <div style="margin-top:16px;background:var(--bg1);border:1px solid var(--border0);
          border-radius:var(--r-lg);padding:18px 20px;">
          <div class="slabel">Legend</div>
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
            <div style="width:10px;height:10px;border-radius:50%;background:#FF3D3D;flex-shrink:0;"></div>
            <span style="font-size:12px;color:var(--tx1);">Unpaid Violation</span>
          </div>
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
            <div style="width:10px;height:10px;border-radius:50%;background:#00D47E;flex-shrink:0;"></div>
            <span style="font-size:12px;color:var(--tx1);">Settled Violation</span>
          </div>
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:10px;height:10px;border-radius:50%;background:#3B82F6;flex-shrink:0;"></div>
            <span style="font-size:12px;color:var(--tx1);">Monitored Junction</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        _zone_rows = "".join(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:7px 0;border-bottom:1px solid var(--border0);">'
            f'<span style="font-size:11px;color:var(--tx1);font-weight:500;">{name}</span>'
            f'<span style="font-size:10px;color:var(--tx2);font-family:JetBrains Mono,monospace;">{lat:.3f}N</span>'
            f'</div>'
            for name, (lat, lng) in JUNCTION_COORDS.items()
        )
        st.markdown(f"""
        <div style="margin-top:12px;background:var(--bg1);border:1px solid var(--border0);
          border-radius:var(--r-lg);padding:18px 20px;">
          <div class="slabel">Active Zones</div>
          {_zone_rows}
        </div>
        """, unsafe_allow_html=True)

    with mc2:
        st.markdown('<div class="slabel">Live Violation Map — OpenStreetMap · CartoDB Dark</div>', unsafe_allow_html=True)
        map_html = make_leaflet_map(map_df, height=560)
        st.markdown('<div class="map-wrap">', unsafe_allow_html=True)
        components.html(map_html, height=560, scrolling=False)
        st.markdown("</div>", unsafe_allow_html=True)

        # Location summary table below map
        st.markdown("<br/>", unsafe_allow_html=True)
        if "location" in df.columns:
            loc_summary = df.groupby("location").agg(
                Violations=("track_id","count"),
                Unpaid=("status", lambda x: (x.str.upper() == "UNPAID").sum()),
                Revenue=("fine_amount","sum")
            ).reset_index().sort_values("Violations", ascending=False)

            st.markdown('<div class="slabel">Junction Summary</div>', unsafe_allow_html=True)
            st.markdown("""
            <div style="display:grid;grid-template-columns:1fr 80px 80px 100px;gap:12px;
              padding:7px 14px;background:var(--bg2);border:1px solid var(--border0);
              border-radius:var(--r-md) var(--r-md) 0 0;">
              <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Junction</span>
              <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Violations</span>
              <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Unpaid</span>
              <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Revenue</span>
            </div>
            """, unsafe_allow_html=True)
            for _, lr in loc_summary.iterrows():
                st.markdown(f"""
                <div style="display:grid;grid-template-columns:1fr 80px 80px 100px;gap:12px;
                  padding:10px 14px;background:var(--bg1);border:1px solid var(--border0);
                  border-top:none;">
                  <span style="font-size:12px;color:var(--tx0);font-weight:500;">{lr['location']}</span>
                  <span style="font-size:13px;color:var(--tx0);font-weight:700;font-variant-numeric:tabular-nums;">{int(lr['Violations'])}</span>
                  <span style="font-size:13px;color:var(--red);font-weight:700;">{int(lr['Unpaid'])}</span>
                  <span style="font-size:13px;color:var(--amber);font-weight:700;">&#8377;{int(lr['Revenue']):,}</span>
                </div>
                """, unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  TAB 3 — CITATION ARCHIVE                                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
with tab_archive:
    # Filters
    fa, fb, fc, fd = st.columns([2.5, 1, 1, 1], gap="medium")
    with fa: search_q   = st.text_input("Search registration plate", placeholder="KA-03-MH-2234")
    with fb: sf_status  = st.selectbox("Status",    ["All","UNPAID","PAID"])
    with fc: sf_vtype   = st.selectbox("Violation", ["All"] + sorted(df["violation_type"].unique().tolist()))
    with fd:
        locs = ["All"] + sorted(df["location"].dropna().unique().tolist()) if "location" in df.columns else ["All"]
        sf_loc = st.selectbox("Location", locs)

    filtered = df.copy()
    if search_q:
        q = search_q.strip().replace(" ","").upper()
        filtered = filtered[filtered["license_plate"].str.replace(" ","",regex=False).str.upper().str.contains(q, na=False)]
    if sf_status != "All" and "status" in filtered.columns:
        filtered = filtered[filtered["status"].str.upper() == sf_status]
    if sf_vtype != "All":
        filtered = filtered[filtered["violation_type"] == sf_vtype]
    if sf_loc != "All" and "location" in filtered.columns:
        filtered = filtered[filtered["location"] == sf_loc]

    f_unpaid = int((filtered.get("status",pd.Series(["UNPAID"]*len(filtered))).str.upper()=="UNPAID").sum()) if "status" in filtered.columns else len(filtered)
    f_revenue= int(filtered.loc[filtered.get("status",pd.Series(["UNPAID"]*len(filtered))).str.upper()!="PAID","fine_amount"].sum()) if "status" in filtered.columns else len(filtered)*500

    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;margin:12px 0 18px;">
      <span style="font-size:13px;color:var(--tx1);">
        <strong style="color:var(--tx0);">{len(filtered)}</strong> record{'s' if len(filtered)!=1 else ''} matched
      </span>
      <div style="display:flex;gap:20px;">
        <span style="font-size:12px;color:var(--tx2);">Unpaid: <strong style="color:var(--red);">{f_unpaid}</strong></span>
        <span style="font-size:12px;color:var(--tx2);">Outstanding: <strong style="color:var(--amber);">&#8377;{f_revenue:,}</strong></span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not filtered.empty:
        st.markdown("""
        <div style="display:grid;grid-template-columns:80px 1fr 1fr 90px 80px 80px 80px;
          gap:12px;padding:8px 14px;background:var(--bg2);border:1px solid var(--border0);
          border-radius:var(--r-md) var(--r-md) 0 0;">
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Evidence</span>
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Plate / Track</span>
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Location &amp; Time</span>
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Violation</span>
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Fine</span>
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Status</span>
          <span style="font-size:9px;font-weight:700;color:var(--tx2);text-transform:uppercase;letter-spacing:0.9px;">Challan</span>
        </div>
        """, unsafe_allow_html=True)

        for idx, row in filtered.reset_index(drop=True).iterrows():
            cp = os.path.join(CROPS_DIR, f"track_{row['track_id']}_No_Helmet.jpg")
            pb, pf = get_pdf(row)
            rs = str(row.get("status","UNPAID")).upper()
            c1,c2,c3,c4,c5,c6,c7 = st.columns([0.55,1.1,1.2,0.7,0.6,0.6,0.6])
            with c1:
                if os.path.exists(cp): st.image(cp, use_container_width=True)
            with c2:
                st.markdown(f"""
                <div style="padding:5px 0;">
                  <div class="trow-plate">{row['license_plate']}</div>
                  <div class="trow-meta">#{row['track_id']}</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div style="padding:5px 0;font-size:11px;color:var(--tx1);line-height:1.55;">
                  {row.get('location','—')}<br/>
                  <span style="color:var(--tx2);">{str(row['timestamp'])[:16]}</span>
                </div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div style="padding:5px 0;">{violation_badge(row["violation_type"])}</div>', unsafe_allow_html=True)
            with c5:
                st.markdown(f'<div style="padding:5px 0;font-size:13px;font-weight:700;color:var(--amber);">&#8377;{int(row.get("fine_amount",500))}</div>', unsafe_allow_html=True)
            with c6:
                st.markdown(f'<div style="padding:5px 0;">{status_badge(rs)}</div>', unsafe_allow_html=True)
            with c7:
                st.download_button("PDF", pb, pf, "application/pdf", key=f"dl_a_{idx}_{row['track_id']}")
            st.markdown('<div style="height:1px;background:var(--border0);margin:2px 0 6px;"></div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="padding:60px;text-align:center;background:var(--bg1);
          border:1px solid var(--border0);border-radius:var(--r-lg);">
          <div style="font-size:13px;color:var(--tx2);font-weight:500;margin-bottom:5px;">No records match your filters</div>
          <div style="font-size:11px;color:var(--tx3);">Try adjusting your search criteria.</div>
        </div>
        """, unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  TAB 4 — ABOUT DEVELOPER                                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
with tab_dev:
    d_left, d_right = st.columns([1.4, 1], gap="large")

    with d_left:
        # Hero card
        dev_img = f'<img class="dev-hero-img" src="{_dev_uri}" alt="bg"/>' if _dev_uri else \
                  '<div style="height:220px;background:var(--bg2);"></div>'
        st.markdown(f"""
        <div class="dev-hero">
          {dev_img}
          <div class="dev-hero-overlay">
            <div class="dev-name">Vanshul Lalwani</div>
            <div class="dev-role">Lead AI & Full-Stack MLOps Developer</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # About
        st.markdown("""
        <div class="dev-card">
          <div class="dev-section-title">About the Creator</div>
          <p style="font-size:13px;color:var(--tx1);line-height:1.8;font-weight:400;">
            This automated traffic enforcement dashboard and e-challan system was engineered 
            independently as a comprehensive technical solution for urban mobility and smart city 
            management. By combining state-of-the-art multi-object tracking computer vision 
            pipelines with a seamless financial payment layer, this architecture streamlines 
            automated violation tracking and penalty processing for law enforcement networks.
          </p>
          <p style="font-size:13px;color:var(--tx1);line-height:1.8;margin-top:12px;">
            The system is built to be extensible — helmet detection is the first module, 
            with signal jump detection, speed violation monitoring, and triple riding 
            detection planned as subsequent additions to the pipeline.
          </p>
        </div>
        """, unsafe_allow_html=True)

        # Tech stack
        st.markdown("""
        <div class="dev-card">
          <div class="dev-section-title">Technology Stack</div>
          <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;">
            <span class="tech-pill">YOLOv8s</span>
            <span class="tech-pill">Python 3.10</span>
            <span class="tech-pill">FastAPI</span>
            <span class="tech-pill">Streamlit</span>
            <span class="tech-pill">OpenCV</span>
            <span class="tech-pill">PyTorch</span>
            <span class="tech-pill">ANPR</span>
            <span class="tech-pill">ReportLab PDF</span>
            <span class="tech-pill">UPI QR</span>
            <span class="tech-pill">ByteTrack</span>
            <span class="tech-pill">MJPEG Stream</span>
            <span class="tech-pill">Leaflet.js</span>
            <span class="tech-pill">Plotly</span>
            <span class="tech-pill">Pandas</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with d_right:
        # Connect
        st.markdown("""
        <div class="dev-card">
          <div class="dev-section-title">Connect</div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <a class="dev-link" href="https://github.com/vanshul04" target="_blank">
          <div class="dev-link-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" fill="#8C98AC"/>
            </svg>
          </div>
          <div>
            <div class="dev-link-label">GitHub — Source Code</div>
            <div class="dev-link-val">github.com/vanshul04</div>
          </div>
        </a>
        <a class="dev-link" href="mailto:vanshullalwani43@gmail.com">
          <div class="dev-link-icon">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
              <rect x="2" y="4" width="20" height="16" rx="2.5" stroke="#8C98AC" stroke-width="1.5"/>
              <path d="M2 7l10 7 10-7" stroke="#8C98AC" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </div>
          <div>
            <div class="dev-link-label">Email — Official Inquiries</div>
            <div class="dev-link-val">vanshullalwani43@gmail.com</div>
          </div>
        </a>
        </div>
        """, unsafe_allow_html=True)

        # Project info
        st.markdown(f"""
        <div class="dev-card" style="margin-top:14px;">
          <div class="dev-section-title">Project Info</div>
          <div style="display:flex;flex-direction:column;gap:0;">
            <div style="display:flex;justify-content:space-between;align-items:center;
              padding:10px 0;border-bottom:1px solid var(--border0);">
              <span style="font-size:12px;color:var(--tx2);font-weight:500;">System Version</span>
              <span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--tx0);">v2.5.0</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;
              padding:10px 0;border-bottom:1px solid var(--border0);">
              <span style="font-size:12px;color:var(--tx2);font-weight:500;">Detection Model</span>
              <span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--tx0);">YOLOv8s · Custom</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;
              padding:10px 0;border-bottom:1px solid var(--border0);">
              <span style="font-size:12px;color:var(--tx2);font-weight:500;">Model Weights</span>
              <span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--tx0);">helmet_best.pt</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;
              padding:10px 0;border-bottom:1px solid var(--border0);">
              <span style="font-size:12px;color:var(--tx2);font-weight:500;">Backend</span>
              <span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--tx0);">FastAPI · port 8000</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;
              padding:10px 0;border-bottom:1px solid var(--border0);">
              <span style="font-size:12px;color:var(--tx2);font-weight:500;">Issued Today</span>
              <span style="font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--red);">{total_v} challans</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;">
              <span style="font-size:12px;color:var(--tx2);font-weight:500;">Enforcement Scope</span>
              <span style="font-size:12px;color:var(--tx0);">Bengaluru, Karnataka</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Legal footer
        st.markdown("""
        <div style="margin-top:14px;padding:16px 18px;background:var(--bg1);
          border:1px solid var(--border0);border-radius:var(--r-md);">
          <p style="font-size:10px;color:var(--tx2);line-height:1.7;font-weight:400;">
            This system is developed for law enforcement and smart city use cases.
            All violation data is processed in compliance with applicable data protection 
            guidelines. Challans issued are subject to review by the presiding traffic authority.
          </p>
          <p style="font-size:10px;color:var(--tx3);margin-top:8px;">
            &copy; 2026 Vanshul Lalwani · Trafficly Platform · All rights reserved
          </p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
