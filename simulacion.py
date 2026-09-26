"""
Motor de la simulación de Montecarlo.

Restricción de la consigna: solo se trabaja con el vector ANTERIOR y el ACTUAL.
Cada fila nueva se calcula con los datos de la fila anterior (promedios, contadores,
mínimo y máximo) y después  anterior = actual.  Las filas viejas no se guardan.

Lo único que se guarda además (y por qué):
  1. Las filas que el usuario pidió MOSTRAR (desde j, i filas) + la última: solo para verlas.
  2. Los 10 contadores de la distribución de frecuencias (no los datos).
  3. Un buffer de tamaño fijo con las primeras n_percentil duraciones (99 por consigna),
     porque para ordenarlas y sacar el percentil hay que tenerlas. Se libera al usarlo.
  4. Una muestra de a lo sumo MAX_PUNTOS_GRAFICO puntos para los gráficos: es solo
     visualización, ningún estimador se calcula con ella.
"""
import math

from distribuciones import armar_tabla_acumulada, constante, discreta, exponencial, uniforme
from generador import GeneradorCongruencialMixto
from modelo import ACTIVIDADES, calcular_red, tiempo_minimo_teorico
from parametros import VARIABLES_ALEATORIAS

MAX_PUNTOS_GRAFICO = 2000
CANTIDAD_INTERVALOS = 10


# ---------------------------------------------------------------------------
# Fórmulas auxiliares
# ---------------------------------------------------------------------------

def promedio_incremental(promedio_anterior, valor, n):
    """P(n) = ((n - 1) * P(n-1) + valor(n)) / n   -> no hace falta guardar los valores."""
    return ((n - 1) * promedio_anterior + valor) / n


def percentil_por_posicion(valores, confianza):
    """
    Método de la cátedra: frecuencia acumulada F(i) = i / (n + 1).
    Se ordenan los n valores y se toma el de la posición i con i/(n+1) = confianza,
    o sea i = ceil(confianza * (n + 1)).  Con n = 99 y 95%: i = 95.
    Devuelve (valor, posición i).
    """
    n = len(valores)
    ordenados = sorted(valores)
    # round(..., 9) evita que 0.95 * 100 = 95.00000000001 se vaya a 96 por el ceil
    i = math.ceil(round(confianza * (n + 1), 9))
    i = min(max(i, 1), n)   # si la confianza es muy alta, i no puede pasarse de n
    return ordenados[i - 1], i


def indice_intervalo(t, t_min, ancho):
    """
    Intervalo k (0..9) al que pertenece t:  [t_min + k*ancho, t_min + (k+1)*ancho).
    Todo lo que queda a partir de t_min + 9*ancho cae en el último (k = 9).
    """
    k = math.floor((t - t_min) / ancho)
    return min(max(k, 0), CANTIDAD_INTERVALOS - 1)


def tabla_frecuencias(contadores, t_min, ancho):
    """Arma la tabla para mostrar a partir de los 10 contadores."""
    total = sum(contadores)
    filas = []
    acumulada = 0.0
    for k, fo in enumerate(contadores):
        desde = t_min + k * ancho
        es_ultimo = k == CANTIDAD_INTERVALOS - 1
        hasta = math.inf if es_ultimo else t_min + (k + 1) * ancho
        relativa = fo / total if total > 0 else 0.0
        acumulada += relativa
        filas.append({
            "intervalo": k + 1,
            "desde": desde,
            "hasta": hasta,
            "marca_clase": None if es_ultimo else (desde + hasta) / 2,
            "etiqueta": f"≥ {desde:g}" if es_ultimo else f"{(desde + hasta) / 2:g}",
            "fo": fo,
            "fr": relativa,
            "fr_acumulada": acumulada,
        })
    return filas


# ---------------------------------------------------------------------------
# Vector de estado
# ---------------------------------------------------------------------------

def fila_inicial():
    """Fila 0: acumuladores en 0 y el mínimo en +infinito (cualquier T lo va a reemplazar)."""
    fila = {"n": 0}
    for act in ACTIVIDADES:
        fila["prom_" + act] = 0.0
        fila["cont_crit_" + act] = 0
        fila["prop_crit_" + act] = 0.0
    fila.update({
        "prom_ruta1": 0.0, "prom_ruta2": 0.0, "prom_T": 0.0,
        "t_min_obs": math.inf, "t_max_obs": 0.0,
        "cont_ruta1": 0, "cont_ruta2": 0, "cont_empate": 0,
        "prop_ruta1": 0.0, "prop_ruta2": 0.0, "prop_empate": 0.0,
        "cont_menor": 0, "prob_menor": 0.0,
        "cont_mayor": 0, "prob_mayor": 0.0,
        "t_confianza": None,
    })
    return fila


def preparar(p):
    """Crea los 4 generadores (uno por variable) y las tablas acumuladas de B y F."""
    generadores = {}
    for variable in VARIABLES_ALEATORIAS:
        g = p["generadores"][variable]
        generadores[variable] = GeneradorCongruencialMixto(
            g["semilla"], g["a"], g["c"], g["m"],
            conversion=p["conversion"], decimales=p["decimales_rnd"])
    tabla_b = armar_tabla_acumulada(p["B"])
    tabla_f = armar_tabla_acumulada(p["F"])
    return generadores, tabla_b, tabla_f


def calcular_fila(n, anterior, generadores, tabla_b, tabla_f, p):
    """
    Calcula la fila n usando SOLO la fila anterior.
    Cada iteración consume exactamente un RND de cada generador, en el orden B, D, E, F.
    """
    actual = {"n": n}

    # 1) Duraciones de las actividades
    actual["A"] = constante(p["A"])

    x, rnd = generadores["B"].siguiente()
    actual["B_x"], actual["B_rnd"], actual["B"] = x, rnd, discreta(rnd, tabla_b)["valor"]

    actual["C"] = constante(p["C"])

    x, rnd = generadores["D"].siguiente()
    actual["D_x"], actual["D_rnd"] = x, rnd
    actual["D"] = uniforme(rnd, p["D"]["a"], p["D"]["b"])

    x, rnd = generadores["E"].siguiente()
    actual["E_x"], actual["E_rnd"] = x, rnd
    actual["E"] = exponencial(rnd, p["E"]["media"])

    x, rnd = generadores["F"].siguiente()
    fila_f = discreta(rnd, tabla_f)
    actual["F_x"], actual["F_rnd"] = x, rnd
    actual["F_estado"], actual["F"] = fila_f["etiqueta"], fila_f["valor"]

    # 2) Tiempos de la red, rutas, T y actividades críticas
    red = calcular_red(actual["A"], actual["B"], actual["C"], actual["D"], actual["E"], actual["F"])
    for clave in ("fin_a", "fin_b", "fin_c", "fin_d", "fin_e", "inicio_f", "fin_f",
                  "ruta1", "ruta2", "holgura", "T", "ruta_critica"):
        actual[clave] = red[clave]
    for act in ACTIVIDADES:
        actual["crit_" + act] = 1 if act in red["criticas"] else 0

    # 3) Estimadores: se actualizan a partir de la fila anterior
    t = actual["T"]
    for act in ACTIVIDADES:
        actual["prom_" + act] = promedio_incremental(anterior["prom_" + act], actual[act], n)
    actual["prom_ruta1"] = promedio_incremental(anterior["prom_ruta1"], actual["ruta1"], n)
    actual["prom_ruta2"] = promedio_incremental(anterior["prom_ruta2"], actual["ruta2"], n)
    actual["prom_T"] = promedio_incremental(anterior["prom_T"], t, n)

    actual["t_min_obs"] = min(anterior["t_min_obs"], t)
    actual["t_max_obs"] = max(anterior["t_max_obs"], t)

    # Proporción de veces que cada actividad fue crítica = contador / n
    for act in ACTIVIDADES:
        actual["cont_crit_" + act] = anterior["cont_crit_" + act] + actual["crit_" + act]
        actual["prop_crit_" + act] = actual["cont_crit_" + act] / n

    actual["cont_ruta1"] = anterior["cont_ruta1"] + (1 if red["ruta_critica"] == "Ruta 1" else 0)
    actual["cont_ruta2"] = anterior["cont_ruta2"] + (1 if red["ruta_critica"] == "Ruta 2" else 0)
    actual["cont_empate"] = anterior["cont_empate"] + (1 if red["ruta_critica"] == "Empate" else 0)
    actual["prop_ruta1"] = actual["cont_ruta1"] / n
    actual["prop_ruta2"] = actual["cont_ruta2"] / n
    actual["prop_empate"] = actual["cont_empate"] / n

    # Probabilidades con umbrales inclusivos: "60 o menos" y "90 o más"
    actual["cont_menor"] = anterior["cont_menor"] + (1 if t <= p["umbral_menor"] else 0)
    actual["prob_menor"] = actual["cont_menor"] / n
    actual["cont_mayor"] = anterior["cont_mayor"] + (1 if t >= p["umbral_mayor"] else 0)
    actual["prob_mayor"] = actual["cont_mayor"] / n

    # El tiempo con X% de confianza se calcula una sola vez (en simular) y se arrastra
    actual["t_confianza"] = anterior["t_confianza"]
    return actual


# ---------------------------------------------------------------------------
# Simulación completa
# ---------------------------------------------------------------------------

def simular(p, hasta=None, guardar_filas=True):
    """
    Corre la simulación completa (o hasta la iteración 'hasta', para consultar
    los estimadores en una iteración puntual sin guardar ninguna tabla).
    """
    total = p["iteraciones"] if hasta is None else hasta
    generadores, tabla_b, tabla_f = preparar(p)

    # Distribución de frecuencias: los intervalos se definen ANTES de simular,
    # porque no podemos guardar los datos para calcularlos después.
    t_min = tiempo_minimo_teorico(p)
    ancho = p["desplazamiento_ultimo"] / (CANTIDAD_INTERVALOS - 1)
    n_frecuencias = min(p["n_frecuencias"] or p["iteraciones"], total)
    contadores = [0] * CANTIDAD_INTERVALOS

    # Percentil: buffer de tamaño fijo con las primeras n_percentil duraciones
    n_percentil = p["n_percentil"]
    buffer_percentil = []
    percentil = None

    paso_grafico = max(1, total // MAX_PUNTOS_GRAFICO)
    muestra = []   # (n, T, promedio de T) — solo para graficar

    desde = p["desde"]
    hasta_mostrar = desde + p["cantidad_filas"]
    filas_visibles = []

    anterior = fila_inicial()
    if guardar_filas and desde <= 0 < hasta_mostrar:
        filas_visibles.append(anterior)

    for n in range(1, total + 1):
        try:
            actual = calcular_fila(n, anterior, generadores, tabla_b, tabla_f, p)
        except ValueError as error:
            raise ValueError(f"Iteración {n}: {error}") from error

        t = actual["T"]

        if n <= n_frecuencias:
            contadores[indice_intervalo(t, t_min, ancho)] += 1

        if n <= n_percentil:
            buffer_percentil.append(t)
            if n == n_percentil:
                valor, posicion = percentil_por_posicion(buffer_percentil, p["confianza"])
                percentil = {"valor": valor, "posicion": posicion, "n": n_percentil}
                actual["t_confianza"] = valor
                buffer_percentil = []   # ya no hace falta: se libera

        if guardar_filas and desde <= n < hasta_mostrar:
            filas_visibles.append(actual)

        if n % paso_grafico == 0 or n == total:
            muestra.append((n, t, actual["prom_T"]))

        anterior = actual   # el actual pasa a ser el anterior; la fila vieja se descarta

    return {
        "ultima_fila": anterior,
        "filas_visibles": filas_visibles,
        "t_min_teorico": t_min,
        "ancho_intervalo": ancho,
        "n_frecuencias": n_frecuencias,
        "frecuencias": tabla_frecuencias(contadores, t_min, ancho),
        "percentil": percentil,
        "tabla_b": tabla_b,
        "tabla_f": tabla_f,
        "muestra": muestra,
    }


# ---------------------------------------------------------------------------
# Traza para verificar a mano (se usa en el README y en la app)
# ---------------------------------------------------------------------------

def traza_primeras_iteraciones(p, cantidad=3):
    """
    Devuelve un texto Markdown con el paso a paso de las primeras iteraciones,
    usando exactamente las mismas funciones que el motor (calcular_fila).
    """
    generadores, tabla_b, tabla_f = preparar(p)
    anterior = fila_inicial()
    x_previo = {v: p["generadores"][v]["semilla"] for v in VARIABLES_ALEATORIAS}
    lineas = []

    for n in range(1, cantidad + 1):
        actual = calcular_fila(n, anterior, generadores, tabla_b, tabla_f, p)
        lineas.append(f"#### Iteración {n}\n")
        for v in VARIABLES_ALEATORIAS:
            g = p["generadores"][v]
            x, rnd = actual[v + "_x"], actual[v + "_rnd"]
            lineas.append(f"- **{v}**: X{n} = ({g['a']} · {x_previo[v]} + {g['c']}) mod {g['m']} = "
                          f"**{x}** → RND = {p['conversion']} = **{rnd:.4f}**")
            x_previo[v] = x
        d, e = p["D"], p["E"]
        lineas.append("")
        lineas.append(f"- A = {actual['A']} (constante), C = {actual['C']} (constante)")
        lineas.append(f"- B: RND {actual['B_rnd']:.4f} cae en la tabla acumulada → **B = {actual['B']}**")
        lineas.append(f"- D = {d['a']} + ({d['b']} − {d['a']}) · {actual['D_rnd']:.4f} = **{actual['D']:.4f}**")
        lineas.append(f"- E = −{e['media']} · ln(1 − {actual['E_rnd']:.4f}) = **{actual['E']:.4f}**")
        lineas.append(f"- F: RND {actual['F_rnd']:.4f} → montacargas {actual['F_estado']} → **F = {actual['F']}**")
        lineas.append(f"- finB = {actual['A']} + {actual['B']} = {actual['fin_b']:.4f} ; "
                      f"finE = {actual['C']} + {actual['D']:.4f} + {actual['E']:.4f} = {actual['fin_e']:.4f}")
        lineas.append(f"- inicioF = max({actual['fin_b']:.4f}, {actual['fin_e']:.4f}) = {actual['inicio_f']:.4f} ; "
                      f"**T = {actual['inicio_f']:.4f} + {actual['F']} = {actual['T']:.4f}**")
        criticas = ", ".join(a for a in ACTIVIDADES if actual["crit_" + a])
        lineas.append(f"- Ruta1 = {actual['ruta1']:.4f}, Ruta2 = {actual['ruta2']:.4f} → "
                      f"{actual['ruta_critica']} es la crítica → críticas: {criticas}")
        lineas.append(f"- Promedio de T hasta acá = {actual['prom_T']:.4f}\n")
        anterior = actual

    return "\n".join(lineas)
