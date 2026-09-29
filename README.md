# TP3 Simulación – Proyecto logístico (red de actividades en paralelo)

Simulación de Montecarlo de un pedido online que se procesa en dos ramas paralelas que
convergen en el despacho:

```
Inicio ─┬─ A ── B ──────┐
        │               ├── F ── Fin
        └─ C ── D ── E ─┘
```

Es un modelo **estático**: cada iteración es un proyecto independiente (no hay reloj ni colas).

---

## 1. Cómo correrlo

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py               # abre la interfaz en el navegador
pytest                             # corre los tests
python generar_traza.py 12345      # regenera la traza de la sección 6 con ese legajo
```

| Archivo | Qué tiene |
|---|---|
| `generador.py` | `GeneradorCongruencialMixto` (X → RND, truncado) y `calcular_periodo` |
| `distribuciones.py` | constante, tabla acumulada + discreta, uniforme, exponencial |
| `modelo.py` | `calcular_red` (tiempos, rutas, críticas) y `tiempo_minimo_teorico` |
| `parametros.py` | valores por defecto de la consigna y `validar` |
| `simulacion.py` | el motor: `calcular_fila` (anterior → actual), `simular`, percentil, frecuencias, `traza_primeras_iteraciones` |
| `app.py` | interfaz Streamlit (solo pantallas) |
| `tests/test_simulacion.py` | tests con pytest |

El motor (`generador`, `distribuciones`, `modelo`, `simulacion`) es **Python puro**: no usa
numpy, pandas ni `random`. Todos los números aleatorios salen de nuestro generador.

---

## 2. Variables y parámetros del problema

### Variables de entrada (duración de cada actividad, en minutos)

| Act. | Actividad | Tipo | Distribución por defecto | ¿Consume RND? |
|---|---|---|---|---|
| A | Verificación de pago y stock | constante | 15 | no |
| B | Picking en almacén | **aleatoria discreta** | 20 (0.25) · 30 (0.40) · 40 (0.35) | sí, generador de B |
| C | Impresión de etiqueta y factura | constante | 5 | no |
| D | Preparación de empaque | **aleatoria continua** | Uniforme U[5, 25] | sí, generador de D |
| E | Control de calidad y pesaje | **aleatoria continua** | Exponencial negativa, media 5 | sí, generador de E |
| F | Despacho y carga | **aleatoria discreta** | Libre 15 (0.5) · Ocupado 25 (0.5) | sí, generador de F |

### Parámetros (todos configurables desde la interfaz)

- **Generadores** (uno por variable aleatoria: B, D, E, F): semilla X0, a, c, m. Prueba: 3922, 1221, 1714, m = legajo.
- **Conversión X → RND de cada generador** (D: `X/(m−1)`; B, E y F: `X/m`) y decimales para truncar el RND.
- **Distribuciones**: valor de A y C; tablas valor/probabilidad de B y F (se pueden agregar filas); a y b de D; media de E.
- **Simulación**: cantidad de iteraciones N, desde qué iteración j mostrar, cuántas filas i.
- **Estimadores**: n para el percentil (99), confianza (0.95), umbrales 60 y 90, desplazamiento del último intervalo (90), N observaciones para la distribución de frecuencias.

### Variables calculadas en cada iteración

finA, finB, finC, finD, finE, inicioF, finF, Ruta1, Ruta2, holgura, ruta crítica, 1/0 de crítica por actividad.

---

## 3. Variable objetivo

**T = duración total del proyecto (min)** = momento en que termina F.

---

## 4. Fórmulas

**Generador congruencial mixto** (`generador.py`)

```
X(n+1) = (a · X(n) + c) mod m
```

La semilla X0 **no** es un número aleatorio: el primer RND sale de X1.

**Conversión a RND**: cada generador tiene la suya (configurable desde la interfaz).

| Variable | Conversión | Rango del RND | Por qué |
|---|---|---|---|
| B, F (discretas) | `RND = X / m` | [0, 1) | El RND cae en intervalos `[desde, hasta)` con `hasta ≤ 1` |
| D (uniforme) | `RND = X / (m − 1)` | [0, 1] | El RND puede valer 0 y 1, así D puede tomar los dos extremos de U[a, b] |
| E (exponencial) | `RND = X / m` | [0, 1) | Con RND = 1 sería `ln(1 − 1) = ln(0)`, que no existe |

Otra opción disponible: `(X+0.5)/m` ∈ (0, 1).
Truncado a k decimales: `RND = trunc(RND · 10^k) / 10^k`, calculado con división entera para
evitar errores de redondeo de los float.

**Distribuciones** (`distribuciones.py`)

| Distribución | Fórmula |
|---|---|
| Constante | valor fijo |
| Discreta | tabla de probabilidad acumulada con intervalos `[desde, hasta)`, donde el primer `desde` es 0 y cada `hasta` es la acumulada. Se asigna el valor cuyo intervalo contiene al RND. B: [0, 0.25) → 20 · [0.25, 0.65) → 30 · [0.65, 1) → 40 |
| Uniforme U[a, b] | `D = a + (b − a) · RND` |
| Exponencial (media μ) | `E = −μ · ln(1 − RND)`, con λ = 1/μ |

**Red** (`modelo.calcular_red`)

```
finA = A              finC = C
finB = finA + B       finD = finC + D
                      finE = finD + E
inicioF = max(finB, finE)        ← F necesita que terminen B y E
T = finF = inicioF + F
Ruta1 = A + B + F     Ruta2 = C + D + E + F     T = max(Ruta1, Ruta2)
holgura = |finB − finE|          ← cuánto espera la rama rápida
```

**Actividades críticas** (camino más lento):

- A+B > C+D+E → Ruta 1 crítica → A, B, F
- A+B < C+D+E → Ruta 2 crítica → C, D, E, F
- iguales (diferencia < 1e-9) → empate → las 6 actividades

F es crítica siempre, porque está en las dos rutas.

**Promedio incremental**: `P(n) = ((n − 1) · P(n−1) + valor(n)) / n`

**Probabilidad** = contador / n

**Tiempo mínimo teórico** (simulacro con el mínimo de cada distribución): constante → su valor,
discreta → menor valor, uniforme → a, exponencial → 0.
`Tmin = max(Amin + Bmin, Cmin + Dmin + Emin) + Fmin = max(15+20, 5+5+0) + 15 = 50 min`

**Percentil (método de la cátedra)**: frecuencia acumulada `F(i) = i / (n + 1)`. Se ordenan las
primeras n duraciones y se toma la de posición `i = ceil(confianza · (n + 1))`.
Con n = 99 y 95 %: i = 0.95 · 100 = **95**, o sea la 95ª duración más chica.

**Distribución de frecuencias**: `ancho = 90 / 9 = 10`.
Intervalos `[Tmin + k·ancho, Tmin + (k+1)·ancho)` para k = 0..8, y el último `[Tmin + 90, ∞)`.
Índice de un valor: `k = floor((T − Tmin) / ancho)`, con tope en 9.

---

## 5. Estimadores y cómo se calculan con solo el vector anterior y el actual

Cada fila (`simulacion.calcular_fila`) se arma con la fila anterior y los RND nuevos, y después
`anterior = actual`. La fila 0 tiene todo en 0 y el mínimo en +∞.

| Estimador | En la fila n se calcula como |
|---|---|
| Duración de cada proceso | columnas A…F, Ruta1, Ruta2, T de la fila |
| Promedio de cada actividad, ruta y T | `promedio_incremental(anterior["prom_X"], X, n)` |
| Mínimo / máximo observado | `min(anterior["t_min_obs"], T)` / `max(anterior["t_max_obs"], T)` |
| Proporción crítica de cada actividad | `cont = anterior + (1 si es crítica)` → `cont / n` |
| Proporción Ruta 1 / Ruta 2 / Empate | igual, con un contador por caso |
| P(T ≤ 60) | `cont = anterior + (1 si T ≤ 60)` → `cont / n` |
| P(T ≥ 90) | `cont = anterior + (1 si T ≥ 90)` → `cont / n` |
| Tiempo con 95 % de confianza | se calcula una vez, en la iteración 99, y se arrastra a las filas siguientes |
| Tiempo mínimo teórico | se calcula antes de simular (`modelo.tiempo_minimo_teorico`) |
| Distribución de frecuencias | 10 contadores; en cada iteración se suma 1 al del intervalo de T |

**Qué se guarda además del vector anterior y el actual, y por qué:**

1. Las filas que el usuario pidió **ver** (desde j, i filas) y siempre la última: es solo para mostrarlas.
2. Los **10 contadores** de frecuencias, no los datos.
3. Un **buffer de 99 valores** para el percentil, porque para ordenar hay que tener los valores. Se vacía apenas se usa.
4. Una **muestra de hasta 2.000 puntos** para los gráficos 1 y 2. Es solo visualización y ningún estimador la usa.

**Consultar la iteración k**: se vuelve a simular desde cero hasta k con los mismos parámetros.
Como el generador es determinista, da exactamente la misma fila k (hay un test que lo verifica).

---

## 6. Traza de las 3 primeras iteraciones

<!-- TRAZA:INICIO -->

_Generada con `python generar_traza.py 12345` (semilla 3922, a 1221, c 1714, m = 12345 en los 4 generadores)._

#### Iteración 1

- **B**: X1 = (1221 · 3922 + 1714) mod 12345 = **616** → RND = X/m = **0.0499**
- **D**: X1 = (1221 · 3922 + 1714) mod 12345 = **616** → RND = X/(m-1) = **0.0499**
- **E**: X1 = (1221 · 3922 + 1714) mod 12345 = **616** → RND = X/m = **0.0499**
- **F**: X1 = (1221 · 3922 + 1714) mod 12345 = **616** → RND = X/m = **0.0499**

- A = 15 (constante), C = 5 (constante)
- B: RND 0.0499 cae en la tabla acumulada → **B = 20**
- D = 5 + (25 − 5) · 0.0499 = **5.9981**
- E = −5 · ln(1 − 0.0499) = **0.2559**
- F: RND 0.0499 → montacargas Libre → **F = 15**
- finB = 15 + 20 = 35.0000 ; finE = 5 + 5.9981 + 0.2559 = 11.2540
- inicioF = max(35.0000, 11.2540) = 35.0000 ; **T = 35.0000 + 15 = 50.0000**
- Ruta1 = 50.0000, Ruta2 = 26.2540 → Ruta 1 es la crítica → críticas: A, B, F
- Promedio de T hasta acá = 50.0000

#### Iteración 2

- **B**: X2 = (1221 · 616 + 1714) mod 12345 = **805** → RND = X/m = **0.0652**
- **D**: X2 = (1221 · 616 + 1714) mod 12345 = **805** → RND = X/(m-1) = **0.0652**
- **E**: X2 = (1221 · 616 + 1714) mod 12345 = **805** → RND = X/m = **0.0652**
- **F**: X2 = (1221 · 616 + 1714) mod 12345 = **805** → RND = X/m = **0.0652**

- A = 15 (constante), C = 5 (constante)
- B: RND 0.0652 cae en la tabla acumulada → **B = 20**
- D = 5 + (25 − 5) · 0.0652 = **6.3043**
- E = −5 · ln(1 − 0.0652) = **0.3372**
- F: RND 0.0652 → montacargas Libre → **F = 15**
- finB = 15 + 20 = 35.0000 ; finE = 5 + 6.3043 + 0.3372 = 11.6414
- inicioF = max(35.0000, 11.6414) = 35.0000 ; **T = 35.0000 + 15 = 50.0000**
- Ruta1 = 50.0000, Ruta2 = 26.6414 → Ruta 1 es la crítica → críticas: A, B, F
- Promedio de T hasta acá = 50.0000

#### Iteración 3

- **B**: X3 = (1221 · 805 + 1714) mod 12345 = **9364** → RND = X/m = **0.7585**
- **D**: X3 = (1221 · 805 + 1714) mod 12345 = **9364** → RND = X/(m-1) = **0.7586**
- **E**: X3 = (1221 · 805 + 1714) mod 12345 = **9364** → RND = X/m = **0.7585**
- **F**: X3 = (1221 · 805 + 1714) mod 12345 = **9364** → RND = X/m = **0.7585**

- A = 15 (constante), C = 5 (constante)
- B: RND 0.7585 cae en la tabla acumulada → **B = 40**
- D = 5 + (25 − 5) · 0.7586 = **20.1717**
- E = −5 · ln(1 − 0.7585) = **7.1050**
- F: RND 0.7585 → montacargas Ocupado → **F = 25**
- finB = 15 + 40 = 55.0000 ; finE = 5 + 20.1717 + 7.1050 = 32.2767
- inicioF = max(55.0000, 32.2767) = 55.0000 ; **T = 55.0000 + 25 = 80.0000**
- Ruta1 = 80.0000, Ruta2 = 57.2767 → Ruta 1 es la crítica → críticas: A, B, F
- Promedio de T hasta acá = 60.0000

<!-- TRAZA:FIN -->

---

## 7. Supuestos e interpretaciones (para confirmar con el profe)

1. **Conversión del RND por generador**: D (uniforme continua) usa `X/(m−1)`, así el RND puede valer 0 y 1 y D cubre todo [a, b]. B, F y E usan `X/m` (RND ∈ [0, 1)); en E esto evita ln(0). Con X/m, D llegaría como máximo a b − (b−a)/m (24,9984 con m = 12345); como D es continua, la diferencia no cambia la distribución, pero así se respeta el intervalo cerrado. Se puede cambiar desde la interfaz.
2. **"Tiempo mínimo"** = mínimo teórico con el mínimo de cada distribución (50 min). Se reporta aparte el mínimo observado.
3. **Empate de rutas**: las dos ramas se consideran críticas (las 6 actividades).
4. **Tiempo con 95 % de confianza**: se calcula con las **primeras 99 iteraciones** y `F(i) = i/(n+1)`, que da la posición 95.
5. **Umbrales inclusivos**: "60 o menos" → T ≤ 60; "90 o más" → T ≥ 90.
6. **Distribución de frecuencias**: cuenta las **primeras N** observaciones (N configurable).
7. **Orden de consumo**: cada iteración consume un RND de cada generador, en el orden B, D, E, F.
8. **"Generador diferente para cada uno"**: puede referirse a **cada alumno** (cada uno usa m = su legajo)
   y no a cada variable. La app tiene un generador independiente por variable. Si los 4 se cargan con
   los mismos parámetros (como pasa con los valores de prueba), **generan la misma secuencia**: B, D, E y F
   reciben el mismo RND en cada iteración y quedan correlacionadas (un B alto viene junto con un D y un E
   altos). La app lo avisa con una advertencia, pero **no bloquea** la simulación.
9. **Período del generador**: con a = 1221, c = 1714 y m = 12345, el período real es **2055**, no 12345,
   porque no se cumplen las condiciones de Hull–Dobell (a − 1 = 1220 no es múltiplo de 3 ni de 823, que
   son factores primos de m). En 100.000 iteraciones la secuencia se repite unas 48 veces. La app calcula
   el período real y lo muestra como advertencia.
