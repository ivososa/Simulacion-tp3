"""
Generador congruencial mixto.

Fórmula:  X(n+1) = (a * X(n) + c) mod m

- La semilla X0 NO se usa como número aleatorio: el primer RND sale de X1.
- Cada variable aleatoria (B, D, E, F) tiene su propio objeto generador,
  así cada una avanza su propia secuencia de forma independiente.
"""

# Fórmulas posibles para pasar de X (entero entre 0 y m-1) a un RND entre 0 y 1.
CONVERSION_X_SOBRE_M = "X/m"                    # por defecto: RND en [0, 1), nunca vale 1
CONVERSION_X_SOBRE_M_MENOS_1 = "X/(m-1)"        # RND en [0, 1], PUEDE valer 1
CONVERSION_PUNTO_MEDIO = "(X+0.5)/m"            # RND en (0, 1), nunca vale 0 ni 1
CONVERSIONES = [CONVERSION_X_SOBRE_M, CONVERSION_X_SOBRE_M_MENOS_1, CONVERSION_PUNTO_MEDIO]


class GeneradorCongruencialMixto:
    def __init__(self, semilla, a, c, m, conversion=CONVERSION_X_SOBRE_M, decimales=None):
        self.semilla = semilla
        self.a = a
        self.c = c
        self.m = m
        self.conversion = conversion
        self.decimales = decimales   # None = sin truncar
        # x guarda el último X generado. Arranca en la semilla.
        self.x = semilla

    def siguiente(self):
        """Avanza un paso y devuelve (X, RND)."""
        self.x = (self.a * self.x + self.c) % self.m
        return self.x, self.convertir(self.x)

    def convertir(self, x):
        """
        Pasa X a RND con la fórmula elegida.

        Cada fórmula es una fracción numerador / denominador. Si hay que truncar
        a k decimales, se hace con división ENTERA:  trunc(num * 10^k / den) / 10^k.
        Se hace con enteros porque con decimales (float) puede pasar que
        0.29 * 100 dé 28.999999... y al truncar quede 0.28 en vez de 0.29.
        """
        if self.conversion == CONVERSION_X_SOBRE_M:
            numerador, denominador = x, self.m
        elif self.conversion == CONVERSION_X_SOBRE_M_MENOS_1:
            numerador, denominador = x, self.m - 1
        elif self.conversion == CONVERSION_PUNTO_MEDIO:
            # (X + 0.5) / m  es lo mismo que  (2X + 1) / (2m), así queda todo entero
            numerador, denominador = 2 * x + 1, 2 * self.m
        else:
            raise ValueError(f"Conversión desconocida: {self.conversion}")

        if self.decimales is None:
            return numerador / denominador

        potencia = 10 ** self.decimales
        return (numerador * potencia // denominador) / potencia


def calcular_periodo(semilla, a, c, m):
    """
    Largo del ciclo del generador: cuántos X distintos salen antes de que se repita uno
    (a partir de ahí la secuencia es idéntica). Es como máximo m, y es exactamente m solo
    si se cumplen las condiciones de Hull-Dobell. Es un diagnóstico que no usa la simulación.
    """
    paso_en_que_aparecio = {}
    x = semilla
    paso = 0
    while x not in paso_en_que_aparecio:
        paso_en_que_aparecio[x] = paso
        x = (a * x + c) % m
        paso += 1
    return paso - paso_en_que_aparecio[x]
