"""
Distribuciones usadas para generar la duración de cada actividad a partir de un RND.
"""
import math


def constante(valor):
    """A y C: siempre valen lo mismo, no consumen RND."""
    return valor


def armar_tabla_acumulada(filas):
    """
    Arma la tabla de probabilidad acumulada de una distribución discreta.

    filas: lista de dicts {"etiqueta", "valor", "probabilidad"}.
    Cada fila recibe un intervalo semiabierto [desde, hasta):
      - el primer "desde" es 0
      - "hasta" es la probabilidad acumulada hasta esa fila
      - el "desde" de cada fila es el "hasta" de la anterior
    Ejemplo B por defecto: [0, 0.25) -> 20 | [0.25, 0.65) -> 30 | [0.65, 1) -> 40
    """
    tabla = []
    acumulada = 0.0
    for fila in filas:
        desde = acumulada
        acumulada = acumulada + fila["probabilidad"]
        tabla.append({
            "etiqueta": fila["etiqueta"],
            "valor": fila["valor"],
            "probabilidad": fila["probabilidad"],
            "acumulada": acumulada,
            "desde": desde,
            "hasta": acumulada,
        })
    # La suma puede dar 0.9999999999 por redondeo de decimales: el último límite es 1.
    tabla[-1]["hasta"] = 1.0
    tabla[-1]["acumulada"] = 1.0
    return tabla


def discreta(rnd, tabla):
    """
    Busca el intervalo [desde, hasta) que contiene al RND y devuelve esa fila
    (de ahí se toma el valor y la etiqueta, por ejemplo "Libre"/"Ocupado").
    Como los intervalos están ordenados, alcanza con encontrar el primero
    cuyo límite superior sea mayor que el RND.
    """
    for fila in tabla:
        if rnd < fila["hasta"]:
            return fila
    # Solo se llega acá si RND = 1 (posible con la conversión X/(m-1)): último valor.
    return tabla[-1]


def uniforme(rnd, a, b):
    """D ~ U[a, b]:  D = a + (b - a) * RND"""
    return a + (b - a) * rnd


def exponencial(rnd, media):
    """
    E ~ Exponencial negativa con la media dada:  E = -media * ln(1 - RND)
    (λ = 1 / media). Se usa 1 - RND para que RND = 0 dé E = 0.
    Si RND = 1, ln(0) no existe: por eso la conversión por defecto es X/m.
    """
    if rnd >= 1:
        raise ValueError("RND = 1 en la exponencial: ln(1 - 1) = ln(0) no está definido. "
                         "Usá la conversión X/m.")
    return -media * math.log(1 - rnd)
