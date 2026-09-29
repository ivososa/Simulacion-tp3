# Defensa TP3 – Proyecto logístico (red de actividades en paralelo)

Guía de estudio para la defensa individual. Todas las referencias son `archivo:línea` del repo
`Simulacion-tp3` (commit `37db7b3`). Los resultados de la sección 8 se generaron corriendo el código.

---

## 1. CONSIGNA

### Resumen

Un pedido online se procesa con **dos ramas en paralelo** que convergen en el despacho:

```
Inicio ─┬─ A ── B ──────┐
        │               ├── F ── Fin
        └─ C ── D ── E ─┘
```

| Cód. | Actividad | Predecesora | Distribución |
|---|---|---|---|
| A | Verificación de pago y stock | Inicio | Constante 15 min |
| B | Picking en almacén | A | Discreta: 20 (0.25) · 30 (0.40) · 40 (0.35) |
| C | Impresión de etiqueta y factura | Inicio | Constante 5 min |
| D | Preparación de empaque (packing) | C | Uniforme U[5, 25] |
| E | Control de calidad y pesaje | D | Exponencial, media 5 min |
| F | Despacho y carga al camión | B **y** E | Discreta (montacargas): Libre 15 (0.5) · Ocupado 25 (0.5) |

- F solo empieza cuando terminaron B **y** E.
- Las actividades del **camino más lento** son las **críticas**.
- Ejemplo con datos fijos del PDF: A=15, B=30, C=5, D=10, E=5, F=15 → Ruta 1 = 60, Ruta 2 = 35, T = 60.

### Todos los pedidos de la consigna

**Restricciones**
1. Simular el caso con las distribuciones propuestas (Montecarlo).
2. **Cada variable aleatoria usa un generador congruencial mixto individual** ("diferente para cada uno"); los coeficientes se dan al evaluar.
3. Valores de prueba: **semilla = 3922, a = 1221, c = 1714, m = número de legajo**.
4. Las variables **mantienen la distribución**, pero pueden cambiar media, varianza, extremos o probabilidades en la evaluación.
5. El software **solo trabaja con el vector actual y el anterior** y da los estimadores **en cada iteración**. **No debe guardar tablas**, porque pueden pedir valores de la iteración **100.000** o similares.

**Identificación**
6. Identificar las fórmulas de las variables y de los estimadores.
7. Identificar variables y parámetros del problema.
8. Identificar la variable objetivo de análisis.

**Estimadores**
9. Tiempo del proyecto haciendo un **simulacro para el tiempo mínimo** en que podría hacerse.
10. **Duración de cada proceso**.
11. **Tiempo promedio** del proceso hasta la iteración pedida.
12. **Proporción de veces que cada actividad es crítica** (cuello de botella).
13. Simulando **99 veces**, el tiempo a fijar para terminar antes con **95 % de confianza**.
14. **P(T ≤ 60)** al simular hasta n veces.
15. **P(T ≥ 90)** al simular hasta n veces.
16. **Distribución de frecuencias con 10 intervalos**: el primero empieza en el **tiempo mínimo**, los **9 primeros son iguales**, el **último empieza 90 min después** del primero y contiene el resto. La **cantidad de observaciones se da al evaluar**.
17. Cualquier dato puede cambiar en la evaluación.

**Gráficos** (no están en el PDF; los pidió la cátedra y el prompt del TP)
18. Dispersión de T por iteración, línea del promedio acumulado y barras de la distribución de frecuencias.

---

## 2. MAPA CONSIGNA → CÓDIGO

| Pedido de la consigna | archivo:línea | Función | Cómo lo resuelve |
|---|---|---|---|
| Generador congruencial mixto | `generador.py:31` | `GeneradorCongruencialMixto.siguiente` | `self.x = (self.a * self.x + self.c) % self.m`: aplica X(n+1) = (a·X(n) + c) mod m y guarda el nuevo X. |
| Conversión X → RND con X/m | `generador.py:43-44`, `:53-54` | `convertir` | Divide X por m, así RND ∈ [0, 1) y nunca vale 1. |
| La semilla no se usa como RND | `generador.py:27`, `:31` | `__init__`, `siguiente` | `self.x` arranca en la semilla, y `siguiente()` primero calcula X1 y recién después convierte. El primer RND sale de X1. |
| Un generador por variable | `simulacion.py:107-117` | `preparar` | Crea un objeto `GeneradorCongruencialMixto` distinto para B, D, E y F, cada uno con sus propios semilla, a, c y m. |
| Parámetros de cada generador | `parametros.py:23-24`, `:34` | `parametros_por_defecto` | Diccionario `generadores` con un bloque por variable (3922, 1221, 1714, m = legajo). |
| m = legajo obligatorio | `parametros.py:88-90` | `validar` | Si `m` está vacío da el error "falta cargar m (número de legajo)" y no se puede simular. |
| A y C constantes | `distribuciones.py:7-9`; `simulacion.py:128`, `:133` | `constante` | Devuelve el valor fijo; no consume RND. |
| B discreta | `distribuciones.py:12-39`, `:42-53`; `simulacion.py:130-131` | `armar_tabla_acumulada`, `discreta` | Arma intervalos [desde, hasta) con la probabilidad acumulada y devuelve la fila cuyo `hasta` supera al RND. |
| D uniforme U[a, b] | `distribuciones.py:58`; `simulacion.py:135-137` | `uniforme` | `a + (b - a) * rnd`. |
| E exponencial (media) | `distribuciones.py:70`; `simulacion.py:139-141` | `exponencial` | `-media * math.log(1 - rnd)`. |
| F discreta (montacargas) | `simulacion.py:143-146` | `discreta` | Igual que B, pero guarda también la etiqueta ("Libre"/"Ocupado") en `F_estado`. |
| Fin de cada actividad | `modelo.py:26-30` | `calcular_red` | finA = A, finB = finA + B, finC = C, finD = finC + D, finE = finD + E. |
| **inicioF = max(finB, finE)** | `modelo.py:31-32` | `calcular_red` | `inicio_f = max(fin_b, fin_e)`: F espera a la rama más lenta; `fin_f = inicio_f + f` es T. |
| Rutas | `modelo.py:34-35` | `calcular_red` | Ruta1 = A+B+F, Ruta2 = C+D+E+F. |
| Criticidad (incluido el empate) | `modelo.py:40-48` | `calcular_red` | Si las ramas difieren en menos de 1e-9 hay empate y las 6 son críticas; si finB > finE, las críticas son A, B, F; si no, C, D, E, F. |
| Tiempo mínimo teórico (simulacro) | `modelo.py:60-83` | `valores_minimos`, `tiempo_minimo_teorico` | Arma la red con el mínimo de cada distribución (constante, menor valor, a, 0): max(15+20, 5+5+0) + 15 = 50. |
| Duración de cada proceso | `simulacion.py:128-146`, `:149-152` | `calcular_fila` | Cada fila guarda A…F, finA…finF, Ruta1, Ruta2 y T de esa iteración. |
| Promedio incremental | `simulacion.py:31-33`, `:158-162` | `promedio_incremental` | `((n - 1) * promedio_anterior + valor) / n` para cada actividad, cada ruta y T. |
| Tiempo promedio del proyecto hasta n | `simulacion.py:162` | `calcular_fila` | `prom_T` se actualiza en cada fila con el promedio incremental. |
| Mínimo y máximo observados | `simulacion.py:164-165` | `calcular_fila` | `min(anterior["t_min_obs"], t)` y `max(...)`; la fila 0 arranca el mínimo en +∞ (`simulacion.py:97`). |
| Proporción crítica por actividad | `simulacion.py:168-170` | `calcular_fila` | Contador = anterior + 1 si fue crítica; proporción = contador / n. |
| Proporción por ruta y empates | `simulacion.py:172-177` | `calcular_fila` | Un contador por "Ruta 1", "Ruta 2" y "Empate", dividido por n. |
| Tiempo con 95 % de confianza (99 simulaciones) | `simulacion.py:36-48`, `:236-242` | `percentil_por_posicion`, `simular` | Junta las primeras 99 T, las ordena y toma la posición i = ceil(0.95 · 100) = 95, con F(i) = i/(n+1). |
| P(T ≤ 60) | `simulacion.py:180-181` | `calcular_fila` | Contador de T ≤ `umbral_menor` (inclusivo) dividido por n. |
| P(T ≥ 90) | `simulacion.py:182-183` | `calcular_fila` | Contador de T ≥ `umbral_mayor` (inclusivo) dividido por n. |
| Frecuencias: 10 intervalos desde Tmin | `simulacion.py:204-207` | `simular` | Antes de simular fija `t_min` (teórico), `ancho = 90 / 9 = 10` y 10 contadores en 0. |
| Frecuencias: asignar cada T | `simulacion.py:51-57`, `:233-234` | `indice_intervalo` | k = floor((T − Tmin) / ancho), con tope en 9; el último intervalo es [Tmin+90, ∞). |
| Frecuencias: N observaciones dado | `simulacion.py:206`, `:233` | `simular` | Solo cuenta si `n <= n_frecuencias` (por defecto, todas las iteraciones). |
| Frecuencias: tabla FO/FR/FRA | `simulacion.py:60-81` | `tabla_frecuencias` | Arma límites, marca de clase, FO, FR y FR acumulada a partir de los 10 contadores. |
| **Solo vector actual y anterior** | `simulacion.py:120-187`, `:221`, `:250` | `calcular_fila`, `simular` | `calcular_fila` recibe solo `anterior` y devuelve `actual`; después `anterior = actual` y la fila vieja se descarta. |
| Qué se guarda aparte y por qué | `simulacion.py:8-14`, `:211`, `:242`, `:244-248` | `simular` | Guarda las filas a mostrar (visualización), 10 contadores, un buffer de 99 valores para el percentil (se libera en la iteración 99) y una muestra de hasta 2.000 puntos para los gráficos. |
| Todos los parámetros configurables | `parametros.py:21-56`; `app.py:59-113` | `parametros_por_defecto`, `leer_parametros` | Todo vive en un diccionario `p` que se edita desde la barra lateral. |
| Consultar la iteración 100.000 (o cualquier k) | `simulacion.py:194-199`; `app.py:496-506` | `simular(p, hasta=k)` | Vuelve a simular hasta k; como el generador es determinista, da la misma fila k. |
| Gráficos | `app.py:200-223`, `:522-529` | `grafico_dispersion_y_promedio`, `grafico_frecuencias` | Dispersión de T con la línea del promedio acumulado y barras de frecuencias. |

---

## 3. GUÍA ARCHIVO POR ARCHIVO

### `generador.py` — el generador de números aleatorios

| Línea | Qué es | Entrada → salida | Fórmula |
|---|---|---|---|
| 12-15 | Constantes de conversión | — | `"X/m"`, `"X/(m-1)"`, `"(X+0.5)/m"` |
| 18 | `class GeneradorCongruencialMixto` | — | — |
| 19-27 | `__init__` | semilla, a, c, m, conversión, decimales | `self.x = semilla` (línea 27) |
| 29-32 | `siguiente()` | — → `(X, RND)` | **X(n+1) = (a·X(n) + c) mod m** (línea 31) |
| 34-57 | `convertir(x)` | X → RND | X/m (44), X/(m−1) (46), (2X+1)/(2m) (49); truncado: `numerador * 10^k // denominador / 10^k` (56-57) |
| 60-73 | `calcular_periodo(semilla, a, c, m)` | → largo del ciclo | Genera X hasta que uno se repite; período = paso actual − paso en que apareció (73) |

### `distribuciones.py` — de RND a duración

| Línea | Función | Entrada → salida | Fórmula |
|---|---|---|---|
| 7-9 | `constante(valor)` | valor → valor | A y C |
| 12-39 | `armar_tabla_acumulada(filas)` | [{etiqueta, valor, probabilidad}] → tabla con desde/hasta/acumulada | `desde = acumulada` (26); `acumulada += p` (27); el último `hasta` se fuerza a 1 (37-38) |
| 42-53 | `discreta(rnd, tabla)` | RND → fila de la tabla | primer intervalo con `rnd < fila["hasta"]` (50) |
| 56-58 | `uniforme(rnd, a, b)` | → D | **D = a + (b − a)·RND** (58) |
| 61-70 | `exponencial(rnd, media)` | → E | **E = −media·ln(1 − RND)** (70); si RND ≥ 1 da error (67-69) |

### `modelo.py` — la red (sin nada aleatorio)

| Línea | Qué es | Entrada → salida | Fórmula |
|---|---|---|---|
| 9 | `ACTIVIDADES` | — | `["A", "B", "C", "D", "E", "F"]` |
| 13 | `TOLERANCIA_EMPATE` | — | 1e-9 |
| 16-57 | `calcular_red(a, b, c, d, e, f)` | 6 duraciones → dict con fines, rutas, holgura, T, ruta crítica y críticas | fines (26-30), **inicioF = max(finB, finE)** (31), T = finF (32), rutas (34-35), holgura = abs(finB − finE) (37), criticidad (40-48) |
| 60-73 | `valores_minimos(p)` | parámetros → mínimo de cada actividad | constante → valor, discreta → `min(...)`, uniforme → a, exponencial → 0 |
| 76-83 | `tiempo_minimo_teorico(p)` | → Tmin | `calcular_red` con los mínimos → 50 |

### `parametros.py` — datos por defecto y validaciones

| Línea | Qué es | Detalle |
|---|---|---|
| 12 | `LEGAJO_EJEMPLO = 12345` | Solo para los tests y la traza |
| 15 | `LIMITE_CALCULO_PERIODO` | El período exacto se calcula solo si m ≤ 1.000.000 |
| 17 | `VARIABLES_ALEATORIAS` | `["B", "D", "E", "F"]`: las que tienen generador |
| 21-56 | `parametros_por_defecto(legajo)` | Todos los datos de la consigna en un diccionario `p` |
| 59-60 | `es_entero(valor)` | int y no bool |
| 63-171 | `validar(p)` | Devuelve `(errores, advertencias)`. Los errores bloquean la simulación; las advertencias no (ver sección 5.3) |

### `simulacion.py` — el motor (el archivo más importante)

| Línea | Función | Entrada → salida | Qué hace / fórmula |
|---|---|---|---|
| 23-24 | Constantes | — | `MAX_PUNTOS_GRAFICO = 2000`, `CANTIDAD_INTERVALOS = 10` |
| 31-33 | `promedio_incremental(prom_ant, valor, n)` | → nuevo promedio | **P(n) = ((n−1)·P(n−1) + valor)/n** |
| 36-48 | `percentil_por_posicion(valores, confianza)` | lista → (valor, i) | ordena (44); **i = ceil(conf·(n+1))** (46); tope entre 1 y n (47) |
| 51-57 | `indice_intervalo(t, t_min, ancho)` | T → k (0..9) | **k = floor((T − Tmin)/ancho)**, con tope en 9 |
| 60-81 | `tabla_frecuencias(contadores, t_min, ancho)` | 10 contadores → tabla | desde, hasta (∞ el último), marca de clase, FO, FR, FR acumulada |
| 88-104 | `fila_inicial()` | → fila 0 | acumuladores en 0, `t_min_obs = inf` (97), `t_confianza = None` |
| 107-117 | `preparar(p)` | → (generadores, tabla_b, tabla_f) | Un generador por variable (110-114) y las tablas acumuladas (115-116) |
| 120-187 | `calcular_fila(n, anterior, …)` | fila anterior → fila actual | Ver sección 4 |
| 194-263 | `simular(p, hasta, guardar_filas)` | → dict de resultados | Bucle principal, frecuencias, percentil, filas visibles, muestra y `anterior = actual` (250) |
| 270-306 | `traza_primeras_iteraciones(p, cantidad)` | → texto Markdown | Usa el mismo `calcular_fila` que el motor |

### `app.py` — la interfaz (solo pantallas)

| Línea | Función | Qué hace |
|---|---|---|
| 34-36 | (estado inicial) | Carga los valores por defecto de los generadores en `session_state` |
| 39-42 | `copiar_generador_b()` | Copia semilla, a, c y m de B a D, E y F |
| 45-52 | `tabla_editable_a_filas(df)` | Convierte las tablas editables de B y F al formato del motor |
| 59-113 | `leer_parametros()` | Barra lateral: arma el diccionario `p` |
| 120-146 | `columnas_vector(p)` | Define las columnas (grupo, subcolumna, clave) de la tabla del vector de estado |
| 149-156 | `formatear(valor)` | 4 decimales, ∞ para infinito, vacío para None |
| 159-173 | `mostrar_vector(filas, p, altura)` | Tabla HTML con encabezado doble; pone "…" si hay un salto de filas |
| 180-223 | Gráficos | `leyenda`, `texto_sobre_barra`, `barras_horizontales`, `grafico_frecuencias`, `grafico_dispersion_y_promedio` |
| 230-256 | `mostrar_estimadores(fila, resultado, p)` | 8 tarjetas y la tabla de promedios y criticidad |
| 259-266 | `mostrar_tabla_acumulada` | Tablas de B y F |
| 269-287 | `mostrar_frecuencias` | Tabla de frecuencias y control de suma de FO |
| 290-299 | `mostrar_datos_fijos` | Simulacro con los datos fijos del PDF |
| 306-327 | `gantt_simulacro_minimo(p)` | Cronograma del tiempo mínimo |
| 330-438 | `mostrar_respuestas(resultado, p)` | Las 8 tarjetas de "Respuestas a la consigna" |
| 445-546 | (página) | Orden de la pantalla: encabezado, control, estimadores, vector, consulta, tablas, frecuencias, gráficos, traza y respuestas |

`estilos.py` (paleta, CSS y piezas visuales) y `.streamlit/config.toml` (tema) son **solo apariencia**, no tienen lógica.

### `generar_traza.py`

- Líneas 15-16: lee el legajo del argumento (o usa 12345) y llama a `traza_primeras_iteraciones`.
- Líneas 18-25: reemplaza en `README.md` el texto entre `<!-- TRAZA:INICIO -->` y `<!-- TRAZA:FIN -->`.
- Uso: `python generar_traza.py 12345`.

### `tests/test_simulacion.py` (20 tests)

| Línea | Test | Qué verifica |
|---|---|---|
| 23 | `test_generador_primeros_x_coinciden_con_calculo_a_mano` | Los 5 primeros X coinciden con (a·X + c) mod m |
| 31 | `test_primer_rnd_sale_de_x1_y_no_de_la_semilla` | El primer RND es X1/m |
| 37 | `test_rnd_siempre_en_0_1_con_conversion_por_defecto` | RND ∈ [0, 1) |
| 44 | `test_truncado_no_redondea` | 2/3 con 2 decimales da 0.66, no 0.67 |
| 55 | `test_discreta_limites_de_los_intervalos` | 0 → 20, 0.2499 → 20, 0.25 → 30, 0.9999 → 40 |
| 62 | `test_uniforme_rnd_cero_da_a` | U(0) = a |
| 66 | `test_exponencial` | E(0) = 0 y siempre ≥ 0 |
| 73 | `test_red_con_datos_fijos_del_enunciado` | T = 60, Ruta1 = 60, Ruta2 = 35, críticas A, B, F |
| 81 | `test_tiempo_minimo_teorico_por_defecto` | Tmin = 50 |
| 85 | `test_empate_marca_las_seis_actividades_criticas` | Empate → las 6 críticas |
| 94 | `test_suma_de_frecuencias_igual_a_n_observaciones` | Suma de FO = N |
| 100 | `test_valor_en_tmin_mas_90_cae_en_el_ultimo_intervalo` | 140 cae en el intervalo 10 |
| 106 | `test_promedio_incremental_igual_a_promedio_clasico` | Promedio incremental = promedio común |
| 116 | `test_percentil_95_de_1_a_99_es_95` | Con 1..99 desordenados da 95 |
| 122 | `test_percentil_se_calcula_en_la_iteracion_99` | Usa n = 99 y posición 95 |
| 128 | `test_consulta_en_iteracion_k_coincide_con_la_fila_k` | Volver a simular hasta k da la misma fila |
| 134 | `test_generadores_identicos_advierten_pero_no_bloquean` | Advierte sin bloquear |
| 140 | `test_sin_legajo_no_se_puede_simular` | Sin m hay error |
| 145 | `test_rendimiento_100000_iteraciones` | 100.000 iteraciones en menos de 10 s |
| 152 | `test_periodo_del_generador` | Período 16 con Hull-Dobell; 2055 con los datos de prueba |

### ⭐ Las 10 líneas para mostrarle al profe

| # | Línea | Código | Por qué es importante |
|---|---|---|---|
| 1 | `generador.py:31` | `self.x = (self.a * self.x + self.c) % self.m` | Es el generador congruencial mixto |
| 2 | `generador.py:44` | `numerador, denominador = x, self.m` | Conversión X/m: RND ∈ [0, 1) |
| 3 | `distribuciones.py:50` | `if rnd < fila["hasta"]:` | Búsqueda en la tabla de la discreta, con intervalo [desde, hasta) |
| 4 | `distribuciones.py:70` | `return -media * math.log(1 - rnd)` | Exponencial por transformada inversa |
| 5 | `modelo.py:31` | `inicio_f = max(fin_b, fin_e)` | Punto de convergencia: F espera a la rama más lenta |
| 6 | `modelo.py:40` | `if holgura < TOLERANCIA_EMPATE:` | Empieza el criterio de criticidad, con empate |
| 7 | `simulacion.py:33` | `return ((n - 1) * promedio_anterior + valor) / n` | Promedio incremental sin guardar datos |
| 8 | `simulacion.py:46` | `i = math.ceil(round(confianza * (n + 1), 9))` | Percentil con F(i) = i/(n+1) |
| 9 | `simulacion.py:56` | `k = math.floor((t - t_min) / ancho)` | Intervalo de frecuencias sin guardar datos |
| 10 | `simulacion.py:250` | `anterior = actual` | La restricción "solo vector actual y anterior" |

---

## 4. RECORRIDO DE UNA ITERACIÓN (`calcular_fila`, `simulacion.py:120-187`)

Contexto: en `simular` (`simulacion.py:225-227`) se llama
`actual = calcular_fila(n, anterior, generadores, tabla_b, tabla_f, p)`.

**Paso 0 – Crear la fila** (125): `actual = {"n": n}`.

**Paso 1 – Duraciones** (siempre en el orden B, D, E, F; un RND de cada generador):

1. `actual["A"] = constante(p["A"])` (128). No usa RND.
2. `x, rnd = generadores["B"].siguiente()` (130). Adentro de `siguiente`, `self.x = (a·self.x + c) % m` (`generador.py:31`) y `convertir` devuelve `x / m` (`generador.py:44`, `:54`).
   Después, `actual["B_x"], actual["B_rnd"], actual["B"] = x, rnd, discreta(rnd, tabla_b)["valor"]` (131).
3. `actual["C"] = constante(p["C"])` (133).
4. `x, rnd = generadores["D"].siguiente()` (135) → `actual["D"] = uniforme(rnd, p["D"]["a"], p["D"]["b"])` (137).
5. `x, rnd = generadores["E"].siguiente()` (139) → `actual["E"] = exponencial(rnd, p["E"]["media"])` (141).
6. `x, rnd = generadores["F"].siguiente()` (143) → `fila_f = discreta(rnd, tabla_f)` (144) → `actual["F_estado"], actual["F"] = fila_f["etiqueta"], fila_f["valor"]` (146).

**Paso 2 – Red** (149-154):
- `red = calcular_red(actual["A"], …, actual["F"])` calcula `fin_a` … `fin_e`, `inicio_f = max(fin_b, fin_e)`, `fin_f`, `ruta1`, `ruta2`, `holgura`, `T`, `ruta_critica` y `criticas`.
- Esas claves se copian a `actual` (150-152).
- `actual["crit_X"] = 1 if X in red["criticas"] else 0` para cada actividad (153-154).

**Paso 3 – Estimadores, usando SOLO `anterior`** (157-186):
- `t = actual["T"]` (157).
- Promedios: `actual["prom_X"] = promedio_incremental(anterior["prom_X"], actual[X], n)` para A…F (158-159), y lo mismo para `prom_ruta1`, `prom_ruta2` y `prom_T` (160-162).
- `actual["t_min_obs"] = min(anterior["t_min_obs"], t)` y `actual["t_max_obs"] = max(anterior["t_max_obs"], t)` (164-165).
- `actual["cont_crit_X"] = anterior["cont_crit_X"] + actual["crit_X"]` y `actual["prop_crit_X"] = cont / n` (168-170).
- `cont_ruta1`, `cont_ruta2`, `cont_empate` y sus proporciones (172-177).
- `actual["cont_menor"] = anterior["cont_menor"] + (1 if t <= p["umbral_menor"] else 0)` y `prob_menor = cont / n` (180-181).
- `cont_mayor` y `prob_mayor` con `t >= p["umbral_mayor"]` (182-183).
- `actual["t_confianza"] = anterior["t_confianza"]` (186): arrastra el percentil ya calculado.
- `return actual` (187).

**Después, en `simular`** (231-250):
- `contadores[indice_intervalo(t, t_min, ancho)] += 1` si `n <= n_frecuencias` (233-234).
- `buffer_percentil.append(t)` si `n <= n_percentil`. En `n == n_percentil` calcula el percentil, lo guarda en `actual["t_confianza"]` y vacía el buffer (236-242).
- Si la fila está en el rango pedido, se guarda para mostrarla (244-245).
- Cada `paso_grafico` iteraciones guarda `(n, t, prom_T)` para el gráfico (247-248).
- **`anterior = actual`** (250). La fila anterior se pierde, y en la próxima vuelta solo existen `anterior` y el nuevo `actual`.

---

## 5. INTERFAZ (FRONT) COMPLETA

### 5.1 Barra lateral ("Parámetros", `app.py:59-113`)

**Simulación**

| Etiqueta exacta | Defecto | Parámetro del enunciado | Si lo cambio… |
|---|---|---|---|
| Cantidad de iteraciones N | 100000 | Cantidad de simulaciones ("iteración 100000") | Cambia cuántas filas se simulan; los estimadores finales son a esa iteración |
| Mostrar desde la iteración j | 1 | Rango a mostrar | Cambia la primera fila visible del vector de estado (0 muestra la fila de inicialización) |
| Cantidad de filas i a mostrar | 20 | Rango a mostrar | Cambia cuántas filas se ven; la última siempre se agrega |
| Decimales del RND (truncar) | vacío ("sin truncar") | No está en la consigna | Trunca el RND a k decimales (nunca redondea) |
| Conversión X → RND | X/m | Cómo pasar de X a RND | X/(m−1) puede dar 1 (y romper la exponencial); (X+0.5)/m nunca da 0 ni 1 |

**Generadores** (uno por variable)

| Etiqueta | Defecto | Parámetro | Si lo cambio… |
|---|---|---|---|
| Botón "Copiar parámetros del generador de B a todos" | — | — | Copia semilla, a, c y m de B a D, E y F |
| Generador de B / D / E / F → Semilla X0 | 3922 | X0 | Cambia la secuencia de esa variable |
| → a (multiplicativa) | 1221 | a | Idem |
| → c (aditiva) | 1714 | c | Idem |
| → m (legajo) | vacío ("Nº de legajo") | m = legajo | **Obligatorio**: sin m no se puede simular |

**Distribuciones**

| Etiqueta | Defecto | Parámetro | Si lo cambio… |
|---|---|---|---|
| A – constante (min) | 15.0 | Duración de A | Cambia A en todas las iteraciones y el Tmin |
| B – discreta (picking): tabla etiqueta/valor/probabilidad | 20/0.25, 30/0.40, 40/0.35 | Distribución de B | Se pueden editar y agregar filas; las probabilidades tienen que sumar 1 |
| C – constante (min) | 5.0 | Duración de C | Idem A |
| D – uniforme U[a, b]: a | 5.0 | Extremo inferior | Tiene que cumplirse a < b; cambia el Tmin |
| D – uniforme U[a, b]: b | 25.0 | Extremo superior | Idem |
| E – exponencial: media (min) | 5.0 | Media de E | Tiene que ser > 0; debajo se muestra λ = 1/media |
| F – discreta (montacargas): tabla | Libre 15/0.5, Ocupado 25/0.5 | Distribución de F | Igual que B; la etiqueta aparece en la columna "Montacargas" |

**Estimadores**

| Etiqueta | Defecto | Parámetro | Si lo cambio… |
|---|---|---|---|
| Simulaciones para el percentil | 99 | "Simulando 99 veces" | Cambia n; la posición es i = ceil(conf·(n+1)) |
| Nivel de confianza | 0.95 | 95 % | Admite entre 0.01 y 0.99 |
| Umbral P(T ≤ x) | 60.0 | "60 minutos o menos" | Cambia el umbral (inclusivo) |
| Umbral P(T ≥ x) | 90.0 | "90 minutos o más" | Idem |
| El último intervalo empieza Tmin + … | 90.0 | "90 minutos después" | ancho = valor / 9 |
| N observaciones para la distribución | vacío ("= todas las iteraciones") | "Cantidad de observaciones al evaluar" | Solo se cuentan las primeras N iteraciones |

### 5.2 Secciones de resultados (en orden de aparición)

**0. Encabezado** (`app.py:445-448`): título, red y las 6 actividades.

**1. Ejecutar la simulación** (`app.py:453-460`): errores (rojo), avisos (amarillo, en un solo recuadro), "Simulacro con datos fijos (ejemplo del enunciado)" (A=15, B=30, C=5, D=10, E=5, F=15 → T = 60, críticas A, B, F) y el botón **Simular** (deshabilitado si hay errores).

**2. Estimadores en la iteración N** (`app.py:479-486`, `:230-256`). 8 tarjetas:

| Tarjeta | Sale de |
|---|---|
| Iteración | `fila["n"]` |
| Tiempo mínimo teórico | `resultado["t_min_teorico"]` (`tiempo_minimo_teorico`) |
| T promedio | `prom_T` |
| T mínimo observado | `t_min_obs` |
| T máximo observado | `t_max_obs` |
| P(T ≤ 60) | `prob_menor` (debajo, `cont_menor` casos) |
| P(T ≥ 90) | `prob_mayor` (debajo, `cont_mayor` casos) |
| T con 95 % de confianza | `t_confianza` ("—" si todavía no se llegó a 99 iteraciones) |

Debajo hay una tabla con **Actividad / ruta | Duración promedio (min) | Veces crítica | Proporción crítica** para A…F, Ruta 1, Ruta 2 y Empate. Sale de `prom_X`, `cont_crit_X` y `prop_crit_X`, y de `prom_ruta1/2`, `cont_ruta1/2/empate` y `prop_ruta1/2/empate`. Al final, el aviso "Con un 95 % de confianza, el pedido se despacha en X min o menos".

**3. Vector de estado** (`app.py:488-494`, columnas en `:120-146`). Filas j…j+i−1 + la última (con "…" en el salto):

| Grupo | Subcolumnas (clave) |
|---|---|
| Iteración | n |
| A | Duración (`A`) |
| B | X (`B_x`), RND (`B_rnd`), Duración (`B`) |
| C | Duración (`C`) |
| D | X, RND, Duración |
| E | X, RND, Duración |
| F | X, RND, Montacargas (`F_estado`), Duración |
| Tiempos de la red | finA, finB, finC, finD, finE, inicioF, finF |
| Rutas | Ruta 1, Ruta 2, Holgura (= abs(finB − finE)) |
| Proyecto | T, Ruta crítica ("Ruta 1" / "Ruta 2" / "Empate") |
| Crítica (1/0) | A, B, C, D, E, F |
| Promedios | A…F, Ruta 1, Ruta 2, T |
| T observado | Mín, Máx |
| Veces crítica | A…F (contadores) |
| Proporción crítica | A…F |
| Ruta crítica: veces | R1, R2, Empate |
| Ruta crítica: proporción | R1, R2, Empate |
| P(T ≤ 60) | Cont., Prob. |
| P(T ≥ 90) | Cont., Prob. |
| T con 95 % confianza | T (aparece desde la iteración 99) |

**4. Consultar una iteración puntual** (`app.py:496-506`): se ingresa k y se toca **Consultar**. Vuelve a simular desde cero hasta k (`simular(p_usado, hasta=k, guardar_filas=False)`) y muestra las mismas 8 tarjetas, la tabla y la fila k del vector.

**5. Tablas de probabilidad acumulada** (`app.py:508-514`, `:259-266`): para B y F, Etiqueta | Valor | Probabilidad | P. acumulada | Intervalo RND [desde, hasta).

**6. Distribución de frecuencias** (`app.py:516-520`, `:269-287`): Intervalo | Desde | Hasta (∞ en el último) | Marca de clase ("—" en el último) | FO | FR | FR acumulada, con el control "suma de FO = N observaciones".

**7. Gráficos** (`app.py:522-529`):
1. Dispersión de T por iteración (puntos celestes).
2. Promedio acumulado de T (línea azul) sobre el mismo gráfico.
3. Barras de frecuencias con el % encima.

Los gráficos 1 y 2 usan una muestra de hasta 2.000 puntos (`simulacion.py:214`, `:247-248`).

**8. Traza de las 3 primeras iteraciones** (`app.py:531-533`): el paso a paso con las mismas funciones del motor.

**9. Respuestas a la consigna** (`app.py:536-546`, `:330-438`). Si se consultó una k, un selector permite responder con la última iteración o con la k. Tiene 8 tarjetas numeradas:
1. Tiempo mínimo, con la cuenta y un Gantt.
2. Duración de cada proceso (barras de promedios).
3. Tiempo promedio (línea que se estabiliza).
4. Actividades críticas (barras en %, cuello de botella).
5. Tiempo con 95 % de confianza (posición i y F(i)).
6. P(T ≤ 60), con barra de progreso.
7. P(T ≥ 90), con barra de progreso.
8. Distribución de frecuencias (gráfico y tabla).

### 5.3 Errores y advertencias

**Errores** (rojos; bloquean el botón Simular) — `parametros.py:validar`:

| Mensaje | Cuándo | Línea |
|---|---|---|
| "falta cargar m (número de legajo)" | m vacío | 88-90 |
| "semilla, a, c y m tienen que ser enteros" | algún dato no entero | 91-93 |
| "m tiene que ser > 0" / "a tiene que ser > 0" / "c tiene que ser ≥ 0" / "la semilla tiene que ser ≥ 0" | valores fuera de rango | 94-101 |
| "con la conversión X/(m-1), m tiene que ser > 1" | X/(m−1) con m = 1 | 102-103 |
| "la duración constante no puede ser negativa" | A o C < 0 | 128-130 |
| "la tabla tiene que tener al menos una fila" | tabla B o F vacía | 133-135 |
| "las probabilidades suman …, tienen que sumar 1" | suma ≠ 1 (tolerancia 1e-9) | 136-138 |
| "hay probabilidades negativas" / "hay duraciones negativas" | en B o F | 139-142 |
| "D: tiene que cumplirse a < b" / "a no puede ser negativo" | uniforme inválida | 143-146 |
| "E: la media tiene que ser > 0" | media ≤ 0 | 147-148 |
| "…percentil tiene que ser un entero ≥ 1" | n del percentil < 1 | 151-152 |
| "El nivel de confianza tiene que estar entre 0 y 1" | fuera de (0, 1) | 159-160 |
| "El desplazamiento del último intervalo tiene que ser > 0" | ≤ 0 | 161-162 |
| "N observaciones … tiene que ser un entero ≥ 1" | N < 1 | 164-165 |
| "Iteración n: RND = 1 en la exponencial…" | durante la simulación, con X/(m−1) | `distribuciones.py:67-69`, `simulacion.py:228-229`, `app.py:468-470` |
| "Control: suma de FO ≠ N observaciones" | no debería pasar nunca (control) | `app.py:287` |

**Advertencias** (amarillas; **no** bloquean):

| Mensaje | Cuándo | Línea |
|---|---|---|
| "el período real es P… los números se repiten cada P" | N > período real del generador | 104-110 |
| "se piden N iteraciones y m = …" | m > 1.000.000 y N > m | 111-114 |
| "Los 4 generadores tienen los mismos parámetros…" | B, D, E y F con los mismos datos | 116-120 |
| "Con X/(m-1) el RND puede valer 1…" | se eligió esa conversión | 122-125 |
| "…con n > 10.000 usa bastante memoria" | n del percentil > 10.000 | 153-154 |
| "El percentil necesita … iteraciones…" | n del percentil > N | 155-158 |
| "N observaciones … es mayor que las iteraciones" | N obs > N | 166-169 |
| "Cambiaste parámetros: los resultados de abajo son de la simulación anterior" (azul) | se tocó un parámetro después de simular | `app.py:476-477` |

---

## 6. LO QUE NO PIDIÓ LA CONSIGNA (y por qué está)

| Agregado | Dónde | Por qué |
|---|---|---|
| Conversiones X/(m−1) y (X+0.5)/m | `generador.py:12-15`, `:45-49` | La cátedra no confirmó cuál usar; si el profe pide otra, se cambia sin tocar código. |
| Truncado del RND a k decimales | `generador.py:56-57` | Algunas cátedras trabajan con RND de 4 decimales. Trunca con enteros para no redondear por error. |
| Advertencia de generadores idénticos | `parametros.py:116-120` | Con los valores de prueba, los 4 dan el mismo RND y las variables quedan correlacionadas. Conviene saberlo, pero no se bloquea. |
| Cálculo del período real | `generador.py:60-73`, `parametros.py:104-114` | Con a=1221, c=1714, m=12345 el período es 2055, no 12345. En 100.000 iteraciones la secuencia se repite unas 48 veces. |
| Consulta de la iteración k | `simulacion.py:194-199`, `app.py:496-506` | Permite responder "¿cuánto da en la iteración 50.000?" sin guardar la tabla: vuelve a simular hasta k. |
| Simulacro con datos fijos | `app.py:290-299` | Reproduce el ejemplo del PDF (T = 60) para mostrar que la red está bien armada. |
| Traza de las 3 primeras iteraciones | `simulacion.py:270-306`, `generar_traza.py` | Para verificar a mano en la defensa; usa las mismas funciones que el motor. |
| Muestra de 2.000 puntos para gráficos | `simulacion.py:23`, `:214`, `:247-248` | Graficar 100.000 puntos sería lento y guardarlos violaría la restricción. Es solo visualización. |
| Validaciones de todos los datos | `parametros.py:63-171` | Si en la evaluación cargo un dato mal (probabilidades que no suman 1, a ≥ b), aparece un error claro en vez de un resultado incorrecto. |
| Holgura | `modelo.py:37` | Muestra cuánto espera la rama rápida a la lenta antes de F; también sirve para detectar el empate. |
| Proporción de Ruta 1 / Ruta 2 / empate | `simulacion.py:172-177` | Complementa la criticidad por actividad. |
| Mínimo y máximo observados | `simulacion.py:164-165` | Para comparar con el tiempo mínimo teórico. |
| Tabla editable (agregar filas a B y F) | `app.py:88`, `:100` | La consigna dice que pueden cambiar probabilidades; también podrían cambiar la cantidad de valores. |
| Sección "Respuestas a la consigna" | `app.py:330-438` | Resume cada pedido en un recuadro, para responder rápido en la defensa. |
| Tests automáticos | `tests/test_simulacion.py` | Prueban que las fórmulas dan lo esperado (Tmin = 50, T = 60, percentil = 95, etc.). |
| Estilos visuales | `estilos.py`, `.streamlit/config.toml` | Solo presentación. |

---

## 7. SUPUESTOS E INTERPRETACIONES (del README, sección 7)

| # | Supuesto | Dónde se aplica |
|---|---|---|
| 1 | La conversión por defecto es **X/m**, que da RND ∈ [0, 1) y nunca produce ln(0) | `parametros.py:32`; `generador.py:43-44`; `distribuciones.py:67-70` |
| 2 | **"Tiempo mínimo" = mínimo teórico** con el mínimo de cada distribución (50). El mínimo observado se reporta aparte | `modelo.py:60-83`; `simulacion.py:164` |
| 3 | **Empate** (diferencia < 1e-9) → las dos ramas son críticas (las 6 actividades) | `modelo.py:13`, `:40-42` |
| 4 | **95 % de confianza** con las **primeras 99** iteraciones y F(i) = i/(n+1) → posición 95 | `parametros.py:50-51`; `simulacion.py:36-48`, `:236-242` |
| 5 | **Umbrales inclusivos**: T ≤ 60 y T ≥ 90 | `simulacion.py:180`, `:182` |
| 6 | La distribución de frecuencias cuenta las **primeras N** observaciones | `simulacion.py:206`, `:233` |
| 7 | **Orden de consumo**: un RND de cada generador por iteración, en el orden B, D, E, F | `simulacion.py:130`, `:135`, `:139`, `:143` |
| 8 | **"Generador diferente para cada uno"** puede significar para cada **alumno** (m = legajo). Igual hay un generador por variable, y si son idénticos solo se avisa | `parametros.py:23-24`, `:34`, `:116-120`; `simulacion.py:107-114` |
| 9 | **Período**: con 1221/1714/12345 el período es 2055 (no se cumple Hull-Dobell) | `generador.py:60-73`; `parametros.py:104-110` |

Otros supuestos que están en el código:
- **Intervalos semiabiertos [desde, hasta)** en la discreta (`distribuciones.py:50`) y en las frecuencias (`simulacion.py:56`).
- **El último `hasta` de la tabla discreta se fuerza a 1**, por si la suma da 0.9999999 (`distribuciones.py:36-38`).
- **La semilla no es un RND** (`generador.py:27`, `:31`).
- **Los intervalos de frecuencias se definen antes de simular**, con el Tmin teórico, porque no se pueden guardar los datos para calcularlos después (`simulacion.py:202-205`).
- **Un valor exactamente igual a Tmin + 90 cae en el último intervalo** (`simulacion.py:57`; test en `tests/test_simulacion.py:100`).
- **La exponencial se parametriza con la media**, no con λ (`distribuciones.py:70`; la app muestra λ = 1/media en `app.py:97-98`).

---

## 8. RESULTADOS

### 8.1 Tests (`.venv/bin/pytest -v`)

```
tests/test_simulacion.py::test_generador_primeros_x_coinciden_con_calculo_a_mano PASSED [  5%]
tests/test_simulacion.py::test_primer_rnd_sale_de_x1_y_no_de_la_semilla PASSED [ 10%]
tests/test_simulacion.py::test_rnd_siempre_en_0_1_con_conversion_por_defecto PASSED [ 15%]
tests/test_simulacion.py::test_truncado_no_redondea PASSED               [ 20%]
tests/test_simulacion.py::test_discreta_limites_de_los_intervalos PASSED [ 25%]
tests/test_simulacion.py::test_uniforme_rnd_cero_da_a PASSED             [ 30%]
tests/test_simulacion.py::test_exponencial PASSED                        [ 35%]
tests/test_simulacion.py::test_red_con_datos_fijos_del_enunciado PASSED  [ 40%]
tests/test_simulacion.py::test_tiempo_minimo_teorico_por_defecto PASSED  [ 45%]
tests/test_simulacion.py::test_empate_marca_las_seis_actividades_criticas PASSED [ 50%]
tests/test_simulacion.py::test_suma_de_frecuencias_igual_a_n_observaciones PASSED [ 55%]
tests/test_simulacion.py::test_valor_en_tmin_mas_90_cae_en_el_ultimo_intervalo PASSED [ 60%]
tests/test_simulacion.py::test_promedio_incremental_igual_a_promedio_clasico PASSED [ 65%]
tests/test_simulacion.py::test_percentil_95_de_1_a_99_es_95 PASSED       [ 70%]
tests/test_simulacion.py::test_percentil_se_calcula_en_la_iteracion_99 PASSED [ 75%]
tests/test_simulacion.py::test_consulta_en_iteracion_k_coincide_con_la_fila_k PASSED [ 80%]
tests/test_simulacion.py::test_generadores_identicos_advierten_pero_no_bloquean PASSED [ 85%]
tests/test_simulacion.py::test_sin_legajo_no_se_puede_simular PASSED     [ 90%]
tests/test_simulacion.py::test_rendimiento_100000_iteraciones PASSED     [ 95%]
tests/test_simulacion.py::test_periodo_del_generador PASSED              [100%]

============================== 20 passed in 0.59s ==============================
```

### 8.2 100.000 iteraciones con los parámetros de prueba

Semilla 3922, a 1221, c 1714, **m = 12345** en los 4 generadores, conversión X/m. Tardó **0,53 s**.

| Estimador | Valor |
|---|---|
| Tiempo mínimo teórico | **50 min** |
| T mínimo observado | 50.0000 min |
| T máximo observado | 98.6361 min |
| **T promedio** | **66.0051 min** |
| Promedio A / B / C | 15.0000 / 30.9877 / 5.0000 |
| Promedio D / E / F | 15.0043 / 5.0165 / 19.9826 |
| Promedio Ruta 1 / Ruta 2 | 65.9703 / 45.0034 |
| Veces crítica A, B | 99.415 → proporción **0.9941** |
| Veces crítica C, D, E | 585 → proporción **0.0059** |
| Veces crítica F | 100.000 → proporción **1.0000** |
| Ruta 1 / Ruta 2 / Empate | 0.9941 / 0.0059 / 0.0000 |
| **T con 95 % de confianza** (primeras 99, posición i = 95) | **80 min** |
| **P(T ≤ 60)** | **0.5017** (50.174 casos) |
| **P(T ≥ 90)** | **0.0015** (146 casos) |

Valores teóricos para comparar: E[B] = 0.25·20 + 0.40·30 + 0.35·40 = **31**; E[D] = (5+25)/2 = **15**; E[E] = **5**; E[F] = **20**. Los promedios simulados coinciden.

**Distribución de frecuencias** (Tmin = 50, ancho = 90/9 = 10, N = 100.000):

| # | Desde | Hasta | Marca | FO | FR | FR acum. |
|---|---|---|---|---|---|---|
| 1 | 50 | 60 | 55 | 25.053 | 0.2505 | 0.2505 |
| 2 | 60 | 70 | 65 | 25.121 | 0.2512 | 0.5017 |
| 3 | 70 | 80 | 75 | 14.896 | 0.1490 | 0.6507 |
| 4 | 80 | 90 | 85 | 34.784 | 0.3478 | 0.9985 |
| 5 | 90 | 100 | 95 | 146 | 0.0015 | 1.0000 |
| 6 | 100 | 110 | 105 | 0 | 0.0000 | 1.0000 |
| 7 | 110 | 120 | 115 | 0 | 0.0000 | 1.0000 |
| 8 | 120 | 130 | 125 | 0 | 0.0000 | 1.0000 |
| 9 | 130 | 140 | 135 | 0 | 0.0000 | 1.0000 |
| 10 | 140 | ∞ | — | 0 | 0.0000 | 1.0000 |
| | | | **Suma** | **100.000** | 1 | |

#### Por qué la tabla da así (sirve para explicarla)

Como los 4 generadores tienen los mismos parámetros, **B y F reciben el mismo RND**. La Ruta 1 (A + B + F) casi siempre es la crítica, así que T depende casi solo de ese RND:

| RND | B | F | T = 15 + B + F | Probabilidad | Intervalo |
|---|---|---|---|---|---|
| [0, 0.25) | 20 | 15 (Libre) | 50 | 0.25 | [50, 60) → 0.2505 ✔ |
| [0.25, 0.50) | 30 | 15 (Libre) | 60 | 0.25 | [60, 70) → 0.2512 ✔ |
| [0.50, 0.65) | 30 | 25 (Ocupado) | 70 | 0.15 | [70, 80) → 0.1490 ✔ |
| [0.65, 1) | 40 | 25 (Ocupado) | 80 | 0.35 | [80, 90) → 0.3478 ✔ |

- Eso explica que **P(T ≤ 60) ≈ 0.50** (RND < 0.5) y que el **tiempo con 95 % sea 80**: el 35 % de las T valen exactamente 80.
- Para que **T ≥ 90**, la Ruta 2 tiene que superar 90: 5 + D + E + 25 ≥ 90, o sea D + E ≥ 60. Como D ≤ 25, hace falta E ≥ 35, algo muy raro con media 5. Por eso sale **0.15 %**.
- **Ojo:** con generadores **independientes** el resultado cambiaría, porque B y F no irían juntos. Por ejemplo, P(B=40 y F=25) = 0.35 · 0.5 = 0.175 en vez de 0.35. Si en la evaluación dan coeficientes distintos para cada generador, los números van a cambiar.

### 8.3 Traza de las 3 primeras iteraciones (generada por `traza_primeras_iteraciones`)

**Iteración 1**

- **B**: X1 = (1221 · 3922 + 1714) mod 12345 = **616** → RND = X/m = **0.0499**
- **D**: X1 = (1221 · 3922 + 1714) mod 12345 = **616** → RND = X/m = **0.0499**
- **E**: X1 = (1221 · 3922 + 1714) mod 12345 = **616** → RND = X/m = **0.0499**
- **F**: X1 = (1221 · 3922 + 1714) mod 12345 = **616** → RND = X/m = **0.0499**
- A = 15 (constante), C = 5 (constante)
- B: RND 0.0499 cae en la tabla acumulada → **B = 20**
- D = 5 + (25 − 5) · 0.0499 = **5.9980**
- E = −5 · ln(1 − 0.0499) = **0.2559**
- F: RND 0.0499 → montacargas Libre → **F = 15**
- finB = 15 + 20 = 35.0000 ; finE = 5 + 5.9980 + 0.2559 = 11.2539
- inicioF = max(35.0000, 11.2539) = 35.0000 ; **T = 35.0000 + 15 = 50.0000**
- Ruta1 = 50.0000, Ruta2 = 26.2539 → Ruta 1 es la crítica → críticas: A, B, F
- Promedio de T hasta acá = 50.0000

**Iteración 2**

- **B**: X2 = (1221 · 616 + 1714) mod 12345 = **805** → RND = X/m = **0.0652**
- **D**: X2 = (1221 · 616 + 1714) mod 12345 = **805** → RND = X/m = **0.0652**
- **E**: X2 = (1221 · 616 + 1714) mod 12345 = **805** → RND = X/m = **0.0652**
- **F**: X2 = (1221 · 616 + 1714) mod 12345 = **805** → RND = X/m = **0.0652**
- A = 15 (constante), C = 5 (constante)
- B: RND 0.0652 cae en la tabla acumulada → **B = 20**
- D = 5 + (25 − 5) · 0.0652 = **6.3042**
- E = −5 · ln(1 − 0.0652) = **0.3372**
- F: RND 0.0652 → montacargas Libre → **F = 15**
- finB = 15 + 20 = 35.0000 ; finE = 5 + 6.3042 + 0.3372 = 11.6413
- inicioF = max(35.0000, 11.6413) = 35.0000 ; **T = 35.0000 + 15 = 50.0000**
- Ruta1 = 50.0000, Ruta2 = 26.6413 → Ruta 1 es la crítica → críticas: A, B, F
- Promedio de T hasta acá = 50.0000

**Iteración 3**

- **B**: X3 = (1221 · 805 + 1714) mod 12345 = **9364** → RND = X/m = **0.7585**
- **D**: X3 = (1221 · 805 + 1714) mod 12345 = **9364** → RND = X/m = **0.7585**
- **E**: X3 = (1221 · 805 + 1714) mod 12345 = **9364** → RND = X/m = **0.7585**
- **F**: X3 = (1221 · 805 + 1714) mod 12345 = **9364** → RND = X/m = **0.7585**
- A = 15 (constante), C = 5 (constante)
- B: RND 0.7585 cae en la tabla acumulada → **B = 40**
- D = 5 + (25 − 5) · 0.7585 = **20.1705**
- E = −5 · ln(1 − 0.7585) = **7.1050**
- F: RND 0.7585 → montacargas Ocupado → **F = 25**
- finB = 15 + 40 = 55.0000 ; finE = 5 + 20.1705 + 7.1050 = 32.2755
- inicioF = max(55.0000, 32.2755) = 55.0000 ; **T = 55.0000 + 25 = 80.0000**
- Ruta1 = 80.0000, Ruta2 = 57.2755 → Ruta 1 es la crítica → críticas: A, B, F
- Promedio de T hasta acá = 60.0000

Cuenta a mano de X1: 1221 · 3922 = 4.788.762; + 1714 = 4.790.476; 4.790.476 − 388 · 12345 (= 4.789.860) = **616**.

### 8.4 Período real del generador

Con semilla 3922, a = 1221, c = 1714, m = 12345: **período = 2055** (`calcular_periodo`, test en `tests/test_simulacion.py:157`).

Por qué no es 12345: para período completo (**Hull-Dobell**) hacen falta tres condiciones:
1. **c y m coprimos.** 1714 = 2 · 857 y 12345 = 3 · 5 · 823 → ✔
2. **a − 1 divisible por todos los primos de m.** a − 1 = 1220 = 2² · 5 · 61: es divisible por 5, pero **no por 3 ni por 823** → ✘
3. **Si 4 divide a m, 4 divide a a − 1.** 4 no divide a 12345 → no aplica.

Como falla la condición 2, el período es menor que m.

---

## 9. PREGUNTAS PROBABLES DEL PROFE

1. **¿Por qué la semilla no es el primer número aleatorio?**
   Porque la semilla es el punto de partida, no un valor generado. El primer RND sale de X1 = (a·X0 + c) mod m. → `generador.py:27` (`self.x = semilla`) y `:31` (primero calcula, después convierte).

2. **¿Por qué dividís por m y no por m − 1?**
   Con X/m el RND va de 0 a (m−1)/m < 1, así que nunca vale 1 y `ln(1 − RND)` nunca es ln(0). Con X/(m−1) podría dar 1. → `generador.py:44`, `distribuciones.py:67-70`.

3. **¿Cómo generás una variable discreta como B?**
   Con la tabla de probabilidad acumulada: cada valor tiene un intervalo [desde, hasta) y el RND cae en uno solo. Por ejemplo, RND = 0.25 da 30, porque el límite inferior está incluido. → `distribuciones.py:26-27` (acumulada) y `:50` (`if rnd < fila["hasta"]`).

4. **¿De dónde sale E = −media·ln(1 − RND)?**
   De la **transformada inversa**. La exponencial tiene F(x) = 1 − e^(−λx); se iguala a RND y se despeja x = −ln(1 − RND)/λ = −media·ln(1 − RND). → `distribuciones.py:70`.

5. **¿Y la uniforme?**
   También por transformada inversa: F(x) = (x − a)/(b − a) = RND → x = a + (b − a)·RND. → `distribuciones.py:58`.

6. **¿Cómo cumplís "solo vector actual y anterior"?**
   `calcular_fila` recibe solo la fila `anterior` y devuelve `actual`. Todos los estimadores son acumuladores (promedios, contadores, mín/máx) que se actualizan con la fila anterior. Después se hace `anterior = actual` y la vieja se descarta. → `simulacion.py:120`, `:156-186`, `:250`.

7. **¿Cómo calculás el promedio sin guardar los valores?**
   Con el promedio incremental P(n) = ((n−1)·P(n−1) + x(n))/n. La suma de los n−1 anteriores es (n−1)·P(n−1): se le suma el nuevo y se divide por n. → `simulacion.py:33`; el test `tests/test_simulacion.py:106` compara contra el promedio clásico.

8. **¿Qué es una actividad crítica y cómo la detectás?**
   Es la que está en el camino más lento: cualquier demora suya atrasa el despacho. Se comparan finB (A+B) y finE (C+D+E): gana la rama mayor, y F es crítica siempre. → `modelo.py:40-48`.

9. **¿Qué pasa si las dos ramas terminan igual?**
   Es un empate y las dos ramas son críticas (las 6 actividades), porque atrasar cualquiera atrasa el proyecto. Se usa una tolerancia de 1e-9 por los errores de decimales. → `modelo.py:13`, `:40-42`; test `tests/test_simulacion.py:85`.

10. **¿Cómo calculás el tiempo con 95 % de confianza?**
    Se guardan las primeras 99 T, se ordenan y se toma la de posición i con F(i) = i/(n+1) = 0.95 → i = 95. Se divide por n+1 para que el máximo no tenga probabilidad acumulada 1. → `simulacion.py:44-48`, `:236-242`.

11. **¿No decía la consigna que no se podían guardar datos? ¿Por qué guardás 99?**
    El percentil necesita ordenar valores, y eso no se puede hacer de forma incremental. Por eso se guarda un buffer fijo de 99 valores (lo que pide la consigna), que se libera apenas se usa. No crece con las iteraciones. → `simulacion.py:11-12`, `:211`, `:242`.

12. **¿Cómo armás la distribución de frecuencias sin guardar los datos?**
    Los intervalos se definen **antes** de simular con el Tmin teórico (50) y ancho 90/9 = 10. En cada iteración solo se suma 1 al contador del intervalo de T, con k = floor((T − 50)/10) y tope en 9. → `simulacion.py:204-207`, `:56-57`, `:233-234`.

13. **Si ahora te doy otros coeficientes o probabilidades, ¿qué tocás?**
    Nada del código: se cargan en la barra lateral, un generador por variable, y las tablas de B y F son editables. La validación avisa si las probabilidades no suman 1. → `app.py:59-113`, `parametros.py:136-138`.

14. **¿Por qué los 4 generadores dan el mismo RND? ¿No debían ser distintos?**
    Porque con los valores de prueba los 4 tienen la misma semilla, a, c y m. El código tiene 4 generadores independientes; si se cargan distintos, dan secuencias distintas. La app advierte que así B, D, E y F quedan correlacionadas. → `simulacion.py:107-114`, `parametros.py:116-120`.

15. **¿Cuál es el período del generador y por qué importa?**
    2055. Después de 2055 números la secuencia se repite, así que en 100.000 iteraciones hay unas 48 vueltas. No es m porque no se cumple Hull-Dobell (a−1 = 1220 no es múltiplo de 3 ni de 823). → `generador.py:60-73`, `parametros.py:104-110`.

Preguntas extra que pueden aparecer:
- **¿Cómo me mostrás la iteración 50.000?** Con "Consultar una iteración puntual": vuelve a simular hasta 50.000 con los mismos parámetros; como el generador es determinista, da la misma fila. → `app.py:501-502`, `simulacion.py:199`; test `tests/test_simulacion.py:128`.
- **¿Por qué el mínimo observado coincide con el teórico (50)?** Porque el mínimo de la Ruta 1 (15 + 20 + 15) se alcanza de verdad: con RND < 0.25 salen B = 20 y F = 15. → `modelo.py:60-83`, traza iteración 1.
- **¿Cuál es la variable objetivo?** T, la duración total del proyecto (= finF). → `modelo.py:32`, `:54`.

---

## 10. CÓMO CORRERLO

### En la Mac (el entorno ya está creado)

```bash
cd /Users/ivososa/Documents/Personal/Facultad/Simulacion/tp3SegundoCuatri/Simulacion-tp3
source .venv/bin/activate
streamlit run app.py          # abre http://localhost:8501
```

- Si pregunta un **Email** la primera vez, apretá **Enter**.
- Para frenarlo: **Ctrl + C**. Si se cambió algún `.py` o el tema, frenalo y volvé a correr `streamlit run app.py`.

Desde cero (otra compu o después de clonar):

```bash
git clone https://github.com/ivososa/Simulacion-tp3.git
cd Simulacion-tp3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Otros comandos útiles:

```bash
pytest -v                          # corre los 20 tests
python generar_traza.py <legajo>   # regenera la traza del README con tu legajo
```

### Si en la evaluación me dan datos nuevos

1. **Generadores:** en la barra lateral, abrí "Generador de B" y cargá semilla, a, c y m.
   - Si son **iguales para todos**, tocá **"Copiar parámetros del generador de B a todos"**.
   - Si son **distintos**, abrí cada "Generador de D / E / F" y cargalos por separado.
2. **Probabilidades o valores de B y F:** editá la tabla (doble clic en la celda). Para agregar un valor usá la fila vacía del final; para borrar, seleccioná la fila y usá el tacho. **Las probabilidades tienen que sumar 1**; si no, aparece un error rojo.
3. **Constantes (A, C), uniforme (a, b) y exponencial (media):** cambialas en sus campos. Tiene que cumplirse a < b y media > 0.
4. **Cantidad de iteraciones, filas a mostrar, N observaciones, umbrales, confianza o n del percentil:** en "Simulación" y "Estimadores".
5. Tocá **Simular**. Si un parámetro cambió después de simular, aparece un aviso azul: volvé a tocar Simular.
6. **Si piden una iteración puntual** (por ejemplo, la 50.000): en "Consultar una iteración puntual", cargá k y tocá **Consultar**. Abajo, en "Respuestas a la consigna", elegí "la iteración consultada".
7. **Si piden otra conversión del RND** (X/(m−1) o (X+0.5)/m) o truncar: están en "Simulación".
8. Para verificar a mano, abrí "Traza de las 3 primeras iteraciones".
