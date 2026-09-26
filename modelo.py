"""
Modelo de la red de actividades (no tiene nada aleatorio: recibe las duraciones ya generadas).

    Inicio ─┬─ A ── B ──────┐
            │               ├── F ── Fin
            └─ C ── D ── E ─┘
"""

ACTIVIDADES = ["A", "B", "C", "D", "E", "F"]

# Tolerancia para decidir que las dos ramas terminan "al mismo tiempo" (empate).
# Hace falta porque con decimales 15 + 30 podría compararse con 44.9999999999.
TOLERANCIA_EMPATE = 1e-9


def calcular_red(a, b, c, d, e, f):
    """
    Calcula los tiempos de la red para una iteración.

    Cada actividad empieza cuando terminó su predecesora:
      finA = A, finB = finA + B          (rama 1: producto)
      finC = C, finD = finC + D, finE = finD + E   (rama 2: empaque)
      F arranca cuando terminaron B Y E  ->  inicioF = max(finB, finE)
      T = finF = inicioF + F
    """
    fin_a = a
    fin_b = fin_a + b
    fin_c = c
    fin_d = fin_c + d
    fin_e = fin_d + e
    inicio_f = max(fin_b, fin_e)
    fin_f = inicio_f + f

    ruta1 = a + b + f
    ruta2 = c + d + e + f
    # Holgura: cuánto espera la rama rápida a la lenta antes de F.
    holgura = abs(fin_b - fin_e)

    # Actividades críticas = las del camino más lento.
    if holgura < TOLERANCIA_EMPATE:
        ruta_critica = "Empate"
        criticas = {"A", "B", "C", "D", "E", "F"}   # las dos ramas son críticas
    elif fin_b > fin_e:
        ruta_critica = "Ruta 1"
        criticas = {"A", "B", "F"}
    else:
        ruta_critica = "Ruta 2"
        criticas = {"C", "D", "E", "F"}

    return {
        "fin_a": fin_a, "fin_b": fin_b, "fin_c": fin_c, "fin_d": fin_d, "fin_e": fin_e,
        "inicio_f": inicio_f, "fin_f": fin_f,
        "ruta1": ruta1, "ruta2": ruta2, "holgura": holgura,
        "T": fin_f,
        "ruta_critica": ruta_critica,
        "criticas": criticas,
    }


def tiempo_minimo_teorico(p):
    """
    "Simulacro" con el valor MÍNIMO posible de cada actividad:
      constante -> su valor | discreta -> menor valor de la tabla
      uniforme  -> a        | exponencial -> 0
    Tmin = max(Amin + Bmin, Cmin + Dmin + Emin) + Fmin
    Con los valores por defecto: max(15 + 20, 5 + 5 + 0) + 15 = 50 min.
    """
    a_min = p["A"]
    b_min = min(fila["valor"] for fila in p["B"])
    c_min = p["C"]
    d_min = p["D"]["a"]
    e_min = 0
    f_min = min(fila["valor"] for fila in p["F"])
    return calcular_red(a_min, b_min, c_min, d_min, e_min, f_min)["T"]
