"""Global CSS. Injected once per run with st.markdown(<style>)."""
from __future__ import annotations

import streamlit as st

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root{
  --bg:#0a0f24; --bg2:#111a3a; --glass:rgba(255,255,255,.05); --glass2:rgba(255,255,255,.08);
  --line:rgba(255,255,255,.10); --teal:#2dd4bf; --violet:#a78bfa; --amber:#f5b544; --rose:#fb7185;
  --text:#e8ecff; --muted:#a3aed8; --radius:18px;
}

/* ---------- base + chrome ---------- */
html, body, .stApp, .stApp p, .stApp label, .stApp input, .stApp textarea,
.stApp button, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp li, .stApp td, .stApp th {
  font-family:'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
.stApp{
  background:
    radial-gradient(1100px 560px at 8% -8%, rgba(139,92,246,.20), transparent 60%),
    radial-gradient(900px 520px at 100% 0%, rgba(45,212,191,.15), transparent 55%),
    var(--bg);
  color:var(--text);
}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"]{display:none !important;}
header[data-testid="stHeader"]{background:transparent;}
.block-container{max-width:1240px; padding-top:2.2rem; padding-bottom:4rem;}
[data-testid="stSidebar"]{
  background:rgba(10,15,36,.88); border-right:1px solid var(--line); backdrop-filter:blur(18px);
}
[data-testid="stSidebar"] .block-container{padding-top:1.4rem;}
:focus-visible{outline:2px solid var(--teal) !important; outline-offset:2px;}

/* ---------- widgets ---------- */
.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button{
  border-radius:12px; font-weight:600; border:1px solid var(--line);
  transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease;
}
.stButton>button:hover, .stFormSubmitButton>button:hover, .stDownloadButton>button:hover{
  transform:translateY(-2px); border-color:rgba(45,212,191,.55); box-shadow:0 10px 26px rgba(45,212,191,.16);
}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"]{
  background:linear-gradient(135deg,#2dd4bf,#a78bfa) !important; color:#06101f !important; border:0 !important;
}
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"]>div{
  border-radius:12px !important; background:rgba(255,255,255,.04) !important;
}
[data-baseweb="tab-list"]{gap:6px;}
button[role="tab"]{border-radius:10px; padding:.45rem 1rem;}
button[role="tab"][aria-selected="true"]{background:rgba(45,212,191,.12);}
[data-baseweb="tab-highlight"]{background:var(--teal) !important;}
[data-testid="stExpander"]{border:1px solid var(--line); border-radius:14px; background:var(--glass);}
[data-testid="stStatus"]{border-radius:14px; border:1px solid var(--line); background:var(--glass);}

/* ---------- brand + hero ---------- */
.brand{display:flex; align-items:center; gap:.75rem; margin-bottom:1.1rem;}
.brand-mark{width:42px; height:42px; border-radius:13px; display:grid; place-items:center; font-size:22px;
  background:linear-gradient(135deg, rgba(45,212,191,.28), rgba(167,139,250,.30)); border:1px solid var(--line);}
.brand-name{font-weight:800; font-size:1.15rem; letter-spacing:-.01em;}
.brand-sub{font-size:.78rem; color:var(--muted);}
.vy-hero{margin:.2rem 0 1.4rem;}
.vy-title{font-size:clamp(2rem,4.2vw,3.3rem); line-height:1.08; font-weight:800; letter-spacing:-.03em; margin:0 0 .6rem;
  background:linear-gradient(100deg,#e8ecff 0%,#2dd4bf 45%,#a78bfa 100%); -webkit-background-clip:text;
  background-clip:text; -webkit-text-fill-color:transparent; color:transparent;}
.vy-sub{color:var(--muted); font-size:1.02rem; max-width:62ch; line-height:1.6; margin:0;}
.vy-compact .vy-title{font-size:1.7rem; margin-bottom:.25rem;}
.vy-compact{margin-bottom:1rem;}

/* ---------- cards ---------- */
.vy-card, [class*="st-key-glass_"], .st-key-final_card, .st-key-approval_panel{
  background:var(--glass); border:1px solid var(--line); border-radius:var(--radius);
  backdrop-filter:blur(16px); box-shadow:0 16px 44px rgba(0,0,0,.32);
}
.vy-card{padding:1.05rem 1.2rem; animation:vyFade .45s ease both;}
.vy-card.hv{transition:transform .18s ease, border-color .18s ease, box-shadow .18s ease;}
.vy-card.hv:hover{transform:translateY(-4px); border-color:rgba(45,212,191,.45); box-shadow:0 22px 50px rgba(0,0,0,.42);}
[class*="st-key-glass_"], .st-key-final_card, .st-key-approval_panel{padding:1.25rem 1.5rem;}
.st-key-approval_panel{border-color:rgba(245,181,68,.55); box-shadow:0 0 0 1px rgba(245,181,68,.18), 0 16px 44px rgba(0,0,0,.32);}
.st-key-final_card{border-color:rgba(45,212,191,.45);}
@keyframes vyFade{from{opacity:0; transform:translateY(8px);} to{opacity:1; transform:none;}}

.vy-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:.9rem;}
.vy-sh{display:flex; align-items:center; gap:.7rem; margin:1.6rem 0 .8rem;}
.vy-sh .ico{width:36px; height:36px; border-radius:11px; display:grid; place-items:center; font-size:18px;
  background:var(--glass2); border:1px solid var(--line);}
.vy-sh h3{margin:0; font-size:1.15rem; font-weight:700; letter-spacing:-.01em;}
.vy-sh .cap{color:var(--muted); font-size:.85rem;}
.vy-sh .sp{flex:1;}

.chip{display:inline-flex; align-items:center; gap:.35rem; padding:.2rem .65rem; border-radius:999px; font-size:.78rem;
  font-weight:600; background:var(--glass2); border:1px solid var(--line); color:var(--text);}
.chip.ok{color:#5eead4; border-color:rgba(45,212,191,.4);}
.chip.warn{color:var(--amber); border-color:rgba(245,181,68,.5);}
.chip.err{color:var(--rose); border-color:rgba(251,113,133,.5);}
.chip.mute{color:var(--muted);}

/* ---------- flights ---------- */
.fl-top{display:flex; justify-content:space-between; align-items:baseline; gap:.6rem;}
.fl-air{font-weight:700; font-size:1.02rem;}
.fl-price{font-weight:800; font-size:1.25rem; color:#5eead4;}
.fl-route{display:grid; grid-template-columns:auto 1fr auto; align-items:center; gap:.8rem; margin:.9rem 0 .5rem;}
.fl-time{font-weight:700; font-size:1.1rem;}
.fl-iata{color:var(--muted); font-size:.8rem;}
.fl-line{display:flex; flex-direction:column; align-items:center; gap:.2rem; font-size:.78rem; color:var(--muted);}
.fl-line i{display:block; width:100%; height:2px; border-radius:2px; background:linear-gradient(90deg,var(--teal),var(--violet));}
.fl-note{color:var(--muted); font-size:.85rem; line-height:1.5;}

/* ---------- hotels ---------- */
.ht-name{font-weight:700; font-size:1.02rem; margin-bottom:.15rem;}
.ht-area{color:var(--muted); font-size:.85rem;}
.ht-row{display:flex; justify-content:space-between; align-items:center; margin:.8rem 0 .4rem;}
.ht-rate{font-weight:700; color:var(--amber);}
.ht-price{font-weight:800; color:#5eead4;}
.ht-price small{color:var(--muted); font-weight:500;}
.ht-note{color:var(--muted); font-size:.85rem; line-height:1.5;}
.ht-link{display:inline-block; margin-top:.5rem; font-size:.82rem; font-weight:600; color:var(--teal); text-decoration:none;}
.ht-link:hover{text-decoration:underline;}

/* ---------- weather ---------- */
.wx-strip{display:flex; gap:.7rem; overflow-x:auto; padding:.2rem .1rem .6rem;}
.wx-day{min-width:108px; flex:1 0 108px; text-align:center; padding:.9rem .6rem;}
.wx-ico{font-size:2rem; line-height:1.2;}
.wx-lbl{font-weight:700; font-size:.88rem; margin-top:.2rem;}
.wx-cond{color:var(--muted); font-size:.78rem; min-height:1.2em;}
.wx-t{font-weight:700; margin-top:.35rem;}
.wx-t span{color:var(--muted); font-weight:500;}

/* ---------- timeline ---------- */
.tl{position:relative; padding-left:2.1rem;}
.tl::before{content:""; position:absolute; left:.78rem; top:.4rem; bottom:.4rem; width:2px;
  background:linear-gradient(180deg,var(--teal),var(--violet)); opacity:.55; border-radius:2px;}
.tl-day{position:relative; margin-bottom:1rem;}
.tl-dot{position:absolute; left:-2.1rem; top:.15rem; width:1.65rem; height:1.65rem; border-radius:50%; display:grid; place-items:center;
  font-size:.78rem; font-weight:800; color:#06101f; background:linear-gradient(135deg,var(--teal),var(--violet));}
.tl-title{font-weight:700; font-size:1.02rem; margin:0 0 .5rem;}
.tl-item{display:flex; gap:.8rem; padding:.35rem 0; border-top:1px solid var(--line); font-size:.92rem; line-height:1.5;}
.tl-item:first-of-type{border-top:0;}
.tl-time{flex:0 0 5.5rem; color:var(--teal); font-weight:600; font-size:.82rem; padding-top:.1rem;}

/* ---------- stats, skeleton, states ---------- */
.stat-row{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:.8rem; margin:.6rem 0 1rem;}
.stat{padding:.8rem 1rem; border-radius:14px; background:var(--glass); border:1px solid var(--line);}
.stat b{display:block; font-size:1.25rem; letter-spacing:-.01em;}
.stat span{color:var(--muted); font-size:.8rem;}
.stat.bad b{color:var(--rose);} .stat.good b{color:#5eead4;}
.sk{border-radius:var(--radius); min-height:118px; border:1px solid var(--line);
  background:linear-gradient(100deg, rgba(255,255,255,.04) 30%, rgba(255,255,255,.10) 50%, rgba(255,255,255,.04) 70%);
  background-size:220% 100%; animation:vyShimmer 1.4s linear infinite;}
@keyframes vyShimmer{from{background-position:120% 0;} to{background-position:-120% 0;}}
.vy-tile{padding:1.1rem 1.2rem;}
.vy-tile h4{margin:.2rem 0 .3rem; font-size:1rem;}
.vy-tile p{margin:0; color:var(--muted); font-size:.88rem; line-height:1.55;}
.vy-banner{display:flex; gap:.8rem; align-items:flex-start; padding:1rem 1.2rem; border-radius:16px; margin:.4rem 0 1rem;
  border:1px solid rgba(251,113,133,.45); background:rgba(251,113,133,.08);}
.vy-banner.info{border-color:rgba(167,139,250,.45); background:rgba(167,139,250,.09);}
.vy-banner .t{font-weight:700; margin-bottom:.15rem;}
.vy-banner .d{color:var(--muted); font-size:.9rem; line-height:1.55; white-space:pre-wrap;}
.hist-cap{color:var(--muted); font-size:.74rem; margin:-.55rem 0 .5rem .3rem;}
.side-h{font-weight:700; font-size:.95rem; margin:1.2rem 0 .5rem;}

@media (max-width: 768px){
  .block-container{padding-left:1rem; padding-right:1rem;}
  .tl-time{flex-basis:4.2rem;}
}
@media (prefers-reduced-motion: reduce){
  *{animation:none !important; transition:none !important;}
}
"""


def inject() -> None:
    """Inject the global stylesheet."""
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
