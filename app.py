"""
Interfaz Streamlit.  Correr con:  streamlit run app.py

Este archivo solo arma pantallas: lee parámetros, llama a simular() y muestra resultados.
Toda la lógica de la simulación está en simulacion.py (Python puro).
pandas se usa solamente para dibujar tablas; la apariencia está en estilos.py.
"""
import copy
import math

import altair as alt
import pandas as pd
import streamlit as st

from estilos import (AZUL, CELESTE, INDIGO, NEUTRO, TEXTO, aviso, encabezado_app, inyectar_css,
                     seccion, tarjetas_kpi, titulo_seccion)
from generador import CONVERSIONES
from modelo import ACTIVIDADES, calcular_red, valores_minimos
from parametros import VARIABLES_ALEATORIAS, parametros_por_defecto, validar
from simulacion import simular, traza_primeras_iteraciones

st.set_page_config(page_title="TP3 Simulación – Proyecto logístico", layout="wide")
inyectar_css()

DEFECTO = parametros_por_defecto()


# ---------------------------------------------------------------------------
# Estado de los generadores (para poder "copiar B a todos")
# ---------------------------------------------------------------------------

CAMPOS_GENERADOR = ["semilla", "a", "c", "m"]

for variable in VARIABLES_ALEATORIAS:
    for campo in CAMPOS_GENERADOR + ["conversion"]:
        st.session_state.setdefault(f"gen_{variable}_{campo}", DEFECTO["generadores"][variable][campo])


def copiar_generador_b():
    # Copia semilla, a, c y m. La conversión NO se copia: cada variable conserva la suya
    # (D usa X/(m-1); B, E y F usan X/m).
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
    sb.title("Parámetros")
    sb.caption("Todos los datos se pueden cambiar en la evaluación.")

    sb.subheader("Simulación", divider="blue")
    p["iteraciones"] = sb.number_input("Cantidad de iteraciones N", min_value=1, value=DEFECTO["iteraciones"], step=1000)
    p["desde"] = sb.number_input("Mostrar desde la iteración j", min_value=0, value=DEFECTO["desde"], step=1)
    p["cantidad_filas"] = sb.number_input("Cantidad de filas i a mostrar", min_value=0, value=DEFECTO["cantidad_filas"], step=1)
    p["decimales_rnd"] = sb.number_input("Decimales del RND (truncar)", min_value=1, max_value=12, value=None,
                                         step=1, placeholder="sin truncar")

    sb.subheader("Generadores", divider="blue")
    sb.caption("X(n+1) = (a·X(n) + c) mod m — uno por variable aleatoria. m = número de legajo. "
               "D usa X/(m-1) (el RND puede valer 0 y 1); B, E y F usan X/m.")
    sb.button("Copiar parámetros del generador de B a todos", on_click=copiar_generador_b, width="stretch")
    for variable in VARIABLES_ALEATORIAS:
        with sb.expander(f"Generador de {variable}", expanded=(variable == "B")):
            generador = {}
            for campo, etiqueta in [("semilla", "Semilla X0"), ("a", "a (multiplicativa)"),
                                    ("c", "c (aditiva)"), ("m", "m (legajo)")]:
                generador[campo] = st.number_input(etiqueta, min_value=0, step=1, key=f"gen_{variable}_{campo}",
                                                   placeholder="Nº de legajo" if campo == "m" else None)
            generador["conversion"] = st.selectbox("Conversión X → RND", CONVERSIONES,
                                                   key=f"gen_{variable}_conversion")
            p["generadores"][variable] = generador

    sb.subheader("Distribuciones", divider="blue")
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

    sb.subheader("Estimadores", divider="blue")
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


def mostrar_vector(filas, p, altura="75vh"):
    """altura: alto máximo de ESTA tabla (75vh = 75 % del alto de la pantalla); si hay más filas, scroll."""
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
    tabla = df.to_html(index=False, classes="vector", border=0)
    st.markdown(f'<div class="contenedor-vector" style="max-height: {altura};">{tabla}</div>',
                unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Gráficos (paleta de azules; etiquetas siempre en color de texto)
# ---------------------------------------------------------------------------

def leyenda():
    return alt.Legend(orient="bottom", title=None, labelColor=TEXTO, labelLimit=0)


def texto_sobre_barra(base, **kwargs):
    return base.mark_text(color=TEXTO, fontWeight=600, **kwargs)


def barras_horizontales(df, campo_valor, formato, color, titulo_x, dominio=None):
    # Con dominio fijo (proporciones) el eje va de 0 % a 100 %; el margen extra es para las etiquetas
    x = alt.X(f"{campo_valor}:Q", title=titulo_x,
              scale=alt.Scale(domain=dominio) if dominio else alt.Undefined,
              axis=alt.Axis(format="%", values=[0, 0.25, 0.5, 0.75, 1]) if dominio else alt.Undefined)
    base = alt.Chart(df).encode(y=alt.Y("Nombre:N", sort=None, title=None, axis=alt.Axis(labelOverlap=False)), x=x)
    barras = base.mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, height=18).encode(
        color=color, tooltip=["Nombre", alt.Tooltip(f"{campo_valor}:Q", format=formato)])
    etiquetas = texto_sobre_barra(base, align="left", dx=4).encode(text=alt.Text(f"{campo_valor}:Q", format=formato))
    return barras + etiquetas


def grafico_frecuencias(frecuencias, altura=320):
    datos = pd.DataFrame([{
        "Intervalo": f"[{f['desde']:g}, " + ("∞)" if math.isinf(f["hasta"]) else f"{f['hasta']:g})"),
        "FO": f["fo"], "FR": f["fr"]} for f in frecuencias])
    base = alt.Chart(datos).encode(x=alt.X("Intervalo:N", sort=None, axis=alt.Axis(labelAngle=0), title=None))
    barras = base.mark_bar(color=AZUL, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        y=alt.Y("FO:Q", title="Frecuencia observada"),
        tooltip=["Intervalo", "FO", alt.Tooltip("FR:Q", format=".2%")])
    etiquetas = texto_sobre_barra(base, dy=-8).encode(y="FO:Q", text=alt.Text("FR:Q", format=".1%"))
    return (barras + etiquetas).properties(height=altura)


def grafico_dispersion_y_promedio(resultado):
    muestra = pd.DataFrame(resultado["muestra"], columns=["Iteración", "T", "Promedio de T"])
    largo = muestra.melt("Iteración", var_name="Serie", value_name="Minutos")
    color = alt.Color("Serie:N", scale=alt.Scale(domain=["T", "Promedio de T"], range=[CELESTE, AZUL]),
                      legend=leyenda())
    tooltip = [alt.Tooltip("Iteración:Q"), alt.Tooltip("Serie:N"), alt.Tooltip("Minutos:Q", format=".4f")]
    puntos = alt.Chart(largo[largo["Serie"] == "T"]).mark_circle(size=16, opacity=0.55).encode(
        x="Iteración:Q", y=alt.Y("Minutos:Q", title="Duración (min)", scale=alt.Scale(zero=False)),
        color=color, tooltip=tooltip)
    linea = alt.Chart(largo[largo["Serie"] == "Promedio de T"]).mark_line(strokeWidth=2.5).encode(
        x="Iteración:Q", y="Minutos:Q", color=color, tooltip=tooltip)
    return (puntos + linea).properties(height=340), len(muestra)


# ---------------------------------------------------------------------------
# Bloques de resultados
# ---------------------------------------------------------------------------

def mostrar_estimadores(fila, resultado, p):
    confianza = "—" if fila["t_confianza"] is None else f"{fila['t_confianza']:.4f}"
    tarjetas_kpi([
        ("Iteración", f"{fila['n']:,}".replace(",", "."), "", "fila del vector de estado"),
        ("Tiempo mínimo teórico", f"{resultado['t_min_teorico']:.4f}", "min", "simulacro con valores mínimos"),
        ("T promedio", f"{fila['prom_T']:.4f}", "min", "promedio incremental"),
        ("T mínimo observado", formatear(fila["t_min_obs"]), "min", "hasta esta iteración"),
        ("T máximo observado", formatear(fila["t_max_obs"]), "min", "hasta esta iteración"),
        (f"P(T ≤ {p['umbral_menor']:g})", f"{fila['prob_menor']:.4f}", "", f"{fila['cont_menor']} casos"),
        (f"P(T ≥ {p['umbral_mayor']:g})", f"{fila['prob_mayor']:.4f}", "", f"{fila['cont_mayor']} casos"),
        (f"T con {p['confianza']:.0%} de confianza", confianza, "min" if fila["t_confianza"] is not None else "",
         f"primeras {p['n_percentil']} iteraciones"),
    ])

    filas = [{"Actividad / ruta": a, "Duración promedio (min)": f"{fila['prom_' + a]:.4f}",
              "Veces crítica": fila["cont_crit_" + a], "Proporción crítica": fila["prop_crit_" + a]}
             for a in ACTIVIDADES]
    filas.append({"Actividad / ruta": "Ruta 1 (A+B+F)", "Duración promedio (min)": f"{fila['prom_ruta1']:.4f}",
                  "Veces crítica": fila["cont_ruta1"], "Proporción crítica": fila["prop_ruta1"]})
    filas.append({"Actividad / ruta": "Ruta 2 (C+D+E+F)", "Duración promedio (min)": f"{fila['prom_ruta2']:.4f}",
                  "Veces crítica": fila["cont_ruta2"], "Proporción crítica": fila["prop_ruta2"]})
    filas.append({"Actividad / ruta": "Empate de rutas", "Duración promedio (min)": "—",
                  "Veces crítica": fila["cont_empate"], "Proporción crítica": fila["prop_empate"]})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch",
                 column_config={"Duración promedio (min)": st.column_config.TextColumn(alignment="right"),
                                "Proporción crítica": st.column_config.ProgressColumn(
                                    format="%.4f", min_value=0.0, max_value=1.0)})


def mostrar_tabla_acumulada(titulo, tabla):
    st.markdown(f"**{titulo}**")
    formato = st.column_config.NumberColumn(format="%.4f")
    st.dataframe(pd.DataFrame([{
        "Etiqueta": f["etiqueta"], "Valor (min)": f["valor"], "Probabilidad": f["probabilidad"],
        "P. acumulada": f["acumulada"], "Intervalo RND": f"[{f['desde']:.4f}, {f['hasta']:.4f})",
    } for f in tabla]), hide_index=True, width="stretch",
        column_config={"Valor (min)": formato, "Probabilidad": formato, "P. acumulada": formato})


def mostrar_frecuencias(resultado):
    frecuencias = resultado["frecuencias"]
    # El último intervalo no tiene límite superior ni marca de clase: se muestran "∞" y "—"
    df = pd.DataFrame([{
        "Intervalo": f["intervalo"], "Desde": f["desde"],
        "Hasta": "∞" if math.isinf(f["hasta"]) else f"{f['hasta']:.4f}",
        "Marca de clase": "—" if f["marca_clase"] is None else f"{f['marca_clase']:.4f}",
        "FO": f["fo"], "FR": f["fr"], "FR acumulada": f["fr_acumulada"],
    } for f in frecuencias])
    formato = st.column_config.NumberColumn(format="%.4f")
    texto_derecha = st.column_config.TextColumn(alignment="right")
    st.dataframe(df, hide_index=True, width="stretch",
                 column_config={"Desde": formato, "Hasta": texto_derecha, "Marca de clase": texto_derecha,
                                "FR": formato, "FR acumulada": formato})
    suma = sum(f["fo"] for f in frecuencias)
    if suma == resultado["n_frecuencias"]:
        aviso(f"✔ Control: suma de FO = <b>{suma}</b> = N observaciones.")
    else:
        st.error(f"Control: suma de FO = {suma} ≠ N observaciones = {resultado['n_frecuencias']}.")


def mostrar_datos_fijos():
    with st.expander("Simulacro con datos fijos (ejemplo del enunciado)"):
        c = st.columns(6)
        valores = [c[i].number_input(a, value=v, step=1.0, key=f"fijo_{a}")
                   for i, (a, v) in enumerate(zip(ACTIVIDADES, [15.0, 30.0, 5.0, 10.0, 5.0, 15.0]))]
        red = calcular_red(*valores)
        criticas = ", ".join(a for a in ACTIVIDADES if a in red["criticas"])
        aviso(f"Ruta 1 = A+B+F = <b>{red['ruta1']:g}</b> · Ruta 2 = C+D+E+F = <b>{red['ruta2']:g}</b> · "
              f"inicioF = max({red['fin_b']:g}, {red['fin_e']:g}) = {red['inicio_f']:g} → "
              f"<b>T = {red['T']:g} min</b> · críticas: <b>{criticas}</b>")


# ---------------------------------------------------------------------------
# Respuestas a la consigna (resumen visual al final de la página)
# ---------------------------------------------------------------------------

def gantt_simulacro_minimo(p):
    """Cronograma de la red con el valor mínimo de cada actividad."""
    m = valores_minimos(p)
    red = calcular_red(m["A"], m["B"], m["C"], m["D"], m["E"], m["F"])
    barras = pd.DataFrame([
        {"Actividad": "A", "Rama": "Rama 1 (producto)", "Inicio": 0, "Fin": red["fin_a"], "Dur": m["A"]},
        {"Actividad": "B", "Rama": "Rama 1 (producto)", "Inicio": red["fin_a"], "Fin": red["fin_b"], "Dur": m["B"]},
        {"Actividad": "C", "Rama": "Rama 2 (empaque)", "Inicio": 0, "Fin": red["fin_c"], "Dur": m["C"]},
        {"Actividad": "D", "Rama": "Rama 2 (empaque)", "Inicio": red["fin_c"], "Fin": red["fin_d"], "Dur": m["D"]},
        {"Actividad": "E", "Rama": "Rama 2 (empaque)", "Inicio": red["fin_d"], "Fin": red["fin_e"], "Dur": m["E"]},
        {"Actividad": "F", "Rama": "Convergencia (F)", "Inicio": red["inicio_f"], "Fin": red["fin_f"], "Dur": m["F"]},
    ])
    color = alt.Color("Rama:N", scale=alt.Scale(
        domain=["Rama 1 (producto)", "Rama 2 (empaque)", "Convergencia (F)"],
        range=[AZUL, CELESTE, INDIGO]), legend=leyenda())
    base = alt.Chart(barras).encode(y=alt.Y("Actividad:N", sort=None, title=None, axis=alt.Axis(labelOverlap=False)))
    rectangulos = base.mark_bar(cornerRadius=4, height=16).encode(
        x=alt.X("Inicio:Q", title="Minutos"), x2="Fin:Q", color=color,
        tooltip=["Actividad", "Rama", alt.Tooltip("Inicio:Q", format=".2f"),
                 alt.Tooltip("Fin:Q", format=".2f"), alt.Tooltip("Dur:Q", title="Duración", format=".2f")])
    etiquetas = texto_sobre_barra(base, align="left", dx=4).encode(x="Fin:Q", text=alt.Text("Dur:Q", format=".2f"))
    return (rectangulos + etiquetas).properties(height=alt.Step(30)), red, m


def mostrar_respuestas(resultado, p):
    fila = resultado["ultima_fila"]
    n = fila["n"]

    # --- 1 y 2 ---
    col1, col2 = st.columns(2)
    with col1:
        with seccion("r1", "Tiempo mínimo del proyecto",
                     "Simulacro con el valor mínimo de cada actividad: ¿en cuánto podría haberse hecho?", 1):
            grafico, red, m = gantt_simulacro_minimo(p)
            tarjetas_kpi([("Tiempo mínimo teórico", f"{resultado['t_min_teorico']:.4f}", "min",
                           "constante → valor · discreta → menor · uniforme → a · exponencial → 0")])
            aviso(f"max(A + B, C + D + E) + F = max({m['A']:g} + {m['B']:g}, "
                  f"{m['C']:g} + {m['D']:g} + {m['E']:g}) + {m['F']:g} = <b>{red['T']:g} min</b>")
            st.altair_chart(grafico, width="stretch")
            st.caption(f"Mínimo observado en la simulación: {fila['t_min_obs']:.4f} min · "
                       f"máximo observado: {fila['t_max_obs']:.4f} min.")

    with col2:
        with seccion("r2", "Duración de cada proceso",
                     f"Duración promedio de cada actividad y de cada ruta hasta la iteración {n}.", 2):
            datos = [{"Nombre": a, "Minutos": fila["prom_" + a], "Tipo": "Actividad"} for a in ACTIVIDADES]
            datos += [{"Nombre": "Ruta 1 (A+B+F)", "Minutos": fila["prom_ruta1"], "Tipo": "Ruta / total"},
                      {"Nombre": "Ruta 2 (C+D+E+F)", "Minutos": fila["prom_ruta2"], "Tipo": "Ruta / total"},
                      {"Nombre": "Proyecto T", "Minutos": fila["prom_T"], "Tipo": "Ruta / total"}]
            color = alt.Color("Tipo:N", scale=alt.Scale(domain=["Actividad", "Ruta / total"], range=[CELESTE, AZUL]),
                              legend=leyenda())
            grafico = barras_horizontales(pd.DataFrame(datos), "Minutos", ".2f", color, "Minutos (promedio)")
            st.altair_chart(grafico.properties(height=alt.Step(30)), width="stretch")
            st.caption(f"En la última iteración: A = {fila['A']:g}, B = {fila['B']:g}, C = {fila['C']:g}, "
                       f"D = {fila['D']:.4f}, E = {fila['E']:.4f}, F = {fila['F']:g} → T = {fila['T']:.4f} min.")

    # --- 3 y 4 ---
    col1, col2 = st.columns(2)
    with col1:
        with seccion("r3", "Tiempo promedio del proyecto",
                     f"Promedio de T hasta la iteración {n} (promedio incremental).", 3):
            tarjetas_kpi([("T promedio", f"{fila['prom_T']:.4f}", "min", f"sobre {n} iteraciones")])
            muestra = pd.DataFrame(resultado["muestra"], columns=["Iteración", "T", "Promedio de T"])
            linea = alt.Chart(muestra).mark_line(strokeWidth=2.5, color=AZUL).encode(
                x="Iteración:Q", y=alt.Y("Promedio de T:Q", scale=alt.Scale(zero=False), title="Promedio de T (min)"),
                tooltip=["Iteración", alt.Tooltip("Promedio de T:Q", format=".4f")])
            st.altair_chart(linea.properties(height=250), width="stretch")
            st.caption("Se ve cómo el promedio se estabiliza a medida que aumentan las iteraciones.")

    with col2:
        with seccion("r4", "Actividades críticas (cuello de botella)",
                     "Proporción de iteraciones en que cada actividad estuvo en el camino más lento.", 4):
            datos = pd.DataFrame([{"Nombre": a, "Proporción": fila["prop_crit_" + a],
                                   "Estado": "Crítica la mayoría de las veces" if fila["prop_crit_" + a] >= 0.5
                                   else "Crítica pocas veces"} for a in ACTIVIDADES])
            color = alt.Color("Estado:N", scale=alt.Scale(
                domain=["Crítica la mayoría de las veces", "Crítica pocas veces"], range=[AZUL, NEUTRO]),
                legend=leyenda())
            grafico = barras_horizontales(datos, "Proporción", ".2%", color, "Proporción de veces crítica", [0, 1.15])
            st.altair_chart(grafico.properties(height=alt.Step(30)), width="stretch")
            # Cuello de botella: la de mayor proporción sin contar F (F está en las dos rutas, siempre es crítica)
            sin_f = [a for a in ACTIVIDADES if a != "F"]
            mayor = max(fila["prop_crit_" + a] for a in sin_f)
            cuellos = ", ".join(a for a in sin_f if fila["prop_crit_" + a] == mayor)
            rama = "Ruta 1 (A → B)" if fila["prop_ruta1"] >= fila["prop_ruta2"] else "Ruta 2 (C → D → E)"
            aviso(f"<b>Cuello de botella: {cuellos}</b> ({mayor:.2%} de las veces). La rama que más veces define "
                  f"el tiempo es <b>{rama}</b>. F es crítica siempre porque está en las dos rutas.")
            st.caption(f"Ruta 1 crítica: {fila['prop_ruta1']:.2%} · Ruta 2: {fila['prop_ruta2']:.2%} · "
                       f"Empate: {fila['prop_empate']:.2%}")

    # --- 5, 6 y 7 ---
    col1, col2, col3 = st.columns(3)
    with col1:
        with seccion("r5", f"Tiempo con {p['confianza']:.0%} de confianza",
                     f"Simulando {p['n_percentil']} veces, ¿qué tiempo prometer?", 5):
            pc = resultado["percentil"]
            if pc:
                tarjetas_kpi([("Tiempo a fijar", f"{pc['valor']:.4f}", "min",
                               f"posición i = {pc['posicion']} de {pc['n']}")])
                aviso(f"Se ordenan las primeras {pc['n']} duraciones y se toma la posición <b>i = {pc['posicion']}</b>: "
                      f"F(i) = i/(n+1) = {pc['posicion']}/{pc['n'] + 1} = {pc['posicion'] / (pc['n'] + 1):.2f}. "
                      f"El {p['confianza']:.0%} de los pedidos se despachan en <b>{pc['valor']:.4f} min o menos</b>.")
            else:
                aviso(f"Hacen falta al menos {p['n_percentil']} iteraciones (hay {n}).")

    with col2:
        with seccion("r6", f"P(T ≤ {p['umbral_menor']:g} min)",
                     f"Probabilidad de terminar en {p['umbral_menor']:g} minutos o menos.", 6):
            tarjetas_kpi([("Probabilidad", f"{fila['prob_menor']:.2%}", "",
                           f"{fila['cont_menor']} de {n} iteraciones")])
            st.progress(min(max(fila["prob_menor"], 0.0), 1.0))

    with col3:
        with seccion("r7", f"P(T ≥ {p['umbral_mayor']:g} min)",
                     f"Probabilidad de terminar en {p['umbral_mayor']:g} minutos o más.", 7):
            tarjetas_kpi([("Probabilidad", f"{fila['prob_mayor']:.2%}", "",
                           f"{fila['cont_mayor']} de {n} iteraciones")])
            st.progress(min(max(fila["prob_mayor"], 0.0), 1.0))

    # --- 8 ---
    with seccion("r8", "Distribución de frecuencias (10 intervalos)",
                 f"Desde Tmin = {resultado['t_min_teorico']:g}, 9 intervalos de {resultado['ancho_intervalo']:g} min "
                 f"y el último desde Tmin + {p['desplazamiento_ultimo']:g} = "
                 f"{resultado['t_min_teorico'] + p['desplazamiento_ultimo']:g} en adelante. "
                 f"N observaciones = {resultado['n_frecuencias']}.", 8):
        frecuencias = resultado["frecuencias"]
        c_grafico, c_tabla = st.columns([3, 2])
        c_grafico.altair_chart(grafico_frecuencias(frecuencias), width="stretch")
        c_tabla.dataframe(pd.DataFrame([{
            "Intervalo": f"[{f['desde']:g}, " + ("∞)" if math.isinf(f["hasta"]) else f"{f['hasta']:g})"),
            "FO": f["fo"], "FR": f["fr"]} for f in frecuencias]), hide_index=True, width="stretch",
            column_config={"FR": st.column_config.NumberColumn(format="%.4f")})
        c_tabla.caption(f"Suma FO = {sum(f['fo'] for f in frecuencias)}")


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------

encabezado_app("Proyecto logístico: red de actividades en paralelo",
               "Simulación de Montecarlo · Inicio → (A → B) ∥ (C → D → E) → F → Fin",
               ["A · Verificación de pago", "B · Picking", "C · Etiqueta y factura",
                "D · Packing", "E · Control de calidad", "F · Despacho"])

p = leer_parametros()
errores, advertencias = validar(p)

with seccion("control", "Ejecutar la simulación",
             "Revisá los avisos, cargá el legajo en m y simulá. Los parámetros están en el panel de la izquierda."):
    for error in errores:
        st.error(error)
    if advertencias:
        st.warning("**Avisos (no impiden simular):**\n" + "\n".join(f"- {a}" for a in advertencias))
    mostrar_datos_fijos()
    simular_ahora = st.button("Simular", type="primary", disabled=bool(errores), width="stretch")

if simular_ahora:
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

    with seccion("estimadores", f"Estimadores en la iteración {ultima['n']}",
                 "Valores acumulados al final de la simulación."):
        mostrar_estimadores(ultima, resultado, p_usado)
        if resultado["percentil"]:
            pc = resultado["percentil"]
            aviso(f"Con un {p_usado['confianza']:.0%} de confianza, el pedido se despacha en "
                  f"<b>{pc['valor']:.4f} min o menos</b> (posición i = {pc['posicion']} de las primeras "
                  f"{pc['n']} duraciones ordenadas, F(i) = i/(n+1)).")

    with seccion("vector", "Vector de estado",
                 f"Filas {p_usado['desde']} a {p_usado['desde'] + p_usado['cantidad_filas'] - 1} + la última. "
                 "Solo se guardan las filas a mostrar; el cálculo usa el vector anterior y el actual."):
        filas = list(resultado["filas_visibles"])
        if not filas or filas[-1]["n"] != ultima["n"]:
            filas.append(ultima)   # siempre se muestra la última fila
        mostrar_vector(filas, p_usado)

    with seccion("consulta", "Consultar una iteración puntual",
                 "Se vuelve a simular desde cero hasta k con los mismos parámetros (no se guardó la tabla)."):
        c_k, c_boton = st.columns([4, 1], vertical_alignment="bottom")
        k = c_k.number_input("Ver estimadores en la iteración k", min_value=1, max_value=p_usado["iteraciones"],
                             value=min(100, p_usado["iteraciones"]), step=1)
        if c_boton.button("Consultar", width="stretch"):
            st.session_state["consulta"] = simular(p_usado, hasta=k, guardar_filas=False)
        if "consulta" in st.session_state:
            consulta = st.session_state["consulta"]
            mostrar_estimadores(consulta["ultima_fila"], consulta, p_usado)
            mostrar_vector([consulta["ultima_fila"]], p_usado, altura="none")

    with seccion("tablas", "Tablas de probabilidad acumulada",
                 "Intervalos semiabiertos [desde, hasta): el RND cae en uno solo."):
        c1, c2 = st.columns(2)
        with c1:
            mostrar_tabla_acumulada("B – Picking", resultado["tabla_b"])
        with c2:
            mostrar_tabla_acumulada("F – Despacho (montacargas)", resultado["tabla_f"])

    with seccion("frecuencias", "Distribución de frecuencias",
                 f"Primer intervalo desde Tmin = {resultado['t_min_teorico']:.4f}; ancho = "
                 f"{p_usado['desplazamiento_ultimo']:g}/9 = {resultado['ancho_intervalo']:.4f} min; "
                 f"N observaciones = {resultado['n_frecuencias']}."):
        mostrar_frecuencias(resultado)

    with seccion("graficos", "Gráficos", "Los 3 gráficos de la cátedra."):
        grafico, puntos = grafico_dispersion_y_promedio(resultado)
        titulo_seccion("Duración T por iteración y promedio acumulado", nivel=2, subtitulo=
                       f"Muestra de {puntos} puntos de {ultima['n']} iteraciones (solo visualización; "
                       "los estimadores se calculan con todas).")
        st.altair_chart(grafico, width="stretch")
        titulo_seccion("Distribución de frecuencias de T", nivel=2)
        st.altair_chart(grafico_frecuencias(resultado["frecuencias"], altura=300), width="stretch")

    with seccion("traza", "Traza de las 3 primeras iteraciones", "Para verificar a mano en la defensa."):
        with st.expander("Ver traza"):
            st.markdown(traza_primeras_iteraciones(p_usado))

    st.markdown("<br>", unsafe_allow_html=True)
    with seccion("respuestas", "Respuestas a la consigna", "Un recuadro por cada punto pedido en el enunciado."):
        respuesta = resultado
        if "consulta" in st.session_state:
            k_consultado = st.session_state["consulta"]["ultima_fila"]["n"]
            opcion = st.radio("Responder con los valores de…",
                              [f"la última iteración ({ultima['n']})", f"la iteración consultada ({k_consultado})"],
                              horizontal=True)
            if opcion.startswith("la iteración consultada"):
                respuesta = st.session_state["consulta"]
        aviso(f"Todos los valores corresponden a la iteración <b>n = {respuesta['ultima_fila']['n']}</b>.")
    mostrar_respuestas(respuesta, p_usado)
