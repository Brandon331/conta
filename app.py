import streamlit as st
import sqlite3
import hashlib
import secrets
import json
import uuid
import io
import html
import inspect
from datetime import date, datetime
from xml.sax.saxutils import escape as xesc
from collections import OrderedDict

import pandas as pd
import plotly.express as px
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)

APP_TITLE = "FINOVA | Análisis Financiero"
DB_PATH = "finova.db"

# --------------------------- Sistema de diseño ---------------------------
# Tokens (CSS custom properties), componentes HTML reutilizables y tema de gráficas.
# Paleta derivada del logotipo de D.E.M.I. MEX (azul #013E8F + rojo señal) con neutros fríos.

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
:root{
  --brand:#013E8F; --brand-d:#012E6B; --navy:#0A2147; --ink:#0F1B2D; --muted:#55657D;
  --bg:#F4F6FA; --surface:#FFFFFF; --line:#DDE3EC; --accent:#C8102E; --signal:#F2183A;
  --ok:#0B7A4F; --ok-bg:#E6F4EE; --warn:#8A5300; --warn-bg:#FFF3D6;
  --err:#B3261E; --err-bg:#FDECEA; --info-bg:#E8EFFA;
  --r:14px; --sh:0 1px 2px rgba(10,33,71,.06),0 4px 14px rgba(10,33,71,.05);
  --display:'Barlow Condensed','Arial Narrow',sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
}
.stApp{background:var(--bg);color:var(--ink)}
.stApp,.stApp p,.stApp li,.stApp label,.stApp input,.stApp textarea,.stApp button,
.stApp [data-baseweb="select"] div,.stApp [data-testid="stCaptionContainer"]{
  font-family:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
.stApp h1,.stApp h2,.stApp h3{font-family:var(--display);color:var(--navy);font-weight:700;letter-spacing:-.005em}
.stApp h2{font-size:1.7rem;margin-top:1.4rem}.stApp h3{font-size:1.3rem}
[data-testid="stHeaderActionElements"],footer{display:none!important}
header[data-testid="stHeader"]{background:transparent}
.block-container{max-width:1240px;padding:2rem 2rem 4rem}

/* Encabezado de página */
.pg-head{margin:0 0 1.4rem;padding-bottom:1.1rem;border-bottom:1px solid var(--line)}
.eyebrow{font-size:.74rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--brand);
  display:flex;align-items:center;gap:.55rem;margin-bottom:.35rem}
.eyebrow:before{content:"";width:22px;height:3px;background:var(--signal);border-radius:2px}
.pg-head h1{font-size:clamp(2rem,4vw,2.8rem);line-height:1.05;margin:0;padding:0;overflow-wrap:anywhere}
.pg-head p{color:var(--muted);margin:.45rem 0 0;font-size:1rem;overflow-wrap:anywhere}

/* KPIs */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:0 0 1.4rem}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:16px 18px;box-shadow:var(--sh)}
.kpi.brand{border-top:3px solid var(--brand)}.kpi.up{border-top:3px solid var(--ok)}
.kpi.down{border-top:3px solid var(--accent)}.kpi.warn{border-top:3px solid #E0A100}
.kpi-label{font-size:.76rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.kpi-value{font-family:var(--display);font-weight:700;font-size:clamp(1.6rem,2.3vw,2.2rem);line-height:1.15;
  color:var(--navy);margin-top:.3rem;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.kpi-value.sm{font-size:1.4rem}
.kpi-unit{font-family:'IBM Plex Sans',sans-serif;font-size:.72rem;font-weight:600;color:var(--muted);margin-left:.4rem;letter-spacing:.05em}
.kpi-hint{font-size:.8rem;color:var(--muted);margin-top:.15rem;overflow-wrap:anywhere}

/* Insignias, estados vacíos, pasos */
.badge{display:inline-block;font-size:.72rem;font-weight:600;padding:2px 9px;border-radius:999px;background:var(--info-bg);color:var(--brand)}
.badge.ok{background:var(--ok-bg);color:var(--ok)}.badge.warn{background:var(--warn-bg);color:var(--warn)}
.badge.err{background:var(--err-bg);color:var(--err)}.badge.muted{background:#EEF1F6;color:var(--muted)}
.empty{background:var(--surface);border:1px dashed #B9C4D6;border-radius:16px;padding:2.2rem 1.5rem;text-align:center;margin:.5rem 0 1.2rem}
.empty-ic{width:54px;height:54px;border-radius:14px;background:var(--info-bg);color:var(--brand);display:inline-flex;align-items:center;justify-content:center;margin-bottom:.7rem}
.empty h3{margin:0 0 .25rem}.empty p{color:var(--muted);margin:0;max-width:46ch;margin-inline:auto}
.stepper{list-style:none;display:flex;flex-wrap:wrap;gap:10px 28px;padding:0;margin:0 0 1.3rem}
.step{display:flex;align-items:center;gap:.55rem;font-weight:500;color:var(--muted)}
.step-dot{width:26px;height:26px;border-radius:50%;border:2px solid #B9C4D6;display:inline-flex;align-items:center;justify-content:center;font-size:.78rem;font-weight:600;background:#fff}
.step.now{color:var(--navy);font-weight:600}.step.now .step-dot{border-color:var(--brand);background:var(--brand);color:#fff}
.step.done{color:var(--ok)}.step.done .step-dot{border-color:var(--ok);background:var(--ok);color:#fff}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 1rem}
.chip{background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:4px 12px;font-size:.84rem;color:var(--ink)}
.mono{font-family:var(--mono);font-size:.82rem;color:var(--muted)}
.th{font-size:.72rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.row-sep{border:0;border-top:1px solid var(--line);margin:.35rem 0}

/* Tarjetas de navegación (Panel) */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.tile-mark){background:var(--surface);border:1px solid var(--line);
  border-radius:var(--r);box-shadow:var(--sh);transition:border-color .15s,transform .15s}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.tile-mark):hover{border-color:var(--brand);transform:translateY(-1px)}
.tile-ic{width:40px;height:40px;border-radius:11px;background:var(--info-bg);color:var(--brand);display:inline-flex;align-items:center;justify-content:center}
.tile h3{margin:.65rem 0 .1rem}.tile p{color:var(--muted);margin:0 0 .4rem;font-size:.92rem}

/* Razones */
.ratios{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;margin:.6rem 0 1.2rem}
.ratio{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:18px;box-shadow:var(--sh)}
.ratio-top{display:flex;justify-content:space-between;align-items:center;gap:8px}
.ratio-name{font-weight:600;color:var(--navy)}
.ratio-value{font-family:var(--display);font-weight:700;font-size:2.3rem;line-height:1.1;color:var(--brand);margin:.35rem 0 .6rem;font-variant-numeric:tabular-nums}
.ratio-value small{font-family:'IBM Plex Sans',sans-serif;font-size:.8rem;color:var(--muted);font-weight:600;margin-left:.35rem}
.ratio dl{margin:0 0 .5rem;display:grid;grid-template-columns:auto 1fr;gap:.2rem .8rem;font-size:.86rem}
.ratio dt{color:var(--muted)}.ratio dd{margin:0;overflow-wrap:anywhere}
.ratio p{margin:0;font-size:.88rem;color:#2A3A52;border-top:1px solid var(--line);padding-top:.6rem}

/* Sidebar */
section[data-testid="stSidebar"]{background:var(--navy);border-right:1px solid #14336A}
section[data-testid="stSidebar"] .stMarkdown,section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:#C9D6EC}
.side-brand{display:flex;align-items:center;gap:12px;padding:.2rem .2rem 1rem}
.side-brand .wordmark{font-family:var(--display);font-weight:700;font-size:1.7rem;color:#fff;line-height:1}
.side-brand small{display:block;font-size:.64rem;letter-spacing:.16em;color:#8FA6CB;font-weight:600;margin-top:3px}
.side-user{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.06);border-radius:12px;padding:10px 12px}
.avatar{width:34px;height:34px;border-radius:50%;background:var(--brand);color:#fff;font-weight:600;display:inline-flex;align-items:center;justify-content:center;border:1px solid rgba(255,255,255,.25)}
.side-user b{color:#fff;display:block;font-size:.92rem;line-height:1.2;overflow-wrap:anywhere}.side-user span{color:#9FB3D4;font-size:.76rem}
.side-ctx{margin-top:10px;border-left:3px solid var(--signal);background:rgba(255,255,255,.06);border-radius:0 10px 10px 0;padding:8px 12px}
.side-ctx small{color:#9FB3D4;font-size:.66rem;letter-spacing:.1em;font-weight:600;text-transform:uppercase}
.side-ctx b{display:block;color:#fff;font-size:.88rem;overflow-wrap:anywhere}.side-ctx span{font-family:var(--mono);font-size:.7rem;color:#9FB3D4}
.nav-label{font-size:.66rem;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:#7F97C0;margin:1.5rem 0 .3rem .4rem}
section[data-testid="stSidebar"] button{width:100%;justify-content:flex-start;border:0;box-shadow:none;border-radius:10px;
  min-height:42px;background:transparent;color:#D5E0F2;font-weight:500;transition:background .15s}
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.15rem}
section[data-testid="stSidebar"] button>div,section[data-testid="stSidebar"] button [data-testid="stMarkdownContainer"]{justify-content:flex-start;text-align:left}
section[data-testid="stSidebar"] button{padding-left:.8rem}
section[data-testid="stSidebar"] button p,section[data-testid="stSidebar"] button span{color:inherit!important}
section[data-testid="stSidebar"] button:hover{background:rgba(255,255,255,.09);color:#fff}
section[data-testid="stSidebar"] button[kind="primary"],section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]{
  background:rgba(255,255,255,.14);color:#fff;font-weight:600;box-shadow:inset 3px 0 0 var(--signal)}
section[data-testid="stSidebar"] :focus-visible{outline:3px solid #fff!important;outline-offset:2px}

/* Controles */
.stApp .stButton>button,.stApp .stDownloadButton>button,.stApp [data-testid="stFormSubmitButton"]>button{
  border-radius:10px;min-height:44px;font-weight:600;transition:background .15s,border-color .15s,box-shadow .15s}
.stApp [data-testid="stMain"] button[kind="secondary"],.stApp [data-testid="stMain"] button[data-testid="stBaseButton-secondary"]{
  background:var(--surface);border:1px solid #C3CDDD;color:var(--navy)}
.stApp [data-testid="stMain"] button[kind="secondary"]:hover{border-color:var(--brand);color:var(--brand)}
.stApp [data-testid="stMain"] button[kind="primary"]:hover,.stApp [data-testid="stMain"] button[data-testid="stBaseButton-primary"]:hover{background:var(--brand-d)}
.stApp [data-testid="stMain"] :focus-visible{outline:3px solid var(--brand);outline-offset:2px}
.stApp label p{font-weight:600;font-size:.86rem;color:var(--ink)}
.stApp [data-baseweb="input"],.stApp [data-baseweb="base-input"],.stApp [data-baseweb="select"]>div{border-radius:10px}
[data-testid="stForm"]{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:1.4rem;box-shadow:var(--sh)}
[data-testid="stExpander"]{background:var(--surface);border:1px solid var(--line);border-radius:12px}
[data-testid="stExpander"] summary p{font-weight:600;color:var(--navy)}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:12px;overflow:hidden}
[data-testid="stAlert"]{border-radius:12px}

/* Acceso */
.auth-brand{text-align:center;margin:2.5rem 0 1.4rem}
.auth-brand .wordmark{font-family:var(--display);font-weight:700;font-size:2.8rem;color:var(--navy);line-height:1;margin-top:.6rem;letter-spacing:.02em}
.auth-brand p{color:var(--muted);margin:.3rem 0 0}
.auth-note{background:var(--info-bg);color:var(--navy);border-radius:12px;padding:.8rem 1rem;margin-bottom:1rem;font-size:.92rem}
.auth-points{list-style:none;padding:0;margin:1.4rem 0 0;display:grid;gap:.55rem;color:var(--muted);font-size:.9rem}
.auth-points li{display:flex;gap:.6rem;align-items:center}.auth-points svg{color:var(--brand);flex:none}

@media (max-width:640px){
  .block-container{padding:1.2rem 1rem 3rem}
  .kpis{grid-template-columns:1fr 1fr}.ratios{grid-template-columns:1fr}
  .stepper{gap:8px 16px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
"""

ICONS = {
    "dashboard": '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    "file-plus": '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="12" x2="12" y1="18" y2="12"/><line x1="9" x2="15" y1="15" y2="15"/>',
    "table": '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18M3 15h18M12 3v18"/>',
    "percent": '<line x1="19" x2="5" y1="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    "bar-chart": '<line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="16"/>',
    "file-text": '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "scale": '<path d="M12 3v18M5 21h14M5 7h14M5 7l-3 7a4 4 0 0 0 6 0L5 7zM19 7l-3 7a4 4 0 0 0 6 0l-3-7z"/>',
}

LOGO = (
    '<svg width="44" height="44" viewBox="0 0 128 128" role="img" aria-label="FINOVA">'
    '<rect x="8" y="8" width="112" height="112" rx="24" fill="#013E8F" stroke="rgba(255,255,255,.22)" stroke-width="2"/>'
    '<rect x="32" y="68" width="16" height="24" fill="#fff"/><rect x="54" y="50" width="16" height="42" fill="#fff"/>'
    '<rect x="76" y="32" width="16" height="60" fill="#fff"/><rect x="28" y="100" width="72" height="8" fill="#F2183A"/></svg>'
)

COLORWAY = ["#013E8F", "#8FA3C0", "#C8102E", "#0B7A4F", "#E0A100", "#5C7CBA", "#293241", "#7A4FA0"]
PERIOD_COLORS = {"Anterior": "#9DB0CC", "Reciente": "#013E8F"}
MOVE_COLORS = {"Aumento": "#0B7A4F", "Disminucion": "#C8102E"}

_V = tuple(int(x) for x in st.__version__.split(".")[:2] if x.isdigit())
STRETCH = {"width": "stretch"} if _V >= (1, 50) else {"use_container_width": True}
_BTN_ICON = "icon" in inspect.signature(st.button).parameters
_COL_VA = {"vertical_alignment": "center"} if "vertical_alignment" in inspect.signature(st.columns).parameters else {}


def H(markup, target=st):
    """Renderiza HTML en una sola línea (evita que Markdown lo trate como bloque de código)."""
    target.markdown("".join(line.strip() for line in markup.strip().splitlines()), unsafe_allow_html=True)


def esc(value):
    return html.escape("" if value is None else str(value))


def icon(name, size=20):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def btn(label, material=None, **kwargs):
    """Botón con icono Material cuando la versión de Streamlit lo soporta."""
    if _BTN_ICON and material:
        kwargs["icon"] = f":material/{material}:"
    return st.button(label, **kwargs)


def go(page_name):
    st.session_state.page = page_name
    st.rerun()


def fmt_money(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def badge(text, tone=""):
    return f'<span class="badge {tone}">{esc(text)}</span>'


def page_header(title, subtitle="", eyebrow=""):
    eb = f'<div class="eyebrow">{esc(eyebrow)}</div>' if eyebrow else ""
    sub = f"<p>{esc(subtitle)}</p>" if subtitle else ""
    H(f'<div class="pg-head">{eb}<h1>{esc(title)}</h1>{sub}</div>')


def kpi_row(items):
    """items: (etiqueta, valor, unidad, nota, tono)"""
    cells = ""
    for it in items:
        label, value = it[0], it[1]
        unit = it[2] if len(it) > 2 else ""
        hint = it[3] if len(it) > 3 else ""
        tone = it[4] if len(it) > 4 else ""
        size = " sm" if len(str(value)) > 18 else ""
        unit_html = f'<span class="kpi-unit">{esc(unit)}</span>' if unit else ""
        hint_html = f'<div class="kpi-hint">{esc(hint)}</div>' if hint else ""
        cells += (f'<div class="kpi {tone}"><div class="kpi-label">{esc(label)}</div>'
                  f'<div class="kpi-value{size}">{esc(value)}{unit_html}</div>{hint_html}</div>')
    H(f'<div class="kpis">{cells}</div>')


def empty_state(icon_name, title, text):
    H(f'<div class="empty"><div class="empty-ic">{icon(icon_name, 26)}</div><h3>{esc(title)}</h3><p>{esc(text)}</p></div>')


def stepper_html(current, steps):
    items = ""
    for i, name in enumerate(steps, 1):
        state = "done" if i < current else "now" if i == current else "todo"
        mark = icon("check", 14) if state == "done" else str(i)
        aria = ' aria-current="step"' if state == "now" else ""
        items += f'<li class="step {state}"{aria}><span class="step-dot">{mark}</span>{esc(name)}</li>'
    return f'<ol class="stepper" aria-label="Progreso del análisis">{items}</ol>'


def show_chart(fig, height=470):
    fig.update_layout(
        template="plotly_white", height=height, colorway=COLORWAY,
        font=dict(family="IBM Plex Sans, system-ui, sans-serif", color="#0F1B2D", size=13),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=84, b=8),
        title=dict(x=0, font=dict(size=20, family="Barlow Condensed, Arial Narrow, sans-serif", color="#0A2147")),
        legend=dict(orientation="h", yanchor="bottom", y=1.07, x=0, title_text=""),
        hoverlabel=dict(font_family="IBM Plex Sans, sans-serif"),
    )
    fig.update_xaxes(gridcolor="#E8ECF3", linecolor="#C3CDDD", zeroline=False)
    fig.update_yaxes(gridcolor="#E8ECF3", zeroline=False)
    st.plotly_chart(fig, **STRETCH, config={"displaylogo": False})


def brand_icon():
    """Icono de pestaña generado en código (sin emoji ni archivos externos)."""
    try:
        from PIL import Image, ImageDraw
        im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((8, 8, 120, 120), radius=24, fill="#013E8F")
        for x, h in ((32, 24), (54, 42), (76, 60)):
            d.rectangle((x, 92 - h, x + 16, 92), fill="white")
        d.rectangle((28, 100, 100, 108), fill="#F2183A")
        return im
    except Exception:
        return None


st.set_page_config(
    page_title=APP_TITLE,
    page_icon=brand_icon(),
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(THEME_CSS, unsafe_allow_html=True)

# Catálogo base basado en las cuentas que aparecen en la hoja verde.
CATALOGO = OrderedDict({
    "Activo circulante": [
        "Caja", "Bancos", "Inversiones temporales", "Clientes",
        "Documentos por cobrar", "Deudores diversos", "Inventarios",
        "Almacén", "Anticipo a proveedores", "IVA acreditable",
        "Pagos anticipados", "Otros activos circulantes"
    ],
    "Activo no circulante": [
        "Terrenos", "Edificios", "Maquinaria", "Mobiliario y equipo",
        "Equipo de cómputo", "Equipo de transporte", "Herramientas",
        "Depreciación acumulada", "Amortización acumulada", "Patentes",
        "Marcas", "Software", "Depósitos en garantía",
        "Inversiones permanentes", "Otros activos no circulantes"
    ],
    "Pasivo circulante": [
        "Proveedores", "Acreedores diversos", "Documentos por pagar",
        "Préstamos bancarios a corto plazo", "Impuestos por pagar",
        "IVA trasladado", "Sueldos por pagar", "Intereses por pagar",
        "Anticipos de clientes", "Otros pasivos circulantes"
    ],
    "Pasivo no circulante": [
        "Préstamos bancarios a largo plazo", "Hipotecas por pagar",
        "Documentos por pagar a largo plazo", "Obligaciones por pagar",
        "Arrendamientos a largo plazo", "Otros pasivos no circulantes"
    ],
    "Capital contable": [
        "Capital social", "Aportaciones para futuros aumentos",
        "Prima en emisión de acciones", "Reserva legal",
        "Utilidades retenidas", "Resultado del ejercicio",
        "Pérdidas acumuladas", "Otros componentes del capital"
    ],
    "Estado de resultados (opcional)": [
        "Ventas", "Devoluciones sobre ventas", "Costo de ventas",
        "Gastos de venta", "Gastos de administración",
        "Otros ingresos", "Otros gastos", "Gastos por intereses",
        "Impuestos a la utilidad", "Utilidad bruta",
        "Utilidad operativa", "Utilidad neta"
    ]
})

CATEGORIAS_BALANCE = [
    "Activo circulante", "Activo no circulante", "Pasivo circulante",
    "Pasivo no circulante", "Capital contable"
]
CUENTAS_CONTRA_ACTIVO = {"Depreciación acumulada", "Amortización acumulada"}
CUENTAS_RESULTADO = set(CATALOGO["Estado de resultados (opcional)"])

# --------------------------- Base de datos y seguridad ---------------------------

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'usuario',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folio TEXT UNIQUE NOT NULL,
            owner_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            rfc TEXT,
            activity TEXT,
            currency TEXT NOT NULL,
            comparison_type TEXT NOT NULL,
            old_date TEXT NOT NULL,
            new_date TEXT NOT NULL,
            accounts_json TEXT NOT NULL,
            adjustments_json TEXT NOT NULL DEFAULT '{}',
            ratios_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        );
        """)


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 400000
    ).hex()
    return hashed, salt


def check_password(password, stored_hash, salt):
    computed, _ = password_hash(password, salt)
    return secrets.compare_digest(computed, stored_hash)


def get_user(username):
    with db() as con:
        return con.execute(
            "SELECT * FROM users WHERE username=? AND active=1",
            (username.strip(),)
        ).fetchone()


def add_user(username, password, role="usuario"):
    username = username.strip()
    if len(username) < 3:
        raise ValueError("El usuario debe tener al menos 3 caracteres.")
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    hashed, salt = password_hash(password)
    with db() as con:
        con.execute(
            "INSERT INTO users(username,password_hash,salt,role,created_at) VALUES(?,?,?,?,?)",
            (username, hashed, salt, role, datetime.now().isoformat(timespec="seconds"))
        )


def owner_analysis(folio, owner_id):
    with db() as con:
        return con.execute(
            "SELECT * FROM analyses WHERE folio=? AND owner_id=?",
            (folio.strip(), owner_id)
        ).fetchone()


# --------------------------- Funciones financieras ---------------------------

def money(value, currency="MXN"):
    try:
        return f"{currency} ${float(value):,.2f}"
    except (TypeError, ValueError):
        return f"{currency} $0.00"


def base_accounts():
    return [
        {"Concepto": concept, "Categoria": category, "Anterior": 0.0, "Reciente": 0.0}
        for category, concepts in CATALOGO.items()
        for concept in concepts
    ]


def clean_accounts(data):
    df = pd.DataFrame(data).copy()
    for col in ["Concepto", "Categoria"]:
        if col not in df:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()
    for col in ["Anterior", "Reciente"]:
        if col not in df:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df = df[df["Concepto"] != ""].copy()
    df = df[df["Categoria"].isin(CATALOGO.keys())].copy()
    # Si se repite un concepto, se conserva la última captura.
    df = df.drop_duplicates(subset=["Concepto"], keep="last")
    df["Cambio"] = df["Reciente"] - df["Anterior"]
    df["Aumento"] = df["Cambio"].clip(lower=0)
    df["Disminucion"] = (-df["Cambio"]).clip(lower=0)
    return df.reset_index(drop=True)


def totals(df, period):
    """Totales calculados desde las cuentas individuales; evita sumar totales duplicados."""
    result = {}
    for cat in CATALOGO:
        result[cat] = float(df.loc[df["Categoria"] == cat, period].sum())

    result["Activo total"] = result["Activo circulante"] + result["Activo no circulante"]
    # Depreciación/amortización acumulada se capturan como saldos negativos o como
    # cuentas correctoras; si se capturan positivos, se restan del activo.
    contra = float(df.loc[df["Concepto"].isin(CUENTAS_CONTRA_ACTIVO), period].sum())
    result["Activo total"] -= max(0.0, contra)
    result["Pasivo total"] = result["Pasivo circulante"] + result["Pasivo no circulante"]
    result["Capital total"] = result["Capital contable"]
    result["Pasivo más capital"] = result["Pasivo total"] + result["Capital total"]
    result["Capital de trabajo"] = result["Activo circulante"] - result["Pasivo circulante"]

    def account(name):
        found = df.loc[df["Concepto"].str.casefold() == name.casefold(), period]
        return float(found.sum()) if not found.empty else 0.0

    result["Caja"] = account("Caja")
    result["Bancos"] = account("Bancos")
    result["Clientes"] = account("Clientes")
    result["Inventarios"] = account("Inventarios") + account("Almacén")
    result["Proveedores"] = account("Proveedores")
    result["Ventas"] = account("Ventas")
    result["Costo de ventas"] = account("Costo de ventas")
    result["Utilidad bruta"] = account("Utilidad bruta")
    result["Utilidad operativa"] = account("Utilidad operativa")
    result["Utilidad neta"] = account("Utilidad neta")
    result["Gastos por intereses"] = account("Gastos por intereses")
    result["Efectivo"] = result["Caja"] + result["Bancos"]
    return result


def classify_flow(row, overrides):
    """Clasificación orientativa por naturaleza de la cuenta, editable por el usuario."""
    concept = row["Concepto"]
    category = row["Categoria"]
    change = float(row["Cambio"])
    if abs(change) < 0.005:
        return "Sin movimiento", "Sin movimiento"

    override = overrides.get(concept, "Automático")
    if override != "Automático":
        parts = override.split(" | ", 1)
        return parts[0], parts[1] if len(parts) > 1 else "Revisar"

    # Origen/aplicación por variación del balance:
    # activos: disminución = origen, aumento = aplicación.
    # pasivos/capital: aumento = origen, disminución = aplicación.
    if category.startswith("Activo"):
        origin = change < 0
    elif category.startswith("Pasivo") or category == "Capital contable":
        origin = change > 0
    else:
        # Estado de resultados no se clasifica como cambio de balance.
        return "Revisar", "Revisar"

    source_use = "Origen" if origin else "Aplicación"

    # Actividad por naturaleza de la cuenta.
    if category == "Activo no circulante":
        activity = "Inversión"
    elif category == "Pasivo no circulante":
        activity = "Financiamiento"
    elif category == "Capital contable":
        activity = "Financiamiento"
    elif category in ("Activo circulante", "Pasivo circulante"):
        activity = "Operación"
    else:
        activity = "Revisar"

    if concept in CUENTAS_CONTRA_ACTIVO:
        activity = "Inversión"
    return source_use, activity


def green_sheet(df, overrides):
    out = df.copy()
    classifications = out.apply(lambda r: classify_flow(r, overrides), axis=1)
    out["Origen / Aplicación"] = [x[0] for x in classifications]
    out["Actividad"] = [x[1] for x in classifications]
    return out


RATIO_DEFS = OrderedDict({
    "Razón circulante": ("Activo circulante / Pasivo circulante", "veces"),
    "Prueba ácida": ("(Activo circulante - Inventarios) / Pasivo circulante", "veces"),
    "Razón de efectivo": ("(Caja + Bancos) / Pasivo circulante", "veces"),
    "Capital de trabajo": ("Activo circulante - Pasivo circulante", "moneda"),
    "Endeudamiento": ("Pasivo total / Activo total × 100", "%"),
    "Autonomía financiera": ("Capital contable / Activo total × 100", "%"),
    "Deuda a capital": ("Pasivo total / Capital contable", "veces"),
    "Margen bruto": ("Utilidad bruta / Ventas × 100", "%"),
    "Margen operativo": ("Utilidad operativa / Ventas × 100", "%"),
    "Margen neto": ("Utilidad neta / Ventas × 100", "%"),
    "ROA": ("Utilidad neta / Activo total × 100", "%"),
    "ROE": ("Utilidad neta / Capital contable × 100", "%"),
    "Rotación de activos": ("Ventas / Activo total", "veces"),
    "Rotación de inventarios": ("Costo de ventas / Inventarios", "veces"),
    "Rotación de cuentas por cobrar": ("Ventas / Clientes", "veces"),
    "Rotación de proveedores": ("Costo de ventas / Proveedores (aproximación)", "veces"),
    "Cobertura de intereses": ("Utilidad operativa / Gastos por intereses", "veces"),
    "Solidez": ("Activo total / Pasivo total", "veces"),
    "Inmovilización de activos": ("Activo no circulante / Activo total × 100", "%")
})


def calc_ratio(name, t, period_label):
    formulas = {
        "Razón circulante": (t["Activo circulante"], t["Pasivo circulante"]),
        "Prueba ácida": (t["Activo circulante"] - t["Inventarios"], t["Pasivo circulante"]),
        "Razón de efectivo": (t["Efectivo"], t["Pasivo circulante"]),
        "Capital de trabajo": (t["Capital de trabajo"], None),
        "Endeudamiento": (t["Pasivo total"], t["Activo total"]),
        "Autonomía financiera": (t["Capital total"], t["Activo total"]),
        "Deuda a capital": (t["Pasivo total"], t["Capital total"]),
        "Margen bruto": (t["Utilidad bruta"], t["Ventas"]),
        "Margen operativo": (t["Utilidad operativa"], t["Ventas"]),
        "Margen neto": (t["Utilidad neta"], t["Ventas"]),
        "ROA": (t["Utilidad neta"], t["Activo total"]),
        "ROE": (t["Utilidad neta"], t["Capital total"]),
        "Rotación de activos": (t["Ventas"], t["Activo total"]),
        "Rotación de inventarios": (t["Costo de ventas"], t["Inventarios"]),
        "Rotación de cuentas por cobrar": (t["Ventas"], t["Clientes"]),
        "Rotación de proveedores": (t["Costo de ventas"], t["Proveedores"]),
        "Cobertura de intereses": (t["Utilidad operativa"], t["Gastos por intereses"]),
        "Solidez": (t["Activo total"], t["Pasivo total"]),
        "Inmovilización de activos": (t["Activo no circulante"], t["Activo total"])
    }
    a, b = formulas[name]
    unit = RATIO_DEFS[name][1]
    if b is None:
        value = a
        substitution = f"{a:,.2f}"
    elif abs(b) < 1e-9:
        value = None
        substitution = f"{a:,.2f} / {b:,.2f}"
    else:
        value = a / b
        substitution = f"{a:,.2f} / {b:,.2f}"
        if unit == "%":
            value *= 100
            substitution += " × 100"

    if value is None:
        interpretation = "No calculable: el denominador es cero o falta información."
        display = "No calculable"
    else:
        display = f"{value:,.2f} {unit}"
        if name == "Razón circulante":
            interpretation = (
                f"Los activos circulantes equivalen a {value:.2f} veces el pasivo circulante. "
                + ("La cobertura contable es superior a 1. " if value >= 1 else
                   "La cobertura contable es inferior a 1; conviene revisar la liquidez. ")
                + "La conclusión debe considerar vencimientos y calidad de los activos."
            )
        elif name == "Prueba ácida":
            interpretation = (
                f"La cobertura excluyendo inventarios es de {value:.2f} veces. "
                "Un valor bajo puede indicar dependencia de la venta de inventarios."
            )
        elif unit == "%":
            interpretation = f"El indicador es {value:.2f}%. Su evaluación depende del sector, periodo y políticas contables."
        elif unit == "moneda":
            interpretation = f"Los recursos circulantes netos ascienden a {value:,.2f}."
        else:
            interpretation = f"El indicador es {value:.2f} veces. Compáralo con periodos anteriores y con empresas del mismo sector."

    return {
        "Razón": name,
        "Periodo": period_label,
        "Fórmula": RATIO_DEFS[name][0],
        "Sustitución": substitution,
        "Resultado": value,
        "Unidad": unit,
        "Interpretación": interpretation,
        "Resultado mostrado": display
    }


def make_pdf(record, sheet, ratios, totals_recent):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(letter),
        rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("FINOVA | REPORTE GERENCIAL FINANCIERO", styles["Title"]),
        Spacer(1, 8),
        Paragraph(f"<b>Empresa:</b> {xesc(record['company'])} &nbsp;&nbsp; <b>RFC:</b> {xesc(record['rfc'] or 'No indicado')}", styles["Normal"]),
        Paragraph(f"<b>Folio:</b> {record['folio']} &nbsp;&nbsp; <b>Comparativo:</b> {record['old_date']} vs {record['new_date']}", styles["Normal"]),
        Paragraph(f"<b>Moneda:</b> {record['currency']} &nbsp;&nbsp; <b>Generado:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Resumen ejecutivo", styles["Heading2"]),
    ]
    kpi_data = [
        ["Activo total", "Pasivo total", "Capital contable", "Capital de trabajo"],
        [
            f"{totals_recent['Activo total']:,.2f}",
            f"{totals_recent['Pasivo total']:,.2f}",
            f"{totals_recent['Capital total']:,.2f}",
            f"{totals_recent['Capital de trabajo']:,.2f}"
        ]
    ]
    kpi = Table(kpi_data, colWidths=[2.3*inch]*4)
    kpi.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0A2147")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("BACKGROUND", (0,1), (-1,1), colors.HexColor("#F4F6FA")),
        ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#DDE3EC")),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7)
    ]))
    story.extend([kpi, Spacer(1, 12), Paragraph("Hoja verde comparativa", styles["Heading2"])])

    rows = [["Concepto", "Categoría", "Anterior", "Reciente", "Aumentó", "Disminuyó", "Origen / Aplicación", "Actividad"]]
    for _, r in sheet.iterrows():
        rows.append([
            str(r["Concepto"])[:27], str(r["Categoria"])[:21],
            f"{r['Anterior']:,.2f}", f"{r['Reciente']:,.2f}",
            f"{r['Aumento']:,.2f}", f"{r['Disminucion']:,.2f}",
            str(r["Origen / Aplicación"]), str(r["Actividad"])
        ])
    table = Table(rows, repeatRows=1, colWidths=[1.55*inch,1.2*inch,.85*inch,.85*inch,.8*inch,.8*inch,1.05*inch,1.0*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0A2147")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 6.5),
        ("GRID", (0,0), (-1,-1), .3, colors.HexColor("#DDE3EC")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F4F6FA")]),
        ("ALIGN", (2,1), (5,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4)
    ]))
    story.append(table)

    if ratios:
        story.extend([Spacer(1, 14), Paragraph("Razones financieras", styles["Heading2"])])
        for r in ratios:
            story.append(KeepTogether([
                Paragraph(f"<b>{r['Razón']} — {r['Periodo']}</b>", styles["Heading3"]),
                Paragraph(f"Fórmula: {r['Fórmula']}", styles["Normal"]),
                Paragraph(f"Sustitución: {r['Sustitución']}", styles["Normal"]),
                Paragraph(f"Resultado: {r['Resultado mostrado']}", styles["Normal"]),
                Paragraph(f"Interpretación: {r['Interpretación']}", styles["Normal"]),
                Spacer(1, 6)
            ]))
    story.extend([
        Spacer(1, 12),
        Paragraph(
            "Nota: clasificación preliminar basada en la naturaleza general de las cuentas. "
            "El estado de flujo de efectivo formal requiere validar movimientos reales de efectivo, "
            "ajustes no monetarios y la información complementaria del periodo.",
            styles["Italic"]
        )
    ])
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# --------------------------- Inicio y sesión ---------------------------

init_db()
for _key, _val in (("user", None), ("page", "Panel"), ("current_folio", None), ("lookup_folio", None)):
    if _key not in st.session_state:
        st.session_state[_key] = _val

with db() as con:
    user_count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def login_screen():
    _, col, _ = st.columns([1, 1.3, 1])
    with col:
        H(f'<div class="auth-brand">{LOGO}<div class="wordmark">FINOVA</div><p>Plataforma de análisis financiero</p></div>')

        if user_count == 0:
            H('<div class="auth-note">Configuración inicial: crea la cuenta administradora. '
              'Esta opción solo aparece cuando no existen usuarios.</div>')
            with st.form("first_admin"):
                username = st.text_input("Usuario administrador")
                password = st.text_input("Contraseña (mínimo 8 caracteres)", type="password")
                confirm = st.text_input("Confirmar contraseña", type="password")
                submitted = st.form_submit_button("Crear administrador", type="primary", **STRETCH)
                if submitted:
                    if password != confirm:
                        st.error("Las contraseñas no coinciden.")
                    else:
                        try:
                            add_user(username, password, "admin")
                            st.success("Administrador creado. Ya puedes iniciar sesión.")
                            st.rerun()
                        except (ValueError, sqlite3.IntegrityError) as e:
                            st.error(str(e))
            return

        with st.form("login_form"):
            username = st.text_input("Usuario", autocomplete="username")
            password = st.text_input("Contraseña", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Ingresar", type="primary", **STRETCH)
            if submitted:
                user = get_user(username)
                if user and check_password(password, user["password_hash"], user["salt"]):
                    st.session_state.user = dict(user)
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
        H(f'<ul class="auth-points">'
          f'<li>{icon("table", 18)}Compara dos balances y detecta orígenes y aplicaciones</li>'
          f'<li>{icon("percent", 18)}Razones financieras con fórmula e interpretación</li>'
          f'<li>{icon("file-text", 18)}Reporte gerencial listo para exportar en PDF</li></ul>')


if not st.session_state.user:
    login_screen()
    st.stop()

user = st.session_state.user
is_admin = user["role"] == "admin"

active = owner_analysis(st.session_state.current_folio, user["id"]) if st.session_state.current_folio else None
if st.session_state.current_folio and not active:
    st.session_state.current_folio = None

NAV = [
    ("Análisis", [("Panel", "dashboard"), ("Nuevo análisis", "note_add"), ("Consulta por folio", "search")]),
    ("Resultados", [("Hoja verde", "table_view"), ("Razones financieras", "percent"),
                    ("Gráficas", "bar_chart"), ("Reporte gerencial", "description")]),
]
if is_admin:
    NAV.append(("Sistema", [("Administrar usuarios", "group")]))

with st.sidebar:
    H(f'<div class="side-brand">{LOGO}<div><div class="wordmark">FINOVA</div><small>INTELIGENCIA FINANCIERA</small></div></div>')
    H(f'<div class="side-user"><span class="avatar" aria-hidden="true">{esc(user["username"][:1].upper())}</span>'
      f'<div><b>{esc(user["username"])}</b><span>{"Administrador" if is_admin else "Usuario"}</span></div></div>')
    if active:
        H(f'<div class="side-ctx"><small>Análisis activo</small><b>{esc(active["company"])}</b><span>{esc(active["folio"])}</span></div>')
    for group_label, items in NAV:
        H(f'<div class="nav-label">{group_label}</div>')
        for name, mat in items:
            if btn(name, mat, key="nav_" + name, **STRETCH,
                   type="primary" if st.session_state.page == name else "secondary"):
                go(name)
    H('<div class="nav-label">Sesión</div>')
    if btn("Cerrar sesión", "logout", key="logout", **STRETCH):
        st.session_state.user = None
        st.session_state.current_folio = None
        st.session_state.lookup_folio = None
        st.rerun()
    st.caption("FINOVA · Versión académica")

page = st.session_state.page


# --------------------------- Panel ---------------------------

if page == "Panel":
    with db() as con:
        records = con.execute(
            "SELECT * FROM analyses WHERE owner_id=? ORDER BY id DESC", (user["id"],)
        ).fetchall()

    page_header("Centro de mando financiero", "Balances comparativos, variaciones, razones y reportes.", "Panel")
    kpi_row([
        ("Mis análisis", len(records), "", "", "brand"),
        ("Empresas analizadas", len({r["company"].casefold() for r in records})),
        ("Último análisis", records[0]["created_at"][:10] if records else "—"),
        ("Análisis activo", active["company"] if active else "Ninguno", "",
         active["folio"] if active else "Ábrelo desde la actividad reciente"),
    ])

    if not records:
        empty_state("file-plus", "Aún no has guardado análisis",
                    "Captura los saldos de dos periodos y FINOVA calculará variaciones, razones y el reporte.")
        if btn("Crear primer análisis", "note_add", type="primary", key="first_analysis"):
            go("Nuevo análisis")
    else:
        st.subheader("Flujo de trabajo")
        tiles = [
            ("file-plus", "Nuevo análisis", "Captura y compara dos balances."),
            ("table", "Hoja verde", "Orígenes, aplicaciones y variaciones."),
            ("percent", "Razones financieras", "Liquidez, deuda y rentabilidad."),
            ("bar-chart", "Gráficas", "Visualiza cambios y composición."),
            ("file-text", "Reporte gerencial", "Exporta un PDF."),
            ("search", "Consulta por folio", "Recupera un análisis guardado."),
        ]
        for start in range(0, len(tiles), 3):
            for col, (ic, name, desc) in zip(st.columns(3), tiles[start:start + 3]):
                with col:
                    with st.container(border=True):
                        H(f'<div class="tile"><span class="tile-mark"></span><span class="tile-ic">{icon(ic)}</span>'
                          f'<h3>{esc(name)}</h3><p>{esc(desc)}</p></div>')
                        if st.button("Abrir", key="tile_" + name, **STRETCH):
                            go(name)

        st.subheader("Actividad reciente")
        spec = [3, 2.4, 1.6, 1.1]
        for c, title in zip(st.columns(spec), ["Empresa y folio", "Comparación", "Creado", ""]):
            H(f'<span class="th">{title}</span>', c)
        H('<hr class="row-sep">')
        for r in records[:8]:
            c = st.columns(spec, **_COL_VA)
            H(f'<b>{esc(r["company"])}</b><br><span class="mono">{esc(r["folio"])}</span>', c[0])
            H(f'<span>{esc(r["old_date"])} → {esc(r["new_date"])}</span>', c[1])
            H(f'<span>{esc(r["created_at"][:16].replace("T", " "))}</span>', c[2])
            if c[3].button("Abrir", key="open_" + r["folio"], **STRETCH):
                st.session_state.current_folio = r["folio"]
                go("Hoja verde")
            H('<hr class="row-sep">')


# --------------------------- Administración ---------------------------

elif page == "Administrar usuarios":
    page_header("Administración de usuarios", "Registra cuentas y controla quién puede ingresar.", "Sistema")
    if not is_admin:
        st.error("Acceso exclusivo para administradores.")
        st.stop()

    with st.expander("Registrar nuevo usuario", expanded=False):
        with st.form("new_user_form", border=False):
            c1, c2 = st.columns(2)
            username = c1.text_input("Nuevo usuario")
            role = c2.selectbox("Rol", ["usuario", "admin"])
            password = c1.text_input("Contraseña (mínimo 8 caracteres)", type="password")
            confirm = c2.text_input("Confirmar contraseña", type="password")
            submitted = st.form_submit_button("Registrar usuario", type="primary")
            if submitted:
                if password != confirm:
                    st.error("Las contraseñas no coinciden.")
                else:
                    try:
                        add_user(username, password, role)
                        st.success("Usuario registrado.")
                        st.rerun()
                    except (ValueError, sqlite3.IntegrityError) as e:
                        st.error(str(e))

    with db() as con:
        users = con.execute("SELECT id,username,role,active,created_at FROM users ORDER BY id").fetchall()

    st.subheader("Usuarios")
    st.dataframe(
        [{"ID": u["id"], "Usuario": u["username"], "Rol": u["role"],
          "Estado": "Activo" if u["active"] else "Inactivo", "Creado": u["created_at"]} for u in users],
        **STRETCH, hide_index=True
    )

    st.subheader("Cambiar estado de una cuenta")
    others = {f'{u["username"]} · {u["role"]} · {"activo" if u["active"] else "inactivo"}': u["id"] for u in users}
    with st.form("user_status_form"):
        c1, c2 = st.columns(2)
        target_label = c1.selectbox("Usuario", list(others.keys()))
        status = c2.selectbox("Estado", ["Activo", "Desactivar"])
        submitted = st.form_submit_button("Actualizar estado")
        if submitted:
            target_id = others[target_label]
            with db() as con:
                target = con.execute("SELECT * FROM users WHERE id=?", (target_id,)).fetchone()
                if not target:
                    st.error("Usuario no encontrado.")
                elif target["id"] == user["id"]:
                    st.error("No puedes cambiar tu propio estado.")
                elif target["role"] == "admin" and status == "Desactivar":
                    st.error("No desactives cuentas administradoras desde este formulario.")
                else:
                    con.execute("UPDATE users SET active=? WHERE id=?", (1 if status == "Activo" else 0, target_id))
                    st.success("Estado actualizado.")
                    st.rerun()


# --------------------------- Nuevo análisis ---------------------------

elif page == "Nuevo análisis":
    page_header("Nuevo análisis financiero", "Confirma los datos de la empresa, captura los saldos y guarda.", "Análisis")
    stepper_slot = st.empty()

    with st.form("company_form"):
        c1, c2 = st.columns(2)
        company = c1.text_input("Razón social *", value=st.session_state.get("draft_company", ""))
        rfc = c2.text_input("RFC", value=st.session_state.get("draft_rfc", ""))
        activity = c1.text_input("Actividad económica", value=st.session_state.get("draft_activity", ""))
        currency = c2.selectbox("Moneda", ["MXN", "USD", "EUR"])
        comparison_type = st.selectbox("Tipo de comparación", ["Mes contra mes", "Año contra año", "Fecha contra fecha"])
        if comparison_type == "Año contra año":
            c3, c4 = st.columns(2)
            year_old = c3.number_input("Año anterior", 1900, 2200, max(1900, date.today().year - 1))
            year_new = c4.number_input("Año reciente", 1900, 2200, date.today().year)
            old_date = date(int(year_old), 12, 31)
            new_date = date(int(year_new), 12, 31)
        elif comparison_type == "Mes contra mes":
            c3, c4 = st.columns(2)
            old_date = c3.date_input("Fecha de cierre anterior", date(date.today().year - 1, 12, 31))
            new_date = c4.date_input("Fecha de cierre reciente", date.today())
        else:
            c3, c4 = st.columns(2)
            old_date = c3.date_input("Fecha anterior", date(date.today().year - 1, 12, 31))
            new_date = c4.date_input("Fecha reciente", date.today())
        save_company = st.form_submit_button("Confirmar datos generales", type="primary")

    if save_company:
        if not company.strip():
            st.error("La razón social es obligatoria.")
        elif new_date <= old_date:
            st.error("La fecha reciente debe ser posterior a la anterior.")
        else:
            st.session_state.draft_company = company.strip()
            st.session_state.draft_rfc = rfc.strip()
            st.session_state.draft_activity = activity.strip()
            st.session_state.draft_currency = currency
            st.session_state.draft_comparison_type = comparison_type
            st.session_state.draft_old_date = old_date.isoformat()
            st.session_state.draft_new_date = new_date.isoformat()
            st.success("Datos generales confirmados.")

    required_keys = ["draft_company", "draft_currency", "draft_old_date", "draft_new_date", "draft_comparison_type"]
    ready = all(k in st.session_state for k in required_keys)
    H(stepper_html(2 if ready else 1, ["Datos generales", "Captura de cuentas", "Guardar y analizar"]), stepper_slot)
    if not ready:
        st.info("Confirma los datos generales para abrir la captura de cuentas.")
        st.stop()

    st.subheader("Captura del balance y cuentas complementarias")
    H(f'<div class="chips"><span class="chip"><b>{esc(st.session_state.draft_company)}</b></span>'
      f'<span class="chip">{esc(st.session_state.draft_old_date)} → {esc(st.session_state.draft_new_date)}</span>'
      f'<span class="chip">{esc(st.session_state.draft_currency)}</span></div>')
    st.info(
        "Captura saldos contables en ambos periodos. Las cuentas del estado de resultados son opcionales "
        "y solo alimentan las razones de rentabilidad; no se suman al activo, pasivo ni capital. "
        "**Pulsa «Aplicar cambios» en cada sección que edites antes de guardar.**"
    )

    if "draft_accounts" not in st.session_state:
        st.session_state.draft_accounts = base_accounts()

    with st.expander("Agregar un concepto que no está en el catálogo"):
        with st.form("add_account_form", border=False):
            c1, c2 = st.columns([2, 2])
            new_concept = c1.text_input("Nombre del concepto")
            new_category = c2.selectbox("Tipo de cuenta", list(CATALOGO.keys()))
            add_account = st.form_submit_button("Agregar concepto")
            if add_account:
                if not new_concept.strip():
                    st.warning("Escribe el nombre del concepto.")
                elif any(x["Concepto"].casefold() == new_concept.strip().casefold() for x in st.session_state.draft_accounts):
                    st.warning("Ese concepto ya existe.")
                else:
                    st.session_state.draft_accounts.append({
                        "Concepto": new_concept.strip(), "Categoria": new_category,
                        "Anterior": 0.0, "Reciente": 0.0
                    })
                    st.rerun()

    for category in CATALOGO:
        with st.expander(category, expanded=(category == "Activo circulante")):
            all_df = pd.DataFrame(st.session_state.draft_accounts)
            sub = all_df[all_df["Categoria"] == category][["Concepto", "Anterior", "Reciente"]].copy()
            edited = st.data_editor(
                sub, key="edit_" + category, num_rows="dynamic",
                **STRETCH, hide_index=True,
                column_config={
                    "Concepto": st.column_config.TextColumn("Concepto", required=True),
                    "Anterior": st.column_config.NumberColumn(st.session_state.draft_old_date, min_value=0.0, step=100.0, format="%.2f"),
                    "Reciente": st.column_config.NumberColumn(st.session_state.draft_new_date, min_value=0.0, step=100.0, format="%.2f")
                }
            )
            if st.button("Aplicar cambios · " + category, key="apply_" + category):
                remaining = [x for x in st.session_state.draft_accounts if x["Categoria"] != category]
                for _, row in edited.iterrows():
                    concept = str(row.get("Concepto", "")).strip()
                    if concept:
                        remaining.append({
                            "Concepto": concept, "Categoria": category,
                            "Anterior": max(0.0, float(row.get("Anterior", 0) or 0)),
                            "Reciente": max(0.0, float(row.get("Reciente", 0) or 0))
                        })
                # Rechaza nombres duplicados para evitar saldos ambiguos.
                names = [x["Concepto"].casefold() for x in remaining]
                if len(names) != len(set(names)):
                    st.error("Hay conceptos duplicados. Corrígelos antes de aplicar.")
                else:
                    st.session_state.draft_accounts = remaining
                    st.success("Cambios aplicados.")
                    st.rerun()

    st.divider()
    filled = sum(1 for x in st.session_state.draft_accounts if x["Anterior"] or x["Reciente"])
    H(f'<div class="chips"><span class="chip"><b>{filled}</b> de {len(st.session_state.draft_accounts)} cuentas con saldo aplicado</span></div>')
    if st.button("Generar hoja verde y guardar análisis", type="primary"):
        df = clean_accounts(st.session_state.draft_accounts)
        if df.empty:
            st.error("Captura al menos una cuenta.")
        else:
            folio = "FIN-" + datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8].upper()
            now = datetime.now().isoformat(timespec="seconds")
            with db() as con:
                con.execute("""
                    INSERT INTO analyses(
                      folio,owner_id,company,rfc,activity,currency,comparison_type,
                      old_date,new_date,accounts_json,adjustments_json,ratios_json,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    folio, user["id"], st.session_state.draft_company,
                    st.session_state.get("draft_rfc", ""),
                    st.session_state.get("draft_activity", ""),
                    st.session_state.draft_currency,
                    st.session_state.draft_comparison_type,
                    st.session_state.draft_old_date,
                    st.session_state.draft_new_date,
                    json.dumps(df.to_dict("records"), ensure_ascii=False),
                    "{}", "[]", now
                ))
            st.session_state.current_folio = folio
            st.session_state.page = "Hoja verde"
            st.rerun()


# --------------------------- Cargar análisis actual ---------------------------

elif page in ["Hoja verde", "Razones financieras", "Gráficas", "Reporte gerencial"]:
    folio = st.session_state.get("current_folio")
    record = owner_analysis(folio, user["id"]) if folio else None
    if not record:
        page_header(page, "Esta sección trabaja sobre un análisis guardado.", "Resultados")
        empty_state("file-plus", "No hay un análisis abierto",
                    "Crea uno nuevo o recupera uno guardado con su folio.")
        c1, c2, _ = st.columns([1, 1, 2])
        if c1.button("Nuevo análisis", type="primary", **STRETCH, key="empty_new"):
            go("Nuevo análisis")
        if c2.button("Consulta por folio", **STRETCH, key="empty_lookup"):
            go("Consulta por folio")
        st.stop()

    df = clean_accounts(json.loads(record["accounts_json"]))
    overrides = json.loads(record["adjustments_json"] or "{}")
    sheet = green_sheet(df, overrides)
    old_totals = totals(df, "Anterior")
    new_totals = totals(df, "Reciente")
    cur = record["currency"]

    page_header(record["company"],
                f"Folio {record['folio']} · {record['old_date']} → {record['new_date']} · {cur}", page)

    # ----- Hoja verde -----
    if page == "Hoja verde":
        kpi_row([
            ("Aumentos acumulados", fmt_money(sheet["Aumento"].sum()), cur, "", "up"),
            ("Disminuciones acumuladas", fmt_money(sheet["Disminucion"].sum()), cur, "", "down"),
            ("Cambio neto de cuentas", fmt_money(sheet["Cambio"].sum()), cur, "", "brand"),
        ])

        st.subheader("Hoja verde comparativa")
        view = sheet[["Concepto", "Categoria", "Anterior", "Reciente", "Aumento", "Disminucion",
                      "Origen / Aplicación", "Actividad"]].rename(
            columns={"Categoria": "Categoría", "Disminucion": "Disminución"})
        flow_styles = {
            "Origen": "background-color:#E6F4EE;color:#0B5D3B;font-weight:600",
            "Aplicación": "background-color:#E8EFFA;color:#0A2A5E;font-weight:600",
            "Revisar": "background-color:#FFF3D6;color:#6B4000;font-weight:600",
        }
        styler = view.style.format("{:,.2f}", subset=["Anterior", "Reciente", "Aumento", "Disminución"])
        styler = (getattr(styler, "map", None) or styler.applymap)(
            lambda v: flow_styles.get(v, "color:#55657D"), subset=["Origen / Aplicación"])
        st.dataframe(styler, **STRETCH, hide_index=True)
        st.caption("Origen: fuente de recursos · Aplicación: uso de recursos · Revisar: requiere tu criterio.")

        st.subheader("Resumen por actividad")
        flow_summary = sheet[sheet["Actividad"] != "Sin movimiento"].groupby(
            ["Actividad", "Origen / Aplicación"], as_index=False)["Cambio"].sum()
        if flow_summary.empty:
            st.info("Aún no hay variaciones entre los dos periodos.")
        else:
            st.dataframe(flow_summary.style.format({"Cambio": "{:,.2f}"}),
                         **STRETCH, hide_index=True)

        with st.expander("Revisar clasificación por concepto"):
            st.caption(
                "El sistema propone la actividad según la naturaleza de la cuenta. "
                "Corrígela cuando la operación real tenga otra naturaleza. Solo se listan cuentas con movimiento."
            )
            options = [
                "Automático",
                "Origen | Operación", "Aplicación | Operación",
                "Origen | Inversión", "Aplicación | Inversión",
                "Origen | Financiamiento", "Aplicación | Financiamiento",
                "Origen | Revisar", "Aplicación | Revisar"
            ]
            moving = sheet.loc[sheet["Cambio"].abs() >= 0.005, "Concepto"].tolist()
            if not moving:
                st.info("No hay cuentas con movimiento para clasificar.")
            else:
                with st.form("override_form", border=False):
                    selected = {}
                    cols = st.columns(2)
                    for i, concept in enumerate(moving):
                        current = overrides.get(concept, "Automático")
                        selected[concept] = cols[i % 2].selectbox(
                            concept, options,
                            index=options.index(current) if current in options else 0,
                            key="override_" + concept
                        )
                    save_overrides = st.form_submit_button("Guardar clasificaciones", type="primary")
                if save_overrides:
                    with db() as con:
                        con.execute(
                            "UPDATE analyses SET adjustments_json=? WHERE folio=? AND owner_id=?",
                            (json.dumps({**overrides, **selected}, ensure_ascii=False), folio, user["id"])
                        )
                    st.success("Clasificaciones guardadas.")
                    st.rerun()

        st.info(
            "La hoja verde identifica fuentes y usos de recursos por variaciones de cuentas. "
            "El flujo formal de efectivo requiere información adicional sobre operaciones "
            "reales de caja/bancos, ajustes no monetarios y el estado de resultados."
        )
        st.download_button(
            "Exportar hoja verde a CSV",
            sheet.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{folio}_hoja_verde.csv", mime="text/csv"
        )

    # ----- Razones financieras -----
    elif page == "Razones financieras":
        st.info(
            "Para rentabilidad y rotaciones captura las cuentas del estado de resultados. "
            "Las rotaciones con saldos finales son aproximaciones; idealmente se usan saldos promedio y compras netas."
        )
        c1, c2 = st.columns([3, 1])
        chosen = c1.multiselect("Razones a calcular", list(RATIO_DEFS.keys()), default=["Razón circulante"])
        period = c2.radio("Periodo", ["Anterior", "Reciente"], horizontal=True)
        if st.button("Calcular y guardar razones", type="primary", disabled=not chosen):
            t = old_totals if period == "Anterior" else new_totals
            existing = json.loads(record["ratios_json"] or "[]")
            for name in chosen:
                result = calc_ratio(name, t, period)
                existing = [r for r in existing if not (r["Razón"] == name and r["Periodo"] == period)]
                existing.append(result)
            with db() as con:
                con.execute(
                    "UPDATE analyses SET ratios_json=? WHERE folio=? AND owner_id=?",
                    (json.dumps(existing, ensure_ascii=False), folio, user["id"])
                )
            st.success("Razones guardadas.")
            st.rerun()

        ratios = json.loads(record["ratios_json"] or "[]")
        if not ratios:
            empty_state("percent", "Aún no has calculado razones",
                        "Elige una o varias razones, el periodo y pulsa «Calcular y guardar razones».")
        else:
            st.subheader(f"Resultados guardados ({len(ratios)})")
            cards = ""
            for ratio in ratios:
                value = ratio.get("Resultado")
                unit = ratio.get("Unidad", "")
                if value is None:
                    big, small = "No calculable", ""
                elif unit == "moneda":
                    big, small = fmt_money(value), cur
                else:
                    big, small = f"{value:,.2f}", ("%" if unit == "%" else unit)
                tone = "warn" if value is None else ""
                cards += (
                    f'<div class="ratio"><div class="ratio-top"><span class="ratio-name">{esc(ratio["Razón"])}</span>'
                    f'{badge(ratio["Periodo"], tone or "")}</div>'
                    f'<div class="ratio-value">{esc(big)}<small>{esc(small)}</small></div>'
                    f'<dl><dt>Fórmula</dt><dd>{esc(ratio["Fórmula"])}</dd>'
                    f'<dt>Sustitución</dt><dd class="mono">{esc(ratio["Sustitución"])}</dd></dl>'
                    f'<p>{esc(ratio["Interpretación"])}</p></div>'
                )
            H(f'<div class="ratios">{cards}</div>')
            with st.expander("Ver tabla de razones"):
                st.dataframe(pd.DataFrame(ratios), **STRETCH, hide_index=True)

            if not st.session_state.get("confirm_delete_ratios"):
                if st.button("Eliminar todas las razones guardadas"):
                    st.session_state.confirm_delete_ratios = True
                    st.rerun()
            else:
                st.warning("Se eliminarán todas las razones guardadas de este análisis. Esta acción no se puede deshacer.")
                c1, c2, _ = st.columns([1, 1, 2])
                if c1.button("Sí, eliminar", type="primary", **STRETCH):
                    with db() as con:
                        con.execute("UPDATE analyses SET ratios_json='[]' WHERE folio=? AND owner_id=?",
                                    (folio, user["id"]))
                    st.session_state.confirm_delete_ratios = False
                    st.rerun()
                if c2.button("Cancelar", **STRETCH):
                    st.session_state.confirm_delete_ratios = False
                    st.rerun()

    # ----- Gráficas -----
    elif page == "Gráficas":
        c1, c2 = st.columns([2, 1])
        chart_type = c1.selectbox("Tipo de gráfica", [
            "Barras comparativas", "Líneas comparativas",
            "Dispersión de puntos", "Histograma de variaciones",
            "Composición por categoría", "Aumentos y disminuciones"
        ])
        period = None
        if chart_type == "Composición por categoría":
            period = c2.radio("Periodo", ["Anterior", "Reciente"], horizontal=True)

        # Se omiten cuentas sin saldo en ambos periodos para que la gráfica sea legible.
        base = df[(df["Anterior"] != 0) | (df["Reciente"] != 0)]
        if base.empty:
            empty_state("bar-chart", "Sin saldos para graficar",
                        "Captura importes distintos de cero para ver las gráficas.")
        elif chart_type == "Composición por categoría":
            chart_df = df.groupby("Categoria", as_index=False)[period].sum()
            chart_df = chart_df[chart_df[period] > 0]
            if chart_df.empty:
                st.warning("No hay importes positivos para esta gráfica.")
            else:
                fig = px.pie(chart_df, names="Categoria", values=period, hole=0.58, title="Composición por categoría")
                fig.update_traces(textposition="outside", textinfo="percent+label", marker=dict(line=dict(color="#fff", width=2)))
                fig.update_layout(showlegend=False)
                show_chart(fig)
        elif chart_type == "Histograma de variaciones":
            fig = px.histogram(base, x="Cambio", nbins=15, title="Distribución de variaciones por cuenta")
            fig.update_traces(marker_color="#013E8F", marker_line_color="#fff", marker_line_width=1)
            show_chart(fig)
        elif chart_type == "Dispersión de puntos":
            fig = px.scatter(base, x="Anterior", y="Reciente", color="Categoria",
                             hover_name="Concepto", title="Saldo anterior frente a saldo reciente")
            low = min(float(base["Anterior"].min()), float(base["Reciente"].min()))
            high = max(float(base["Anterior"].max()), float(base["Reciente"].max()))
            fig.add_shape(type="line", x0=low, y0=low, x1=high, y1=high, line=dict(dash="dash", color="#8FA3C0"))
            fig.update_traces(marker=dict(size=10, line=dict(color="#fff", width=1)))
            show_chart(fig)
            st.caption("Sobre la diagonal: sin cambio. Arriba: aumentó. Abajo: disminuyó.")
        elif chart_type == "Líneas comparativas":
            long_df = base.melt(id_vars=["Concepto"], value_vars=["Anterior", "Reciente"],
                                var_name="Periodo", value_name="Saldo")
            fig = px.line(long_df, x="Periodo", y="Saldo", color="Concepto", markers=True, title="Saldos por periodo")
            show_chart(fig)
        elif chart_type == "Aumentos y disminuciones":
            long_df = base.melt(id_vars=["Concepto"], value_vars=["Aumento", "Disminucion"],
                                var_name="Movimiento", value_name="Importe")
            fig = px.bar(long_df, x="Concepto", y="Importe", color="Movimiento", barmode="group",
                         color_discrete_map=MOVE_COLORS, title="Aumentos y disminuciones")
            fig.update_xaxes(tickangle=-35)
            show_chart(fig)
        else:
            long_df = base.melt(id_vars=["Concepto", "Categoria"], value_vars=["Anterior", "Reciente"],
                                var_name="Periodo", value_name="Saldo")
            fig = px.bar(long_df, x="Concepto", y="Saldo", color="Periodo", barmode="group",
                         color_discrete_map=PERIOD_COLORS, hover_data=["Categoria"], title="Comparación de saldos")
            fig.update_xaxes(tickangle=-35)
            show_chart(fig)

        with st.expander("Ver datos de la gráfica"):
            st.dataframe(df[["Concepto", "Categoria", "Anterior", "Reciente", "Cambio"]],
                         **STRETCH, hide_index=True)

    # ----- Reporte gerencial -----
    elif page == "Reporte gerencial":
        kpi_row([
            ("Activo total reciente", fmt_money(new_totals["Activo total"]), cur, "", "brand"),
            ("Pasivo total reciente", fmt_money(new_totals["Pasivo total"]), cur),
            ("Capital contable", fmt_money(new_totals["Capital total"]), cur),
            ("Capital de trabajo", fmt_money(new_totals["Capital de trabajo"]), cur, "",
             "up" if new_totals["Capital de trabajo"] > 0 else "down" if new_totals["Capital de trabajo"] < 0 else ""),
        ])

        st.subheader("Observaciones automáticas")
        difference = new_totals["Activo total"] - new_totals["Pasivo más capital"]
        if abs(difference) < 0.01:
            st.success("El balance reciente cuadra aritméticamente.")
        else:
            st.warning(
                f"El balance reciente no cuadra: activo total menos pasivo y capital = "
                f"{money(difference, cur)}. Revisa las cuentas capturadas."
            )
        if new_totals["Activo total"] != 0:
            debt_pct = new_totals["Pasivo total"] / new_totals["Activo total"] * 100
            st.write(f"El pasivo representa {debt_pct:.2f}% del activo total.")
        else:
            st.write("No es posible calcular endeudamiento porque el activo total es cero.")
        st.write(
            "El capital de trabajo es "
            + ("positivo" if new_totals["Capital de trabajo"] > 0 else "negativo" if new_totals["Capital de trabajo"] < 0 else "igual a cero")
            + f": {money(new_totals['Capital de trabajo'], cur)}."
        )

        ratios = json.loads(record["ratios_json"] or "[]")
        st.subheader("Exportar")
        st.caption(
            f"El PDF incluye la hoja verde y {len(ratios)} razón(es) guardada(s)."
            if ratios else
            "El PDF incluye la hoja verde. Calcula razones en «Razones financieras» para añadirlas al reporte."
        )
        pdf = make_pdf(record, sheet, ratios, new_totals)
        st.download_button(
            "Descargar reporte gerencial PDF", pdf,
            file_name=f"{folio}_reporte_gerencial.pdf",
            mime="application/pdf", type="primary"
        )


# --------------------------- Consulta por folio ---------------------------

elif page == "Consulta por folio":
    page_header("Consulta por folio", "Solo puedes abrir los análisis asociados a tu usuario.", "Análisis")
    with st.form("lookup_form"):
        search_folio = st.text_input("Folio completo", placeholder="FIN-20260101-AB12CD34")
        searched = st.form_submit_button("Consultar análisis", type="primary")
    if searched:
        found = owner_analysis(search_folio.strip().upper(), user["id"])
        if not found:
            st.session_state.lookup_folio = None
            st.error("Folio no encontrado o no tienes permiso para consultarlo.")
        else:
            st.session_state.lookup_folio = found["folio"]
            st.session_state.current_folio = found["folio"]
            st.rerun()

    lookup = st.session_state.get("lookup_folio")
    record = owner_analysis(lookup, user["id"]) if lookup else None
    if record:
        H(f'<div class="chips">{badge("Análisis recuperado", "ok")}</div>')
        kpi_row([
            ("Empresa", record["company"], "", "", "brand"),
            ("RFC", record["rfc"] or "No indicado"),
            ("Comparación", f"{record['old_date']} → {record['new_date']}"),
            ("Creado", record["created_at"].replace("T", " ")),
        ])
        if btn("Abrir hoja verde", "table_view", type="primary", key="lookup_open"):
            go("Hoja verde")
        st.subheader("Cuentas capturadas")
        st.dataframe(pd.DataFrame(json.loads(record["accounts_json"])), **STRETCH, hide_index=True)