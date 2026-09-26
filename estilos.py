"""
Estilos visuales de la interfaz (solo apariencia, nada de lógica de simulación).

Regla de legibilidad: todo bloque HTML propio define SIEMPRE su color de fondo
y su color de letra juntos, para que nunca quede letra clara sobre fondo claro
(o oscura sobre oscuro).
"""
import streamlit as st

# Paleta de azules
MARINO = "#0b2545"        # títulos y encabezados de tabla
AZUL = "#1d5fbf"          # color principal (serie 1)
CELESTE = "#3b9fdc"       # serie 2
INDIGO = "#6a5acd"        # serie 3
NEUTRO = "#a9b8cc"        # barras que no son protagonistas
TEXTO = "#10233f"         # texto sobre fondos claros
TEXTO_SUAVE = "#4a5f7d"   # textos secundarios (contraste > 6:1 sobre blanco)
FONDO_TARJETA = "#ffffff"
FONDO_AVISO = "#e8f3fc"
BORDE = "#c8d6ea"

CSS = f"""
<style>
/* ---------- Encabezado principal ---------- */
.hero {{ background: linear-gradient(120deg, {MARINO} 0%, {AZUL} 100%); color: #ffffff;
  border-radius: 14px; padding: 22px 28px; margin-bottom: 18px; }}
.hero-etiqueta {{ color: #cfe4fa; font-size: .8rem; letter-spacing: .08em; text-transform: uppercase; font-weight: 600; }}
.hero-titulo {{ color: #ffffff; font-size: 1.9rem; font-weight: 700; margin: 4px 0 6px; line-height: 1.2; }}
.hero-sub {{ color: #dbeafb; font-size: .95rem; }}
.hero-chips {{ margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px; }}
.hero-chip {{ background: rgba(255,255,255,.14); color: #ffffff; border: 1px solid rgba(255,255,255,.35);
  border-radius: 999px; padding: 3px 12px; font-size: .8rem; }}

/* ---------- Tarjetas (st.container con key "caja_...") ---------- */
[class*="st-key-caja"] {{ background: {FONDO_TARJETA}; border-radius: 12px !important;
  box-shadow: 0 1px 3px rgba(11,37,69,.08); }}
.titulo-seccion {{ border-left: 4px solid {AZUL}; padding: 2px 0 2px 12px; margin-bottom: 6px; }}
.titulo-seccion .titulo {{ color: {MARINO}; font-size: 1.25rem; font-weight: 700; line-height: 1.3; }}
.titulo-seccion .subtitulo {{ color: {TEXTO_SUAVE}; font-size: .88rem; margin-top: 2px; }}
.titulo-seccion.nivel-2 {{ border-left: 3px solid {CELESTE}; margin-top: 10px; }}
.titulo-seccion.nivel-2 .titulo {{ font-size: 1rem; }}
.numero {{ display: inline-block; background: {AZUL}; color: #ffffff; border-radius: 6px;
  padding: 0 8px; margin-right: 8px; font-size: .95rem; }}

/* ---------- Indicadores (KPI) ---------- */
.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 6px 0 12px; }}
.kpi {{ background: #f7faff; color: {TEXTO}; border: 1px solid {BORDE}; border-top: 3px solid {AZUL};
  border-radius: 10px; padding: 10px 14px; }}
.kpi-label {{ color: {TEXTO_SUAVE}; font-size: .74rem; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }}
.kpi-valor {{ color: {MARINO}; font-size: 1.55rem; font-weight: 700; margin-top: 2px; line-height: 1.2; }}
.kpi-unidad {{ color: {TEXTO_SUAVE}; font-size: .9rem; font-weight: 600; margin-left: 3px; }}
.kpi-detalle {{ color: {TEXTO_SUAVE}; font-size: .78rem; margin-top: 2px; }}

/* ---------- Avisos destacados ---------- */
.aviso {{ background: {FONDO_AVISO}; color: {TEXTO}; border-left: 4px solid {AZUL};
  border-radius: 8px; padding: 10px 14px; margin: 6px 0 10px; font-size: .95rem; }}
.aviso b {{ color: {MARINO}; }}

/* ---------- Tabla del vector de estado ---------- */
.contenedor-vector {{ overflow: auto; border: 1px solid {BORDE}; border-radius: 10px; background: #ffffff; }}
table.vector {{ border-collapse: separate; border-spacing: 0; font-size: 12px; white-space: nowrap;
  font-variant-numeric: tabular-nums; }}
table.vector th, table.vector td {{ padding: 4px 9px; border-right: 1px solid #e3eaf4; border-bottom: 1px solid #e3eaf4; }}
table.vector thead th {{ position: sticky; text-align: center; color: #ffffff; font-weight: 600; z-index: 1; }}
table.vector thead tr:first-child th {{ top: 0; background: {MARINO}; }}
table.vector thead tr:nth-child(2) th {{ top: 26px; background: #1d406e; }}
table.vector tbody td {{ background: #ffffff; color: {TEXTO}; text-align: right; }}
table.vector tbody tr:nth-child(even) td {{ background: #f4f8fd; }}
table.vector tbody tr:hover td {{ background: #e3eefb; }}
</style>
"""


def inyectar_css():
    st.markdown(CSS, unsafe_allow_html=True)


def html(contenido, destino=st):
    destino.markdown(contenido, unsafe_allow_html=True)


def encabezado_app(titulo, subtitulo, chips):
    chips_html = "".join(f'<span class="hero-chip">{c}</span>' for c in chips)
    html(f'<div class="hero"><div class="hero-etiqueta">UTN FRC · Simulación · TP3</div>'
         f'<div class="hero-titulo">{titulo}</div><div class="hero-sub">{subtitulo}</div>'
         f'<div class="hero-chips">{chips_html}</div></div>')


def titulo_seccion(titulo, subtitulo=None, numero=None, destino=st, nivel=1):
    """nivel 1 = título de un recuadro; nivel 2 = subtítulo dentro de un recuadro (más chico)."""
    numero_html = f'<span class="numero">{numero}</span>' if numero is not None else ""
    sub_html = f'<div class="subtitulo">{subtitulo}</div>' if subtitulo else ""
    clase = "titulo-seccion" if nivel == 1 else "titulo-seccion nivel-2"
    html(f'<div class="{clase}"><div class="titulo">{numero_html}{titulo}</div>{sub_html}</div>', destino)


def seccion(clave, titulo, subtitulo=None, numero=None):
    """Recuadro blanco con borde y título. Se usa con:  with seccion(...):"""
    caja = st.container(border=True, key=f"caja_{clave}")
    titulo_seccion(titulo, subtitulo, numero, destino=caja)
    return caja


def tarjetas_kpi(indicadores, destino=st):
    """indicadores: lista de (etiqueta, valor, unidad, detalle)."""
    tarjetas = "".join(
        f'<div class="kpi"><div class="kpi-label">{etiqueta}</div>'
        f'<div class="kpi-valor">{valor}<span class="kpi-unidad">{unidad}</span></div>'
        f'<div class="kpi-detalle">{detalle}</div></div>'
        for etiqueta, valor, unidad, detalle in indicadores)
    html(f'<div class="kpi-grid">{tarjetas}</div>', destino)


def aviso(texto, destino=st):
    html(f'<div class="aviso">{texto}</div>', destino)
