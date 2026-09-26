"""
Interfaz Streamlit.  Correr con:  streamlit run app.py

Este archivo solo arma pantallas: lee parámetros, llama a simular() y muestra resultados.
Toda la lógica de la simulación está en simulacion.py (Python puro).
pandas se usa solamente para dibujar tablas.
"""
import copy
import math

import altair as alt
import pandas as pd
import streamlit as st

from generador import CONVERSIONES
from modelo import ACTIVIDADES, calcular_red
from parametros import VARIABLES_ALEATORIAS, parametros_por_defecto, validar
from simulacion import simular, traza_primeras_iteraciones

st.set_page_config(page_title="TP3 Simulación – Proyecto logístico", layout="wide")

DEFECTO = parametros_por_defecto()
COLOR_SERIE_1 = "#2a78d6"   # duraciones T
COLOR_SERIE_2 = "#eb6834"   # promedio acumulado


# ---------------------------------------------------------------------------
# Estado de los generadores (para poder "copiar B a todos")
# ---------------------------------------------------------------------------

CAMPOS_GENERADOR = ["semilla", "a", "c", "m"]

for variable in VARIABLES_ALEATORIAS:
    for campo in CAMPOS_GENERADOR:
        st.session_state.setdefault(f"gen_{variable}_{campo}", DEFECTO["generadores"][variable][campo])


def copiar_generador_b():
    for variable in ("D", "E", "F"):
        for campo in CAMPOS_GENERADOR:
            st.session_state[f"gen_{variable}_{campo}"] = st.session_state[f"gen_B_{campo}"]


def tabla_editable_a_filas(df):
    """Convierte la tabla editada en la interfaz a la lista de dicts que usa el motor."""
    filas = []
    for _, fila in df.dropna(subset=["valor", "probabilidad"]).iterrows():
        etiqueta = fila["etiqueta"] if isinstance(fila["etiqueta"], str) and fila["etiqueta"] else f"{fila['valor']:g}"
        filas.append({"etiqueta": etiqueta, "valor": float(fila["valor"]),
                      "probabilidad": float(fila["probabilidad"])})
    return filas


# ---------------------------------------------------------------------------
# Panel de parámetros
# ---------------------------------------------------------------------------

def leer_parametros():
    p = parametros_por_defecto()
    sb = st.sidebar

    sb.header("Simulación")
    p["iteraciones"] = sb.number_input("Cantidad de iteraciones N", min_value=1, value=DEFECTO["iteraciones"], step=1000)
    p["desde"] = sb.number_input("Mostrar desde la iteración j", min_value=0, value=DEFECTO["desde"], step=1)
    p["cantidad_filas"] = sb.number_input("Cantidad de filas i a mostrar", min_value=0, value=DEFECTO["cantidad_filas"], step=1)
    p["decimales_rnd"] = sb.number_input("Decimales del RND (truncar)", min_value=1, max_value=12, value=None,
                                         step=1, placeholder="sin truncar")
    p["conversion"] = sb.selectbox("Conversión X → RND", CONVERSIONES, index=0)

    sb.header("Generadores")
    sb.caption("X(n+1) = (a·X(n) + c) mod m — uno por variable aleatoria. m = número de legajo.")
    sb.button("Copiar parámetros del generador de B a todos", on_click=copiar_generador_b)
    for variable in VARIABLES_ALEATORIAS:
        with sb.expander(f"Generador de {variable}", expanded=(variable == "B")):
            generador = {}
            for campo, etiqueta in [("semilla", "Semilla X0"), ("a", "a (multiplicativa)"),
                                    ("c", "c (aditiva)"), ("m", "m (legajo)")]:
                generador[campo] = st.number_input(etiqueta, min_value=0, step=1, key=f"gen_{variable}_{campo}",
                                                   placeholder="Nº de legajo" if campo == "m" else None)
            p["generadores"][variable] = generador

    sb.header("Distribuciones")
    p["A"] = sb.number_input("A – constante (min)", min_value=0.0, value=float(DEFECTO["A"]), step=1.0)
    sb.markdown("**B – discreta** (picking)")
    df_b = sb.data_editor(pd.DataFrame(DEFECTO["B"]), num_rows="dynamic", key="tabla_B", hide_index=True)
    p["B"] = tabla_editable_a_filas(df_b)
    p["C"] = sb.number_input("C – constante (min)", min_value=0.0, value=float(DEFECTO["C"]), step=1.0)
    sb.markdown("**D – uniforme U[a, b]** (packing)")
    col1, col2 = sb.columns(2)
    p["D"] = {"a": col1.number_input("a", value=float(DEFECTO["D"]["a"]), step=1.0),
              "b": col2.number_input("b", value=float(DEFECTO["D"]["b"]), step=1.0)}
    media = sb.number_input("E – exponencial: media (min)", value=float(DEFECTO["E"]["media"]), step=1.0)
    p["E"] = {"media": media}
    if media > 0:
        sb.caption(f"λ = 1 / media = {1 / media:.4f}")
    sb.markdown("**F – discreta** (montacargas)")
    df_f = sb.data_editor(pd.DataFrame(DEFECTO["F"]), num_rows="dynamic", key="tabla_F", hide_index=True)
    p["F"] = tabla_editable_a_filas(df_f)

    sb.header("Estimadores")
    p["n_percentil"] = sb.number_input("Simulaciones para el percentil", min_value=1, value=DEFECTO["n_percentil"], step=1)
    p["confianza"] = sb.number_input("Nivel de confianza", min_value=0.01, max_value=0.99,
                                     value=DEFECTO["confianza"], step=0.01)
    p["umbral_menor"] = sb.number_input("Umbral P(T ≤ x)", value=float(DEFECTO["umbral_menor"]), step=1.0)
    p["umbral_mayor"] = sb.number_input("Umbral P(T ≥ x)", value=float(DEFECTO["umbral_mayor"]), step=1.0)
    p["desplazamiento_ultimo"] = sb.number_input("El último intervalo empieza Tmin + …", min_value=1.0,
                                                 value=float(DEFECTO["desplazamiento_ultimo"]), step=1.0)
    p["n_frecuencias"] = sb.number_input("N observaciones para la distribución", min_value=1, value=None,
                                         step=1, placeholder="= todas las iteraciones")
    return p


# ---------------------------------------------------------------------------
# Tabla del vector de estado (encabezado doble)
# ---------------------------------------------------------------------------

def columnas_vector(p):
    """(grupo, subcolumna, clave en la fila)"""
    cols = [("Iteración", "n", "n"), ("A", "Duración", "A")]
    cols += [("B", "X", "B_x"), ("B", "RND", "B_rnd"), ("B", "Duración", "B")]
    cols += [("C", "Duración", "C")]
    cols += [("D", "X", "D_x"), ("D", "RND", "D_rnd"), ("D", "Duración", "D")]
    cols += [("E", "X", "E_x"), ("E", "RND", "E_rnd"), ("E", "Duración", "E")]
    cols += [("F", "X", "F_x"), ("F", "RND", "F_rnd"), ("F", "Montacargas", "F_estado"), ("F", "Duración", "F")]
    cols += [("Tiempos de la red", nombre, clave) for nombre, clave in
             [("finA", "fin_a"), ("finB", "fin_b"), ("finC", "fin_c"), ("finD", "fin_d"),
              ("finE", "fin_e"), ("inicioF", "inicio_f"), ("finF", "fin_f")]]
    cols += [("Rutas", "Ruta 1", "ruta1"), ("Rutas", "Ruta 2", "ruta2"), ("Rutas", "Holgura", "holgura")]
    cols += [("Proyecto", "T", "T"), ("Proyecto", "Ruta crítica", "ruta_critica")]
    cols += [("Crítica (1/0)", a, "crit_" + a) for a in ACTIVIDADES]
    cols += [("Promedios", a, "prom_" + a) for a in ACTIVIDADES]
    cols += [("Promedios", "Ruta 1", "prom_ruta1"), ("Promedios", "Ruta 2", "prom_ruta2"), ("Promedios", "T", "prom_T")]
    cols += [("T observado", "Mín", "t_min_obs"), ("T observado", "Máx", "t_max_obs")]
    cols += [("Veces crítica", a, "cont_crit_" + a) for a in ACTIVIDADES]
    cols += [("Proporción crítica", a, "prop_crit_" + a) for a in ACTIVIDADES]
    cols += [("Ruta crítica: veces", "R1", "cont_ruta1"), ("Ruta crítica: veces", "R2", "cont_ruta2"),
             ("Ruta crítica: veces", "Empate", "cont_empate")]
    cols += [("Ruta crítica: proporción", "R1", "prop_ruta1"), ("Ruta crítica: proporción", "R2", "prop_ruta2"),
             ("Ruta crítica: proporción", "Empate", "prop_empate")]
    cols += [(f"P(T ≤ {p['umbral_menor']:g})", "Cont.", "cont_menor"), (f"P(T ≤ {p['umbral_menor']:g})", "Prob.", "prob_menor")]
    cols += [(f"P(T ≥ {p['umbral_mayor']:g})", "Cont.", "cont_mayor"), (f"P(T ≥ {p['umbral_mayor']:g})", "Prob.", "prob_mayor")]
    cols += [(f"T con {p['confianza']:.0%} confianza", "T", "t_confianza")]
    return cols


def formatear(valor):
    if valor is None:
        return ""
    if isinstance(valor, float):
        if math.isinf(valor):
            return "∞"
        return f"{valor:.4f}"
    return str(valor)


def mostrar_vector(filas, p, altura=520):
    cols = columnas_vector(p)
    datos = []
    n_anterior = None
    for fila in filas:
        # Si hay un salto (ej. de la fila j+i a la última), se marca con "…"
        if n_anterior is not None and fila["n"] != n_anterior + 1:
            datos.append(["…"] * len(cols))
        datos.append([formatear(fila.get(clave)) for _, _, clave in cols])
        n_anterior = fila["n"]
    df = pd.DataFrame(datos, columns=pd.MultiIndex.from_tuples([(g, s) for g, s, _ in cols]))
    html = df.to_html(index=False, classes="vector", border=0)
    st.markdown(f"""
<style>
.contenedor-vector {{ overflow: auto; max-height: {altura}px; border: 1px solid rgba(128,128,128,.35); border-radius: 6px; }}
table.vector {{ border-collapse: collapse; font-size: 12px; white-space: nowrap; }}
table.vector th, table.vector td {{ padding: 3px 8px; border: 1px solid rgba(128,128,128,.25); text-align: right; }}
table.vector thead th {{ position: sticky; background: var(--background-color, #f0f2f6); text-align: center; }}
table.vector thead tr:first-child th {{ top: 0; }}
table.vector thead tr:nth-child(2) th {{ top: 24px; }}
</style>
<div class="contenedor-vector">{html}</div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------

def mostrar_estimadores(fila, resultado, p):
    c = st.columns(4)
    c[0].metric("Tiempo mínimo teórico", f"{resultado['t_min_teorico']:.4f} min")
    c[1].metric("T promedio", f"{fila['prom_T']:.4f} min")
    c[2].metric("T mínimo observado", formatear(fila["t_min_obs"]))
    c[3].metric("T máximo observado", formatear(fila["t_max_obs"]))
    c = st.columns(4)
    c[0].metric(f"P(T ≤ {p['umbral_menor']:g})", f"{fila['prob_menor']:.4f}")
    c[1].metric(f"P(T ≥ {p['umbral_mayor']:g})", f"{fila['prob_mayor']:.4f}")
    c[2].metric(f"T con {p['confianza']:.0%} de confianza",
                "—" if fila["t_confianza"] is None else f"{fila['t_confianza']:.4f} min")
    c[3].metric("Iteración", f"{fila['n']}")

    filas = [{"Actividad / ruta": a, "Duración promedio (min)": fila["prom_" + a],
              "Veces crítica": fila["cont_crit_" + a], "Proporción crítica": fila["prop_crit_" + a]}
             for a in ACTIVIDADES]
    filas.append({"Actividad / ruta": "Ruta 1 (A+B+F)", "Duración promedio (min)": fila["prom_ruta1"],
                  "Veces crítica": fila["cont_ruta1"], "Proporción crítica": fila["prop_ruta1"]})
    filas.append({"Actividad / ruta": "Ruta 2 (C+D+E+F)", "Duración promedio (min)": fila["prom_ruta2"],
                  "Veces crítica": fila["cont_ruta2"], "Proporción crítica": fila["prop_ruta2"]})
    filas.append({"Actividad / ruta": "Empate de rutas", "Duración promedio (min)": None,
                  "Veces crítica": fila["cont_empate"], "Proporción crítica": fila["prop_empate"]})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="content",
                 column_config={"Duración promedio (min)": st.column_config.NumberColumn(format="%.4f"),
                                "Proporción crítica": st.column_config.NumberColumn(format="%.4f")})


def mostrar_tabla_acumulada(titulo, tabla):
    st.markdown(f"**{titulo}**")
    st.dataframe(pd.DataFrame([{
        "Etiqueta": f["etiqueta"], "Valor (min)": f["valor"], "Probabilidad": f["probabilidad"],
        "P. acumulada": f["acumulada"], "Intervalo RND": f"[{f['desde']:.4f}, {f['hasta']:.4f})",
    } for f in tabla]), hide_index=True)


def mostrar_frecuencias(resultado):
    frecuencias = resultado["frecuencias"]
    df = pd.DataFrame([{
        "Intervalo": f["intervalo"], "Desde": f"{f['desde']:.4f}",
        "Hasta": "∞" if math.isinf(f["hasta"]) else f"{f['hasta']:.4f}",
        "Marca de clase": "—" if f["marca_clase"] is None else f"{f['marca_clase']:.4f}",
        "FO": f["fo"], "FR": f"{f['fr']:.4f}", "FR acumulada": f"{f['fr_acumulada']:.4f}",
    } for f in frecuencias])
    st.dataframe(df, hide_index=True)
    suma = sum(f["fo"] for f in frecuencias)
    if suma == resultado["n_frecuencias"]:
        st.success(f"Control: suma de FO = {suma} = N observaciones.")
    else:
        st.error(f"Control: suma de FO = {suma} ≠ N observaciones = {resultado['n_frecuencias']}.")


def mostrar_graficos(resultado):
    muestra = pd.DataFrame(resultado["muestra"], columns=["Iteración", "T", "Promedio de T"])
    total = resultado["ultima_fila"]["n"]
    st.caption(f"Gráficos 1 y 2: muestra de {len(muestra)} puntos de {total} iteraciones (solo visualización; "
               "los estimadores se calculan con todas).")
    largo = muestra.melt("Iteración", var_name="Serie", value_name="Minutos")
    color = alt.Color("Serie:N", scale=alt.Scale(domain=["T", "Promedio de T"],
                                                 range=[COLOR_SERIE_1, COLOR_SERIE_2]),
                      legend=alt.Legend(orient="top", title=None))
    tooltip = [alt.Tooltip("Iteración:Q"), alt.Tooltip("Serie:N"), alt.Tooltip("Minutos:Q", format=".4f")]
    puntos = alt.Chart(largo[largo["Serie"] == "T"]).mark_circle(size=14, opacity=0.5).encode(
        x="Iteración:Q", y=alt.Y("Minutos:Q", title="Duración (min)"), color=color, tooltip=tooltip)
    linea = alt.Chart(largo[largo["Serie"] == "Promedio de T"]).mark_line(strokeWidth=2).encode(
        x="Iteración:Q", y="Minutos:Q", color=color, tooltip=tooltip)
    st.markdown("**1 y 2. Duración T por iteración y promedio acumulado**")
    st.altair_chart((puntos + linea).properties(height=340), width="stretch")

    barras = pd.DataFrame([{"Marca de clase": f["etiqueta"], "Frecuencia": f["fo"], "FR": f["fr"]}
                           for f in resultado["frecuencias"]])
    grafico = alt.Chart(barras).mark_bar(color=COLOR_SERIE_1, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("Marca de clase:N", sort=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Frecuencia:Q", title="Frecuencia observada"),
        tooltip=["Marca de clase", "Frecuencia", alt.Tooltip("FR:Q", format=".4f")])
    st.markdown("**3. Distribución de frecuencias de T**")
    st.altair_chart(grafico.properties(height=300), width="stretch")


def mostrar_datos_fijos():
    with st.expander("Simulacro con datos fijos (ejemplo del enunciado)"):
        c = st.columns(6)
        valores = [c[i].number_input(a, value=v, step=1.0, key=f"fijo_{a}")
                   for i, (a, v) in enumerate(zip(ACTIVIDADES, [15.0, 30.0, 5.0, 10.0, 5.0, 15.0]))]
        red = calcular_red(*valores)
        criticas = ", ".join(a for a in ACTIVIDADES if a in red["criticas"])
        st.markdown(f"Ruta 1 = A+B+F = **{red['ruta1']:g}** · Ruta 2 = C+D+E+F = **{red['ruta2']:g}** · "
                    f"inicioF = max({red['fin_b']:g}, {red['fin_e']:g}) = {red['inicio_f']:g} → "
                    f"**T = {red['T']:g} min** · críticas: {criticas}")


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------

st.title("Proyecto logístico – red de actividades en paralelo")
st.caption("Montecarlo · Inicio → (A → B) ∥ (C → D → E) → F → Fin")

p = leer_parametros()
errores, advertencias = validar(p)
for error in errores:
    st.error(error)
for advertencia in advertencias:
    st.warning(advertencia)

mostrar_datos_fijos()

if st.button("Simular", type="primary", disabled=bool(errores)):
    try:
        with st.spinner("Simulando…"):
            st.session_state["resultado"] = simular(p)
            st.session_state["p_usado"] = copy.deepcopy(p)
            st.session_state.pop("consulta", None)
    except ValueError as error:
        st.session_state.pop("resultado", None)
        st.error(str(error))

if "resultado" in st.session_state:
    resultado = st.session_state["resultado"]
    p_usado = st.session_state["p_usado"]
    ultima = resultado["ultima_fila"]
    if p_usado != p:
        st.info("Cambiaste parámetros: los resultados de abajo son de la simulación anterior. Volvé a simular.")

    st.header(f"Estimadores en la iteración {ultima['n']}")
    mostrar_estimadores(ultima, resultado, p_usado)
    if resultado["percentil"]:
        pc = resultado["percentil"]
        st.success(f"Con un {p_usado['confianza']:.0%} de confianza, el pedido se despacha en "
                   f"**{pc['valor']:.4f} min o menos** (posición i = {pc['posicion']} de las primeras "
                   f"{pc['n']} duraciones ordenadas, F(i) = i/(n+1)).")

    st.header("Vector de estado")
    filas = list(resultado["filas_visibles"])
    if not filas or filas[-1]["n"] != ultima["n"]:
        filas.append(ultima)   # siempre se muestra la última fila
    st.caption(f"Filas {p_usado['desde']} a {p_usado['desde'] + p_usado['cantidad_filas'] - 1} + la última.")
    mostrar_vector(filas, p_usado)

    st.header("Consultar una iteración puntual")
    k = st.number_input("Ver estimadores en la iteración k", min_value=1, max_value=p_usado["iteraciones"],
                        value=min(100, p_usado["iteraciones"]), step=1)
    if st.button("Consultar"):
        # Se vuelve a simular desde cero hasta k con los mismos parámetros (no se guardó la tabla).
        st.session_state["consulta"] = simular(p_usado, hasta=k, guardar_filas=False)
    if "consulta" in st.session_state:
        consulta = st.session_state["consulta"]
        mostrar_estimadores(consulta["ultima_fila"], consulta, p_usado)
        mostrar_vector([consulta["ultima_fila"]], p_usado, altura=140)

    st.header("Tablas de probabilidad acumulada")
    c1, c2 = st.columns(2)
    with c1:
        mostrar_tabla_acumulada("B – Picking", resultado["tabla_b"])
    with c2:
        mostrar_tabla_acumulada("F – Despacho (montacargas)", resultado["tabla_f"])

    st.header("Distribución de frecuencias")
    st.caption(f"Primer intervalo desde Tmin = {resultado['t_min_teorico']:.4f}; ancho = "
               f"{p_usado['desplazamiento_ultimo']:g}/9 = {resultado['ancho_intervalo']:.4f} min; "
               f"N observaciones = {resultado['n_frecuencias']}.")
    mostrar_frecuencias(resultado)

    st.header("Gráficos")
    mostrar_graficos(resultado)

    with st.expander("Traza de las 3 primeras iteraciones (para verificar a mano)"):
        st.markdown(traza_primeras_iteraciones(p_usado))
