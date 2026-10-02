"""Cuadros específicos del libro "Predio-ganadero" (más allá de Cuadro 1/2,
comunes a los 3 libros de publicación - ver `cuadros/comun.py`).

"Predio-ganadero" = la combinación predio (`CODIGO_SIT`) + documento de
identidad del ganadero (`IDENT_GANADERO`), es decir `predioganid` - DISTINTO
de "predio" solo (físico, `CODIGO_SIT` solo) y de "ganadero" solo
(`IDENT_GANADERO` solo). Confirmado por el usuario (2026-09-21). Los cuadros
de este libro cuentan esa unidad con `peso_predio_ganadero = calruv *
cal_cobertura` (ya en `base_maestra_c1.py`) - NO con `peso_predio_fisico`
(predios físicos, esa es la unidad de "Total predios" en Cuadro 1, la usa
`cal_predios`, y SÍ reconcilia con el "Total Predios PM" de Fedegán).

Fedegán NO tiene ninguna cifra de "predios-ganadero" (pares) contra la cual
reconciliar - su marco mide predios físicos y animales, no relaciones
predio-ganadero (confirmado por el usuario: "no tengo la información para
reconciliar contra Fedegán" esa unidad). Por eso los cuadros de este libro
NO se validan contra Fedegán (a diferencia de Cuadro 1 "Total predios",
Cuadro 3/7 de inventario, etc.) - su validación es de consistencia interna
únicamente (vertical/horizontal, ver `validacion_estructura_cuadros.py`).

Cuadro 3 - "Cantidad de predios ganaderos, por inventario ganadero bovino o
bufalino": categorías confirmadas contra `Programas Carolina/4.3. cuadros
predio ganadero.sas` (líneas 757-786, leído como referencia de metodología en
`/s/02Programas`) - `count(distinct predioganid) * calruv * cal_cobertura`
(= `peso_predio_ganadero`) agrupado por si el predio tiene inventario bovino
(`TOTAL_AFT_BOV > 0` o `TOTAL_AFT_BOV_NV > 0`) y/o bufalino
(`TOTAL_AFT_BUF > 0` o `TOTAL_AFT_BUF_NV > 0`) - 3 categorías MUTUAMENTE
EXCLUYENTES ("con bovinos" = bovino Y NO bufalino, "con bufalinos" =
bufalino Y NO bovino, "con bovinos y bufalinos" = ambos), verificado con
datos reales que todo predio-ganadero tiene al menos una de las 2 especies
(0 filas sin ninguna) - la partición es exhaustiva, por eso sí se declara
`columnas_totales`. `TOTAL_AFT_BUF`/`TOTAL_AFT_BUF_NV` no estaban cargadas en
`base_maestra_c1` (solo `TOTAL_AFT_BOV` vía `_COLS_ID`) - se agregaron para
este cuadro.

Cuadro 4 - "Cantidad de predios ganaderos según la principal orientación del
hato" (pregunta encuesta "7. ¿Cuál es la principal orientación de su hato
ganadero (actividad principal)?" - `orientacionhato`, ya en `base_maestra_c1`,
normalizada). Sin redistribución proporcional (a diferencia de Cuadro 4/5 del
libro de inventario, que sí la necesitan): verificado que `orientacionhato`
NO tiene filas en blanco en `base_maestra_c1` (100% de los predio-ganadero
reportan una orientación), así que una simple agrupación por categoría ya es
exhaustiva - no hace falta `redistribucion.redistribuir_por_categoria`.
`total_predios_ganaderos` NO se deriva como suma de las 6 orientaciones (por
la misma razón que en Cuadro 3: debe coincidir exacto con Cuadro 1/3, que lo
redondean de forma independiente - ver `validacion_estructura_cuadros.py`,
`_comparaciones_cruzadas`).

Encontrado en el camino a este cuadro (2026-09-21): `orientacionhato` venía
con TODAS sus tildes corrompidas por un bug de codificación en
`fuente_cruda_c1.py` (`encoding="latin1"` en vez de `"utf-8"`) - esto rompía en
silencio la comparación de texto exacto contra las categorías en
`redistribucion.py`, dejando en CERO las 4 categorías con tilde (Leche/
Cría/Doble propósito/Genética) del Cuadro 4/5 YA PUBLICADO del libro de
inventario (~84% del inventario bovino desaparecía de esos cuadros). Corregido
en `fuente_cruda_c1.py` (ver ese módulo) y todo el pipeline C1 reconstruido y
revalidado antes de seguir con este cuadro.

Cuadro 5 - "Cantidad de predios ganaderos según la cantidad de personas que
trabajaron en la actividad ganadera en el predio ganadero" (`canttrabaj`, sin
nulos). La plantilla real solo trae 2 encabezados de ejemplo con texto
literal "XXX hasta XXXX" (columnas F-G) + una nota pidiendo un análisis de
frecuencia para definir los rangos - PERO el formato de celda (bordes,
`number_format`) del bloque de datos real llega hasta la columna M: la
plantilla reserva 8 clases (E=Total + F..M), no 2 (detectado 2026-09-22 al
inspeccionar bordes/formato, no solo texto - la primera versión de este
cuadro usó por error solo 2 clases).

Definición de las 8 clases (CONFIRMADA por el usuario 2026-09-22): se evaluó
la regla de Sturges (k = 1 + log2(n) ≈ 20.5 clases) sobre el rango completo
de `canttrabaj` (0 a 2211) y resultó inútil - un ancho de clase de ~110
unidades, cuando 89.67% de los predios reporta ≤2 trabajadores y el máximo es
un outlier extremo (hay un clúster de valores redondos sospechosos - 1500
repetido decenas de veces, más 1700/1900/2000/2211 - probable error de
captura, no cifras reales de campo). Sturges asume una distribución más o
menos simétrica; para un conteo tan sesgado a la derecha no es la
herramienta correcta para fijar el ANCHO de las clases (si acaso, informa
que se quieren MUCHAS clases en el cuerpo denso de la distribución). En su
lugar, con las 8 clases disponibles en la plantilla, se usaron quiebres
naturales de la frecuencia acumulada real: 0 (2.91%) / 1 (66.10% acum.) / 2
(89.67% acum.) / 3 (95.42% acum.) / "4 a 5" (98.31% acum.) / "6 a 10"
(99.62% acum.) / "11 a 20" (99.90% acum.) / "21 o más" (100%, cola abierta
que absorbe el outlier extremo sin distorsionar las demás clases) - cada
clase queda con una frecuencia no despreciable (ninguna vacía ni casi vacía),
con más resolución donde la distribución tiene más masa (0/1/2/3 cada uno en
su propia columna, que juntos son 95.4% de los datos) y clases más anchas en
la cola dispersa.

Cuadro 6 - "Cantidad de predios ganaderos según el sistema productivo
implementado en el predio ganadero, sexo del ganadero y persona jurídica"
(pregunta "11. ¿Cuál es el sistema productivo que tiene implementado en el
predio?" - `sistemaproductivo`, ya normalizada en `base_maestra_c1`, 4 categorías
exhaustivas y sin nulos, mismo catálogo que Cuadro 6 del libro de inventario -
ver `SISTEMA_PRODUCTIVO_ORDEN`/`_SISTEMA_SLUG` en `cuadros/inventario.py`).
Sexo/persona jurídica usa la columna `genero` ya normalizada
("Mujer"/"Hombre"/`config.GENERO_JURIDICA`, sin nulos - mismo criterio que
Cuadro 3 del libro ganadero). Estructura por cada uno de los 4 bloques de
sistema productivo: Total = Persona natural (Total = Hombres + Mujeres) +
Persona jurídica - estas SÍ se derivan con `columnas_totales` porque son
subtotales que solo existen dentro de este cuadro (no se reportan en ningún
otro). `total_predios_ganaderos` (columna E) NO se deriva como suma de los 4
bloques de sistema productivo - mismo criterio que Cuadro 3/4/5: debe
coincidir exacto con Cuadro 1 (ver `validacion_estructura_cuadros.py`,
`_comparaciones_cruzadas`).

Cuadro 7 - "Cantidad de predios ganaderos, por sistema de producción y
principal orientación del hato": cruce de las 2 variables de Cuadro 4
(`orientacionhato`) y Cuadro 6 (`sistemaproductivo`). Estructura: 1 bloque
"Total" (todas las orientaciones, desglosado en los 4 sistemas productivos) +
6 bloques de orientación (Leche/Cría/Ceba/Levante/Doble propósito/Genética),
cada uno con su propia columna "Total predios ganaderos" desglosada en los 4
sistemas productivos. Tanto la columna "Total predios ganaderos" del bloque
"Total" (debe coincidir con Cuadro 1/3/4/5/6) como la de cada bloque de
orientación (debe coincidir con la columna correspondiente de Cuadro 4) son
valores INDEPENDIENTES - no se derivan como suma de sus 4 columnas de sistema
productivo, mismo criterio de consistencia entre cuadros que el resto del
libro.

Cuadro 8 - "Cantidad de predios ganaderos, por sexo del ganadero y persona
jurídica y sistema de producción": mismo patrón que Cuadro 7, pero cruzando
`genero` (en vez de `orientacionhato`) con `sistemaproductivo`. Estructura: 1
bloque "Total" (todos los géneros, por sistema productivo) + 3 bloques de
género/persona jurídica (Hombre/Mujer/`config.GENERO_JURIDICA`), cada uno con
su propia columna "Total predios ganaderos" desglosada en los 4 sistemas
productivos. Todas las columnas "Total predios ganaderos" (bloque "Total" y
los 3 bloques de género) son valores INDEPENDIENTES, no derivados como suma
de sus 4 columnas de sistema productivo - la del bloque "Total" coincide con
Cuadro 1/3/4/5/6/7; las de los 3 bloques de género no tienen equivalente en
ningún otro cuadro ya construido (Cuadro 6 solo reporta género DENTRO de cada
bloque de sistema productivo, no como total agregado), así que no hay
comparación cruzada adicional que agregar para ellas.

Cuadro 9 - "Cantidad de predios ganaderos por sexo del ganadero, condición
jurídica y principal orientación del hato": mismo patrón que Cuadro 7/8, pero
cruzando `genero` con `orientacionhato` (en vez de `sistemaproductivo`).
Estructura: 1 columna "Total predios ganaderos" (general, columna E) + 3
bloques de género/persona jurídica en el orden de la plantilla real
(Mujeres, Hombres, Persona jurídica - distinto del orden usado en Cuadro 8),
cada uno con su propia columna "Total predios ganaderos" desglosada en las 6
orientaciones. La columna E es independiente (coincide con Cuadro
1/3/4/5/6/7/8); la columna "Total" de cada uno de los 3 bloques de género
TAMBIÉN es independiente, y coincide exacto con la columna equivalente de
Cuadro 8 (`{genero}_total`) - MISMA cantidad real (predios-ganadero por sexo/
persona jurídica, sin cruzar con ninguna otra variable), calculada dos veces
con el mismo filtro. A diferencia de Cuadro 7/8, esta plantilla SÍ trae un
bloque "Segundo ciclo" (columnas AA en adelante) - queda pendiente por la
misma razón que Cuadro 4/5 del libro ganadero (no existe aún el equivalente
de `base_maestra_c1` para Ciclo 2 en este libro); solo se construyen las
columnas E-Z (Primer ciclo).

Cuadro 10 - "Cantidad de predios ganaderos por tenencia del predio y tipo de
sistema productivo": mismo patrón que Cuadro 7/8 (columna "Total" general + N
bloques, cada uno con su propio "Total" desglosado en los 4 sistemas
productivos), cruzando `PREDIO_CARGO` (tenencia, `TENENCIA_ORDEN`/
`_TENENCIA_SLUG` reutilizados de `cuadros/ganadero.py` - mismo catálogo y
orden que su Cuadro 8, ya confirmado contra la plantilla real de ese libro)
con `sistemaproductivo`. 6 bloques de tenencia (Propio/Arrendado/Poseedor/
Tenedor/Territorio colectivo/Otro). La columna "Total predios ganaderos"
general (E) es independiente (coincide con Cuadro 1/.../9); las 6 columnas
"Total" de cada bloque de tenencia coinciden exacto con la columna
equivalente de Cuadro 11 (`{tenencia}_total` en ese cuadro - MISMA cantidad
real, predios-ganadero por tenencia sin cruzar con sistema productivo,
calculada dos veces con el mismo filtro).

Cuadro 11 - "Cantidad de predios ganaderos por tenencia del predio": columna
"Total predios ganaderos" (E) + 6 columnas de tenencia (F-K, MISMO orden que
Cuadro 10 - Propio/Arrendado/Poseedor/Tenedor/Territorio colectivo/Otro), sin
cruce con ninguna otra variable. Tanto E como cada una de las 6 columnas de
tenencia son valores INDEPENDIENTES: E coincide con Cuadro 1/.../10; cada
columna de tenencia coincide exacto con la columna `{tenencia}_total`
correspondiente de Cuadro 10 (ver arriba). La plantilla SÍ trae un bloque
"Segundo ciclo" (columnas L-R) - queda pendiente, mismo criterio que
Cuadro 9; solo se construyen las columnas E-K (Primer ciclo).

Cuadro 12 - "Cantidad de predios ganaderos por tenencia del predio y
principal orientación del hato": mismo patrón que Cuadro 7/8/10 (columna
"Total" general + 6 bloques de tenencia, cada uno con su propio "Total"
desglosado en las 6 orientaciones - cruce tenencia x orientación, en vez de
tenencia x sistema productivo como Cuadro 10). La columna "Total predios
ganaderos" general (E) es independiente (coincide con Cuadro 1/.../11); la
columna "Total" de cada uno de los 6 bloques de tenencia coincide exacto con
la columna equivalente de Cuadro 11 (misma cantidad real, predios-ganadero
por tenencia sin cruzar con otra variable). Igual que Cuadro 9/11, la
plantilla trae un bloque "Segundo ciclo" (columnas AV en adelante) que queda
pendiente; solo se construyen las columnas E-AU (Primer ciclo).

Cuadro 13 - "Cantidad de predios ganaderos por número de niños que residen
permanentemente en el predio ganadero" (pregunta "¿Cuántos menores de 18
años viven permanentemente en el predio ganadero? ____ No sabe/no
responde" - columna cruda `menores18`, numérica, agregada a `base_maestra_c1`
para este cuadro). Rangos tomados literal de la plantilla real (0 / "1-5" /
"6-10" / "11-15" / "16-20" / "20-50" / "> 50" / "No sabe/no responde") - la
plantilla trae una nota ("Verificar los rangos de edad...") que señala que
este bloque de opciones puede venir de otra pregunta y debería revisarse con
DANE, pero SÍ trae rangos numéricos ya definidos (a diferencia de Cuadro 5,
que traía placeholders "XXX hasta XXXX" sin ningún valor) - se construyen tal
cual están escritos, documentando la advertencia acá. Los rangos "16-20" y
"20-50" se solapan literalmente en 20 (probable error de tipeo) - se
interpreta el segundo como "21-50" para que la partición sea exhaustiva y sin
traslape. 26.3% de los predios-ganadero tiene `menores18` en blanco en la
base cruda - igual que Cuadro 12 del libro ganadero, se fusiona con la
categoría "No sabe/no responde" (la pregunta ya ofrece esa opción de
respuesta explícita, decisión confirmada por el usuario para ese cuadro y
reutilizada acá con el mismo criterio).

Cuadro 14 - "Cantidad de predios ganaderos con colmenas y número total de
colmenas" (preguntas "¿Tiene colmenas de abejas actualmente en su predio?" -
`tienecolmenas`, Si/No, SIN blancos en la base cruda - y "¿Cuál es el número
de colmenas?" - `numcolmenas`, solo diligenciada cuando `tienecolmenas` = Si).
Estructura: E = total general (independiente, coincide con Cuadro 1/.../13);
F = total con colmenas (`tienecolmenas` = Si, columna independiente, sin
equivalente en otro cuadro de este libro); G-L = cantidad de colmenas en 6
rangos (0/"1-10"/"11-30"/"30-50"/"> 50"/"No sabe/No responde") sobre un valor
"efectivo" que vale 0 para quien respondió `tienecolmenas` = No (no tiene
colmenas) y el valor real de `numcolmenas` para quien respondió Si - así G-L
es una partición exhaustiva de TODOS los predios-ganadero (no solo los que
tienen colmenas), igual que el header "0" en G7 sugiere. Mismo tratamiento
que Cuadro 13 para el traslape "11-30"/"30-50" en la plantilla (se interpreta
el segundo como "31-50"). "No sabe/No responde" queda casi vacío en la
práctica (solo captura el caso residual `tienecolmenas` = Si sin
`numcolmenas` diligenciado, 0 casos verificados en el ciclo actual).

Cuadro 3 a 14: SOLO Ciclo 1 (verificado 2026-09-21: la plantilla real de
Cuadro 15-19 los marca explícitamente como "Segundo ciclo nacional de
vacunación de 2025" - a diferencia de Cuadro 3-14, "Primer ciclo" o "Primer y
Segundo ciclo" - y NINGUNA columna cruda relacionada existe en
`ciclo1encuesta.sas7bdat`: son preguntas nuevas del cuestionario de Ciclo 2,
no un bloque adicional de una pregunta ya existente en Ciclo 1).

Cuadro 15 - "Cantidad de predios ganaderos, por tipo de cobertura existente
en el predio ganadero y área (ha)" (pregunta "11.1. De las ___ de esta finca,
indique la cantidad de terreno utilizada en: 11.1.1. Actividades agrícolas /
11.1.2. Producción de animales / 11.1.3. Plantaciones forestales / 11.1.4.
Construcciones para animales / 11.1.5. Otros usos"). Estructura: E = total
general (independiente) + 5 bloques (uno por tipo de cobertura), cada uno con
2 columnas: "Total predios" (predios con esa cobertura > 0, EN CUALQUIER
UNIDAD - es un conteo de predios, no una suma de área) y "Hectáreas" (ver
`_area_en_hectareas` para la conversión de unidad).

Cuadro 16 - "Cantidad de predios ganaderos por área destinada a ganadería
bovina o bufalina" (pregunta 12, subconjunto de la pregunta 11.1.2 - "De las
___ del terreno dedicado a la producción de animales, ¿cuál es la cantidad
usada para ganadería bovina o bufalina?"). E = total general + F = predios
con área de producción de animales > 0 + G = hectáreas dedicadas a
producción de animales + H = hectáreas destinadas a ganadería bovina/bufalina
(subconjunto de G, NO de la finca completa).

Cuadro 15/16 - CONVERSIÓN DE UNIDAD (decisión confirmada por el usuario,
2026-09-23): la pregunta de área permite 3 unidades (`unidadmedidaarea`) -
"Hectáreas" (86.8% de los predios), "Metros cuadrados" (1.1%, se divide entre
10.000) y **"Fanegadas o Plaza o Cuadra"** (12.0%, 85.856 predios) - esta
última mezcla 3 unidades tradicionales colombianas DISTINTAS que varían por
región (fanegada/plaza/cuadra), sin un factor de conversión único y correcto.
Se decidió NO inventar un factor aproximado: esos predios SÍ cuentan en
"Total predios" (con área > 0 en su unidad original, cualquiera que sea) pero
su área NO se suma a ninguna columna en hectáreas (`_area_en_hectareas`
devuelve `NaN` para ellos, excluidos de la suma). Los valores de área además
vienen con coma decimal ("0,5") en vez de punto - `_parsear_area` lo
normaliza antes de convertir a número.

Cuadro 17 - "Cantidad de predios ganaderos ubicados dentro de un área
protegida" (pregunta "17. ¿Sabe si su predio ganadero se encuentra ubicado
dentro de un área protegida...? 1. Sí 2. No 3. No sabe/no responde" -
`areaprotegida`). E = total general + F/G/H = Sí/No/No sabe-no responde.
Misma corrección de tilde que `cuadros/ganadero.py` (`_filtro_valor`
reutilizado, ver ese módulo): la respuesta afirmativa en Ciclo 2 es
mayoritariamente "Sí" con tilde, no "Si".

Cuadro 18 - "Cantidad de predios ganaderos por razas puras o cruces"
(pregunta "8. Las razas del hato de este predio son:" - opción múltiple,
`tienerazapura`/`tienerazacruce`, flags "Puras"/"Cruces" o `NaN`, NO son
"Si"/"No" literales). E = total general + F = con razas puras
(`tienerazapura` no nulo) + G = con razas de cruces (`tienerazacruce` no
nulo) - NO mutuamente excluyentes (un predio puede tener ambas), sin
`columnas_totales` para F/G frente a E, mismo criterio que el resto del
libro.

Cuadro 19 - "Cantidad de predios ganaderos por tipo de raza pura o cruce
predominante" (preguntas 8.1/8.2 - `razapurapredominante`/
`razacrucepredominante`, texto libre de selección única contra una lista
oficial de 57 razas puras + 29 cruces = 86 categorías en la plantilla real).
Ver `generar_cuadro19` para el detalle de cómo se validó cada categoría
contra el texto real de respuesta antes de mapear (no se asume que el texto
de la encuesta coincide exacto con el de la plantilla).
"""
from __future__ import annotations

import pandas as pd

from .. import agregador, base_maestra_c1, base_maestra_c2, config
from .ganadero import TENENCIA_ORDEN, _TENENCIA_SLUG, _filtro_valor

_RUTA_BASE_MAESTRA = {"C1": base_maestra_c1.RUTA_BASE_MAESTRA_C1, "C2": base_maestra_c2.RUTA_BASE_MAESTRA_C2}


def _leer_maestra(ciclo: str) -> pd.DataFrame:
    return pd.read_parquet(_RUTA_BASE_MAESTRA[ciclo])


def generar_cuadro3(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    maestra = _leer_maestra(ciclo)
    tiene_bov = (maestra["TOTAL_AFT_BOV"].fillna(0) > 0) | (maestra["TOTAL_AFT_BOV_NV"].fillna(0) > 0)
    tiene_buf = (maestra["TOTAL_AFT_BUF"].fillna(0) > 0) | (maestra["TOTAL_AFT_BUF_NV"].fillna(0) > 0)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    for col, filtro in [
        ("con_bovinos", tiene_bov & ~tiene_buf),
        ("con_bufalinos", tiene_buf & ~tiene_bov),
        ("con_ambos", tiene_bov & tiene_buf),
    ]:
        sub = (
            maestra[filtro]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
    for c in ("con_bovinos", "con_bufalinos", "con_ambos"):
        agg[c] = agg[c].fillna(0.0)

    value_cols = ["total_predios_ganaderos", "con_bovinos", "con_bufalinos", "con_ambos"]
    # "total_predios_ganaderos" NO se declara `columnas_totales`: si se
    # derivara directo como suma de sus 3 categorías (ya redondeadas), el
    # redondeo de ESTE cuadro seguiría un camino distinto al de Cuadro 1 (que
    # redondea "total_predios_ganaderos" directo, sin categorías) para la
    # MISMA cantidad real - eso rompía la coincidencia entre cuadros (744.821
    # vs 744.832, detectado por el usuario). En vez de eso, se deja
    # "total_predios_ganaderos" como valor independiente (coincide exacto con
    # Cuadro 1 por construcción) y se ajustan las 3 categorías DESPUÉS con
    # `agregador.forzar_suma_exacta` para que sumen exacto ese mismo total -
    # las 3 categorías SÍ son una partición mutuamente excluyente y
    # exhaustiva (ver docstring del módulo), a diferencia de con_puras/
    # con_cruces en Cuadro 18, así que acá SÍ debe cumplirse la suma (a
    # pedido del usuario, 2026-10-02, tras detectar el residuo: +28 a nivel
    # nacional, 0.0038%).
    tabla = agregador.generar_cuadro(agg, value_cols)
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", ["con_bovinos", "con_bufalinos", "con_ambos"])
    return tabla, value_cols


ORIENTACIONES_ORDEN = ["Ganadería de Leche", "Cría", "Ceba", "Levante", "Doble propósito", "Genética"]
_ORIENTACION_SLUG = {
    "Ganadería de Leche": "leche",
    "Cría": "cria",
    "Ceba": "ceba",
    "Levante": "levante",
    "Doble propósito": "doble_proposito",
    "Genética": "genetica",
}


def generar_cuadro4(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    maestra = _leer_maestra(ciclo)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    cols_orientacion = []
    for orientacion in ORIENTACIONES_ORDEN:
        col = _ORIENTACION_SLUG[orientacion]
        cols_orientacion.append(col)
        sub = (
            maestra[maestra["orientacionhato"] == orientacion]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
    for c in cols_orientacion:
        agg[c] = agg[c].fillna(0.0)

    value_cols = ["total_predios_ganaderos"] + cols_orientacion
    # "total_predios_ganaderos" independiente (coincide con Cuadro 1/3), las
    # 6 orientaciones se ajustan DESPUÉS para sumar exacto ese total - mismo
    # criterio que Cuadro 3 (ver docstring del módulo y de
    # `agregador.forzar_suma_exacta`); `orientacionhato` es exhaustiva y sin
    # blancos (ver docstring del módulo), partición válida para esto.
    tabla = agregador.generar_cuadro(agg, value_cols)
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_orientacion)
    return tabla, value_cols


CLASES_CUADRO5 = [
    ("0", lambda x: x == 0),
    ("1", lambda x: x == 1),
    ("2", lambda x: x == 2),
    ("3", lambda x: x == 3),
    ("4_a_5", lambda x: x.between(4, 5)),
    ("6_a_10", lambda x: x.between(6, 10)),
    ("11_a_20", lambda x: x.between(11, 20)),
    ("21_o_mas", lambda x: x > 20),
]


def generar_cuadro5() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 5 - ver docstring del módulo: 8 clases de `canttrabaj` (0/1/2/3/
    4-5/6-10/11-20/21+), quiebres naturales de la frecuencia acumulada real,
    confirmados por el usuario (2026-09-22)."""
    maestra = pd.read_parquet(base_maestra_c1.RUTA_BASE_MAESTRA_C1)
    x = maestra["canttrabaj"]

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    cols_clase = []
    for col, filtro_fn in CLASES_CUADRO5:
        cols_clase.append(col)
        sub = (
            maestra[filtro_fn(x)]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
    for c in cols_clase:
        agg[c] = agg[c].fillna(0.0)

    value_cols = ["total_predios_ganaderos"] + cols_clase
    # "total_predios_ganaderos" independiente (coincide con Cuadro 1/3/4),
    # las 8 clases (partición exhaustiva de `canttrabaj`, sin nulos) se
    # ajustan DESPUÉS para sumar exacto ese total - ver docstring del módulo
    # y de `agregador.forzar_suma_exacta`.
    tabla = agregador.generar_cuadro(agg, value_cols)
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_clase)
    return tabla, value_cols


SISTEMAS_PRODUCTIVOS_ORDEN = ["Pastoreo mejorado", "Pastoreo extractivo", "Estabulado", "Silvopastoril"]
_SISTEMA_SLUG = {
    "Pastoreo mejorado": "pastoreo_mejorado",
    "Pastoreo extractivo": "pastoreo_extractivo",
    "Estabulado": "estabulado",
    "Silvopastoril": "silvopastoril",
}
_GENERO_PREFIJO = [("h", "Hombre"), ("m", "Mujer"), ("j", config.GENERO_JURIDICA)]


def generar_cuadro6() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 6 - ver docstring del módulo. 4 bloques de sistema productivo,
    cada uno con Total/Persona natural (Total/Hombres/Mujeres)/Persona
    jurídica."""
    maestra = pd.read_parquet(base_maestra_c1.RUTA_BASE_MAESTRA_C1)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )

    value_cols = ["total_predios_ganaderos"]
    columnas_totales: dict[str, list[str]] = {}
    for sistema in SISTEMAS_PRODUCTIVOS_ORDEN:
        slug = _SISTEMA_SLUG[sistema]
        subset = maestra[maestra["sistemaproductivo"] == sistema]
        cols_genero = []
        for prefijo, genero in _GENERO_PREFIJO:
            col = f"{slug}_{prefijo}"
            cols_genero.append(col)
            sub = (
                subset[subset["genero"] == genero]
                .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
                .sum()
                .rename(columns={"peso_predio_ganadero": col})
            )
            agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
        for c in cols_genero:
            agg[c] = agg[c].fillna(0.0)

        col_h, col_m, col_j = (f"{slug}_h", f"{slug}_m", f"{slug}_j")
        col_natural = f"{slug}_natural"
        col_total = f"{slug}_total"
        agg[col_natural] = agg[col_h] + agg[col_m]
        agg[col_total] = agg[col_natural] + agg[col_j]

        value_cols += [col_total, col_natural, col_h, col_m, col_j]
        columnas_totales[col_natural] = [col_h, col_m]
        columnas_totales[col_total] = [col_natural, col_j]

    # "total_predios_ganaderos" independiente (NO en `columnas_totales`,
    # coincide con Cuadro 1/3/4/5) - los 4 "{sistema}_total" (partición
    # exhaustiva de `sistemaproductivo`, sin nulos) se ajustan DESPUÉS para
    # sumar exacto ese total, ver docstring del módulo y de
    # `agregador.forzar_suma_exacta`. OJO: el sistema que absorbe el residuo
    # en cada fila queda con su propio "{sistema}_natural"/"_h"/"_m"/"_j" ya
    # NO exactamente consistente con su "{sistema}_total" ajustado (mismo
    # tipo de trade-off ya aceptado en "Doble propósito" de Cuadro 4/5 del
    # libro inventario) - no se puede satisfacer simultáneamente "Total =
    # suma de los 4 sistemas" Y "cada sistema internamente consistente" con
    # redondeo entero simple.
    tabla = agregador.generar_cuadro(agg, value_cols, columnas_totales=columnas_totales)
    cols_sistema_total = [f"{_SISTEMA_SLUG[s]}_total" for s in SISTEMAS_PRODUCTIVOS_ORDEN]
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_sistema_total)
    return tabla, value_cols


def generar_cuadro7() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 7 - ver docstring del módulo. Bloque "Total" (por sistema
    productivo) + 6 bloques de orientación (cada uno por sistema
    productivo)."""
    maestra = pd.read_parquet(base_maestra_c1.RUTA_BASE_MAESTRA_C1)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    value_cols = ["total_predios_ganaderos"]

    # Bloque "Total" (todas las orientaciones), por sistema productivo.
    for sistema in SISTEMAS_PRODUCTIVOS_ORDEN:
        col = f"total_{_SISTEMA_SLUG[sistema]}"
        sub = (
            maestra[maestra["sistemaproductivo"] == sistema]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
        agg[col] = agg[col].fillna(0.0)
        value_cols.append(col)

    # 6 bloques de orientación: total independiente (coincide con Cuadro 4) +
    # desglose por sistema productivo.
    for orientacion in ORIENTACIONES_ORDEN:
        oslug = _ORIENTACION_SLUG[orientacion]
        subset_orient = maestra[maestra["orientacionhato"] == orientacion]
        col_total_orient = f"{oslug}_total"
        sub = (
            subset_orient.groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col_total_orient})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
        agg[col_total_orient] = agg[col_total_orient].fillna(0.0)
        value_cols.append(col_total_orient)

        for sistema in SISTEMAS_PRODUCTIVOS_ORDEN:
            col = f"{oslug}_{_SISTEMA_SLUG[sistema]}"
            sub2 = (
                subset_orient[subset_orient["sistemaproductivo"] == sistema]
                .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
                .sum()
                .rename(columns={"peso_predio_ganadero": col})
            )
            agg = agg.merge(sub2, on="CODIGO_MUNICIPIO", how="left")
            agg[col] = agg[col].fillna(0.0)
            value_cols.append(col)

    # "total_predios_ganaderos" (bloque "Total") y los 6 "{orientacion}_total"
    # quedan como valores independientes (coinciden exacto con Cuadro
    # 1/3/4/5/6 y Cuadro 4 respectivamente, ver docstring del módulo) - NO se
    # declaran `columnas_totales`. En su lugar, se ajustan DESPUÉS con
    # `agregador.forzar_suma_exacta` para que: (a) "total_predios_ganaderos"
    # = suma de los 4 "total_{sistema}" (margen de sistema productivo), (b)
    # "total_predios_ganaderos" = suma de los 6 "{orientacion}_total" (margen
    # de orientación), y (c) cada "{orientacion}_total" = suma de sus 4
    # columnas de sistema productivo (identidad interna de cada bloque) -
    # `sistemaproductivo` y `orientacionhato` son particiones exhaustivas sin
    # nulos (ver docstring del módulo), válidas para esto. Igual que en
    # Cuadro 6, el bloque que absorbe el residuo en cada ajuste puede quedar
    # con una pequeña inconsistencia interna propia - trade-off ya aceptado.
    tabla = agregador.generar_cuadro(agg, value_cols)
    cols_sistema_total = [f"total_{_SISTEMA_SLUG[s]}" for s in SISTEMAS_PRODUCTIVOS_ORDEN]
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_sistema_total)
    cols_orientacion_total = [f"{_ORIENTACION_SLUG[o]}_total" for o in ORIENTACIONES_ORDEN]
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_orientacion_total)
    for orientacion in ORIENTACIONES_ORDEN:
        oslug = _ORIENTACION_SLUG[orientacion]
        cols_bloque = [f"{oslug}_{_SISTEMA_SLUG[s]}" for s in SISTEMAS_PRODUCTIVOS_ORDEN]
        agregador.forzar_suma_exacta(tabla, f"{oslug}_total", cols_bloque)
    return tabla, value_cols


_GENERO_BLOQUE_ORDEN = ["Hombre", "Mujer", config.GENERO_JURIDICA]
_GENERO_BLOQUE_SLUG = {"Hombre": "hombre", "Mujer": "mujer", config.GENERO_JURIDICA: "juridica"}


def generar_cuadro8() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 8 - ver docstring del módulo. Bloque "Total" (por sistema
    productivo) + 3 bloques de sexo/persona jurídica (cada uno por sistema
    productivo)."""
    maestra = pd.read_parquet(base_maestra_c1.RUTA_BASE_MAESTRA_C1)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    value_cols = ["total_predios_ganaderos"]

    # Bloque "Total" (todos los géneros), por sistema productivo.
    for sistema in SISTEMAS_PRODUCTIVOS_ORDEN:
        col = f"total_{_SISTEMA_SLUG[sistema]}"
        sub = (
            maestra[maestra["sistemaproductivo"] == sistema]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
        agg[col] = agg[col].fillna(0.0)
        value_cols.append(col)

    # 3 bloques de sexo/persona jurídica: total independiente + desglose por
    # sistema productivo.
    for genero in _GENERO_BLOQUE_ORDEN:
        gslug = _GENERO_BLOQUE_SLUG[genero]
        subset_gen = maestra[maestra["genero"] == genero]
        col_total_gen = f"{gslug}_total"
        sub = (
            subset_gen.groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col_total_gen})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
        agg[col_total_gen] = agg[col_total_gen].fillna(0.0)
        value_cols.append(col_total_gen)

        for sistema in SISTEMAS_PRODUCTIVOS_ORDEN:
            col = f"{gslug}_{_SISTEMA_SLUG[sistema]}"
            sub2 = (
                subset_gen[subset_gen["sistemaproductivo"] == sistema]
                .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
                .sum()
                .rename(columns={"peso_predio_ganadero": col})
            )
            agg = agg.merge(sub2, on="CODIGO_MUNICIPIO", how="left")
            agg[col] = agg[col].fillna(0.0)
            value_cols.append(col)

    # Mismo criterio que Cuadro 7 (ver docstring del módulo y de
    # `agregador.forzar_suma_exacta`): "total_predios_ganaderos" y los 3
    # "{genero}_total" quedan independientes, ajustados después para que
    # las sumas (margen de sistema, margen de género, y cada bloque de
    # género internamente) coincidan exacto.
    tabla = agregador.generar_cuadro(agg, value_cols)
    cols_sistema_total = [f"total_{_SISTEMA_SLUG[s]}" for s in SISTEMAS_PRODUCTIVOS_ORDEN]
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_sistema_total)
    cols_genero_total = [f"{_GENERO_BLOQUE_SLUG[g]}_total" for g in _GENERO_BLOQUE_ORDEN]
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_genero_total)
    for genero in _GENERO_BLOQUE_ORDEN:
        gslug = _GENERO_BLOQUE_SLUG[genero]
        cols_bloque = [f"{gslug}_{_SISTEMA_SLUG[s]}" for s in SISTEMAS_PRODUCTIVOS_ORDEN]
        agregador.forzar_suma_exacta(tabla, f"{gslug}_total", cols_bloque)
    return tabla, value_cols


# Orden de bloques de género en la plantilla del Cuadro 9 (Mujeres, Hombres,
# Persona jurídica) - DISTINTO del orden en Cuadro 8 (Hombre, Mujer,
# jurídica), ver plantilla real.
_GENERO_ORDEN_CUADRO9 = ["Mujer", "Hombre", config.GENERO_JURIDICA]


def generar_cuadro9(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 9 - ver docstring del módulo. Columna "Total" general + 3
    bloques de sexo/persona jurídica (cada uno por orientación del hato).
    `ciclo="C1"` llena E-Z, `ciclo="C2"` llena AA-AS (mismas 2 preguntas -
    `genero`/`orientacionhato` - sí existen en Ciclo 2, ver `base_maestra_c2.py`)."""
    maestra = _leer_maestra(ciclo)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    value_cols = ["total_predios_ganaderos"]

    for genero in _GENERO_ORDEN_CUADRO9:
        gslug = _GENERO_BLOQUE_SLUG[genero]
        subset_gen = maestra[maestra["genero"] == genero]
        col_total_gen = f"{gslug}_total"
        sub = (
            subset_gen.groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col_total_gen})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
        agg[col_total_gen] = agg[col_total_gen].fillna(0.0)
        value_cols.append(col_total_gen)

        for orientacion in ORIENTACIONES_ORDEN:
            oslug = _ORIENTACION_SLUG[orientacion]
            col = f"{gslug}_{oslug}"
            sub2 = (
                subset_gen[subset_gen["orientacionhato"] == orientacion]
                .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
                .sum()
                .rename(columns={"peso_predio_ganadero": col})
            )
            agg = agg.merge(sub2, on="CODIGO_MUNICIPIO", how="left")
            agg[col] = agg[col].fillna(0.0)
            value_cols.append(col)

    # "total_predios_ganaderos" y los 3 "{genero}_total" quedan
    # independientes (coinciden exacto con Cuadro 1/.../8 y Cuadro 8
    # respectivamente, ver docstring del módulo), ajustados después para que
    # las sumas coincidan exacto (margen de género, y cada bloque
    # internamente con sus 6 orientaciones) - ver docstring de
    # `agregador.forzar_suma_exacta`.
    tabla = agregador.generar_cuadro(agg, value_cols)
    cols_genero_total = [f"{_GENERO_BLOQUE_SLUG[g]}_total" for g in _GENERO_ORDEN_CUADRO9]
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_genero_total)
    for genero in _GENERO_ORDEN_CUADRO9:
        gslug = _GENERO_BLOQUE_SLUG[genero]
        cols_bloque = [f"{gslug}_{_ORIENTACION_SLUG[o]}" for o in ORIENTACIONES_ORDEN]
        agregador.forzar_suma_exacta(tabla, f"{gslug}_total", cols_bloque)
    return tabla, value_cols


def generar_cuadro10() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 10 - ver docstring del módulo. Columna "Total" general + 6
    bloques de tenencia (cada uno por sistema productivo)."""
    maestra = pd.read_parquet(base_maestra_c1.RUTA_BASE_MAESTRA_C1)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    value_cols = ["total_predios_ganaderos"]

    for tenencia in TENENCIA_ORDEN:
        tslug = _TENENCIA_SLUG[tenencia]
        subset_ten = maestra[maestra["PREDIO_CARGO"] == tenencia]
        col_total_ten = f"{tslug}_total"
        sub = (
            subset_ten.groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col_total_ten})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
        agg[col_total_ten] = agg[col_total_ten].fillna(0.0)
        value_cols.append(col_total_ten)

        for sistema in SISTEMAS_PRODUCTIVOS_ORDEN:
            col = f"{tslug}_{_SISTEMA_SLUG[sistema]}"
            sub2 = (
                subset_ten[subset_ten["sistemaproductivo"] == sistema]
                .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
                .sum()
                .rename(columns={"peso_predio_ganadero": col})
            )
            agg = agg.merge(sub2, on="CODIGO_MUNICIPIO", how="left")
            agg[col] = agg[col].fillna(0.0)
            value_cols.append(col)

    # Mismo criterio que Cuadro 7/8/9 (ver docstring del módulo y de
    # `agregador.forzar_suma_exacta`): "total_predios_ganaderos" independiente
    # (coincide con Cuadro 1/.../9), ajustado después para que las 6
    # "{tenencia}_total" sumen exacto ese total (margen de tenencia), y cada
    # bloque de tenencia internamente con sus 4 sistemas productivos.
    tabla = agregador.generar_cuadro(agg, value_cols)
    cols_tenencia_total = [f"{_TENENCIA_SLUG[t]}_total" for t in TENENCIA_ORDEN]
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_tenencia_total)
    for tenencia in TENENCIA_ORDEN:
        tslug = _TENENCIA_SLUG[tenencia]
        cols_bloque = [f"{tslug}_{_SISTEMA_SLUG[s]}" for s in SISTEMAS_PRODUCTIVOS_ORDEN]
        agregador.forzar_suma_exacta(tabla, f"{tslug}_total", cols_bloque)
    return tabla, value_cols


def generar_cuadro11(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 11 - ver docstring del módulo. Total + 6 columnas de tenencia,
    sin cruce. `ciclo="C1"` llena E-K, `ciclo="C2"` llena L-R (`PREDIO_CARGO`
    viene del RUV, no de la encuesta - existe en los 2 ciclos)."""
    maestra = _leer_maestra(ciclo)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    cols_tenencia = []
    for tenencia in TENENCIA_ORDEN:
        col = _TENENCIA_SLUG[tenencia]
        cols_tenencia.append(col)
        sub = (
            maestra[maestra["PREDIO_CARGO"] == tenencia]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
    for c in cols_tenencia:
        agg[c] = agg[c].fillna(0.0)

    value_cols = ["total_predios_ganaderos"] + cols_tenencia
    # "total_predios_ganaderos" independiente (ver docstring del módulo),
    # ajustado después para que las 6 columnas de tenencia (partición
    # exhaustiva de `PREDIO_CARGO`, sin nulos) sumen exacto ese total.
    tabla = agregador.generar_cuadro(agg, value_cols)
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_tenencia)
    return tabla, value_cols


def generar_cuadro12(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 12 - ver docstring del módulo. Columna "Total" general + 6
    bloques de tenencia (cada uno por orientación del hato). `ciclo="C1"`
    llena E-AU, `ciclo="C2"` llena AV en adelante (`PREDIO_CARGO`/
    `orientacionhato` existen en los 2 ciclos)."""
    maestra = _leer_maestra(ciclo)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    value_cols = ["total_predios_ganaderos"]

    for tenencia in TENENCIA_ORDEN:
        tslug = _TENENCIA_SLUG[tenencia]
        subset_ten = maestra[maestra["PREDIO_CARGO"] == tenencia]
        col_total_ten = f"{tslug}_total"
        sub = (
            subset_ten.groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col_total_ten})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
        agg[col_total_ten] = agg[col_total_ten].fillna(0.0)
        value_cols.append(col_total_ten)

        for orientacion in ORIENTACIONES_ORDEN:
            oslug = _ORIENTACION_SLUG[orientacion]
            col = f"{tslug}_{oslug}"
            sub2 = (
                subset_ten[subset_ten["orientacionhato"] == orientacion]
                .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
                .sum()
                .rename(columns={"peso_predio_ganadero": col})
            )
            agg = agg.merge(sub2, on="CODIGO_MUNICIPIO", how="left")
            agg[col] = agg[col].fillna(0.0)
            value_cols.append(col)

    # Mismo criterio que Cuadro 7/8/9/10 (ver docstring del módulo y de
    # `agregador.forzar_suma_exacta`): "total_predios_ganaderos" independiente
    # (coincide con Cuadro 1/.../11), ajustado después para que las 6
    # "{tenencia}_total" sumen exacto ese total, y cada bloque de tenencia
    # internamente con sus 6 orientaciones.
    tabla = agregador.generar_cuadro(agg, value_cols)
    cols_tenencia_total = [f"{_TENENCIA_SLUG[t]}_total" for t in TENENCIA_ORDEN]
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_tenencia_total)
    for tenencia in TENENCIA_ORDEN:
        tslug = _TENENCIA_SLUG[tenencia]
        cols_bloque = [f"{tslug}_{_ORIENTACION_SLUG[o]}" for o in ORIENTACIONES_ORDEN]
        agregador.forzar_suma_exacta(tabla, f"{tslug}_total", cols_bloque)
    return tabla, value_cols


def generar_cuadro13() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 13 - ver docstring del módulo. Total + 7 rangos de `menores18`
    (blancos fusionados a "No sabe/no responde")."""
    maestra = pd.read_parquet(base_maestra_c1.RUTA_BASE_MAESTRA_C1)
    menores = maestra["menores18"]

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    filtros = [
        ("cero", menores == 0),
        ("de_1_a_5", menores.between(1, 5)),
        ("de_6_a_10", menores.between(6, 10)),
        ("de_11_a_15", menores.between(11, 15)),
        ("de_16_a_20", menores.between(16, 20)),
        ("de_21_a_50", menores.between(21, 50)),
        ("mas_50", menores > 50),
        ("no_sabe", menores.isna()),
    ]
    cols_rango = []
    for col, filtro in filtros:
        cols_rango.append(col)
        sub = (
            maestra[filtro]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
    for c in cols_rango:
        agg[c] = agg[c].fillna(0.0)

    value_cols = ["total_predios_ganaderos"] + cols_rango
    # "total_predios_ganaderos" independiente, coincide con Cuadro 1/.../12
    # (ver docstring del módulo); los 8 rangos SÍ son exhaustivos y
    # mutuamente excluyentes por construcción (partición completa de
    # `menores18`, incluyendo nulos) - se ajustan DESPUÉS con
    # `agregador.forzar_suma_exacta` para que sumen exacto ese total, sin
    # romper la coincidencia con Cuadro 1/.../12.
    tabla = agregador.generar_cuadro(agg, value_cols)
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_rango)
    return tabla, value_cols


def generar_cuadro14() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 14 - ver docstring del módulo. Total + con colmenas + 6 rangos
    de cantidad de colmenas (partición exhaustiva de todos los predios)."""
    maestra = pd.read_parquet(base_maestra_c1.RUTA_BASE_MAESTRA_C1)
    efectivo = maestra["numcolmenas"].where(maestra["tienecolmenas"] == "Si", 0.0)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    filtros = [
        ("con_colmenas", maestra["tienecolmenas"] == "Si"),
        ("cero", efectivo == 0),
        ("de_1_a_10", efectivo.between(1, 10)),
        ("de_11_a_30", efectivo.between(11, 30)),
        ("de_31_a_50", efectivo.between(31, 50)),
        ("mas_50", efectivo > 50),
        ("no_sabe", efectivo.isna()),
    ]
    cols_rango = []
    for col, filtro in filtros:
        cols_rango.append(col)
        sub = (
            maestra[filtro]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
    for c in cols_rango:
        agg[c] = agg[c].fillna(0.0)

    value_cols = ["total_predios_ganaderos"] + cols_rango
    # "total_predios_ganaderos" independiente (coincide con Cuadro 1/.../13).
    # "con_colmenas" NO participa de la suma (es un marcador aparte, no una
    # categoría de esta partición - ver docstring del módulo); los 6 rangos
    # de cantidad de colmenas SÍ son una partición exhaustiva de TODOS los
    # predios-ganadero (ver docstring del módulo) y se ajustan DESPUÉS con
    # `agregador.forzar_suma_exacta` para sumar exacto el total.
    tabla = agregador.generar_cuadro(agg, value_cols)
    cols_rango_solo = [c for c in cols_rango if c != "con_colmenas"]
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", cols_rango_solo)
    return tabla, value_cols


def _parsear_area(serie: pd.Series) -> pd.Series:
    """Columnas de área de Ciclo 2 vienen como texto con coma decimal
    ("0,5") - normaliza a número. Casos borde verificados en datos reales:
    "0," (coma sin dígitos, ~decenas de filas) y "," sola (~1 fila) quedan en
    0.0 y NaN respectivamente (comportamiento de `pd.to_numeric` sobre "0."/
    "." - ver docstring del módulo)."""
    texto = serie.astype(str).str.strip().str.replace(",", ".", regex=False)
    texto = texto.where(~texto.isin(["", "nan", "."]), None)
    return pd.to_numeric(texto, errors="coerce")


_AREA_MAX_HA = 100_000  # ver docstring de `_area_en_hectareas`


def _area_en_hectareas(maestra: pd.DataFrame, columna: str) -> pd.Series:
    """Convierte una columna de área cruda a hectáreas, según
    `unidadmedidaarea` - ver docstring del módulo (decisión del usuario
    2026-09-23 sobre "Fanegadas o Plaza o Cuadra", que queda en `NaN`, NO en
    0 - un `NaN` no se suma en los totales de hectáreas, un 0 sí contaría
    como área real cero).

    También excluye (deja en `NaN`) valores > `_AREA_MAX_HA` = 100.000 ha por
    predio - decisión del usuario 2026-09-23: se encontraron ~78 registros
    (de 712.846) con 300-885 millones de hectáreas (más que el territorio
    completo de Colombia, imposible para un solo predio - error de captura,
    no un predio real gigante), que sin excluir inflaban el total nacional a
    miles de millones de hectáreas. 100.000 ha es muchísimo más grande que
    cualquier hacienda ganadera conocida en Colombia (las más grandes llegan
    a unas pocas decenas de miles de ha) - descarta solo los casos
    claramente imposibles, sin tocar predios grandes pero reales."""
    valor = _parsear_area(maestra[columna])
    unidad = maestra["unidadmedidaarea"]
    ha = pd.Series(pd.NA, index=maestra.index, dtype="Float64")
    ha = ha.mask((unidad == "Hectáreas").to_numpy(), valor)
    ha = ha.mask((unidad == "Metros cuadrados").to_numpy(), valor / 10000)
    # El límite se aplica DESPUÉS de convertir a hectáreas (no sobre el valor
    # crudo): para filas en "Metros cuadrados" el valor crudo real puede
    # superar 100.000 sin problema (100.000 m² = 10 ha, un predio normal) -
    # aplicar el límite antes de dividir por 10.000 habría descartado predios
    # legítimos reportados en esa unidad.
    return ha.where(ha <= _AREA_MAX_HA)


def generar_cuadro15() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 15 - ver docstring del módulo. Total + 5 bloques de cobertura
    de tierra (cada uno: Total predios + Hectáreas). Solo Ciclo 2 (esta
    pregunta no existe en Ciclo 1)."""
    maestra = _leer_maestra("C2")

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    value_cols = ["total_predios_ganaderos"]
    bloques = [
        ("agricola", "areaagricola"),
        ("produccion_animales", "areaproducanimales"),
        ("forestal", "areaforestal"),
        ("construcciones", "areaconstrucciones"),
        ("otros_usos", "areaotrosusos"),
    ]
    for slug, columna in bloques:
        valor_num = _parsear_area(maestra[columna])
        ha = _area_en_hectareas(maestra, columna)
        col_predios, col_ha = f"{slug}_predios", f"{slug}_ha"

        sub_predios = (
            maestra[valor_num.fillna(0) > 0]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col_predios})
        )
        agg = agg.merge(sub_predios, on="CODIGO_MUNICIPIO", how="left")

        sub_ha = (
            maestra.assign(_ha=ha.astype(float) * maestra["peso_predio_ganadero"])
            .groupby("CODIGO_MUNICIPIO", as_index=False)["_ha"]
            .sum()
            .rename(columns={"_ha": col_ha})
        )
        agg = agg.merge(sub_ha, on="CODIGO_MUNICIPIO", how="left")

        agg[col_predios] = agg[col_predios].fillna(0.0)
        agg[col_ha] = agg[col_ha].fillna(0.0)
        value_cols += [col_predios, col_ha]

    # SIN `columnas_totales` - mismo criterio que el resto del libro (ver
    # docstring del módulo): "total_predios_ganaderos" es independiente.
    tabla = agregador.generar_cuadro(agg, value_cols)
    return tabla, value_cols


def generar_cuadro16() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 16 - ver docstring del módulo. Total + con área de producción
    de animales + hectáreas de producción + hectáreas de ganadería bovina/
    bufalina. Solo Ciclo 2."""
    maestra = _leer_maestra("C2")
    valor_produccion = _parsear_area(maestra["areaproducanimales"])
    ha_produccion = _area_en_hectareas(maestra, "areaproducanimales")
    ha_ganaderia = _area_en_hectareas(maestra, "areaganaderiabovbuf")

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )

    sub_predios = (
        maestra[valor_produccion.fillna(0) > 0]
        .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
        .sum()
        .rename(columns={"peso_predio_ganadero": "con_produccion_animales"})
    )
    agg = agg.merge(sub_predios, on="CODIGO_MUNICIPIO", how="left")

    for col_ha, serie_ha in [("ha_produccion_animales", ha_produccion), ("ha_ganaderia_bovbuf", ha_ganaderia)]:
        sub_ha = (
            maestra.assign(_ha=serie_ha.astype(float) * maestra["peso_predio_ganadero"])
            .groupby("CODIGO_MUNICIPIO", as_index=False)["_ha"]
            .sum()
            .rename(columns={"_ha": col_ha})
        )
        agg = agg.merge(sub_ha, on="CODIGO_MUNICIPIO", how="left")

    value_cols = ["total_predios_ganaderos", "con_produccion_animales", "ha_produccion_animales", "ha_ganaderia_bovbuf"]
    for c in value_cols[1:]:
        agg[c] = agg[c].fillna(0.0)

    # SIN `columnas_totales` - "ha_ganaderia_bovbuf" es subconjunto real de
    # "ha_produccion_animales" (pregunta 12 de la ECG), pero cada una se
    # redondea de forma independiente (mismo criterio horizontal ±1 aceptado
    # en el resto del proyecto, ver `agregador.py`).
    tabla = agregador.generar_cuadro(agg, value_cols)
    return tabla, value_cols


def generar_cuadro17() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 17 - ver docstring del módulo. Total + Sí/No/No sabe-no
    responde (área protegida). Solo Ciclo 2.

    "total_predios_ganaderos" independiente, NUNCA derivado vía
    `columnas_totales` (corregido 2026-09-24, Fase 8: la versión original SÍ
    lo derivaba como suma de sí/no/no_sabe - único cuadro nuevo de Ciclo 2
    que rompía el principio del resto del proyecto de que el total coincida
    exacto entre cuadros, ver docstring de `cuadros/comun.py`. Detectado por
    el validador: 728.546 vs. 728.576 en Cuadro 1/15/16/18/19, dif 30).

    A partir de 2026-10-02 (a pedido del usuario), sí/no/no_sabe (partición
    exhaustiva y excluyente de una pregunta de única respuesta) se ajustan
    DESPUÉS con `agregador.forzar_suma_exacta` para sumar exacto ese mismo
    total - se logran AMBAS cosas a la vez (coincidencia con Cuadro 1 Y
    consistencia interna fila a fila), sin el trade-off de la corrección
    anterior."""
    maestra = _leer_maestra("C2")

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    filtros = [
        ("si", _filtro_valor(maestra["areaprotegida"], "Si")),
        ("no", maestra["areaprotegida"] == "No"),
        ("no_sabe", maestra["areaprotegida"].isna() | (maestra["areaprotegida"] == "No sabe/no responde")),
    ]
    for col, filtro in filtros:
        sub = (
            maestra[filtro]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
    for col, _ in filtros:
        agg[col] = agg[col].fillna(0.0)

    value_cols = ["total_predios_ganaderos", "si", "no", "no_sabe"]
    tabla = agregador.generar_cuadro(agg, value_cols)
    agregador.forzar_suma_exacta(tabla, "total_predios_ganaderos", ["si", "no", "no_sabe"])
    return tabla, value_cols


def generar_cuadro18() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 18 - ver docstring del módulo. Total + con razas puras + con
    razas de cruces (no excluyentes). Solo Ciclo 2."""
    maestra = _leer_maestra("C2")

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    for col, filtro in [
        ("con_puras", maestra["tienerazapura"].notna()),
        ("con_cruces", maestra["tienerazacruce"].notna()),
    ]:
        sub = (
            maestra[filtro]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
            .sum()
            .rename(columns={"peso_predio_ganadero": col})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
    for c in ("con_puras", "con_cruces"):
        agg[c] = agg[c].fillna(0.0)

    value_cols = ["total_predios_ganaderos", "con_puras", "con_cruces"]
    # SIN `columnas_totales` - no son categorías excluyentes (ver docstring del módulo).
    tabla = agregador.generar_cuadro(agg, value_cols)
    return tabla, value_cols


# --- Cuadro 19: 52 razas puras (F-BE de la plantilla) + 28 cruces (BF-CG) ---
# Orden EXACTO de la plantilla real (no alfabético del todo: "Otra raza
# bovinos" está intercalada donde alfabéticamente cabría "O..."; "Otra" y "No
# existe raza predominante (mestizo)" van al final).
RAZA_PURA_ORDEN = [
    "Abeerden angus", "Amarillo Aleman (Gelbvieh)", "Ayrshire", "Beef master", "Blanco azul belga",
    "Blanco Orejinenegro (BON)", "Blonde d'Aquitaine", "Braford", "Brahman", "Brangus", "Campuzano",
    "Caqueteño", "Casanareño", "Cebu comercial", "Charbray", "Charolais", "Chianina", "Chino Santandereano",
    "Costeño con Cuernos", "Girolando", "Guernesey", "Guzerath", "Gyr", "Hartón del valle", "Hereford",
    "Holstein", "Indubrazil", "Jersey", "Limousin", "Lucerna", "Montbéliarde", "Nellore", "Normando",
    "Otra raza bovinos", "Overo colorado", "Pardo suizo (Brown Swiss)", "Red Poll", "Red Sindhi",
    "Rojo danes", "Romagnola", "Romosinuano (ROMO)", "Sanmartinero", "Santa Coloma", "Santa Gertrudis",
    "Senepol", "Shorthorn", "Simbrah", "Simmental (alemán / americano)", "Velásquez", "Wagyu", "Otra",
    "No existe raza predominante (mestizo)",
]
CRUCES_ORDEN = [
    "Brahaman Rojo X Brangus", "Brahaman X Holstein", "Brahaman X Mestizo", "Brahaman X Pardo Suizo",
    "Cebu Comercial", "Cebu Comercial X Abeerden Agnus", "Cebu Comercial X Brahaman",
    "Cebu Comercial X Guernesey", "Cebu Comercial X Mestizo", "Cebu Comercial X Nellore",
    "Cebu Comercial X Normando", "Cebu Comercial X Simmental Aleman", "Guzerath X Mestizo",
    "Gyrholando X Mestizo", "Gyrolando X Brahaman", "Holstein X Cebu", "Holstein X Jersey",
    "Holstein X Mestizo", "Jersey X Cebu", "Jersey X Mestizo", "Nellore X Mestizo", "Normando X Mestizo",
    "Pardo Siuzo X Cebu", "Pardo Suizo X Mestizo", "Simmental Americano X Mestizo", "Simmental X Cebu",
    "Simmental X Cebu Comercial", "Otra ",
]

# Valores REALES de `razapurapredominante`/`razacrucepredominante` que NO
# coinciden ni siquiera normalizados (mayúsculas/tildes) con ninguna etiqueta
# de la plantilla - verificado 2026-09-23 comparando las 53/28 respuestas
# únicas reales contra las 52/28 categorías de la plantilla antes de mapear
# nada (ver docstring del módulo):
#  - "Brahaman" (dato, 7.593 predios) vs "Brahman" (plantilla) - error de
#    tipeo en uno de los 2 (no se puede saber cuál, se asume la misma raza).
#  - "Pardo Suizo X Cebú" (dato) vs "Pardo Siuzo X Cebu" (plantilla, "Siuzo"
#    con las letras trastocadas) - mismo caso.
#  - "Murrah" (239) y "Mediterraneo" (27): razas de BÚFALO reales, sin
#    columna propia en una plantilla pensada para razas BOVINAS ("Otra raza
#    bovinos" incluso lo dice en el nombre) - se mapean a "Otra" (la genérica,
#    no a "Otra raza bovinos", porque explícitamente NO son bovinos).
_RAZA_PURA_EXCEPCIONES = {"Brahaman": "Brahman", "Murrah": "Otra", "Mediterraneo": "Otra"}
_CRUCES_EXCEPCIONES = {"Pardo Suizo X Cebú": "Pardo Siuzo X Cebu"}


def _normalizar_raza(texto: str) -> str:
    import unicodedata

    # Apóstrofe recto (') vs tipográfico (') - "Blonde d'Aquitaine" viene con
    # el tipográfico en los datos reales, se quitan ambas variantes junto con
    # las tildes para que coincidan sin importar cuál se usó al escribir la
    # plantilla en Python (detectado 2026-09-23, ver docstring del módulo).
    texto = texto.replace("'", "").replace("’", "")
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sin_tildes.upper().strip()


def _slug_raza(etiqueta: str) -> str:
    limpio = _normalizar_raza(etiqueta).replace("(", "").replace(")", "").replace("/", " ").replace("-", " ")
    return "_".join(limpio.split()).lower()


def _mapa_valor_a_etiqueta(valores_datos, etiquetas_template: list[str], excepciones: dict[str, str]) -> dict[str, str]:
    """`{valor_crudo_real: etiqueta_de_la_plantilla}` - EXIGE que cada valor
    real mapee a algo (falla fuerte con `KeyError` si aparece un valor nuevo
    sin mapear, en vez de perderlo en silencio - mismo criterio que el resto
    del proyecto)."""
    normalizado_a_etiqueta = {_normalizar_raza(e): e for e in etiquetas_template}
    mapa = {}
    for valor in valores_datos:
        if valor in excepciones:
            mapa[valor] = excepciones[valor]
        else:
            mapa[valor] = normalizado_a_etiqueta[_normalizar_raza(valor)]
    return mapa


def generar_cuadro19() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 19 - ver docstring del módulo. Total + 52 columnas de raza pura
    + 28 columnas de cruce (mutuamente excluyentes ENTRE SÍ dentro de cada
    grupo - un predio-ganadero tiene 1 sola raza pura predominante Y/O 1 sola
    de cruce, según respondió `tienerazapura`/`tienerazacruce` en Cuadro 18).
    Solo Ciclo 2."""
    maestra = _leer_maestra("C2")

    valores_pura = maestra["razapurapredominante"].dropna().unique().tolist()
    mapa_pura = _mapa_valor_a_etiqueta(valores_pura, RAZA_PURA_ORDEN, _RAZA_PURA_EXCEPCIONES)
    etiqueta_pura = maestra["razapurapredominante"].map(mapa_pura)

    valores_cruce = maestra["razacrucepredominante"].dropna().unique().tolist()
    mapa_cruce = _mapa_valor_a_etiqueta(valores_cruce, CRUCES_ORDEN, _CRUCES_EXCEPCIONES)
    etiqueta_cruce = maestra["razacrucepredominante"].map(mapa_cruce)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios_ganaderos=("peso_predio_ganadero", "sum")
    )
    value_cols = ["total_predios_ganaderos"]

    # Prefijo "pura_"/"cruce_" - "Otra" y "Cebu comercial"/"Cebu Comercial"
    # existen en AMBOS grupos (raza pura Y cruce), sin prefijo colisionarían
    # en el mismo nombre de columna (verificado: 78 slugs únicos de 80
    # etiquetas sin prefijo).
    for prefijo, etiqueta_col, orden in [("pura", etiqueta_pura, RAZA_PURA_ORDEN), ("cruce", etiqueta_cruce, CRUCES_ORDEN)]:
        for etiqueta in orden:
            slug = f"{prefijo}_{_slug_raza(etiqueta)}"
            sub = (
                maestra[etiqueta_col == etiqueta]
                .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_predio_ganadero"]
                .sum()
                .rename(columns={"peso_predio_ganadero": slug})
            )
            agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
            value_cols.append(slug)

    for c in value_cols[1:]:
        agg[c] = agg[c].fillna(0.0)

    # SIN `columnas_totales` - "total_predios_ganaderos" es independiente
    # (coincide con Cuadro 1); las 80 columnas de raza NO tienen por qué
    # sumar ese total (predios con `tienerazapura`/`tienerazacruce` en blanco
    # no aportan a ninguna columna de raza, mismo criterio que Cuadro 18).
    tabla = agregador.generar_cuadro(agg, value_cols)
    return tabla, value_cols
