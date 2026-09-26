"""
Genera la traza de las 3 primeras iteraciones y la escribe en el README.md,
entre las marcas <!-- TRAZA:INICIO --> y <!-- TRAZA:FIN -->.

Uso:  python generar_traza.py [legajo]      (por defecto, el legajo de ejemplo)
"""
import sys

from parametros import LEGAJO_EJEMPLO, parametros_por_defecto
from simulacion import traza_primeras_iteraciones

INICIO = "<!-- TRAZA:INICIO -->"
FIN = "<!-- TRAZA:FIN -->"

legajo = int(sys.argv[1]) if len(sys.argv) > 1 else LEGAJO_EJEMPLO
traza = traza_primeras_iteraciones(parametros_por_defecto(legajo=legajo), cantidad=3)

with open("README.md", encoding="utf-8") as archivo:
    readme = archivo.read()
antes, resto = readme.split(INICIO)
_, despues = resto.split(FIN)
with open("README.md", "w", encoding="utf-8") as archivo:
    archivo.write(f"{antes}{INICIO}\n\n_Generada con `python generar_traza.py {legajo}` "
                  f"(semilla 3922, a 1221, c 1714, m = {legajo} en los 4 generadores)._\n\n"
                  f"{traza}\n{FIN}{despues}")
print(traza)
