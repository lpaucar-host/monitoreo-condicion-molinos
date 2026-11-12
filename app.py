import html
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import APP_TITLE, EXCEL_PATH, COLORES, UI
from calculos import (
    cargar_mediciones, resumen_fuente, tabla_prueba_limites,
    estado_actual_por_punto, estado_actual_por_equipo,
    tendencia_ultimas_6_velocidad, tendencia_global_velocidad,
    observaciones_recientes, prioridad_actual, jackknife_velocidad,
    rachas_condicion, resumen_rachas, eventos_mantenimiento_observados,
    cobertura_monitoreo, proyeccion_lineal_punto,
    eventos_mantenimiento_detalle, evento_mantenimiento_relevante,
    rachas_operativas_velocidad, confiabilidad_ciclo_actual,
    ciclos_mantenimiento, cobertura_global,
)

from espectros import (
    cargar_directorio_espectros, espectro_por_clave, evolucion_rms,
    matriz_evolucion, resumen_comparativo, picos_locales, energia_banda,
    familia_armonica, unidad_amplitud, rms_espectral,
    datos_mecanicos_equipo, diagnostico_contraeje_molino1a,
    metricas_engranaje, metricas_familia_candidata_rodamiento,
)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------
# ESTILO GENERAL
# ---------------------------------------------------------------------
st.markdown(f"""
<style>
/* Oculta elementos propios de Streamlit que muestran textos en inglés. */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {{
    display:none !important;
}}
header[data-testid="stHeader"] {{
    display:none !important;
}}

.stApp {{
    background:{UI['bg']};
}}

.block-container {{
    max-width:none;
    width:100%;
    padding-top:1.20rem;
    padding-bottom:1.15rem;
    padding-left:1.05rem;
    padding-right:1.05rem;
}}

[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] {{
    display:none !important;
}}

.exec-header {{
    background:linear-gradient(100deg,{UI['navy_dark']} 0%,{UI['navy']} 100%);
    border-radius:13px;
    padding:13px 19px 14px 19px;
    margin:0 0 10px 0;
    color:#fff;
    min-height:70px;
    display:flex;
    flex-direction:column;
    justify-content:center;
    overflow:visible;
}}
.exec-title {{
    font-size:1.31rem;
    font-weight:800;
    line-height:1.25;
    margin:0;
    padding:0;
    white-space:normal;
    letter-spacing:.01em;
}}
.exec-subtitle {{
    font-size:.81rem;
    opacity:.90;
    margin-top:4px;
    line-height:1.3;
}}

.section-title {{
    font-size:.98rem;
    font-weight:780;
    color:{UI['navy_dark']};
    margin:7px 0 6px 0;
}}

.note {{
    color:{UI['muted']};
    font-size:.72rem;
    line-height:1.35;
}}

.kpi-card {{
    --accent:{UI['navy']};
    background:#fff;
    border:1px solid {UI['border']};
    border-left:5px solid var(--accent);
    border-radius:12px;
    padding:10px 11px;
    min-height:88px;
    box-shadow:0 1px 3px rgba(11,42,69,.06);
    display:flex;
    gap:9px;
    align-items:flex-start;
}}
.kpi-icon {{
    flex:0 0 31px;
    width:31px;
    height:31px;
    border-radius:9px;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:1.02rem;
    background:color-mix(in srgb, var(--accent) 12%, white);
    color:var(--accent);
    border:1px solid color-mix(in srgb, var(--accent) 25%, white);
}}
.kpi-body {{min-width:0;}}
.kpi-label {{
    font-size:.72rem;
    color:{UI['muted']};
    font-weight:670;
    margin-bottom:4px;
    line-height:1.2;
}}
.kpi-value {{
    font-size:1.34rem;
    color:{UI['navy_dark']};
    font-weight:800;
    line-height:1.05;
}}
.kpi-note {{
    font-size:.67rem;
    color:{UI['muted']};
    margin-top:4px;
    line-height:1.25;
}}

.mill-card {{
    background:#fff;
    border:1px solid {UI['border']};
    border-left:6px solid var(--status-color);
    border-radius:12px;
    padding:10px 11px;
    min-height:140px;
    box-shadow:0 1px 3px rgba(11,42,69,.06);
    position:relative;
}}
.mill-card.priority {{
    box-shadow:0 0 0 2px #2B6CB0 inset,0 2px 7px rgba(18,58,99,.12);
}}
.priority-chip {{
    position:absolute;
    right:7px;
    bottom:7px;
    font-size:.58rem;
    font-weight:800;
    color:#1E5A91;
    background:#EAF2FA;
    border:1px solid #BFD3E8;
    border-radius:999px;
    padding:2px 6px;
}}
.mill-top {{
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    gap:7px;
}}
.mill-name {{
    font-size:.93rem;
    font-weight:800;
    color:{UI['navy_dark']};
}}
.tag {{
    font-size:.62rem;
    color:#78909C;
    margin-top:1px;
}}
.badge {{
    display:inline-block;
    padding:3px 7px;
    border-radius:999px;
    font-size:.62rem;
    font-weight:800;
    color:var(--status-color);
    background:color-mix(in srgb,var(--status-color) 8%,white);
    border:1px solid var(--status-color);
    white-space:nowrap;
}}
.mill-main {{
    font-size:.71rem;
    color:#334155;
    margin-top:8px;
    line-height:1.45;
}}
.mill-main strong {{color:#17212B;}}

/* Tablas propias: evita menús y textos del componente de tabla de Streamlit. */
.table-wrap {{
    width:100%;
    overflow-x:auto;
    background:white;
    border:1px solid {UI['border']};
    border-radius:10px;
}}
.exec-table {{
    width:100%;
    border-collapse:collapse;
    font-size:.70rem;
    color:#263442;
}}
.exec-table th {{
    background:#EAF0F6;
    color:#385066;
    font-weight:760;
    text-align:left;
    padding:6px 7px;
    border-bottom:1px solid #D4DEE8;
    white-space:nowrap;
}}
.exec-table td {{
    padding:5px 7px;
    border-bottom:1px solid #E7EDF3;
    vertical-align:middle;
}}
.exec-table tbody tr:nth-child(even) td {{
    background:#FAFBFC;
}}
.exec-table tbody tr:last-child td {{
    border-bottom:none;
}}
.state-pill {{
    display:inline-block;
    color:#fff;
    font-size:.60rem;
    font-weight:800;
    padding:2px 7px;
    border-radius:999px;
    white-space:nowrap;
}}
.trend-up {{
    color:#B45309;
    font-weight:760;
}}
.trend-down {{
    color:#237A46;
    font-weight:760;
}}
.trend-flat {{
    color:#64748B;
    font-weight:700;
}}

div[data-testid="stPlotlyChart"] {{
    background:#fff;
    border:1px solid {UI['border']};
    border-radius:12px;
    padding:2px 3px 0 3px;
}}
div[data-testid="stSelectbox"] label,
div[data-testid="stRadio"] label {{
    color:#34495E !important;
    font-size:.74rem !important;
}}
hr {{
    margin:.6rem 0 !important;
}}

</style>
""", unsafe_allow_html=True)

# Estilos adicionales de Análisis por Equipo + corrección del panel lateral.
st.markdown("""
<style>
/* Dashboard puro: sin panel lateral ni control de expansión. */
header[data-testid="stHeader"] {
    display:none !important;
}
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] {
    display:none !important;
}
.block-container {
    max-width:none !important;
    width:100% !important;
    padding-left:.70rem !important;
    padding-right:.70rem !important;
}

.analysis-chip {
    display:inline-flex;
    align-items:center;
    gap:6px;
    font-size:.67rem;
    font-weight:760;
    color:#334155;
    background:#F8FAFC;
    border:1px solid #D9E2EC;
    border-radius:999px;
    padding:4px 8px;
    margin-right:4px;
}
.tech-summary {
    background:#FFFFFF;
    border:1px solid #D9E2EC;
    border-left:5px solid #123A63;
    border-radius:12px;
    padding:11px 13px;
    min-height:132px;
}
.tech-summary-title {
    font-size:.83rem;
    font-weight:800;
    color:#0B2A45;
    margin-bottom:6px;
}
.tech-line {
    font-size:.71rem;
    color:#334155;
    line-height:1.5;
    margin-bottom:3px;
}
.var-card {
    --accent:#2563EB;
    background:#fff;
    border:1px solid #D9E2EC;
    border-top:4px solid var(--accent);
    border-radius:10px;
    padding:8px 9px;
    min-height:82px;
}
.var-label {
    font-size:.65rem;
    color:#64748B;
    font-weight:700;
}
.var-value {
    font-size:1.00rem;
    font-weight:800;
    color:#17212B;
    margin-top:2px;
}
.var-note {
    font-size:.60rem;
    color:#64748B;
    margin-top:3px;
    line-height:1.25;
}

.exec-header-nav {
    display:flex !important;
    flex-direction:row !important;
    align-items:center !important;
    justify-content:space-between !important;
    gap:14px !important;
    min-height:62px !important;
    padding:9px 12px 9px 17px !important;
}
.header-main {
    flex:1 1 auto;
    min-width:300px;
}
.header-actions {
    display:flex;
    align-items:center;
    justify-content:flex-end;
    gap:7px;
    flex:0 0 auto;
}
.top-nav-wrap {
    display:flex;
    align-items:center;
    gap:4px;
    flex-wrap:nowrap;
}
.top-nav {
    display:inline-flex;
    align-items:center;
    justify-content:center;
    height:27px;
    padding:0 8px;
    border-radius:7px;
    color:#DCEAF6 !important;
    text-decoration:none !important;
    font-size:.64rem;
    font-weight:740;
    border:1px solid rgba(255,255,255,.14);
    background:rgba(255,255,255,.05);
    white-space:nowrap;
}
.top-nav:hover {
    background:rgba(255,255,255,.14);
    color:#FFFFFF !important;
}
.top-nav.active {
    background:#FFFFFF;
    color:#123A63 !important;
    border-color:#FFFFFF;
}
.top-nav.disabled {
    opacity:.42;
    cursor:default;
}
.refresh-btn {
    display:inline-flex;
    align-items:center;
    justify-content:center;
    width:29px;
    height:29px;
    border-radius:8px;
    text-decoration:none !important;
    color:#FFFFFF !important;
    border:1px solid rgba(255,255,255,.30);
    background:rgba(255,255,255,.08);
    font-size:1.03rem;
    font-weight:800;
    line-height:1;
}
.refresh-btn:hover {
    background:rgba(255,255,255,.18);
}
@media (max-width:1180px) {
    .top-nav {
        padding:0 5px;
        font-size:.58rem;
    }
    .exec-title {
        font-size:1.10rem !important;
    }
}

</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Leyendo Excel y calculando indicadores...")
def load_data(_mtime: float):
    return cargar_mediciones()

@st.cache_data(show_spinner=False)
def load_tendencias(_mtime: float):
    return tendencia_ultimas_6_velocidad(load_data(_mtime))


@st.cache_data(show_spinner=False)
def load_prioridad(_mtime: float, dias_vigencia: int = 30):
    datos = load_data(_mtime)
    return prioridad_actual(
        datos,
        dias_vigencia=dias_vigencia,
        tendencias=load_tendencias(_mtime),
    )


@st.cache_data(show_spinner=False)
def load_jackknife(_mtime: float):
    datos = load_data(_mtime)
    return jackknife_velocidad(datos, tendencias=load_tendencias(_mtime))


@st.cache_data(show_spinner=False)
def load_cobertura_global(_mtime: float, ventana: int):
    return cobertura_global(load_data(_mtime), int(ventana))


@st.cache_data(show_spinner=False)
def load_proyeccion(_mtime: float, equipo: str, cod_punto: str):
    return proyeccion_lineal_punto(load_data(_mtime), equipo, cod_punto)


@st.cache_data(show_spinner=False)
def load_ciclos(_mtime: float, equipo: str, cod_punto: str):
    return ciclos_mantenimiento(load_data(_mtime), equipo, cod_punto)



def _cambiar_pagina_dashboard():
    nuevo = st.session_state.get("_dashboard_nav")
    if nuevo:
        st.query_params["pagina"] = nuevo


def cabecera_dashboard(titulo, subtitulo, activa):
    items = [
        ("resumen", "Resumen"),
        ("analisis", "Análisis"),
        ("prioridad", "Prioridad"),
        ("jackknife", "Jack-knife"),
        ("historico", "Histórico"),
        ("cobertura", "Cobertura"),
        ("espectral", "Espectral"),
    ]
    etiquetas = dict(items)
    slugs = [slug for slug, _ in items]

    recarga = (
        f"<a class='refresh-btn' href='?pagina={activa}&actualizar=1' "
        f"target='_self' title='Actualizar datos'>↻</a>"
    )

    st.markdown(
        f"""
        <div class="exec-header exec-header-nav">
          <div class="header-main">
            <div class="exec-title">{html.escape(titulo)}</div>
            <div class="exec-subtitle">{html.escape(subtitulo)}</div>
          </div>
          <div class="header-actions">
            {recarga}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Navegación interna: mantiene la misma sesión Streamlit y evita
    # una recarga completa del navegador al cambiar de sección.
    if st.session_state.get("_dashboard_nav") != activa:
        st.session_state["_dashboard_nav"] = activa

    st.pills(
        "Sección",
        slugs,
        format_func=lambda slug: etiquetas.get(slug, slug),
        selection_mode="single",
        required=True,
        key="_dashboard_nav",
        on_change=_cambiar_pagina_dashboard,
        label_visibility="collapsed",
        width="stretch",
        wrap=False,
    )


def color_estado(estado):
    return COLORES.get(str(estado), "#78909C")

def fmt_fecha(x):
    return pd.to_datetime(x).strftime("%d/%m/%Y") if pd.notna(x) else "—"

def estado_general(sev):
    return {0:"NORMAL",1:"TOLERABLE",2:"ALERTA",3:"PELIGRO"}.get(int(sev),"SIN DATO")

def badge_estado(estado):
    estado = str(estado)
    color = color_estado(estado)
    return f"<span class='state-pill' style='background:{color}'>{html.escape(estado)}</span>"

def tabla_html(df, estado_col=None, max_rows=None):
    if df is None or df.empty:
        return "<div class='note'>Sin datos para mostrar.</div>"
    view = df.copy()
    if max_rows:
        view = view.head(max_rows)
    headers = "".join(f"<th>{html.escape(str(c))}</th>" for c in view.columns)
    rows = []
    for _, row in view.iterrows():
        cells = []
        for col in view.columns:
            value = row[col]
            if pd.isna(value):
                txt = "—"
            else:
                txt = str(value)
            if estado_col and col == estado_col:
                cell = badge_estado(txt)
            elif col == "Prioridad":
                pcolors = {"P1":"#C62828","P2":"#E86A12","P3":"#D99A00","P4":"#2E7D32"}
                pc = pcolors.get(txt, "#64748B")
                cell = f"<span class='state-pill' style='background:{pc}'>{html.escape(txt)}</span>"
            elif col in ("Cobertura", "Estado cobertura"):
                cc = "#2E7D32" if txt in ("MEDIDO","COMPLETA") else "#C62828"
                cell = f"<span class='state-pill' style='background:{cc}'>{html.escape(txt)}</span>"
            elif col == "Tendencia":
                css = "trend-flat"
                low = txt.lower()
                if "subiendo" in low or txt.startswith("+"):
                    css = "trend-up"
                elif "bajando" in low or txt.startswith("-"):
                    css = "trend-down"
                cell = f"<span class='{css}'>{html.escape(txt)}</span>"
            else:
                cell = html.escape(txt)
            cells.append(f"<td>{cell}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        "<div class='table-wrap'><table class='exec-table'>"
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )

def etiqueta_tendencia(pendiente, r2):
    """
    Traducción ejecutiva de la tendencia.
    R² se usa internamente para evitar conclusiones con datos dispersos,
    pero no se muestra al usuario.
    """
    if pd.isna(pendiente) or pd.isna(r2):
        return "Sin historial suficiente"
    if float(r2) < 0.60:
        return "Sin tendencia clara"
    p = float(pendiente)
    if p > 0:
        return f"Subiendo (+{p:.2f} mm/s/mes)"
    if p < 0:
        return f"Bajando ({p:.2f} mm/s/mes)"
    return "Estable"


def tendencia_codigo(tendencias_df, equipo, codigo):
    """Devuelve etiqueta ejecutiva de tendencia para un código de velocidad."""
    if tendencias_df.empty:
        return "Sin historial suficiente"
    q = tendencias_df[
        (tendencias_df["EquipoCorto"] == equipo)
        & (tendencias_df["CodPunto"] == codigo)
    ]
    if q.empty:
        return "Sin historial suficiente"
    r = q.iloc[0]
    return etiqueta_tendencia(r["Pendiente_mm_s_mes"], r["R2"])

def ultimo_por_tipo_y_punto(mediciones_df, equipo, punto_fisico, tipo):
    q = mediciones_df[
        (mediciones_df["EquipoCorto"] == equipo)
        & (mediciones_df["Punto"].astype(str) == str(punto_fisico))
        & (mediciones_df["TipoVariable"] == tipo)
    ].copy()
    if q.empty:
        return pd.DataFrame()
    return (
        q.sort_values("Fecha")
         .groupby("CodPunto", as_index=False)
         .tail(1)
         .sort_values("Valor", ascending=False)
    )

def serie_punto(mediciones_df, equipo, punto_fisico, tipo, desde, hasta):
    q = mediciones_df[
        (mediciones_df["EquipoCorto"] == equipo)
        & (mediciones_df["Punto"].astype(str) == str(punto_fisico))
        & (mediciones_df["TipoVariable"] == tipo)
        & (mediciones_df["Fecha"].dt.date >= desde)
        & (mediciones_df["Fecha"].dt.date <= hasta)
    ].copy()
    return q.sort_values(["Fecha", "CodPunto"])

def texto_vigencia(fecha_dato, fecha_equipo):
    if pd.isna(fecha_dato):
        return "Sin dato"
    dias = int((pd.to_datetime(fecha_equipo).normalize() - pd.to_datetime(fecha_dato).normalize()).days)
    if dias <= 0:
        return "Última ronda"
    return f"{dias} días antes de la última ronda"

def valor_max_actual(actuales_punto_df, equipo, tipo):
    q = actuales_punto_df[
        (actuales_punto_df["EquipoCorto"] == equipo)
        & (actuales_punto_df["TipoVariable"] == tipo)
    ]
    if q.empty:
        return None
    return q.sort_values("Valor", ascending=False).iloc[0]


def aplicar_estilo_temporal(fig, df, desde, hasta, fecha_col="Fecha"):
    """
    En ventanas largas oculta marcadores para evitar saturación visual.
    No suaviza matemáticamente ni altera los datos: conserva segmentos reales.
    """
    try:
        dias = max((pd.to_datetime(hasta) - pd.to_datetime(desde)).days, 0)
    except Exception:
        dias = 0

    nfechas = (
        int(pd.to_datetime(df[fecha_col]).nunique())
        if df is not None and not df.empty and fecha_col in df.columns
        else 0
    )
    historico_largo = dias > 180 or nfechas > 20

    if historico_largo:
        fig.update_traces(
            mode="lines",
            line=dict(width=2.15, shape="linear"),
        )
    else:
        fig.update_traces(
            mode="lines+markers",
            marker=dict(size=5),
            line=dict(width=2.0, shape="linear"),
        )
    return fig


def equipos_dashboard(mediciones_df):
    return (
        estado_actual_por_equipo(mediciones_df)
        .sort_values("OrdenEquipo")["EquipoCorto"]
        .tolist()
    )


def selector_equipo_compartido(mediciones_df, key="selector_equipo_tecnico"):
    equipos = equipos_dashboard(mediciones_df)
    if "equipo_tecnico" not in st.session_state:
        st.session_state["equipo_tecnico"] = "Molino 1A" if "Molino 1A" in equipos else equipos[0]

    actual = st.session_state["equipo_tecnico"]
    idx = equipos.index(actual) if actual in equipos else 0
    seleccionado = st.selectbox(
        "Equipo",
        equipos,
        index=idx,
        key=key,
    )
    st.session_state["equipo_tecnico"] = seleccionado
    return seleccionado


def prioridad_color(p):
    return {
        "P1":"#C62828",
        "P2":"#E86A12",
        "P3":"#D99A00",
        "P4":"#2E7D32",
    }.get(str(p), "#64748B")


# ---------------------------------------------------------------------
# ACTUALIZACIÓN AUTOMÁTICA DEL EXCEL
# ---------------------------------------------------------------------
@st.fragment(run_every="60s")
def vigilar_excel():
    actual = EXCEL_PATH.stat().st_mtime if EXCEL_PATH.exists() else 0
    previo = st.session_state.get("_excel_mtime")
    if previo is None:
        st.session_state["_excel_mtime"] = actual
    elif actual != previo:
        st.session_state["_excel_mtime"] = actual
        st.cache_data.clear()
        st.rerun()

vigilar_excel()

# ---------------------------------------------------------------------
# CARGA
# ---------------------------------------------------------------------
try:
    mtime = EXCEL_PATH.stat().st_mtime if EXCEL_PATH.exists() else 0
    mediciones = load_data(mtime)
except Exception as e:
    st.error("No se pudo leer el Excel.")
    st.exception(e)
    st.stop()

if mediciones.empty:
    st.warning("No se encontraron mediciones válidas en el Excel.")
    st.stop()

# ---------------------------------------------------------------------
# FUENTE ESPECTRAL LOCAL
# ---------------------------------------------------------------------
ESPECTROS_DIR = Path(__file__).resolve().parent / "espectros" / "Molino_1A" / "Contraeje"


def _firma_espectros(base_dir: Path):
    if not base_dir.exists():
        return (0, 0.0)
    archivos=list(base_dir.rglob("*.csv"))
    if not archivos:
        return (0, 0.0)
    return (len(archivos), max(p.stat().st_mtime for p in archivos))


@st.cache_data(show_spinner="Leyendo espectros MAINTraq...")
def load_espectros(_firma):
    return cargar_directorio_espectros(ESPECTROS_DIR)

# ---------------------------------------------------------------------
# NAVEGACIÓN PRINCIPAL
# ---------------------------------------------------------------------
PAGINAS = {
    "resumen": "Resumen Ejecutivo",
    "analisis": "Análisis por Equipo",
    "prioridad": "Prioridad de Intervención",
    "jackknife": "Jack-knife",
    "historico": "Histórico y Confiabilidad",
    "cobertura": "Cobertura de Monitoreo",
    "espectral": "Diagnóstico Espectral",
    "validacion": "Validación de datos",
}

pagina_slug = st.query_params.get("pagina", "resumen")
if isinstance(pagina_slug, list):
    pagina_slug = pagina_slug[0]
if pagina_slug not in PAGINAS:
    pagina_slug = "resumen"
pagina = PAGINAS[pagina_slug]

# El icono ↻ de la cabecera fuerza una nueva lectura del Excel.
if st.query_params.get("actualizar") is not None:
    st.cache_data.clear()
    st.query_params.clear()
    st.query_params["pagina"] = pagina_slug
    st.rerun()

# =====================================================================
# RESUMEN EJECUTIVO
# =====================================================================
if pagina == "Resumen Ejecutivo":
    info = resumen_fuente(mediciones)
    actuales_punto = estado_actual_por_punto(mediciones)
    actuales_equipo = estado_actual_por_equipo(mediciones).copy()
    tendencias = load_tendencias(mtime)
    actuales_equipo["EstadoEjecutivo"] = actuales_equipo["Severidad"].map(estado_general)

    fecha_global = pd.to_datetime(mediciones["Fecha"].max())
    fechas_disponibles = sorted(pd.to_datetime(mediciones["Fecha"]).dt.date.unique().tolist())
    fecha_fin_default = fechas_disponibles[-1]
    objetivo_inicio = (fecha_global - pd.Timedelta(days=90)).date()
    fecha_ini_default = min(
        fechas_disponibles,
        key=lambda d: abs((d - objetivo_inicio).days)
    )

    cabecera_dashboard(
        "MONITOREO DE CONDICIÓN — MOLINOS",
        "Planta Concentradora Andaychagua · Resumen Ejecutivo de condición, tendencia y atención requerida",
        "resumen",
    )

    # Período sin calendario nativo para evitar textos en inglés.
    p1, p2, p3 = st.columns([.9, .9, 3.2])
    with p1:
        idx_ini = fechas_disponibles.index(fecha_ini_default)
        f_ini = st.selectbox(
            "Desde",
            fechas_disponibles,
            index=idx_ini,
            format_func=lambda d: d.strftime("%d/%m/%Y"),
        )
    with p2:
        fechas_fin = [d for d in fechas_disponibles if d >= f_ini]
        f_fin = st.selectbox(
            "Hasta",
            fechas_fin,
            index=len(fechas_fin)-1,
            format_func=lambda d: d.strftime("%d/%m/%Y"),
        )
    with p3:
        st.markdown(
            "<div class='note' style='padding-top:25px'>"
            "El período modifica únicamente tendencias e históricos. "
            "El estado actual siempre usa la última lectura válida de cada punto."
            "</div>",
            unsafe_allow_html=True,
        )

    # En Resumen, la condición ejecutiva se respalda exclusivamente con velocidad RMS.
    actuales_velocidad = actuales_punto[
        actuales_punto["TipoVariable"].eq("Vibracion-Velocidad")
    ].copy()
    atencion_equipos = int((actuales_equipo["Severidad"] >= 2).sum())
    puntos_alerta = int((actuales_velocidad["Severidad"] == 2).sum())
    puntos_peligro = int((actuales_velocidad["Severidad"] >= 3).sum())

    # Tarjetas KPI con acentos e iconos.
    k1,k2,k3,k4,k5 = st.columns(5)
    kpis = [
        (k1, "🗓", "#2563EB", "Última medición global", fmt_fecha(fecha_global), "Último dato disponible"),
        (k2, "⚙", "#2E7D32", "Equipos monitoreados", f"{info['equipos']} / 5", "Cobertura de equipos"),
        (k3, "!", "#D99A00", "Equipos con atención actual", str(atencion_equipos), "Estado ≥ Alerta"),
        (k4, "▲", "#E86A12", "Puntos actuales en alerta", str(puntos_alerta), "Última lectura válida"),
        (k5, "●", "#C62828", "Puntos en peligro / crítico", str(puntos_peligro), "Prioridad de revisión"),
    ]
    for col, icono, accent, label, value, note in kpis:
        col.markdown(
            f"""
            <div class='kpi-card' style='--accent:{accent}'>
              <div class='kpi-icon'>{icono}</div>
              <div class='kpi-body'>
                <div class='kpi-label'>{label}</div>
                <div class='kpi-value'>{value}</div>
                <div class='kpi-note'>{note}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div class='section-title'>Estado actual de los 5 molinos</div>", unsafe_allow_html=True)
    cards = st.columns(5)
    for col, (_, r) in zip(cards, actuales_equipo.iterrows()):
        estado_exec = r["EstadoEjecutivo"]
        color = color_estado(estado_exec)
        valor = f"{r['ValorDominante']:.2f} {r['UnidadDominante']}" if pd.notna(r["ValorDominante"]) else "—"
        priority = " priority" if r["EquipoCorto"] == "Molino 1A" else ""
        priority_chip = "<span class='priority-chip'>PRIORIDAD</span>" if r["EquipoCorto"] == "Molino 1A" else ""
        with col:
            st.markdown(
                f"""
                <div class='mill-card{priority}' style='--status-color:{color}'>
                  <div class='mill-top'>
                    <div>
                      <div class='mill-name'>{html.escape(str(r['EquipoCorto']))}</div>
                      <div class='tag'>{html.escape(str(r['TAG']))}</div>
                    </div>
                    <span class='badge'>{estado_exec}</span>
                  </div>
                  <div class='mill-main'>
                    Punto dominante: <strong>{html.escape(str(r['CodPuntoDominante']))}</strong><br/>
                    {html.escape(str(r['ComponenteDominante'] or ''))}<br/>
                    Último valor: <strong>{valor}</strong><br/>
                    Última medición: <strong>{fmt_fecha(r['UltimaMedicion'])}</strong><br/>
                    Puntos con atención: <strong>{int(r['PuntosAtencion'])}</strong>
                  </div>
                  {priority_chip}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Dona + Foco Molino 1A
    dcol, fcol = st.columns([.88, 2.12], gap="medium")
    with dcol:
        st.markdown("<div class='section-title'>Distribución del estado actual</div>", unsafe_allow_html=True)
        orden = ["NORMAL","TOLERABLE","ALERTA","PELIGRO"]
        counts = actuales_equipo["EstadoEjecutivo"].value_counts().reindex(orden, fill_value=0)
        donut = pd.DataFrame({"Estado":orden, "Molinos":counts.values})
        donut = donut[donut["Molinos"] > 0]

        figd = go.Figure(go.Pie(
            labels=donut["Estado"],
            values=donut["Molinos"],
            hole=.65,
            marker=dict(colors=[color_estado(x) for x in donut["Estado"]]),
            textinfo="label+value",
            textfont=dict(size=11),
            hovertemplate="<b>%{label}</b><br>Molinos: %{value}<extra></extra>",
            sort=False,
        ))
        figd.add_annotation(
            text=f"<b>{len(actuales_equipo)}</b><br><span style='font-size:10px'>molinos</span>",
            x=.5, y=.5, showarrow=False,
            font=dict(size=19, color=UI["navy_dark"]),
        )
        figd.update_layout(
            height=228,
            margin=dict(l=2,r=2,t=2,b=2),
            showlegend=False,
            paper_bgcolor="white",
        )
        st.plotly_chart(figd, use_container_width=True, config={"displayModeBar":False})
        st.caption("Un estado ejecutivo por molino, igual que las cinco tarjetas.")

    with fcol:
        st.markdown("<div class='section-title'>Foco prioritario — Molino 1A</div>", unsafe_allow_html=True)
        st.caption("Los puntos de velocidad con mayor valor actual. El ranking es por severidad actual.")

        m1 = actuales_punto[
            (actuales_punto["EquipoCorto"]=="Molino 1A")
            & (actuales_punto["TipoVariable"]=="Vibracion-Velocidad")
        ].copy()
        m1 = m1.sort_values("Valor", ascending=False).head(5)

        if m1.empty:
            st.info("No hay lecturas actuales de velocidad para Molino 1A.")
        else:
            trend_idx = tendencias[tendencias["EquipoCorto"]=="Molino 1A"].set_index("CodPunto")
            filas = []
            for _, r in m1.iterrows():
                punto = r["CodPunto"]
                if punto in trend_idx.index:
                    tr = trend_idx.loc[punto]
                    if isinstance(tr, pd.DataFrame):
                        tr = tr.iloc[0]
                    tendencia_txt = etiqueta_tendencia(tr["Pendiente_mm_s_mes"], tr["R2"])
                else:
                    tendencia_txt = "Sin historial suficiente"

                filas.append({
                    "Punto": punto,
                    "Componente": r["Componente"],
                    "Valor actual": f"{r['Valor']:.2f} mm/s",
                    "Estado": r["Estado"],
                    "Tendencia": tendencia_txt,
                })

            foco_df = pd.DataFrame(filas)
            st.markdown(tabla_html(foco_df, estado_col="Estado"), unsafe_allow_html=True)
            st.markdown(
                "<div class='note' style='margin-top:6px'>"
                "<b>Tendencia:</b> “Subiendo” indica que las últimas mediciones muestran un crecimiento consistente. "
                "“Sin tendencia clara” significa que los valores varían demasiado para afirmar una dirección con seguridad."
                "</div>",
                unsafe_allow_html=True,
            )

    # Tendencia global + Top 5
    left, right = st.columns([1.78, .92], gap="medium")
    with left:
        st.markdown("<div class='section-title'>Tendencia global de vibración — máximo RMS por molino y fecha</div>", unsafe_allow_html=True)
        tg = tendencia_global_velocidad(mediciones, f_ini, f_fin)
        if tg.empty:
            st.info("No hay datos de velocidad en el período seleccionado.")
        else:
            series_colors = {
                "Molino 1A":"#0B4F8A",
                "Molino 1":"#3D78A8",
                "Molino 2":"#6B9AC4",
                "Molino 3":"#7C8A96",
                "Molino 4":"#A0AAB4",
            }
            fig = px.line(
                tg,
                x="Fecha",
                y="MaxVelocidad",
                color="EquipoCorto",
                markers=True,
                color_discrete_map=series_colors,
                labels={
                    "Fecha":"",
                    "MaxVelocidad":"Velocidad RMS (mm/s)",
                    "EquipoCorto":"Equipo",
                },
            )
            fig.add_hline(y=3, line_dash="dot", line_color="#2E7D32", opacity=.34)
            fig.add_hline(y=5, line_dash="dot", line_color="#D99A00", opacity=.46)
            fig.add_hline(y=7, line_dash="dot", line_color="#C62828", opacity=.54)
            fig.update_traces(
                hovertemplate="<b>%{fullData.name}</b><br>Fecha: %{x|%d/%m/%Y}<br>Máx. RMS: %{y:.2f} mm/s<extra></extra>"
            )
            aplicar_estilo_temporal(fig, tg, f_ini, f_fin)
            fig.update_layout(
                height=330,
                margin=dict(l=10,r=10,t=12,b=8),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    x=0,
                    title_text="Equipo",
                    font=dict(size=10),
                ),
                paper_bgcolor="white",
                plot_bgcolor="white",
                hovermode="closest",
            )
            fig.update_xaxes(
                showgrid=False,
                tickformat="%d/%m/%Y",
                tickangle=0,
                nticks=8,
            )
            fig.update_yaxes(gridcolor="#E9EEF3")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with right:
        st.markdown("<div class='section-title'>Top 5 — deterioro reciente</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='note'>"
            "Ordena los puntos cuya velocidad viene aumentando de forma consistente en sus últimas mediciones. "
            "Los datos muy dispersos se descartan para evitar falsas alarmas."
            "</div>",
            unsafe_allow_html=True,
        )

        limite_frescura = fecha_global - pd.Timedelta(days=30)
        top = tendencias[
            (tendencias["Pendiente_mm_s_mes"] > 0)
            & (tendencias["R2"] >= .60)
            & (pd.to_datetime(tendencias["UltimaFecha"]) >= limite_frescura)
        ].head(5).copy()

        if top.empty:
            st.success("No hay tendencias positivas suficientemente consistentes para el ranking.")
        else:
            # Estado actual para cada punto del ranking.
            estados_idx = actuales_punto.set_index(["TAG","CodPunto"])["Estado"]
            filas_top = []
            for _, r in top.iterrows():
                estado = estados_idx.get((r["TAG"], r["CodPunto"]), "SIN DATO")
                filas_top.append({
                    "Equipo": r["EquipoCorto"],
                    "Punto": r["CodPunto"],
                    "Último": f"{r['UltimoValor']:.2f} mm/s",
                    "Cambio": f"+{r['Pendiente_mm_s_mes']:.2f} mm/s/mes",
                    "Estado": estado,
                    "Fecha": fmt_fecha(r["UltimaFecha"]),
                })
            st.markdown(
                tabla_html(pd.DataFrame(filas_top), estado_col="Estado"),
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='note' style='margin-top:6px'>"
                "<b>Lectura:</b> valor alto indica severidad actual; cambio positivo sostenido indica deterioro reciente. "
                "Son señales distintas y ambas ayudan a priorizar."
                "</div>",
                unsafe_allow_html=True,
            )

    # Atención + observaciones en paralelo para reducir scroll.
    acol, ocol = st.columns([1.62, 1.00], gap="medium")
    with acol:
        st.markdown("<div class='section-title'>Atención requerida ahora</div>", unsafe_allow_html=True)
        at = actuales_velocidad[actuales_velocidad["Severidad"] >= 2].copy()
        if at.empty:
            st.success("No hay puntos actuales en Alerta, Peligro o Crítico.")
        else:
            at["Equipo"] = at["EquipoCorto"]
            at["Fecha"] = pd.to_datetime(at["Fecha"]).dt.strftime("%d/%m/%Y")
            at["Valor actual"] = at.apply(lambda r:f"{r['Valor']:.2f} {r['Unidad']}", axis=1)
            at = at.sort_values(
                ["Severidad","OrdenEquipo","Valor"],
                ascending=[False,True,False],
            )
            tabla_at = at[[
                "Equipo","CodPunto","Componente","TipoVariable",
                "Valor actual","Estado","Fecha"
            ]].rename(columns={
                "CodPunto":"Punto",
                "TipoVariable":"Variable",
            }).head(12)
            st.markdown(tabla_html(tabla_at, estado_col="Estado"), unsafe_allow_html=True)
            if len(at) > 12:
                st.caption(f"Se muestran los 12 de mayor severidad de {len(at)} puntos que requieren atención.")

    with ocol:
        st.markdown("<div class='section-title'>Últimas observaciones de campo</div>", unsafe_allow_html=True)
        obs = observaciones_recientes(mediciones, limite=6)
        if obs.empty:
            st.markdown("<div class='note'>No hay observaciones registradas.</div>", unsafe_allow_html=True)
        else:
            obs = obs.copy()
            obs["Fecha"] = pd.to_datetime(obs["Fecha"]).dt.strftime("%d/%m/%Y")
            obs = obs.rename(columns={
                "EquipoCorto":"Equipo",
                "CodPunto":"Punto",
                "Observacion":"Observación",
            })
            st.markdown(tabla_html(obs), unsafe_allow_html=True)

    st.markdown(
        "<div class='note' style='margin-top:8px'>"
        "<b>Actualización:</b> el estado de los cinco molinos y la tabla “Atención requerida ahora” "
        "se calculan únicamente con la última lectura válida de velocidad RMS de cada punto. "
        "gE y temperatura quedan como indicadores técnicos de análisis. Al guardar o reemplazar el Excel, "
        "el dashboard detecta el cambio automáticamente (máximo 60 s) o de inmediato con “Actualizar datos”."
        "</div>",
        unsafe_allow_html=True,
    )

# =====================================================================
# ANÁLISIS POR EQUIPO
# =====================================================================
elif pagina == "Análisis por Equipo":
    actuales_punto = estado_actual_por_punto(mediciones)
    actuales_equipo = estado_actual_por_equipo(mediciones).copy()
    tendencias = load_tendencias(mtime)

    equipos_ordenados = (
        actuales_equipo.sort_values("OrdenEquipo")["EquipoCorto"].tolist()
    )
    if "equipo_tecnico" not in st.session_state:
        st.session_state["equipo_tecnico"] = "Molino 1A"

    # Cabecera
    cabecera_dashboard(
        "ANÁLISIS POR EQUIPO — MONITOREO DE CONDICIÓN",
        "Condición actual, evolución por punto físico y lectura técnica del molino seleccionado",
        "analisis",
    )

    # Selector del equipo: esta misma clave se reutilizará en páginas 2–6.
    f1, f2, f3, f4 = st.columns([1.05, 1.18, .82, .82])

    with f1:
        equipo_sel = st.selectbox(
            "Equipo",
            equipos_ordenados,
            index=equipos_ordenados.index(st.session_state["equipo_tecnico"])
                if st.session_state["equipo_tecnico"] in equipos_ordenados else 0,
            key="selector_equipo_tecnico",
        )
        st.session_state["equipo_tecnico"] = equipo_sel

    med_eq = mediciones[mediciones["EquipoCorto"] == equipo_sel].copy()
    act_eq_points = actuales_punto[actuales_punto["EquipoCorto"] == equipo_sel].copy()
    row_eq = actuales_equipo[actuales_equipo["EquipoCorto"] == equipo_sel].iloc[0]
    fecha_eq = pd.to_datetime(act_eq_points["Fecha"].max())

    # Puntos físicos con al menos una medición de velocidad.
    puntos_info = (
        med_eq[med_eq["TipoVariable"] == "Vibracion-Velocidad"][["Punto","Componente"]]
        .dropna()
        .drop_duplicates()
        .sort_values(["Punto","Componente"])
    )
    puntos_labels = {}
    for _, rr in puntos_info.iterrows():
        p = str(rr["Punto"]).replace(".0","")
        puntos_labels[p] = f"{p} · {rr['Componente']}"

    puntos_fisicos = list(puntos_labels.keys())
    if not puntos_fisicos:
        puntos_fisicos = ["—"]
        puntos_labels = {"—":"Sin puntos de velocidad"}

    # Punto físico por defecto:
    # 1) CONTRAEJE con mayor velocidad RMS actual;
    # 2) si no existe, punto de velocidad dominante del equipo;
    # 3) si tampoco existe, primer punto disponible.
    vel_actual_eq = act_eq_points[
        act_eq_points["TipoVariable"].eq("Vibracion-Velocidad")
    ].copy()
    contra_actual = vel_actual_eq[
        vel_actual_eq["Componente"].astype(str).str.upper().str.contains("CONTRAEJE", na=False)
    ].copy()

    if not contra_actual.empty:
        rr_default = contra_actual.sort_values(
            ["Valor", "Fecha"], ascending=[False, False]
        ).iloc[0]
        pdom = str(rr_default["Punto"]).replace(".0", "")
    else:
        dom_match = vel_actual_eq[
            vel_actual_eq["CodPunto"].eq(row_eq["CodPuntoDominante"])
        ]
        if not dom_match.empty:
            pdom = str(dom_match.iloc[0]["Punto"]).replace(".0", "")
        elif not vel_actual_eq.empty:
            rr_default = vel_actual_eq.sort_values(
                ["Severidad", "Valor", "Fecha"],
                ascending=[False, False, False],
            ).iloc[0]
            pdom = str(rr_default["Punto"]).replace(".0", "")
        else:
            pdom = puntos_fisicos[0]

    if pdom not in puntos_fisicos:
        pdom = puntos_fisicos[0]

    # Al cambiar de molino se recalcula el punto recomendado. Después, el usuario
    # puede seleccionar manualmente cualquier otro punto físico.
    if st.session_state.get("_equipo_default_punto_analisis") != equipo_sel:
        st.session_state["_equipo_default_punto_analisis"] = equipo_sel
        st.session_state["punto_fisico_analisis"] = pdom
    elif st.session_state.get("punto_fisico_analisis") not in puntos_fisicos:
        st.session_state["punto_fisico_analisis"] = pdom

    with f2:
        punto_sel = st.selectbox(
            "Punto físico",
            puntos_fisicos,
            format_func=lambda p: puntos_labels.get(p,p),
            key="punto_fisico_analisis",
        )

    fechas_eq = sorted(pd.to_datetime(med_eq["Fecha"]).dt.date.unique().tolist())
    objetivo_inicio = (fecha_eq - pd.Timedelta(days=120)).date()
    fecha_ini_eq = min(fechas_eq, key=lambda d: abs((d-objetivo_inicio).days))
    with f3:
        desde_eq = st.selectbox(
            "Desde",
            fechas_eq,
            index=fechas_eq.index(fecha_ini_eq),
            format_func=lambda d:d.strftime("%d/%m/%Y"),
            key="desde_analisis",
        )
    with f4:
        fechas_hasta = [d for d in fechas_eq if d >= desde_eq]
        hasta_eq = st.selectbox(
            "Hasta",
            fechas_hasta,
            index=len(fechas_hasta)-1,
            format_func=lambda d:d.strftime("%d/%m/%Y"),
            key="hasta_analisis",
        )

    # Datos actuales principales.
    max_vel = valor_max_actual(actuales_punto, equipo_sel, "Vibracion-Velocidad")
    max_temp = valor_max_actual(actuales_punto, equipo_sel, "Temperatura")
    max_acc = valor_max_actual(actuales_punto, equipo_sel, "Vibracion-Aceleracion")
    estado_exec = estado_general(row_eq["Severidad"])
    color_exec = color_estado(estado_exec)

    # KPI técnicos
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    kpis_eq = [
        (k1,"●",color_exec,"Estado actual",estado_exec,
         f"Punto dominante: {row_eq['CodPuntoDominante']}"),
        (k2,"🗓","#2563EB","Última medición",fmt_fecha(fecha_eq),
         str(row_eq["TAG"])),
        (k3,"↕","#E86A12","Velocidad máx.",
         f"{max_vel['Valor']:.2f} mm/s" if max_vel is not None else "Sin dato",
         f"{max_vel['CodPunto']} · {max_vel['Componente']}" if max_vel is not None else ""),
        (k4,"≈","#7C3AED","Aceleración máx.",
         f"{max_acc['Valor']:.2f} gE" if max_acc is not None else "Sin dato",
         (f"{max_acc['CodPunto']} · {fmt_fecha(max_acc['Fecha'])}" if max_acc is not None else "No disponible")),
        (k5,"°","#D97706","Temperatura máx.",
         f"{max_temp['Valor']:.1f} °C" if max_temp is not None else "Sin dato",
         f"{max_temp['CodPunto']} · {max_temp['Estado']}" if max_temp is not None else ""),
        (k6,"!","#C62828","Puntos con atención",
         str(int(((act_eq_points["TipoVariable"] == "Vibracion-Velocidad") & (act_eq_points["Severidad"] >= 2)).sum())),
         "Velocidad: Alerta / Peligro"),
    ]
    for col,icono,accent,label,value,note in kpis_eq:
        col.markdown(
            f"""
            <div class='kpi-card' style='--accent:{accent}'>
              <div class='kpi-icon'>{icono}</div>
              <div class='kpi-body'>
                <div class='kpi-label'>{html.escape(str(label))}</div>
                <div class='kpi-value'>{html.escape(str(value))}</div>
                <div class='kpi-note'>{html.escape(str(note))}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------------
    # Velocidad RMS del punto físico + lectura técnica
    # --------------------------------------------------------------
    vel_col, lectura_col = st.columns([1.72, .88], gap="medium")

    with vel_col:
        st.markdown(
            f"<div class='section-title'>Tendencia de velocidad RMS — {html.escape(puntos_labels.get(punto_sel,punto_sel))}</div>",
            unsafe_allow_html=True,
        )
        sv = serie_punto(
            mediciones, equipo_sel, punto_sel,
            "Vibracion-Velocidad", desde_eq, hasta_eq
        )
        if sv.empty:
            st.info("No hay mediciones de velocidad para este punto en el período.")
        else:
            # H/V/A: colores neutros diferenciables, semáforo queda en límites.
            colores_dir = {
                "Horizontal":"#0B4F8A",
                "Vertical":"#3D78A8",
                "Axial":"#7A5AA6",
            }
            figv = px.line(
                sv,
                x="Fecha",
                y="Valor",
                color="Direccion",
                markers=True,
                color_discrete_map=colores_dir,
                labels={
                    "Fecha":"",
                    "Valor":"Velocidad RMS (mm/s)",
                    "Direccion":"Dirección",
                },
            )
            figv.add_hrect(y0=0,y1=3,fillcolor="#2E7D32",opacity=.035,line_width=0)
            figv.add_hrect(y0=3,y1=5,fillcolor="#D99A00",opacity=.045,line_width=0)
            figv.add_hrect(y0=5,y1=7,fillcolor="#E86A12",opacity=.045,line_width=0)
            figv.add_hrect(y0=7,y1=max(7.1,float(sv["Valor"].max())*1.10),fillcolor="#C62828",opacity=.04,line_width=0)
            figv.add_hline(y=3,line_dash="dot",line_color="#2E7D32",opacity=.45)
            figv.add_hline(y=5,line_dash="dot",line_color="#D99A00",opacity=.55)
            figv.add_hline(y=7,line_dash="dot",line_color="#C62828",opacity=.60)
            figv.update_traces(
                hovertemplate="<b>%{fullData.name}</b><br>Fecha: %{x|%d/%m/%Y}<br>Velocidad: %{y:.2f} mm/s<extra></extra>"
            )
            aplicar_estilo_temporal(figv, sv, desde_eq, hasta_eq)
            figv.update_layout(
                height=330,
                margin=dict(l=8,r=8,t=10,b=6),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, x=0,
                    title_text="", font=dict(size=10),
                ),
                paper_bgcolor="white",
                plot_bgcolor="white",
                hovermode="closest",
            )
            figv.update_xaxes(tickformat="%d/%m/%Y",nticks=8,showgrid=False)
            figv.update_yaxes(gridcolor="#E9EEF3",rangemode="tozero")
            st.plotly_chart(figv,use_container_width=True,config={"displayModeBar":False})

    with lectura_col:
        st.markdown("<div class='section-title'>Lectura técnica del punto</div>",unsafe_allow_html=True)

        ult_vel = ultimo_por_tipo_y_punto(mediciones,equipo_sel,punto_sel,"Vibracion-Velocidad")
        ult_acc = ultimo_por_tipo_y_punto(mediciones,equipo_sel,punto_sel,"Vibracion-Aceleracion")
        ult_acc_rms = ultimo_por_tipo_y_punto(mediciones,equipo_sel,punto_sel,"Vibracion-Aceleracion-RMS")
        ult_temp = ultimo_por_tipo_y_punto(mediciones,equipo_sel,punto_sel,"Temperatura")

        if not ult_vel.empty:
            rv = ult_vel.sort_values("Valor",ascending=False).iloc[0]
            tendencia_rv = tendencia_codigo(tendencias,equipo_sel,rv["CodPunto"])
            vel_txt = (
                f"<b>Velocidad:</b> {rv['CodPunto']} = {rv['Valor']:.2f} mm/s "
                f"({rv['Estado']}). {tendencia_rv}."
            )
        else:
            vel_txt = "<b>Velocidad:</b> sin datos."

        if not ult_temp.empty:
            rt = ult_temp.sort_values("Valor",ascending=False).iloc[0]
            temp_txt = (
                f"<b>Temperatura:</b> {rt['CodPunto']} = {rt['Valor']:.1f} °C "
                f"({rt['Estado']}). {texto_vigencia(rt['Fecha'],fecha_eq)}."
            )
        else:
            temp_txt = "<b>Temperatura:</b> sin datos para este punto."

        partes_acc = []
        if not ult_acc_rms.empty:
            rag = ult_acc_rms.sort_values("Fecha").iloc[-1]
            partes_acc.append(
                f"<b>Aceleración RMS:</b> {rag['CodPunto']} = {rag['Valor']:.2f} g"
            )
        if not ult_acc.empty:
            ra = ult_acc.sort_values("Fecha").iloc[-1]
            partes_acc.append(
                f"<b>Envolvente:</b> {ra['CodPunto']} = {ra['Valor']:.2f} gE "
                f"({ra['Estado']})"
            )
        if partes_acc:
            acc_txt = " · ".join(partes_acc) + "."
        else:
            acc_txt = "<b>Aceleración / envolvente:</b> sin datos registrados para este punto."

        st.markdown(
            f"""
            <div class='tech-summary'>
              <div class='tech-summary-title'>{html.escape(equipo_sel)} · {html.escape(puntos_labels.get(punto_sel,punto_sel))}</div>
              <div class='tech-line'>{vel_txt}</div>
              <div class='tech-line'>{temp_txt}</div>
              <div class='tech-line'>{acc_txt}</div>
              <div class='tech-line'><b>Criterio:</b> el estado usa la última lectura válida; la tendencia usa una ventana adaptativa validada del ciclo vigente.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Estado actual H/V/A compacto.
        st.markdown("<div class='section-title'>Condición actual</div>",unsafe_allow_html=True)
        if ult_vel.empty:
            st.markdown("<div class='note'>Sin datos de velocidad.</div>",unsafe_allow_html=True)
        else:
            cards_dir = st.columns(min(3,len(ult_vel)))
            orden_dir = {"Horizontal":0,"Vertical":1,"Axial":2}
            uv = ult_vel.copy()
            uv["ord"] = uv["Direccion"].map(orden_dir).fillna(9)
            uv = uv.sort_values("ord").head(3)
            for cc,(_,rr) in zip(cards_dir,uv.iterrows()):
                accent = color_estado(rr["Estado"])
                cc.markdown(
                    f"""
                    <div class='var-card' style='--accent:{accent}'>
                      <div class='var-label'>{html.escape(str(rr['Direccion']))} · {html.escape(str(rr['CodPunto']))}</div>
                      <div class='var-value'>{rr['Valor']:.2f} mm/s</div>
                      <div class='var-note'>{html.escape(str(rr['Estado']))}<br>{fmt_fecha(rr['Fecha'])}</div>
                    </div>
                    """,unsafe_allow_html=True
                )

    # --------------------------------------------------------------
    # Aceleración + temperatura
    # --------------------------------------------------------------
    ac_col,temp_col = st.columns(2,gap="medium")

    with ac_col:
        st.markdown("<div class='section-title'>Aceleración / envolvente del punto</div>",unsafe_allow_html=True)
        sa_env = serie_punto(
            mediciones,equipo_sel,punto_sel,
            "Vibracion-Aceleracion",desde_eq,hasta_eq
        )
        sa_rms = serie_punto(
            mediciones,equipo_sel,punto_sel,
            "Vibracion-Aceleracion-RMS",desde_eq,hasta_eq
        )

        if sa_env.empty and sa_rms.empty:
            st.markdown(
                "<div class='tech-summary' style='min-height:210px'>"
                "<div class='tech-summary-title'>Sin datos g / gE en el período</div>"
                "<div class='tech-line'>El lector reconoce la nueva nomenclatura nG y nGE del Excel.</div>"
                "<div class='tech-line'>No se sustituye un dato ausente con una estimación.</div>"
                "</div>",unsafe_allow_html=True
            )
        else:
            figa = go.Figure()

            # Envolvente gE: eje izquierdo y límites oficiales gE.
            if not sa_env.empty:
                for codigo, gg in sa_env.groupby("CodPunto"):
                    figa.add_trace(go.Scatter(
                        x=gg["Fecha"], y=gg["Valor"],
                        mode="lines+markers",
                        name=f"{codigo} · Envolvente gE",
                        line=dict(width=2.1),
                        marker=dict(size=6),
                        yaxis="y",
                        hovertemplate="<b>%{fullData.name}</b><br>Fecha: %{x|%d/%m/%Y}<br>Envolvente: %{y:.2f} gE<extra></extra>",
                    ))
                figa.add_hline(y=.75,line_dash="dot",line_color="#2E7D32",opacity=.45)
                figa.add_hline(y=1.0,line_dash="dot",line_color="#D99A00",opacity=.55)
                figa.add_hline(y=3.0,line_dash="dot",line_color="#C62828",opacity=.60)

            # Aceleración RMS g: eje derecho, sin aplicar límites de gE.
            if not sa_rms.empty:
                for codigo, gg in sa_rms.groupby("CodPunto"):
                    figa.add_trace(go.Scatter(
                        x=gg["Fecha"], y=gg["Valor"],
                        mode="lines+markers",
                        name=f"{codigo} · Aceleración RMS g",
                        line=dict(width=1.9, dash="dash"),
                        marker=dict(size=5),
                        yaxis="y2",
                        hovertemplate="<b>%{fullData.name}</b><br>Fecha: %{x|%d/%m/%Y}<br>Aceleración RMS: %{y:.2f} g<extra></extra>",
                    ))

            datos_estilo = pd.concat(
                [x for x in [sa_env, sa_rms] if not x.empty],
                ignore_index=True
            )
            aplicar_estilo_temporal(figa, datos_estilo, desde_eq, hasta_eq)
            figa.update_layout(
                height=245,
                margin=dict(l=8,r=8,t=8,b=5),
                legend=dict(orientation="h",y=1.03,x=0,title_text=""),
                paper_bgcolor="white",
                plot_bgcolor="white",
                yaxis=dict(
                    title="Envolvente (gE)",
                    gridcolor="#E9EEF3",
                    rangemode="tozero",
                ),
                yaxis2=dict(
                    title="Aceleración RMS (g)",
                    overlaying="y",
                    side="right",
                    rangemode="tozero",
                    showgrid=False,
                ),
            )
            figa.update_xaxes(tickformat="%d/%m/%Y",nticks=6,showgrid=False)
            st.plotly_chart(figa,use_container_width=True,config={"displayModeBar":False})

            st.markdown(
                "<div class='note'>Límites 0.75 / 1 / 3 aplican únicamente a la envolvente gE; "
                "la aceleración RMS en g se muestra como tendencia y no se clasifica con esos límites.</div>",
                unsafe_allow_html=True,
            )

    with temp_col:
        st.markdown("<div class='section-title'>Temperatura del punto</div>",unsafe_allow_html=True)
        stemp = serie_punto(
            mediciones,equipo_sel,punto_sel,
            "Temperatura",desde_eq,hasta_eq
        )
        if stemp.empty:
            st.markdown(
                "<div class='tech-summary' style='min-height:210px'>"
                "<div class='tech-summary-title'>Sin temperatura asociada</div>"
                "<div class='tech-line'>No existe un registro de temperatura para este punto físico en el período seleccionado.</div>"
                "</div>",unsafe_allow_html=True
            )
        else:
            figt = px.line(
                stemp,x="Fecha",y="Valor",color="CodPunto",markers=True,
                labels={"Fecha":"","Valor":"Temperatura (°C)","CodPunto":"Código"}
            )
            figt.add_hline(y=45,line_dash="dot",line_color="#D99A00",opacity=.55)
            figt.add_hline(y=60,line_dash="dot",line_color="#C62828",opacity=.65)
            figt.update_traces(
                hovertemplate="<b>%{fullData.name}</b><br>Fecha: %{x|%d/%m/%Y}<br>Temperatura: %{y:.1f} °C<extra></extra>"
            )
            aplicar_estilo_temporal(figt, stemp, desde_eq, hasta_eq)
            figt.update_layout(
                height=245,margin=dict(l=8,r=8,t=8,b=5),
                legend=dict(orientation="h",y=1.03,x=0,title_text=""),
                paper_bgcolor="white",plot_bgcolor="white",
            )
            figt.update_xaxes(tickformat="%d/%m/%Y",nticks=6,showgrid=False)
            figt.update_yaxes(gridcolor="#E9EEF3",rangemode="tozero")
            st.plotly_chart(figt,use_container_width=True,config={"displayModeBar":False})

    # --------------------------------------------------------------
    # Vigilancia actual + tendencias del molino
    # --------------------------------------------------------------
    vig_col, tend_col = st.columns([1.34,1.0],gap="medium")

    with vig_col:
        st.markdown("<div class='section-title'>Puntos que requieren vigilancia — estado actual</div>",unsafe_allow_html=True)
        vig = act_eq_points[act_eq_points["Severidad"] >= 1].copy()
        if vig.empty:
            st.success("Todos los puntos actuales se encuentran en condición normal / aceptada.")
        else:
            vig["Valor actual"] = vig.apply(
                lambda r:f"{r['Valor']:.2f} {r['Unidad']}",axis=1
            )
            vig["Fecha"] = pd.to_datetime(vig["Fecha"]).dt.strftime("%d/%m/%Y")
            vig["Tendencia"] = vig.apply(
                lambda r:tendencia_codigo(tendencias,equipo_sel,r["CodPunto"])
                    if r["TipoVariable"]=="Vibracion-Velocidad" else "—",
                axis=1
            )
            vig = vig.sort_values(
                ["Severidad","Valor"],ascending=[False,False]
            )
            tv = vig[[
                "CodPunto","Componente","TipoVariable","Valor actual","Estado","Tendencia","Fecha"
            ]].rename(columns={
                "CodPunto":"Punto",
                "TipoVariable":"Variable",
            }).head(12)
            st.markdown(tabla_html(tv,estado_col="Estado"),unsafe_allow_html=True)
            if len(vig) > 12:
                st.caption(f"Se muestran los 12 de mayor severidad de {len(vig)} puntos en vigilancia.")

    with tend_col:
        st.markdown("<div class='section-title'>Mayor crecimiento reciente de velocidad</div>",unsafe_allow_html=True)
        teq = tendencias[
            (tendencias["EquipoCorto"]==equipo_sel)
            & (tendencias["Pendiente_mm_s_mes"]>0)
            & (tendencias["R2"]>=.60)
        ].sort_values("Pendiente_mm_s_mes",ascending=False).head(6).copy()

        if teq.empty:
            st.markdown(
                "<div class='tech-summary'>"
                "<div class='tech-summary-title'>Sin tendencias crecientes consistentes</div>"
                "<div class='tech-line'>Las últimas mediciones no muestran un crecimiento suficientemente estable para priorizar por tendencia.</div>"
                "</div>",unsafe_allow_html=True
            )
        else:
            filas = []
            estado_idx = act_eq_points.set_index("CodPunto")["Estado"]
            for _,rr in teq.iterrows():
                filas.append({
                    "Punto":rr["CodPunto"],
                    "Último":f"{rr['UltimoValor']:.2f} mm/s",
                    "Cambio":f"+{rr['Pendiente_mm_s_mes']:.2f} mm/s/mes",
                    "Estado":estado_idx.get(rr["CodPunto"],"SIN DATO"),
                })
            st.markdown(
                tabla_html(pd.DataFrame(filas),estado_col="Estado"),
                unsafe_allow_html=True
            )
            st.markdown(
                "<div class='note' style='margin-top:6px'>"
                "Se muestran únicamente tendencias con comportamiento suficientemente consistente; "
                "los valores dispersos se excluyen para evitar conclusiones débiles."
                "</div>",unsafe_allow_html=True
            )

    st.markdown(
        "<div class='note' style='margin-top:7px'>"
        "<b>Alcance técnico:</b> esta pantalla evalúa condición y evolución. "
        "La causa raíz (desalineación, soltura, rodamientos, engranajes, etc.) se confirma con espectro, envolvente y forma de onda cuando estén disponibles."
        "</div>",
        unsafe_allow_html=True,
    )


# =====================================================================
# PRIORIDAD DE INTERVENCIÓN
# =====================================================================
elif pagina == "Prioridad de Intervención":
    cabecera_dashboard(
        "PRIORIDAD DE INTERVENCIÓN — MOLINOS",
        "Ordenamiento técnico por condición actual, tendencia y vigencia de la medición",
        "prioridad",
    )

    csel, cnota = st.columns([1.0, 3.2])
    with csel:
        equipo_sel = selector_equipo_compartido(mediciones)
    with cnota:
        st.markdown(
            "<div class='note' style='padding-top:25px'>"
            "La prioridad organiza el trabajo de mantenimiento. "
            "El estado usa los límites oficiales y la tendencia solo aumenta prioridad cuando el crecimiento es consistente."
            "</div>",
            unsafe_allow_html=True,
        )

    pri = load_prioridad(mtime, dias_vigencia=30)
    peq = pri[pri["EquipoCorto"].eq(equipo_sel)].copy()
    counts = peq["Prioridad"].value_counts().reindex(["P1","P2","P3","P4"], fill_value=0)

    k1,k2,k3,k4 = st.columns(4)
    cards = [
        (k1,"P1","#C62828","Intervención inmediata",int(counts["P1"]),"condición Peligro / Crítico"),
        (k2,"P2","#E86A12","Atención prioritaria",int(counts["P2"]),"revisar en corto plazo"),
        (k3,"P3","#D99A00","Seguimiento programado",int(counts["P3"]),"vigilar en próxima ruta"),
        (k4,"P4","#2E7D32","Monitoreo rutinario",int(counts["P4"]),"condición estable"),
    ]
    for col,p,color,desc,val,note in cards:
        col.markdown(
            f"""
            <div class='kpi-card' style='--accent:{color}'>
              <div class='kpi-icon'>{p}</div>
              <div class='kpi-body'>
                <div class='kpi-label'>{desc}</div>
                <div class='kpi-value'>{val}</div>
                <div class='kpi-note'>{note}</div>
              </div>
            </div>
            """, unsafe_allow_html=True
        )

    left,right = st.columns([1.0,1.15],gap="medium")

    with left:
        st.markdown("<div class='section-title'>Distribución de prioridades</div>",unsafe_allow_html=True)
        barras = pd.DataFrame({
            "Prioridad":["P1","P2","P3","P4"],
            "Puntos":[int(counts[x]) for x in ["P1","P2","P3","P4"]],
        })
        figp = go.Figure()
        for _,rr in barras.iterrows():
            figp.add_trace(go.Bar(
                x=[rr["Puntos"]],
                y=[rr["Prioridad"]],
                orientation="h",
                marker_color=prioridad_color(rr["Prioridad"]),
                text=[str(int(rr["Puntos"]))],
                textposition="auto",
                hovertemplate=f"<b>{rr['Prioridad']}</b><br>Puntos: %{{x}}<extra></extra>",
                showlegend=False,
            ))
        figp.update_layout(
            height=245,
            margin=dict(l=20,r=15,t=8,b=8),
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis_title="Cantidad de puntos",
            yaxis_title="",
            barmode="stack",
        )
        figp.update_xaxes(gridcolor="#E9EEF3",rangemode="tozero")
        st.plotly_chart(figp,use_container_width=True,config={"displayModeBar":False})
        st.markdown(
            "<div class='note'>"
            "<b>Cómo leerlo:</b> las barras muestran cuántos puntos del molino caen en cada prioridad. "
            "Si P1 o P2 crecen, aumenta la carga de intervención inmediata/corto plazo; P3 y P4 corresponden a seguimiento y rutina."
            "</div>",
            unsafe_allow_html=True,
        )

    with right:
        st.markdown("<div class='section-title'>Lectura de prioridad</div>",unsafe_allow_html=True)
        if peq.empty:
            st.info("Sin puntos para priorizar.")
        else:
            maxp = peq.iloc[0]
            st.markdown(
                f"""
                <div class='tech-summary'>
                  <div class='tech-summary-title'>{html.escape(equipo_sel)} · prioridad dominante {maxp['Prioridad']}</div>
                  <div class='tech-line'><b>Punto:</b> {html.escape(str(maxp['CodPunto']))} · {html.escape(str(maxp['Componente']))}</div>
                  <div class='tech-line'><b>Motivo:</b> {html.escape(str(maxp['Motivo']))}</div>
                  <div class='tech-line'><b>Acción sugerida:</b> {html.escape(str(maxp['Accion']))}</div>
                  <div class='tech-line'><b>Vigencia:</b> {int(maxp['DiasDesfase'])} días respecto de la última fecha global.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div class='section-title'>Órdenes sugeridas por prioridad</div>",unsafe_allow_html=True)
        ordenes = pd.DataFrame([
            {"Prioridad":"P1","Horizonte":"Inmediato","Criterio":"Peligro / Crítico","Acción":"Intervenir y confirmar causa","Puntos":int(counts["P1"])},
            {"Prioridad":"P2","Horizonte":"≤ 7 días","Criterio":"Alerta / tendencia / dato vencido","Acción":"Inspección dirigida","Puntos":int(counts["P2"])},
            {"Prioridad":"P3","Horizonte":"Próxima ruta","Criterio":"Tolerable / Moderado","Acción":"Seguimiento programado","Puntos":int(counts["P3"])},
            {"Prioridad":"P4","Horizonte":"Rutina","Criterio":"Estable","Acción":"Monitoreo normal","Puntos":int(counts["P4"])},
        ])
        st.markdown(tabla_html(ordenes),unsafe_allow_html=True)

    st.markdown("<div class='section-title'>Lista priorizada de puntos</div>",unsafe_allow_html=True)
    if not peq.empty:
        peq["Valor actual"] = peq.apply(lambda r:f"{r['Valor']:.2f} {r['Unidad']}",axis=1)
        peq["Tendencia"] = peq.apply(
            lambda r: etiqueta_tendencia(r["Pendiente_mm_s_mes"],r["R2"])
            if r["TipoVariable"]=="Vibracion-Velocidad" else "—",
            axis=1,
        )
        peq["Vigencia"] = peq["DiasDesfase"].map(
            lambda d:"Vigente" if int(d)<=30 else f"Desactualizado ({int(d)} d)"
        )
        tabla_p = peq[[
            "Prioridad","CodPunto","Componente","TipoVariable",
            "Valor actual","Estado","Tendencia","Vigencia","Accion"
        ]].rename(columns={
            "CodPunto":"Punto","TipoVariable":"Variable","Accion":"Acción sugerida"
        }).head(18)
        st.markdown(tabla_html(tabla_p,estado_col="Estado"),unsafe_allow_html=True)

    st.markdown(
        "<div class='note' style='margin-top:7px'>"
        "<b>Regla:</b> P1 = Peligro/Crítico; P2 = Alerta, medición desactualizada o Tolerable con crecimiento consistente; "
        "P3 = Tolerable/Moderado o crecimiento consistente aún normal; P4 = estable. "
        "La prioridad ordena la intervención, pero no reemplaza el diagnóstico de causa raíz."
        "</div>",
        unsafe_allow_html=True,
    )


# =====================================================================
# JACK-KNIFE
# =====================================================================
elif pagina == "Jack-knife":
    cabecera_dashboard(
        "JACK-KNIFE — TENDENCIA Y PROYECCIÓN",
        "Severidad actual, velocidad de deterioro y proyección matemática del punto seleccionado",
        "jackknife",
    )

    jk = load_jackknife(mtime)
    jeq_all_pre = jk.copy()

    c1,c2,c3 = st.columns([1.0,1.35,2.1])
    with c1:
        equipo_sel = selector_equipo_compartido(mediciones)
    jeq_all = jeq_all_pre[jeq_all_pre["EquipoCorto"].eq(equipo_sel)].copy()
    jeq_claras = jeq_all[jeq_all["TendenciaClara"] & jeq_all["Pendiente_mm_s_mes"].notna()].copy()

    codigos = jeq_all.sort_values(["RiesgoVisual","Valor"],ascending=[False,False])["CodPunto"].tolist()
    if not codigos:
        codigos = ["—"]
    default_cod = (
        jeq_claras.sort_values("RiesgoVisual",ascending=False).iloc[0]["CodPunto"]
        if not jeq_claras.empty else codigos[0]
    )
    labels = {
        r["CodPunto"]: f"{r['CodPunto']} · {r['Componente']}"
        for _,r in jeq_all.drop_duplicates("CodPunto").iterrows()
    }
    with c2:
        cod_sel = st.selectbox(
            "Punto de velocidad",
            codigos,
            index=codigos.index(default_cod) if default_cod in codigos else 0,
            format_func=lambda x:labels.get(x,x),
            key="jackknife_cod",
        )
    with c3:
        st.markdown(
            "<div class='note' style='padding-top:25px'>"
            "<b>Jack-knife:</b> el eje vertical representa qué tan alto está el valor actual; "
            "el eje horizontal indica qué tan rápido viene cambiando. "
            "La zona superior derecha concentra los puntos con mayor severidad y crecimiento."
            "</div>",
            unsafe_allow_html=True,
        )

    modelo = load_proyeccion(mtime,equipo_sel,cod_sel)
    current_row = jeq_all[jeq_all["CodPunto"].eq(cod_sel)]
    current_value = float(current_row.iloc[0]["Valor"]) if not current_row.empty else np.nan
    current_state = str(current_row.iloc[0]["Estado"]) if not current_row.empty else "SIN DATO"
    current_slope = float(current_row.iloc[0]["Pendiente_mm_s_mes"]) if (
        not current_row.empty and pd.notna(current_row.iloc[0]["Pendiente_mm_s_mes"])
    ) else np.nan

    k1,k2,k3,k4,k5 = st.columns(5)
    alerta_txt = (
        "Umbral superado" if modelo["dias_alerta"] == 0
        else f"{modelo['dias_alerta']} días" if modelo["dias_alerta"] is not None
        else "Sin proyección"
    )
    peligro_txt = (
        "Umbral superado" if modelo["dias_peligro"] == 0
        else f"{modelo['dias_peligro']} días" if modelo["dias_peligro"] is not None
        else "Sin proyección"
    )
    vals = [
        (k1,"↕","#E86A12","Valor actual",f"{current_value:.2f} mm/s" if pd.notna(current_value) else "Sin dato",current_state),
        (k2,"▲","#D99A00","Cambio reciente",f"{current_slope:+.2f} mm/s/mes" if pd.notna(current_slope) else "Sin tendencia",f"ventana adaptativa · {modelo['n']} datos"),
        (k3,"✓","#2563EB","Calidad del modelo",modelo["confianza"],f"R² {modelo['r2']:.2f}" if pd.notna(modelo["r2"]) else "sin ajuste"),
        (k4,"!","#E86A12","Proyección a Alerta",alerta_txt,"umbral 5.0 mm/s"),
        (k5,"●","#C62828","Proyección a Peligro",peligro_txt,"umbral 7.0 mm/s"),
    ]
    for col,icono,color,label,value,note in vals:
        col.markdown(
            f"""
            <div class='kpi-card' style='--accent:{color}'>
              <div class='kpi-icon'>{icono}</div>
              <div class='kpi-body'>
                <div class='kpi-label'>{label}</div>
                <div class='kpi-value'>{html.escape(str(value))}</div>
                <div class='kpi-note'>{html.escape(str(note))}</div>
              </div>
            </div>
            """,unsafe_allow_html=True
        )

    plot_col,model_col = st.columns([1.55,1.0],gap="medium")

    with plot_col:
        st.markdown("<div class='section-title'>Mapa Jack-knife — severidad vs cambio reciente</div>",unsafe_allow_html=True)
        jeq = jeq_claras.copy()
        if jeq.empty:
            st.info("No hay tendencias suficientemente consistentes para construir el Jack-knife de este equipo.")
        else:
            figj = go.Figure()
            for est in ["NORMAL","TOLERABLE","ALERTA","PELIGRO"]:
                q = jeq[jeq["Estado"].eq(est)]
                if q.empty:
                    continue
                figj.add_trace(go.Scatter(
                    x=q["Pendiente_mm_s_mes"],
                    y=q["Valor"],
                    mode="markers",
                    name=est,
                    marker=dict(size=11,color=color_estado(est),line=dict(width=1,color="white"),opacity=.92),
                    customdata=np.stack([q["CodPunto"].astype(str),q["Componente"].astype(str)],axis=-1),
                    hovertemplate=(
                        "<b>%{customdata[0]} · %{customdata[1]}</b>"
                        "<br>Valor actual: %{y:.2f} mm/s"
                        "<br>Cambio: %{x:+.2f} mm/s/mes<extra></extra>"
                    ),
                ))
            top_labels = jeq.sort_values("RiesgoVisual",ascending=False).head(6)
            figj.add_trace(go.Scatter(
                x=top_labels["Pendiente_mm_s_mes"],y=top_labels["Valor"],
                mode="text",text=top_labels["CodPunto"],textposition="top center",
                textfont=dict(size=10,color="#0B2A45"),showlegend=False,hoverinfo="skip",
            ))
            figj.add_hline(y=3,line_dash="dot",line_color="#2E7D32",opacity=.45)
            figj.add_hline(y=5,line_dash="dot",line_color="#D99A00",opacity=.60)
            figj.add_hline(y=7,line_dash="dot",line_color="#C62828",opacity=.70)
            figj.add_vline(x=0,line_dash="dash",line_color="#78909C",opacity=.55)
            figj.update_layout(
                height=410,margin=dict(l=10,r=10,t=10,b=10),
                paper_bgcolor="white",plot_bgcolor="white",
                xaxis_title="Cambio reciente (mm/s/mes)",
                yaxis_title="Valor actual de velocidad (mm/s)",
                legend=dict(orientation="h",y=1.03,x=0,title_text=""),
            )
            figj.update_xaxes(gridcolor="#E9EEF3",zeroline=False)
            figj.update_yaxes(gridcolor="#E9EEF3",rangemode="tozero")
            st.plotly_chart(figj,use_container_width=True,config={"displayModeBar":False})

    with model_col:
        st.markdown("<div class='section-title'>Modelo de proyección</div>",unsafe_allow_html=True)
        if modelo["valido"]:
            fecha_alerta = fmt_fecha(modelo["fecha_alerta"]) if modelo["fecha_alerta"] is not None else "Fuera de horizonte"
            fecha_peligro = fmt_fecha(modelo["fecha_peligro"]) if modelo["fecha_peligro"] is not None else "Fuera de horizonte"
            st.markdown(
                f"""
                <div class='tech-summary'>
                  <div class='tech-summary-title'>{html.escape(labels.get(cod_sel,cod_sel))}</div>
                  <div class='tech-line'><b>Método:</b> regresión lineal adaptativa sobre {modelo['n']} de {modelo.get('n_total_ciclo', modelo['n'])} mediciones del ciclo.</div>
                  <div class='tech-line'><b>Pendiente:</b> {modelo['pendiente_mes']:+.2f} mm/s/mes.</div>
                  <div class='tech-line'><b>Ajuste:</b> R² = {modelo['r2']:.2f} · confianza {modelo['confianza'].lower()}.</div>
                  <div class='tech-line'><b>Alerta 5.0 mm/s:</b> {fecha_alerta}.</div>
                  <div class='tech-line'><b>Peligro 7.0 mm/s:</b> {fecha_peligro}.</div>
                </div>
                """,unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class='tech-summary'>
                  <div class='tech-summary-title'>Predicción no confiable</div>
                  <div class='tech-line'>{html.escape(str(modelo['motivo']))}</div>
                  <div class='tech-line'>El dashboard no fuerza una fecha cuando la pendiente o la dispersión no sostienen el pronóstico.</div>
                </div>
                """,unsafe_allow_html=True
            )

        st.markdown("<div class='section-title'>Últimas mediciones del punto</div>",unsafe_allow_html=True)
        s = modelo["serie"].copy()
        if not s.empty:
            figs = go.Figure()
            figs.add_trace(go.Scatter(
                x=s["Fecha"],y=s["Valor"],mode="lines+markers",name=cod_sel,
                line=dict(color="#0B6FA4",width=2.2),marker=dict(size=6),
                hovertemplate="Fecha: %{x|%d/%m/%Y}<br>Velocidad: %{y:.2f} mm/s<extra></extra>",
            ))
            figs.add_hline(y=5,line_dash="dot",line_color="#D99A00",opacity=.65)
            figs.add_hline(y=7,line_dash="dot",line_color="#C62828",opacity=.75)
            figs.update_layout(
                height=215,margin=dict(l=8,r=8,t=5,b=5),
                paper_bgcolor="white",plot_bgcolor="white",
                showlegend=False,yaxis_title="mm/s",
            )
            figs.update_xaxes(tickformat="%d/%m/%Y",showgrid=False,nticks=6)
            figs.update_yaxes(gridcolor="#E9EEF3",rangemode="tozero")
            st.plotly_chart(figs,use_container_width=True,config={"displayModeBar":False})

    st.markdown(
        "<div class='note'>"
        "<b>Importante:</b> esta proyección es de tendencia vibracional, no una fecha automática de cambio de rodamiento. "
        "La decisión de mantenimiento debe combinar condición, causa raíz, criticidad e historial de intervenciones."
        "</div>",
        unsafe_allow_html=True,
    )


# =====================================================================
# HISTÓRICO Y CONFIABILIDAD
# =====================================================================
elif pagina == "Histórico y Confiabilidad":
    cabecera_dashboard(
        "HISTÓRICO Y CONFIABILIDAD — MOLINOS",
        "Ciclo desde mantenimiento, evolución de condición e historial de intervenciones",
        "historico",
    )

    c1,c2,c3 = st.columns([1.0,1.25,2.2])
    with c1:
        equipo_sel = selector_equipo_compartido(mediciones)
    med_eq = mediciones[mediciones["EquipoCorto"].eq(equipo_sel)].copy()
    velocidades = (
        med_eq[med_eq["TipoVariable"].eq("Vibracion-Velocidad")]
        [["CodPunto","Componente","Direccion"]]
        .drop_duplicates().sort_values(["Componente","CodPunto"])
    )
    codigos = velocidades["CodPunto"].tolist()
    actuales = estado_actual_por_punto(mediciones)
    acteq = actuales[
        (actuales["EquipoCorto"].eq(equipo_sel))
        & (actuales["TipoVariable"].eq("Vibracion-Velocidad"))
    ].sort_values("Valor",ascending=False)
    default_cod = acteq.iloc[0]["CodPunto"] if not acteq.empty else codigos[0]
    labels_cod = {
        r["CodPunto"]:f"{r['CodPunto']} · {r['Componente']} · {r['Direccion']}"
        for _,r in velocidades.iterrows()
    }
    with c2:
        cod_sel = st.selectbox(
            "Punto de velocidad",codigos,
            index=codigos.index(default_cod) if default_cod in codigos else 0,
            format_func=lambda x:labels_cod.get(x,x),key="historico_cod",
        )
    with c3:
        st.markdown(
            "<div class='note' style='padding-top:25px'>"
            "<b>Regla de confiabilidad:</b> sano operativo ≤ 5 mm/s; degradado > 5 a 7 mm/s; crítico > 7 mm/s. "
            "Se reutilizan los límites oficiales del dashboard, sin crear umbrales nuevos."
            "</div>",unsafe_allow_html=True
        )

    ciclo = confiabilidad_ciclo_actual(mediciones,equipo_sel,cod_sel)
    ciclos = load_ciclos(mtime,equipo_sel,cod_sel)
    evento = ciclo.get("evento")
    fecha_evento = pd.to_datetime(evento["fecha"]) if evento else None

    rachas_all = rachas_operativas_velocidad(mediciones,equipo_sel,cod_sel)
    sano_hist = rachas_all[rachas_all["CondicionOperativa"].eq("SANO")] if not rachas_all.empty else pd.DataFrame()
    deg_hist = rachas_all[rachas_all["CondicionOperativa"].eq("DEGRADADO")] if not rachas_all.empty else pd.DataFrame()
    crit_hist = rachas_all[rachas_all["CondicionOperativa"].eq("CRITICO")] if not rachas_all.empty else pd.DataFrame()

    sano_max = int(sano_hist["Dias"].max()) if not sano_hist.empty else None
    deg_max = int(deg_hist["Dias"].max()) if not deg_hist.empty else None
    dias_m = ciclo.get("dias_desde_mantto")
    dias_sano = ciclo.get("dias_sano")
    dias_deg = ciclo.get("dias_degradado")
    dias_crit = ciclo.get("dias_critico")

    proy_ciclo = ciclos.get("proyeccion")
    proy_txt = fmt_fecha(proy_ciclo["fecha_estimada"]) if proy_ciclo else "Sin ciclos suficientes"
    ciclos_completos = len(ciclos.get("intervalos",[]))

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    cards = [
        (k1,"↻","#2563EB","Desde último mantenimiento",f"{dias_m} días" if dias_m is not None else "Sin registro",evento["alcance"] if evento else "agregar fecha en Observación"),
        (k2,"✓","#2E7D32","Sano acumulado en ciclo",f"{dias_sano} días" if dias_sano is not None else "Sin dato","≤ 5 mm/s"),
        (k3,"~","#D99A00","Degradado acumulado",f"{dias_deg} días" if dias_deg is not None else "Sin dato","> 5 a 7 mm/s"),
        (k4,"●","#C62828","Crítico acumulado",f"{dias_crit} días" if dias_crit is not None else "Sin dato","> 7 mm/s"),
        (k5,"★","#2E7D32","Máximo sano histórico",f"{sano_max} días" if sano_max is not None else "Sin dato","racha observada"),
        (k6,"◎","#7C3AED","Próximo cambio estimado",proy_txt,f"{ciclos_completos} intervalos completos"),
    ]
    for col,icono,color,label,value,note in cards:
        col.markdown(
            f"""
            <div class='kpi-card' style='--accent:{color}'>
              <div class='kpi-icon'>{icono}</div>
              <div class='kpi-body'>
                <div class='kpi-label'>{label}</div>
                <div class='kpi-value'>{html.escape(str(value))}</div>
                <div class='kpi-note'>{html.escape(str(note))}</div>
              </div>
            </div>
            """,unsafe_allow_html=True
        )

    hist_col,right_col = st.columns([1.62,.98],gap="medium")
    serie = med_eq[med_eq["CodPunto"].eq(cod_sel)].sort_values("Fecha").copy()

    with hist_col:
        st.markdown(
            f"<div class='section-title'>Histórico del punto — {html.escape(labels_cod.get(cod_sel,cod_sel))}</div>",
            unsafe_allow_html=True,
        )
        if serie.empty:
            st.info("Sin histórico para el punto.")
        else:
            figh = go.Figure(go.Scatter(
                x=serie["Fecha"],y=serie["Valor"],mode="lines+markers",
                line=dict(color="#0B6FA4",width=2.2),marker=dict(size=4),
                hovertemplate="Fecha: %{x|%d/%m/%Y}<br>Velocidad: %{y:.2f} mm/s<extra></extra>",
            ))
            aplicar_estilo_temporal(figh,serie,serie["Fecha"].min(),serie["Fecha"].max())
            ymax = max(8.0,float(serie["Valor"].max())*1.08)
            figh.add_hrect(y0=0,y1=5,fillcolor="#2E7D32",opacity=.045,line_width=0)
            figh.add_hrect(y0=5,y1=7,fillcolor="#D99A00",opacity=.065,line_width=0)
            figh.add_hrect(y0=7,y1=ymax,fillcolor="#C62828",opacity=.045,line_width=0)
            figh.add_hline(y=5,line_dash="dot",line_color="#D99A00",opacity=.70)
            figh.add_hline(y=7,line_dash="dot",line_color="#C62828",opacity=.80)

            evrel = ciclos.get("eventos",pd.DataFrame())
            if not evrel.empty:
                for fecha in pd.to_datetime(evrel["Fecha"].drop_duplicates()).head(8):
                    figh.add_vline(x=fecha,line_dash="dash",line_color="#7C3AED",opacity=.55)

            figh.update_layout(
                height=385,margin=dict(l=10,r=10,t=10,b=8),
                paper_bgcolor="white",plot_bgcolor="white",
                yaxis_title="Velocidad RMS (mm/s)",
            )
            figh.update_xaxes(tickformat="%d/%m/%Y",nticks=10,showgrid=False)
            figh.update_yaxes(gridcolor="#E9EEF3",rangemode="tozero")
            st.plotly_chart(figh,use_container_width=True,config={"displayModeBar":False})

        st.markdown(
            "<div class='note'>"
            "<b>Lectura del ciclo:</b> verde = sano operativo (≤5); ámbar = degradado (>5–7); rojo = crítico (>7). "
            "Las líneas verticales moradas corresponden a eventos de mantenimiento detectados en Observación."
            "</div>",unsafe_allow_html=True
        )

    with right_col:
        st.markdown("<div class='section-title'>Historial de mantenimiento</div>",unsafe_allow_html=True)
        ev = ciclos.get("eventos",pd.DataFrame()).copy()
        if ev.empty:
            st.markdown(
                "<div class='tech-summary'><div class='tech-summary-title'>Sin eventos suficientes</div>"
                "<div class='tech-line'>Registra en Observación frases como “CAMBIO DE RODAMIENTO” o “OVH” en la fecha real. "
                "El dashboard detectará el evento al actualizar el Excel.</div></div>",
                unsafe_allow_html=True,
            )
        else:
            ev = ev.drop_duplicates(subset=["Fecha","Observacion"]).copy()
            ev["Fecha"] = pd.to_datetime(ev["Fecha"]).dt.strftime("%d/%m/%Y")
            cols_ev = ["Fecha","CodPunto","Componente","Observacion"]
            cols_ev = [c for c in cols_ev if c in ev.columns]
            eview = ev[cols_ev].rename(columns={
                "CodPunto":"Punto","Observacion":"Evento registrado"
            }).head(8)
            st.markdown(tabla_html(eview),unsafe_allow_html=True)

        st.markdown("<div class='section-title'>Confiabilidad del componente</div>",unsafe_allow_html=True)
        if proy_ciclo:
            st.markdown(
                f"""
                <div class='tech-summary'>
                  <div class='tech-summary-title'>Estimación por ciclos históricos</div>
                  <div class='tech-line'><b>Método:</b> mediana entre cambios registrados.</div>
                  <div class='tech-line'><b>Intervalos completos:</b> {proy_ciclo['intervalos']}.</div>
                  <div class='tech-line'><b>Mediana:</b> {proy_ciclo['mediana_dias']:.0f} días.</div>
                  <div class='tech-line'><b>Promedio:</b> {proy_ciclo['media_dias']:.0f} días.</div>
                  <div class='tech-line'><b>Próximo cambio estimado:</b> {fmt_fecha(proy_ciclo['fecha_estimada'])}.</div>
                </div>
                """,unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class='tech-summary'>
                  <div class='tech-summary-title'>Predicción de cambio aún no disponible</div>
                  <div class='tech-line'>Se necesitan al menos <b>3 eventos</b> del mismo componente/punto para obtener 2 intervalos completos.</div>
                  <div class='tech-line'>Ciclos completos actuales: <b>{ciclos_completos}</b>.</div>
                  <div class='tech-line'>No se ajusta Weibull ni se inventa una fecha con una sola intervención.</div>
                </div>
                """,unsafe_allow_html=True
            )

    st.markdown("<div class='section-title'>Rachas históricas por condición operativa</div>",unsafe_allow_html=True)
    if rachas_all.empty:
        st.info("Sin rachas calculables.")
    else:
        rr = rachas_all.copy()
        rr["Inicio"] = pd.to_datetime(rr["Inicio"]).dt.strftime("%d/%m/%Y")
        rr["Fin"] = pd.to_datetime(rr["Fin"]).dt.strftime("%d/%m/%Y")
        rr = rr.rename(columns={
            "CondicionOperativa":"Condición","Mediciones":"N° mediciones","Dias":"Días"
        })
        st.markdown(
            tabla_html(rr[["Condición","Inicio","Fin","Días","N° mediciones"]].tail(12)),
            unsafe_allow_html=True,
        )


# =====================================================================
# COBERTURA DE MONITOREO
# =====================================================================
elif pagina == "Cobertura de Monitoreo":
    cabecera_dashboard(
        "COBERTURA DE MONITOREO — MOLINOS",
        "Cumplimiento de la ruta: puntos físicos medidos, pendientes y vigencia",
        "cobertura",
    )

    c1,c2,c3 = st.columns([1.0,.85,2.35])
    with c1:
        equipo_sel = selector_equipo_compartido(mediciones)
    with c2:
        ventana = st.selectbox(
            "Ventana de cobertura",[7,30,60,90,180],index=1,
            format_func=lambda x:f"Últimos {x} días",key="ventana_cobertura",
        )
    with c3:
        st.markdown(
            "<div class='note' style='padding-top:25px'>"
            "<b>Cobertura no es condición mecánica.</b> Indica si la ruta planificada fue ejecutada dentro de la ventana seleccionada."
            "</div>",unsafe_allow_html=True
        )

    glob = load_cobertura_global(mtime,ventana)
    cobertura = glob["cobertura"]
    detalle = glob["detalle"]
    crow = cobertura[cobertura["EquipoCorto"].eq(equipo_sel)].iloc[0]
    det = detalle[detalle["EquipoCorto"].eq(equipo_sel)].copy()

    k1,k2,k3,k4,k5 = st.columns(5)
    gc = "#2E7D32" if glob["pct"]>=95 else "#D99A00" if glob["pct"]>=80 else "#C62828"
    cards = [
        (k1,"◎","#2563EB","Puntos planificados",str(glob["planificados"]),"5 molinos"),
        (k2,"✓","#2E7D32","Puntos medidos",str(glob["medidos"]),f"últimos {ventana} días"),
        (k3,"% ",gc,"Cobertura global",f"{glob['pct']:.1f}%","cumplimiento de ruta"),
        (k4,"!","#C62828","Puntos pendientes",str(glob["pendientes"]),"sin medición en ventana"),
        (k5,"🗓","#2563EB","Última medición global",fmt_fecha(mediciones["Fecha"].max()),"referencia temporal"),
    ]
    for col,icono,color,label,value,note in cards:
        col.markdown(
            f"""
            <div class='kpi-card' style='--accent:{color}'>
              <div class='kpi-icon'>{icono}</div>
              <div class='kpi-body'>
                <div class='kpi-label'>{label}</div>
                <div class='kpi-value'>{value}</div>
                <div class='kpi-note'>{note}</div>
              </div>
            </div>
            """,unsafe_allow_html=True
        )

    gl,gr = st.columns([.95,1.45],gap="medium")
    with gl:
        st.markdown("<div class='section-title'>Cobertura global</div>",unsafe_allow_html=True)
        figd = go.Figure(go.Pie(
            labels=["Medidos","Pendientes"],
            values=[glob["medidos"],glob["pendientes"]],
            hole=.67,
            marker=dict(colors=["#2E7D32","#C62828"]),
            textinfo="label+value",
            hovertemplate="<b>%{label}</b><br>Puntos: %{value}<extra></extra>",
            sort=False,
        ))
        figd.add_annotation(
            text=f"<b>{glob['pct']:.1f}%</b><br><span style='font-size:10px'>cobertura</span>",
            x=.5,y=.5,showarrow=False,font=dict(size=18,color=UI["navy_dark"])
        )
        figd.update_layout(height=245,margin=dict(l=2,r=2,t=2,b=2),showlegend=False,paper_bgcolor="white")
        st.plotly_chart(figd,use_container_width=True,config={"displayModeBar":False})

    with gr:
        st.markdown("<div class='section-title'>Cobertura por molino</div>",unsafe_allow_html=True)
        covv = cobertura.copy()
        covv["Cobertura"] = covv["CoberturaPct"].map(lambda x:f"{x:.1f}%")
        covv["Última medición"] = pd.to_datetime(covv["UltimaMedicion"]).dt.strftime("%d/%m/%Y")
        covv["Pendientes"] = covv["PuntosFaltantes"].astype(int)
        covv["Medidos / Plan"] = covv.apply(
            lambda r:f"{int(r['PuntosMedidos'])} / {int(r['PuntosPlanificados'])}",axis=1
        )
        st.markdown(
            tabla_html(covv[["EquipoCorto","Medidos / Plan","Cobertura","Pendientes","Última medición"]].rename(
                columns={"EquipoCorto":"Equipo"}
            )),
            unsafe_allow_html=True,
        )

    st.markdown(f"<div class='section-title'>Detalle de ruta — {html.escape(equipo_sel)}</div>",unsafe_allow_html=True)
    dleft,dright = st.columns([1.25,1.0],gap="medium")
    with dleft:
        det["Estado cobertura"] = np.where(det["EnVentana"],"MEDIDO","PENDIENTE")
        det["Última medición"] = pd.to_datetime(det["UltimaMedicion"]).dt.strftime("%d/%m/%Y")
        det["Última medición"] = det["Última medición"].fillna("Sin registro")
        st.markdown(
            tabla_html(det[["Punto","Estado cobertura","Última medición"]]),
            unsafe_allow_html=True,
        )

    with dright:
        fecha_global = pd.to_datetime(mediciones["Fecha"].max())
        inicio = fecha_global - pd.Timedelta(days=int(ventana))
        q = mediciones[
            (mediciones["EquipoCorto"].eq(equipo_sel))
            & (mediciones["Fecha"].ge(inicio))
        ].copy()
        q["PuntoNum"] = pd.to_numeric(q["Punto"],errors="coerce")
        q = q[q["PuntoNum"].notna()]
        st.markdown("<div class='section-title'>Puntos medidos por ronda</div>",unsafe_allow_html=True)
        if q.empty:
            st.info("No hay mediciones en la ventana seleccionada.")
        else:
            daily = (
                q.groupby("Fecha",as_index=False)["PuntoNum"].nunique()
                .rename(columns={"PuntoNum":"PuntosMedidos"}).sort_values("Fecha")
            )
            figc = go.Figure(go.Bar(
                x=daily["Fecha"],y=daily["PuntosMedidos"],marker_color="#2563EB",
                hovertemplate="Fecha: %{x|%d/%m/%Y}<br>Puntos medidos: %{y}<extra></extra>",
            ))
            figc.update_layout(
                height=275,margin=dict(l=10,r=10,t=8,b=8),
                paper_bgcolor="white",plot_bgcolor="white",
                yaxis_title="Puntos físicos medidos",
            )
            figc.update_xaxes(tickformat="%d/%m/%Y",showgrid=False,nticks=7)
            figc.update_yaxes(gridcolor="#E9EEF3",rangemode="tozero",dtick=1)
            st.plotly_chart(figc,use_container_width=True,config={"displayModeBar":False})

    st.markdown(
        "<div class='note'>"
        "<b>Lectura:</b> la dona resume el cumplimiento global de la ruta; la tabla compara los cinco molinos; "
        "el detalle inferior permite localizar exactamente qué punto físico quedó pendiente."
        "</div>",unsafe_allow_html=True
    )


# =====================================================================
# DIAGNÓSTICO ESPECTRAL
# =====================================================================
elif pagina == "Diagnóstico Espectral":
    cabecera_dashboard(
        "DIAGNÓSTICO ESPECTRAL — MOLINO 1A · CONTRAEJE",
        "FFT histórica, frecuencias mecánicas y comparación de hipótesis de causa",
        "espectral",
    )

    espectros = load_espectros(_firma_espectros(ESPECTROS_DIR))

    if not espectros:
        st.warning(
            "No se encontraron CSV espectrales. Copia las carpetas de puntos dentro de "
            "espectros/Molino_1A/Contraeje/."
        )
    else:
        datos_mec = datos_mecanicos_equipo("Molino 1A")
        diag = diagnostico_contraeje_molino1a(espectros)
        gear = diag.get("engranaje", {})
        bearing = diag.get("rodamiento", {})

        # --------------------------------------------------------------
        # Ficha mecánica: solo Molino 1A queda poblado con datos reales.
        # Molino 1 está preparado en el backend, sin copiar valores de 1A.
        # --------------------------------------------------------------
        st.markdown("<div class='section-title'>Referencia mecánica del conjunto</div>", unsafe_allow_html=True)
        m1,m2,m3,m4,m5,m6 = st.columns(6)
        rpm = datos_mec.get("RPMContraeje")
        f1 = float(rpm)/60.0 if rpm else np.nan
        gmf = gear.get("gmf_hz", np.nan)
        rpm_cat = gear.get("rpm_catalina", np.nan)

        mec_cards = [
            (m1,"⚙","#2563EB","Potencia",f"{datos_mec.get('PotenciaHP',0):.0f} HP","Molino 1A"),
            (m2,"↻","#2563EB","Contraeje",f"{rpm:.0f} RPM" if rpm else "Sin dato",f"1X = {f1:.2f} Hz" if pd.notna(f1) else ""),
            (m3,"#","#D99A00","Piñón",f"{datos_mec.get('DientesPinion')} dientes",f"GMF = {gmf:.2f} Hz" if pd.notna(gmf) else ""),
            (m4,"#","#D99A00","Catalina",f"{datos_mec.get('DientesCatalina')} dientes",f"≈ {rpm_cat:.2f} RPM" if pd.notna(rpm_cat) else ""),
            (m5,"◎","#7C3AED","Rodamiento L.A.",str(datos_mec.get("RodamientoLA")),"Punto físico 3"),
            (m6,"◎","#C62828","Rodamiento L.L.",str(datos_mec.get("RodamientoLL")),"Punto físico 4"),
        ]
        for col,icono,color,label,value,note in mec_cards:
            col.markdown(
                f"""
                <div class='kpi-card' style='--accent:{color}'>
                  <div class='kpi-icon'>{icono}</div>
                  <div class='kpi-body'>
                    <div class='kpi-label'>{label}</div>
                    <div class='kpi-value'>{html.escape(str(value))}</div>
                    <div class='kpi-note'>{html.escape(str(note))}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True
            )

        puntos = sorted(set(k[0] for k in espectros))
        variables = [v for v in ["Velocidad","Aceleración","Envolvente"]
                     if any(k[2] == v for k in espectros)]

        s1,s2,s3,s4 = st.columns([.75,.95,1.0,1.0])
        with s1:
            punto_sp = st.selectbox(
                "Punto",
                puntos,
                index=puntos.index("4H") if "4H" in puntos else 0,
                key="sp_punto",
            )
        with s2:
            variable_sp = st.selectbox(
                "Variable",
                variables,
                index=0,
                key="sp_variable",
            )

        fechas_sp = sorted(
            set(k[1] for k in espectros if k[0] == punto_sp and k[2] == variable_sp)
        )
        with s3:
            fecha_sp = st.selectbox(
                "Fecha actual",
                fechas_sp,
                index=len(fechas_sp)-1,
                format_func=lambda d: pd.to_datetime(d).strftime("%d/%m/%Y"),
                key="sp_fecha_actual",
            )
        with s4:
            refs=[d for d in fechas_sp if d <= fecha_sp]
            fecha_ref_sp = st.selectbox(
                "Comparar contra",
                refs,
                index=0,
                format_func=lambda d: pd.to_datetime(d).strftime("%d/%m/%Y"),
                key="sp_fecha_ref",
            )

        actual = espectro_por_clave(espectros,punto_sp,fecha_sp,variable_sp)
        referencia = espectro_por_clave(espectros,punto_sp,fecha_ref_sp,variable_sp)
        comp = resumen_comparativo(espectros,punto_sp,variable_sp,fecha_sp,fecha_ref_sp)
        evo = evolucion_rms(espectros,punto_sp,variable_sp)
        unidad = unidad_amplitud(variable_sp)

        k1,k2,k3,k4,k5 = st.columns(5)
        cambio = comp.get("cambio_pct",np.nan)
        cambio_txt = f"{cambio:+.1f}%" if pd.notna(cambio) else "—"
        rms_act = comp.get("rms_actual",np.nan)
        pico_hz = comp.get("pico_hz",np.nan)
        pico_amp = comp.get("pico_amp",np.nan)
        principal = diag.get("principal") or {}
        cards=[
            (k1,"▥","#2563EB","Evidencias disponibles",str(len(fechas_sp)),f"{punto_sp} · {variable_sp}"),
            (k2,"≈","#0B6FA4","RMS espectral actual",f"{rms_act:.3f} {unidad}" if pd.notna(rms_act) else "—",pd.to_datetime(fecha_sp).strftime("%d/%m/%Y")),
            (k3,"↗","#E86A12","Cambio vs referencia",cambio_txt,pd.to_datetime(fecha_ref_sp).strftime("%d/%m/%Y")),
            (k4,"⌁","#7C3AED","Pico dominante",f"{pico_hz:.2f} Hz" if pd.notna(pico_hz) else "—",f"{pico_amp:.3f} {unidad}" if pd.notna(pico_amp) else ""),
            (k5,"⚙","#C62828","Hipótesis principal",principal.get("Hipotesis","En análisis"),f"Confianza {principal.get('Confianza','—')}"),
        ]
        for col,icono,color,label,value,note in cards:
            col.markdown(
                f"""
                <div class='kpi-card' style='--accent:{color}'>
                  <div class='kpi-icon'>{icono}</div>
                  <div class='kpi-body'>
                    <div class='kpi-label'>{label}</div>
                    <div class='kpi-value'>{html.escape(str(value))}</div>
                    <div class='kpi-note'>{html.escape(str(note))}</div>
                  </div>
                </div>
                """,unsafe_allow_html=True
            )

        # --------------------------------------------------------------
        # Comparación espectral con frecuencias mecánicas superpuestas
        # --------------------------------------------------------------
        sp_left,sp_right = st.columns([1.65,.95],gap="medium")
        with sp_left:
            st.markdown("<div class='section-title'>Espectro actual vs referencia</div>",unsafe_allow_html=True)
            figsp=go.Figure()
            if not referencia.empty:
                figsp.add_trace(go.Scatter(
                    x=referencia["FrecuenciaHz"],y=referencia["Amplitud"],
                    mode="lines",name=f"Referencia {pd.to_datetime(fecha_ref_sp).strftime('%d/%m/%Y')}",
                    line=dict(color="#94A3B8",width=1.4),
                    hovertemplate="%{x:.2f} Hz · %{y:.4f}<extra></extra>",
                ))
            if not actual.empty:
                figsp.add_trace(go.Scatter(
                    x=actual["FrecuenciaHz"],y=actual["Amplitud"],
                    mode="lines",name=f"Actual {pd.to_datetime(fecha_sp).strftime('%d/%m/%Y')}",
                    line=dict(color="#0B6FA4",width=2.0),
                    hovertemplate="%{x:.2f} Hz · %{y:.4f}<extra></extra>",
                ))

            # Referencias físicas. No se usan como diagnóstico por sí solas.
            if pd.notna(f1):
                figsp.add_vline(x=f1,line_dash="dot",line_color="#64748B",opacity=.55)
            if pd.notna(gmf):
                for n in range(1,5):
                    figsp.add_vline(
                        x=n*gmf,
                        line_dash="dash",
                        line_color="#E86A12",
                        opacity=.48 if n > 1 else .75,
                    )
            fcand = bearing.get("frecuencia_hz", np.nan)
            if pd.notna(fcand):
                for n in range(1,6):
                    figsp.add_vline(
                        x=n*fcand,
                        line_dash="dot",
                        line_color="#7C3AED",
                        opacity=.30,
                    )

            figsp.update_layout(
                height=365,margin=dict(l=10,r=10,t=8,b=8),
                paper_bgcolor="white",plot_bgcolor="white",
                xaxis_title="Frecuencia (Hz)",yaxis_title=f"{variable_sp} ({unidad})",
                legend=dict(orientation="h",y=1.03,x=0,title_text=""),
            )
            figsp.update_xaxes(gridcolor="#EEF2F6",rangemode="tozero")
            figsp.update_yaxes(gridcolor="#EEF2F6",rangemode="tozero")
            st.plotly_chart(figsp,use_container_width=True,config={"displayModeBar":False})
            st.markdown(
                "<div class='note'>"
                "<b>Referencias:</b> gris = 1X; naranja = GMF y armónicos; "
                "morado = familia candidata 30.8 Hz. Las líneas son guías de frecuencia, no alarmas."
                "</div>", unsafe_allow_html=True
            )

        with sp_right:
            st.markdown("<div class='section-title'>Picos principales — espectro actual</div>",unsafe_allow_html=True)
            picos = picos_locales(actual,n=10,min_rel=.03) if not actual.empty else pd.DataFrame()
            if picos.empty:
                st.info("No se detectaron picos locales suficientes.")
            else:
                tp=picos.copy()
                tp["Frecuencia"] = tp["FrecuenciaHz"].map(lambda x:f"{x:.2f} Hz")
                tp["Amplitud"] = tp["Amplitud"].map(lambda x:f"{x:.4f} {unidad}")
                tp["Orden"] = range(1,len(tp)+1)
                st.markdown(tabla_html(tp[["Orden","Frecuencia","Amplitud"]]),unsafe_allow_html=True)

        # --------------------------------------------------------------
        # Diagnóstico comparativo de hipótesis
        # --------------------------------------------------------------
        st.markdown("<div class='section-title'>Diagnóstico por evidencia física — contraeje</div>", unsafe_allow_html=True)
        hcols = st.columns(3)
        hcolors = {
            "Engranaje piñón–catalina":"#E86A12",
            "Rodamiento lado libre 22244CC":"#7C3AED",
            "Soltura / holgura mecánica":"#64748B",
        }
        for col, hip in zip(hcols, diag.get("hipotesis", [])):
            color = hcolors.get(hip["Hipotesis"], "#2563EB")
            evid = "<br>".join("• " + html.escape(e) for e in hip.get("Evidencias", [])[:4])
            col.markdown(
                f"""
                <div class='tech-summary' style='border-left-color:{color};min-height:168px'>
                  <div class='tech-summary-title'>{html.escape(hip['Hipotesis'])}</div>
                  <div class='tech-line'><b>Confianza:</b> {html.escape(hip['Confianza'])} · Evidencia {hip['Puntaje']}/100</div>
                  <div class='tech-line' style='margin-top:5px'>{evid or 'Evidencia insuficiente.'}</div>
                </div>
                """, unsafe_allow_html=True
            )

        # --------------------------------------------------------------
        # Implicancia específica del rodamiento lado libre
        # --------------------------------------------------------------
        rleft, rright = st.columns([1.0,1.35],gap="medium")
        with rleft:
            st.markdown("<div class='section-title'>Rodamiento lado libre — Punto 4</div>", unsafe_allow_html=True)
            order_cand = bearing.get("orden_x", np.nan)
            env_growth = bearing.get("Envolvente_growth_pct", np.nan)
            env_harm = bearing.get("Envolvente_armonicos", 0)
            st.markdown(
                f"""
                <div class='tech-summary' style='border-left-color:#7C3AED'>
                  <div class='tech-summary-title'>22244CC · implicancia actual</div>
                  <div class='tech-line'><b>Familia candidata:</b> {bearing.get('frecuencia_hz',np.nan):.2f} Hz
                  ({order_cand:.2f}X del contraeje).</div>
                  <div class='tech-line'><b>Evolución en envolvente:</b> {env_growth:+.0f}% frente al nivel base.</div>
                  <div class='tech-line'><b>Armónicos relevantes actuales:</b> {int(env_harm)}.</div>
                  <div class='tech-line'><b>Interpretación:</b> existe evidencia compatible con participación del apoyo/rodamiento,
                  pero todavía no se identifica pista interna, externa, rodillo o jaula.</div>
                </div>
                """, unsafe_allow_html=True
            )

        with rright:
            st.markdown("<div class='section-title'>Criterio de diagnóstico y acciones</div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div class='tech-summary'>
                  <div class='tech-summary-title'>Conclusión actual</div>
                  <div class='tech-line'>
                    <b>1.</b> La evidencia de engrane es fuerte: GMF = 76 Hz, armónicos y modulación ±1X aumentan en 4H.
                  </div>
                  <div class='tech-line'>
                    <b>2.</b> El rodamiento lado libre no debe descartarse: la envolvente aumenta y aparece una familia no sincrónica ≈7.70X con armónicos.
                  </div>
                  <div class='tech-line'>
                    <b>3.</b> La prioridad de campo es revisar conjuntamente backlash/patrón de contacto del engrane y el apoyo 4:
                    fijación, juego, lubricación, temperatura y ruido localizado.
                  </div>
                  <div class='tech-line'>
                    <b>4.</b> Para confirmar BPFO/BPFI/BSF/FTF se requiere el factor de frecuencias o geometría interna exacta del 22244CC.
                    Hasta entonces el sistema mantiene la clasificación como “familia candidata de rodamiento”.
                  </div>
                </div>
                """, unsafe_allow_html=True
            )

        # --------------------------------------------------------------
        # Evolución temporal + heatmap
        # --------------------------------------------------------------
        eleft,eright=st.columns([1.25,1.0],gap="medium")
        with eleft:
            st.markdown("<div class='section-title'>Evolución del RMS espectral</div>",unsafe_allow_html=True)
            if not evo.empty:
                fige=go.Figure(go.Scatter(
                    x=evo["Fecha"],y=evo["RMS_Espectral"],mode="lines+markers",
                    line=dict(color="#0B6FA4",width=2.2),marker=dict(size=6),
                    hovertemplate="Fecha: %{x|%d/%m/%Y}<br>RMS espectral: %{y:.4f}<extra></extra>",
                ))
                fige.update_layout(
                    height=280,margin=dict(l=8,r=8,t=6,b=5),
                    paper_bgcolor="white",plot_bgcolor="white",showlegend=False,
                    xaxis_title="",yaxis_title=f"RMS espectral ({unidad})",
                )
                fige.update_xaxes(tickformat="%d/%m/%Y",showgrid=False)
                fige.update_yaxes(gridcolor="#E9EEF3",rangemode="tozero")
                st.plotly_chart(fige,use_container_width=True,config={"displayModeBar":False})

        with eright:
            st.markdown("<div class='section-title'>Lectura de tendencia espectral</div>",unsafe_allow_html=True)
            if punto_sp == "4H":
                vel4 = diag.get("cambio_vel_4H_pct", np.nan)
                env4 = diag.get("cambio_env_4H_pct", np.nan)
                accb = diag.get("cambio_acc_100_300_pct", np.nan)
                st.markdown(
                    f"""
                    <div class='tech-summary'>
                      <div class='tech-summary-title'>4H · rodamiento lado libre / zona piñón</div>
                      <div class='tech-line'>Velocidad espectral: <b>{vel4:+.0f}%</b> respecto al nivel inicial.</div>
                      <div class='tech-line'>Envolvente: <b>{env4:+.0f}%</b>.</div>
                      <div class='tech-line'>Aceleración 100–300 Hz: <b>{accb:+.0f}%</b>.</div>
                      <div class='tech-line'>El cambio es persistente y localizado respecto a 3V.</div>
                    </div>
                    """, unsafe_allow_html=True
                )
            else:
                st.markdown(
                    """
                    <div class='tech-summary'>
                      <div class='tech-summary-title'>3V · referencia comparativa</div>
                      <div class='tech-line'>
                        Su evolución es considerablemente más estable que 4H, por lo que sirve como referencia para demostrar que la anomalía no es uniforme en todo el contraeje.
                      </div>
                    </div>
                    """, unsafe_allow_html=True
                )

        st.markdown("<div class='section-title'>Evolución espectral por fecha</div>",unsafe_allow_html=True)
        freq,fechas_m,z=matriz_evolucion(espectros,punto_sp,variable_sp)
        if len(freq) and len(fechas_m):
            fighm=go.Figure(go.Heatmap(
                x=freq,
                y=[pd.to_datetime(f).strftime("%d/%m/%Y") for f in fechas_m],
                z=z,
                colorscale="Blues",
                colorbar=dict(title=unidad),
                hovertemplate="Fecha: %{y}<br>Frecuencia: %{x:.2f} Hz<br>Amplitud: %{z:.4f}<extra></extra>",
            ))
            fighm.update_layout(
                height=315,margin=dict(l=10,r=10,t=5,b=8),
                paper_bgcolor="white",plot_bgcolor="white",
                xaxis_title="Frecuencia (Hz)",yaxis_title="Fecha",
            )
            st.plotly_chart(fighm,use_container_width=True,config={"displayModeBar":False})


# =====================================================================
# VALIDACIÓN DE DATOS
# =====================================================================
elif pagina == "Validación de datos":
    cabecera_dashboard(
        "VALIDACIÓN DE DATOS — MOLINOS",
        "Comprobación de lectura del Excel y clasificación de límites",
        "validacion",
    )

    info = resumen_fuente(mediciones)
    c1,c2,c3,c4,c5 = st.columns(5)
    valores = [
        ("Equipos", info["equipos"]),
        ("Primera fecha", info["fecha_min"].strftime("%d/%m/%Y")),
        ("Última fecha", info["fecha_max"].strftime("%d/%m/%Y")),
        ("Rondas", f"{info['rondas']:,}"),
        ("Valores", f"{info['valores']:,}"),
    ]
    for col, (lbl, val) in zip([c1,c2,c3,c4,c5], valores):
        col.markdown(
            f"<div class='kpi-card' style='--accent:#2563EB'>"
            f"<div class='kpi-icon'>•</div><div class='kpi-body'>"
            f"<div class='kpi-label'>{lbl}</div><div class='kpi-value'>{val}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    a,b,c = st.columns(3)
    equipos = (
        mediciones[["OrdenEquipo","EquipoCorto"]]
        .drop_duplicates()
        .sort_values("OrdenEquipo")["EquipoCorto"]
        .tolist()
    )
    equipo = a.selectbox("Equipo", equipos)
    dfe = mediciones[mediciones["EquipoCorto"] == equipo]
    punto = b.selectbox("Punto", ["Todos"] + sorted(dfe["CodPunto"].unique().tolist()))
    variable = c.selectbox("Variable", ["Todas"] + sorted(dfe["TipoVariable"].dropna().unique().tolist()))

    dff = dfe.copy()
    if punto != "Todos":
        dff = dff[dff["CodPunto"] == punto]
    if variable != "Todas":
        dff = dff[dff["TipoVariable"] == variable]

    cols = [
        "Fecha","EquipoCorto","TAG","CodPunto","Componente",
        "TipoVariable","Valor","Unidad","Estado","Tecnico","Observacion"
    ]
    vista = dff[[x for x in cols if x in dff.columns]].copy()
    vista["Fecha"] = pd.to_datetime(vista["Fecha"]).dt.strftime("%d/%m/%Y")
    vista = vista.rename(columns={
        "EquipoCorto":"Equipo",
        "CodPunto":"Punto",
        "TipoVariable":"Variable",
        "Tecnico":"Técnico",
        "Observacion":"Observación",
    })
    st.markdown(tabla_html(vista.head(80), estado_col="Estado"), unsafe_allow_html=True)
    if len(vista) > 80:
        st.caption(f"Se muestran 80 de {len(vista):,} registros filtrados.")

    st.markdown("<div class='section-title'>Prueba de límites oficiales</div>", unsafe_allow_html=True)
    st.markdown(tabla_html(tabla_prueba_limites(), estado_col="Estado esperado"), unsafe_allow_html=True)
