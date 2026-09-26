import math
import random
import time

from distribuciones import armar_tabla_acumulada, discreta, exponencial, uniforme
from generador import GeneradorCongruencialMixto
from modelo import calcular_red, tiempo_minimo_teorico
from parametros import LEGAJO_EJEMPLO, parametros_por_defecto, validar
from simulacion import (CANTIDAD_INTERVALOS, indice_intervalo, percentil_por_posicion,
                        simular)

M = LEGAJO_EJEMPLO


def parametros_prueba(**cambios):
    p = parametros_por_defecto(legajo=M)
    p.update(cambios)
    return p


# ---------------- Generador ----------------

def test_generador_primeros_x_coinciden_con_calculo_a_mano():
    g = GeneradorCongruencialMixto(3922, 1221, 1714, M)
    x = 3922
    for _ in range(5):
        x = (1221 * x + 1714) % M
        assert g.siguiente()[0] == x


def test_primer_rnd_sale_de_x1_y_no_de_la_semilla():
    g = GeneradorCongruencialMixto(3922, 1221, 1714, M)
    x1 = (1221 * 3922 + 1714) % M
    assert g.siguiente() == (x1, x1 / M)


def test_rnd_siempre_en_0_1_con_conversion_por_defecto():
    g = GeneradorCongruencialMixto(3922, 1221, 1714, M)
    for _ in range(3 * M):
        _, rnd = g.siguiente()
        assert 0 <= rnd < 1


def test_truncado_no_redondea():
    # 2/3 = 0.6666... truncado a 2 decimales es 0.66 (redondeado sería 0.67)
    g = GeneradorCongruencialMixto(0, 1, 2, 3, decimales=2)
    assert g.siguiente() == (2, 0.66)


# ---------------- Distribuciones ----------------

TABLA_B = armar_tabla_acumulada(parametros_por_defecto()["B"])


def test_discreta_limites_de_los_intervalos():
    assert discreta(0, TABLA_B)["valor"] == 20
    assert discreta(0.2499, TABLA_B)["valor"] == 20
    assert discreta(0.25, TABLA_B)["valor"] == 30   # límite inferior incluido
    assert discreta(0.9999, TABLA_B)["valor"] == 40


def test_uniforme_rnd_cero_da_a():
    assert uniforme(0, 5, 25) == 5


def test_exponencial():
    assert exponencial(0, 5) == 0
    assert all(exponencial(i / 1000, 5) >= 0 for i in range(1000))


# ---------------- Modelo ----------------

def test_red_con_datos_fijos_del_enunciado():
    red = calcular_red(15, 30, 5, 10, 5, 15)
    assert red["T"] == 60
    assert red["ruta1"] == 60
    assert red["ruta2"] == 35
    assert red["criticas"] == {"A", "B", "F"}


def test_tiempo_minimo_teorico_por_defecto():
    assert tiempo_minimo_teorico(parametros_por_defecto()) == 50


def test_empate_marca_las_seis_actividades_criticas():
    # A + B = 15 + 20 = 35 y C + D + E = 5 + 25 + 5 = 35
    red = calcular_red(15, 20, 5, 25, 5, 15)
    assert red["ruta_critica"] == "Empate"
    assert red["criticas"] == {"A", "B", "C", "D", "E", "F"}


# ---------------- Simulación ----------------

def test_suma_de_frecuencias_igual_a_n_observaciones():
    p = parametros_prueba(iteraciones=5000, n_frecuencias=1234, cantidad_filas=0)
    resultado = simular(p)
    assert sum(f["fo"] for f in resultado["frecuencias"]) == 1234


def test_valor_en_tmin_mas_90_cae_en_el_ultimo_intervalo():
    assert indice_intervalo(50 + 90, 50, 10) == CANTIDAD_INTERVALOS - 1
    assert indice_intervalo(50 + 89.9999, 50, 10) == CANTIDAD_INTERVALOS - 2
    assert indice_intervalo(50, 50, 10) == 0


def test_promedio_incremental_igual_a_promedio_clasico():
    # Solo en el test se guarda la lista, para comparar contra el promedio de siempre.
    p = parametros_prueba(iteraciones=500, desde=1, cantidad_filas=500)
    resultado = simular(p)
    duraciones = [fila["T"] for fila in resultado["filas_visibles"]]
    assert math.isclose(resultado["ultima_fila"]["prom_T"], sum(duraciones) / len(duraciones))
    assert resultado["ultima_fila"]["t_min_obs"] == min(duraciones)
    assert resultado["ultima_fila"]["t_max_obs"] == max(duraciones)


def test_percentil_95_de_1_a_99_es_95():
    valores = list(range(1, 100))
    random.Random(7).shuffle(valores)
    assert percentil_por_posicion(valores, 0.95) == (95, 95)


def test_percentil_se_calcula_en_la_iteracion_99():
    resultado = simular(parametros_prueba(iteraciones=200, cantidad_filas=0))
    assert resultado["percentil"]["n"] == 99
    assert resultado["percentil"]["posicion"] == 95


def test_consulta_en_iteracion_k_coincide_con_la_fila_k():
    p = parametros_prueba(iteraciones=1000, desde=300, cantidad_filas=1)
    fila_300 = simular(p)["filas_visibles"][0]
    assert simular(p, hasta=300, guardar_filas=False)["ultima_fila"] == fila_300


def test_generadores_identicos_advierten_pero_no_bloquean():
    errores, advertencias = validar(parametros_prueba())
    assert errores == []
    assert any("mismos parámetros" in a for a in advertencias)


def test_sin_legajo_no_se_puede_simular():
    errores, _ = validar(parametros_por_defecto(legajo=None))
    assert errores


def test_rendimiento_100000_iteraciones():
    inicio = time.perf_counter()
    resultado = simular(parametros_prueba(iteraciones=100_000, cantidad_filas=20))
    assert resultado["ultima_fila"]["n"] == 100_000
    assert time.perf_counter() - inicio < 10


def test_periodo_del_generador():
    from generador import calcular_periodo
    # Hull-Dobell se cumple (m=16, a=5, c=3): período completo = m
    assert calcular_periodo(7, 5, 3, 16) == 16
    # Con los valores de prueba y m = 12345, el período es mucho menor que m
    assert calcular_periodo(3922, 1221, 1714, 12345) == 2055
