"""
Valores por defecto de todos los parámetros y validaciones.

Todos los parámetros viven en un único diccionario "p" que se le pasa al motor.
Así, en la evaluación, cambiar un dato = cambiar un valor de este diccionario
(desde la interfaz).
"""
from generador import (CONVERSION_X_SOBRE_M, CONVERSION_X_SOBRE_M_MENOS_1, CONVERSIONES,
                       calcular_periodo)

# Legajo de ejemplo para tests y para la traza del README (reemplazar por el propio).
LEGAJO_EJEMPLO = 12345

# Solo se calcula el período exacto si m es chico (un legajo lo es); si no, tardaría mucho.
LIMITE_CALCULO_PERIODO = 1_000_000

VARIABLES_ALEATORIAS = ["B", "D", "E", "F"]   # las que tienen generador propio
TOLERANCIA_PROBABILIDADES = 1e-9


def parametros_por_defecto(legajo=None):
    """Datos de la consigna. m = legajo (si es None, no se puede simular)."""
    def generador_de_prueba():
        return {"semilla": 3922, "a": 1221, "c": 1714, "m": legajo}

    return {
        # Simulación
        "iteraciones": 100_000,
        "desde": 1,                 # mostrar desde la iteración j
        "cantidad_filas": 20,       # cantidad i de filas a mostrar
        "decimales_rnd": None,      # None = sin truncar
        "conversion": CONVERSION_X_SOBRE_M,
        # Un generador independiente por variable aleatoria
        "generadores": {v: generador_de_prueba() for v in VARIABLES_ALEATORIAS},
        # Distribuciones
        "A": 15,
        "B": [
            {"etiqueta": "20 min", "valor": 20, "probabilidad": 0.25},
            {"etiqueta": "30 min", "valor": 30, "probabilidad": 0.40},
            {"etiqueta": "40 min", "valor": 40, "probabilidad": 0.35},
        ],
        "C": 5,
        "D": {"a": 5, "b": 25},
        "E": {"media": 5},
        "F": [
            {"etiqueta": "Libre", "valor": 15, "probabilidad": 0.50},
            {"etiqueta": "Ocupado", "valor": 25, "probabilidad": 0.50},
        ],
        # Estimadores
        "n_percentil": 99,
        "confianza": 0.95,
        "umbral_menor": 60,         # P(T <= 60)
        "umbral_mayor": 90,         # P(T >= 90)
        "desplazamiento_ultimo": 90,  # el último intervalo empieza Tmin + 90
        "n_frecuencias": None,      # None = todas las iteraciones
    }


def es_entero(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def validar(p):
    """
    Devuelve (errores, advertencias).
    - errores: impiden simular.
    - advertencias: se muestran pero NO bloquean la simulación.
    """
    errores = []
    advertencias = []

    # --- Simulación ---
    if not es_entero(p["iteraciones"]) or p["iteraciones"] < 1:
        errores.append("La cantidad de iteraciones tiene que ser un entero ≥ 1.")
    if not es_entero(p["desde"]) or p["desde"] < 0:
        errores.append("'Mostrar desde la iteración j' tiene que ser un entero ≥ 0.")
    if not es_entero(p["cantidad_filas"]) or p["cantidad_filas"] < 0:
        errores.append("La cantidad de filas a mostrar tiene que ser un entero ≥ 0.")
    if p["decimales_rnd"] is not None and (not es_entero(p["decimales_rnd"]) or p["decimales_rnd"] < 1):
        errores.append("Los decimales del RND tienen que ser un entero ≥ 1 (o vacío para no truncar).")
    if p["conversion"] not in CONVERSIONES:
        errores.append(f"Conversión del RND desconocida: {p['conversion']}")

    # --- Generadores ---
    for variable in VARIABLES_ALEATORIAS:
        g = p["generadores"][variable]
        nombre = f"Generador de {variable}"
        if g["m"] is None:
            errores.append(f"{nombre}: falta cargar m (número de legajo).")
            continue
        if not all(es_entero(g[k]) for k in ("semilla", "a", "c", "m")):
            errores.append(f"{nombre}: semilla, a, c y m tienen que ser enteros.")
            continue
        if g["m"] <= 0:
            errores.append(f"{nombre}: m tiene que ser > 0.")
        if g["a"] <= 0:
            errores.append(f"{nombre}: a tiene que ser > 0.")
        if g["c"] < 0:
            errores.append(f"{nombre}: c tiene que ser ≥ 0.")
        if g["semilla"] < 0:
            errores.append(f"{nombre}: la semilla tiene que ser ≥ 0.")
        if p["conversion"] == CONVERSION_X_SOBRE_M_MENOS_1 and g["m"] <= 1:
            errores.append(f"{nombre}: con la conversión X/(m-1), m tiene que ser > 1.")
        if es_entero(p["iteraciones"]) and g["m"] > 0 and g["a"] > 0 and g["c"] >= 0 and g["semilla"] >= 0:
            if g["m"] <= LIMITE_CALCULO_PERIODO:
                periodo = calcular_periodo(g["semilla"], g["a"], g["c"], g["m"])
                if p["iteraciones"] > periodo:
                    advertencias.append(
                        f"{nombre}: el período real es {periodo} (m = {g['m']}). Con "
                        f"{p['iteraciones']} iteraciones los números se repiten cada {periodo}.")
            elif p["iteraciones"] > g["m"]:
                advertencias.append(
                    f"{nombre}: se piden {p['iteraciones']} iteraciones y m = {g['m']}. "
                    f"El período es como máximo m, así que los números se van a repetir.")

    gens = [p["generadores"][v] for v in VARIABLES_ALEATORIAS]
    if all(g == gens[0] for g in gens):
        advertencias.append(
            "Los 4 generadores tienen los mismos parámetros: B, D, E y F reciben el MISMO RND "
            "en cada iteración (quedan correlacionadas). Se simula igual.")

    if p["conversion"] == CONVERSION_X_SOBRE_M_MENOS_1:
        advertencias.append(
            "Con X/(m-1) el RND puede valer 1. Si le toca a la exponencial (E), ln(0) no existe "
            "y la simulación se detiene en esa iteración.")

    # --- Distribuciones ---
    for variable in ("A", "C"):
        if p[variable] < 0:
            errores.append(f"{variable}: la duración constante no puede ser negativa.")
    for variable in ("B", "F"):
        filas = p[variable]
        if len(filas) == 0:
            errores.append(f"{variable}: la tabla tiene que tener al menos una fila.")
            continue
        suma = sum(fila["probabilidad"] for fila in filas)
        if abs(suma - 1) > TOLERANCIA_PROBABILIDADES:
            errores.append(f"{variable}: las probabilidades suman {suma:.6f}, tienen que sumar 1.")
        if any(fila["probabilidad"] < 0 for fila in filas):
            errores.append(f"{variable}: hay probabilidades negativas.")
        if any(fila["valor"] < 0 for fila in filas):
            errores.append(f"{variable}: hay duraciones negativas.")
    if not p["D"]["a"] < p["D"]["b"]:
        errores.append("D: tiene que cumplirse a < b.")
    if p["D"]["a"] < 0:
        errores.append("D: a no puede ser negativo (es una duración).")
    if not p["E"]["media"] > 0:
        errores.append("E: la media tiene que ser > 0.")

    # --- Estimadores ---
    if not es_entero(p["n_percentil"]) or p["n_percentil"] < 1:
        errores.append("La cantidad de simulaciones para el percentil tiene que ser un entero ≥ 1.")
    elif p["n_percentil"] > 10_000:
        advertencias.append("El percentil guarda un buffer de n valores: con n > 10.000 usa bastante memoria.")
    elif es_entero(p["iteraciones"]) and p["n_percentil"] > p["iteraciones"]:
        advertencias.append(
            f"El percentil necesita {p['n_percentil']} iteraciones y solo se simulan "
            f"{p['iteraciones']}: no se va a poder calcular.")
    if not 0 < p["confianza"] < 1:
        errores.append("El nivel de confianza tiene que estar entre 0 y 1.")
    if not p["desplazamiento_ultimo"] > 0:
        errores.append("El desplazamiento del último intervalo tiene que ser > 0.")
    if p["n_frecuencias"] is not None:
        if not es_entero(p["n_frecuencias"]) or p["n_frecuencias"] < 1:
            errores.append("N observaciones para la distribución tiene que ser un entero ≥ 1.")
        elif es_entero(p["iteraciones"]) and p["n_frecuencias"] > p["iteraciones"]:
            advertencias.append(
                f"N observaciones ({p['n_frecuencias']}) es mayor que las iteraciones "
                f"({p['iteraciones']}): se cuentan solo {p['iteraciones']}.")

    return errores, advertencias
