"""Cuadros específicos del libro "Ganadero" (más allá de Cuadro 1/2, comunes
a los 3 libros de publicación - ver `cuadros/comun.py`).

Cuadro 3 - "Cantidad de ganaderos por sexo y persona jurídica": fórmula
confirmada contra `Programas Carolina/4.2. cuadros ganadero.sas` (líneas
641-656, leído como referencia de metodología en `/s/02Programas`) -
`SUM(gan_cal)` agrupado por `genero`, sobre la tabla deduplicada por
predio-ganadero (`ciclo1c`). `gan_cal = conteo_gan * cal_cobertura` con
`conteo_gan = 1/conteo(ganadero_id)` (líneas 328-342 del mismo SAS) - EXACTO
el mismo cálculo que `peso_ganadero` en `base_maestra_c1.py` (agrupado por
IDENT_GANADERO en vez de GANADERO_ID, mejora ya documentada ahí). No hace
falta releer/recalcular nada: `base_maestra_c1` ya trae `peso_ganadero` y
`genero` (normalizado a "Mujer"/"Hombre"/`config.GENERO_JURIDICA`, sin
nulos - ver `preparar_base_c1.normalizar_categoricas`).

Cuadro 6 - "Cantidad de ganaderos víctimas de algún delito" (pregunta 18 de
la encuesta): fórmula confirmada contra el mismo SAS (líneas 680-696) -
`SUM(gan_cal)` (= `peso_ganadero`) agrupado por cada bandera 'X'/'' de delito
(`abigeato`/`carneo`/`extorsion`/`hurto`/`invasiontierra`/`secuestro`/`otro`/
`ninguno`, ya en `base_maestra_c1`). NO son categorías mutuamente excluyentes
(un ganadero puede marcar varios delitos a la vez) - a diferencia de Cuadro 3,
acá NO se declara `columnas_totales` en `agregador.generar_cuadro`: la suma
de las 8 columnas NO tiene por qué dar "Total de ganaderos", y forzarla
sería incorrecto. El SAS además filtra
`WHERE coalesce(strip(orientacionhato), '') ne ''` (excluye predios-ganadero
sin orientación de hato reportada) - se replica igual, aunque hoy no excluye
ninguna fila (`orientacionhato` no tiene nulos/vacíos en los datos actuales).

Cuadro 8 - "Cantidad de ganaderos por sexo, tenencia del predio y persona
jurídica" (pregunta del RUV "16.5. El predio a su cargo es: 1.Propio
2.Arrendado 3.Poseedor 4.Tenedor 5.Territorio colectivo 6.Otro" -
`PREDIO_CARGO`, ya en `base_maestra_c1`, 6 categorías limpias sin nulos,
verificado). A DIFERENCIA de Cuadro 3/6: revisado `4.2`/`4.3 cuadros *.sas`
completos y `predioCargoOrden` (el orden que usaría un cuadro por tenencia)
se calcula en los 2 programas pero NUNCA se usa para construir ningún cuadro
- no hay cuadro equivalente publicado en el pipeline original que sirva de
referencia exacta. Se aplica la MISMA metodología ya validada en Cuadro 3/6
(`peso_ganadero` agrupado por categoría, sobre la base ya deduplicada por
predio-ganadero) por consistencia, ya que es la técnica general del proyecto
para "cantidad de ganaderos según <categoría>" - un ganadero con predios de
distinta tenencia contribuye (fraccionalmente, vía `peso_ganadero`) a cada
categoría que le corresponda, igual que ya pasa con "predios ganaderos" en
Cuadro 1.

Estructura (28 columnas, E-AF): "Total de ganaderos" (general) + 6 columnas
de tenencia (todas los géneros) + 3 bloques de 7 columnas c/u (Total + 6
tenencias) para Hombres/Mujeres/Persona jurídica. Consistencia horizontal
declarada en `columnas_totales` en las 2 direcciones: cada bloque de género
suma su propio total (`h_total = suma de sus 6 tenencias`), y cada columna
de tenencia "general" sume sus 3 bloques de género
(`propio = h_propio + m_propio + j_propio`).

Cuadro 9 - "Cantidad de ganaderos que comparten los mismos lotes con otros
ganaderos, por sexo y persona jurídica" (pregunta encuesta "¿En este predio
su ganado comparte los mismos lotes con los de otros ganaderos?", SI/NO -
`compartelote` en el RUV, R5 según `3. configura base.sas`). MISMA situación
que Cuadro 8: no hay cuadro equivalente en `4.2`/`4.3` que sirva de
referencia - se agregó `compartelote` a `base_maestra_c1._COLS_ENCUESTA_MASTER`
(no estaba cargada) y se aplica la misma metodología de `peso_ganadero`
agrupado por categoría (acá SI/NO x género, 2 categorías en vez de las 6 de
tenencia - misma estructura general/hombres/mujeres/jurídica, sin columna
"Total" por bloque porque SI+NO ya es el total del bloque).

Cuadro 10 - "Cantidad de ganaderos de acuerdo con el lugar de residencia,
por sexo y persona jurídica" (pregunta encuesta "2. ¿En dónde vive el
ganadero? 1. En el predio visitado 2. En otro lugar diferente al predio").
La columna cruda es `R2` - a diferencia de R3 en adelante, NO viene
pre-renombrada en el `.sas7bdat` (sigue literal "R2") ni está en
`config.RENOMBRE_PREGUNTAS` original de Carolina (`3. configura base.sas` no
tiene `r2=`) - el SAS original nunca la usó en ningún cuadro. Se agregó
`"R2": "lugarresidencia"` a `config.RENOMBRE_PREGUNTAS` y `"R2"` a
`base_maestra_c1._COLS_ENCUESTA_MASTER` para poder construir este cuadro. Mismo
patrón que Cuadro 9 (2 categorías x género), con una diferencia de layout:
acá el bloque general NO tiene columna "Total" (ya está en "Total de
ganaderos"), pero los 3 bloques de género SÍ tienen su propio "Total"
(primero en el bloque, igual que Cuadro 8) - verificado columna por columna
contra la plantilla real, no asumido por analogía con Cuadro 9.

Cuadro 11 - "Cantidad de ganaderos que responden directamente la encuesta,
por sexo y persona jurídica" (pregunta encuesta "1. ¿La encuesta fue
atendida por el ganadero?", SI/NO - `R1`, la única de R1/R2 que seguía sin
usarse). MISMA estructura exacta que Cuadro 9 (SI/NO x género, sin columna
"Total" por bloque) - verificado columna por columna contra la plantilla
real, coincide. Se agregó `"R1": "atendioencuesta"` a
`config.RENOMBRE_PREGUNTAS` y `"R1"` a `base_maestra_c1._COLS_ENCUESTA_MASTER`.

Cuadro 12 - "Cantidad de ganaderos donde el ganadero manifestó conocer qué
es un sensor epidemiológico" (pregunta encuesta "12. ¿Usted sabe qué es un
sensor epidemiológico? 1. Sí 2. No 3. No sabe/no responde" - `consensorepidem`,
R13 según `3. configura base.sas`). Sin desagregación por sexo/persona
jurídica (a diferencia de Cuadro 3/6/8/9/10/11) - solo Total + 3 categorías.

A diferencia de las preguntas SI/NO usadas en Cuadro 9/11 (sin nulos, ver
esos docstrings), `consensorepidem` SÍ tiene ~10.823 respuestas en blanco
(cadena vacía, no nulo real - verificado: `""`, ni Sí, ni No, ni "No sabe/no
responde") - verificado con datos reales antes de decidir esto, no asumido.
La plantilla solo tiene 3 columnas de categoría (Sí/No/No sabe/no responde),
sin una 4ª para "sin dato" - decisión del usuario (2026-09-21): las
respuestas en blanco se suman a "No sabe/no responde" (la categoría más
cercana en significado - "no contestó" es un caso particular de "no sabe/no
responde"), en vez de dejarlas como una brecha sin explicar frente al Total.
Con esto, `total_ganaderos = si + no + no_sabe` SÍ se cumple exacto y se
declara en `columnas_totales` - antes de esta decisión no se declaraba.

Cuadro 13 - "Cantidad de ganaderos que manifestaron conocer el sistema de
alerta temprana" (pregunta encuesta "14. ¿Conoce usted el sistema de alerta
temprana? 1. Sí 2. No 3. No sabe/no responde" - `conalertatem`, R14 según
`3. configura base.sas`). MISMA estructura exacta que Cuadro 12 (Total +
Sí/No/No sabe, sin sexo/persona jurídica) - a diferencia de
`consensorepidem`, `conalertatem` NO tiene respuestas en blanco (verificado:
Sí+No+No sabe suma exacto el total sin ningún ajuste) - se reutiliza
`_generar_cuadro_si_no_general` (compartida con Cuadro 12).

Cuadro 14 - "Cantidad de ganaderos que manifestaron tener conocimiento sobre
la obligación de notificar al ICA en caso de que su ganado presente síntomas
como lesiones vesiculares (aftas) en cavidad bucal, lengua, pezones y patas
(pezuñas)" (pregunta encuesta "15. ¿Sabe usted que debe notificar al ICA...?
1. Sí 2. No 3. No sabe/no responde" - `debenotificarica`, R15 según
`3. configura base.sas`). MISMA estructura exacta que Cuadro 12/13 (Total +
Sí/No/No sabe, sin sexo/persona jurídica) - `debenotificarica` tampoco tiene
respuestas en blanco (verificado). Se reutiliza `_generar_cuadro_si_no_general`.

Cuadro 15 - "Cantidad de ganaderos que manifestaron que en los últimos 6
meses, su ganado ha presentado signos clínicos reproductivos (abortos,
retención de placenta, metritis, aumento del intervalo entre partos o
aumento de días abiertos)" (`signosclinicos`, R16 según
`3. configura base.sas`). MISMA estructura que Cuadro 12/13/14 (Total +
Sí/No/No sabe) - `signosclinicos` tampoco tiene respuestas en blanco
(verificado). Se reutiliza `_generar_cuadro_si_no_general`. OJO: la nota al
pie de esta hoja en la plantilla real trae pegado el texto de la pregunta de
Cuadro 14 ("15. ¿Sabe usted que debe notificar al ICA...?") en vez de la
propia - error de la plantilla original, no algo que este código deba
corregir (se preserva la nota tal cual viene, como con cualquier otra).

Cuadro 16 - "Cantidad de ganaderos que manifestaron conocer los programas de
formación técnica/tecnológica en producción ganadera sostenible de la
Universidad del Área Andina e interés en cursarla" (`conformacion`
"¿Conoce los programas...?" y `intcarrera` "¿Le interesaría cursar esta
carrera?", ambas 1.Sí 2.No - sin "No sabe/no responde", a diferencia de
Cuadro 12-15). Estructura DISTINTA a los demás: no es un bloque Primer/
Segundo ciclo, son 2 PREGUNTAS INDEPENDIENTES lado a lado, cada una con su
propio "Total de ganaderos" (E y H - el mismo valor repetido, ver
`generar_cuadro16`) + SI/NO. Se encontró un problema real de calidad de
datos, verificado byte por byte antes de "arreglarlo" (no asumido por el
texto que se veía en pantalla): `conformacion`/`intcarrera` traen "Si" y una
tercera variante como valores de texto DISTINTOS (~3.300 filas de ~730.000).
Esa tercera variante NO es la "Sí" Unicode normal - es "Sí" truncada a 1
byte en la fuente (el campo tiene longitud fija demasiado corta para el
carácter completo, se pierde la tilde) y queda como `"S"` sola (confirmado
DESPUÉS de corregir `fuente_cruda_c1.py` a `encoding="utf-8"` - ver ese módulo:
antes, con `encoding="latin1"`, esta misma fila se veía como `"S" + chr(0xC3)`,
un mojibake DISTINTO y más confuso del mismo problema de fondo). Se trata
"S" como la misma respuesta afirmativa que "Si" (`.isin(["Si", "S"])`) - sin
este ajuste, esas ~3.300 respuestas afirmativas desaparecían silenciosamente
del conteo "Sí" (total nacional ~3.134 ganaderos por debajo de lo esperado,
detectado al comparar contra `peso_ganadero.sum()` antes de escribir el
cuadro).

Solo Ciclo 1 por ahora (columnas E-M de la plantilla en Cuadro 3, E-M en
Cuadro 6, E-AF en Cuadro 8, E-M en Cuadro 9, E-P en Cuadro 10, E-M en Cuadro
11, E-H en Cuadro 12, E-H en Cuadro 13, E-H en Cuadro 14, E-H en Cuadro 15,
E-J en Cuadro 16; los bloques "Segundo ciclo" quedan pendientes de que
exista el equivalente de `base_maestra_c1` para Ciclo 2 - mismo criterio que
`cuadros/comun.py`. Cuadro 16 en particular ya viene con una sola sección
"Primer ciclo" en la plantilla real, sin bloque "Segundo ciclo" separado).
"""
from __future__ import annotations

import pandas as pd

from .. import agregador, base_maestra_c1, base_maestra_c2, config

_RUTA_BASE_MAESTRA = {"C1": base_maestra_c1.RUTA_BASE_MAESTRA_C1, "C2": base_maestra_c2.RUTA_BASE_MAESTRA_C2}


def _leer_maestra(ciclo: str) -> pd.DataFrame:
    return pd.read_parquet(_RUTA_BASE_MAESTRA[ciclo])


def generar_cuadro3(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    maestra = _leer_maestra(ciclo)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(total_ganaderos=("peso_ganadero", "sum"))
    for col, genero in [("mujeres", "Mujer"), ("hombres", "Hombre"), ("juridica", config.GENERO_JURIDICA)]:
        sub = (
            maestra[maestra["genero"] == genero]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_ganadero"]
            .sum()
            .rename(columns={"peso_ganadero": col})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
    for col in ("mujeres", "hombres", "juridica"):
        agg[col] = agg[col].fillna(0.0)
    agg["natural_total"] = agg["mujeres"] + agg["hombres"]

    value_cols = ["total_ganaderos", "natural_total", "mujeres", "hombres", "juridica"]
    # "natural_total" primero: "total_ganaderos" depende de él, ver docstring
    # de `agregador.generar_cuadro`.
    columnas_totales = {"natural_total": ["mujeres", "hombres"], "total_ganaderos": ["natural_total", "juridica"]}
    tabla = agregador.generar_cuadro(agg, value_cols, columnas_totales=columnas_totales)
    return tabla, value_cols


_DELITOS = ["abigeato", "carneo", "extorsion", "hurto", "invasiontierra", "secuestro", "otro"]


def generar_cuadro6(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    maestra = _leer_maestra(ciclo)
    # Réplica del WHERE del SAS - ver docstring del módulo.
    maestra = maestra[maestra["orientacionhato"].notna() & (maestra["orientacionhato"].astype(str).str.strip() != "")]

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(total_ganaderos=("peso_ganadero", "sum"))
    for col in _DELITOS + ["ninguno"]:
        sub = (
            maestra[maestra[col] == "X"]
            .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_ganadero"]
            .sum()
            .rename(columns={"peso_ganadero": col})
        )
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
    for col in _DELITOS + ["ninguno"]:
        agg[col] = agg[col].fillna(0.0)

    value_cols = ["total_ganaderos"] + _DELITOS + ["ninguno"]
    # Sin `columnas_totales`: no son categorías mutuamente excluyentes (ver
    # docstring del módulo) - cada columna se redondea de forma independiente.
    tabla = agregador.generar_cuadro(agg, value_cols)
    return tabla, value_cols


TENENCIA_ORDEN = ["PROPIO", "ARRENDADO", "POSEEDOR", "TENEDOR", "TERRITORIO COLECTIVO", "OTRO"]
_TENENCIA_SLUG = {
    "PROPIO": "propio",
    "ARRENDADO": "arrendado",
    "POSEEDOR": "poseedor",
    "TENEDOR": "tenedor",
    "TERRITORIO COLECTIVO": "territorio_colectivo",
    "OTRO": "otro",
}
_GENERO_PREFIJO = [("h", "Hombre"), ("m", "Mujer"), ("j", config.GENERO_JURIDICA)]

# Respuesta afirmativa: "Si" (sin tilde) es el valor real en Ciclo 1 (sin
# excepciones, verificado); en Ciclo 2 el valor real es MAYORITARIAMENTE "Sí"
# (con tilde, confirmado byte a byte: 0x53 0xed) con una minoría "Si" sin
# tilde (198 de ~713.000) - convención distinta entre ciclos en la fuente,
# no un bug de ninguno de los 2. Se aceptan ambas variantes siempre (no hace
# daño en C1, donde "Sí" simplemente nunca aparece) en vez de bifurcar por
# ciclo - detectado 2026-09-22 al ver totales de Cuadro 10-15 muy por debajo
# de "Total ganaderos" en C2 (la mayoría de "Sí" quedaba fuera del filtro).
_VALORES_SI = ["Si", "Sí"]


def _filtro_valor(serie: pd.Series, valor: str) -> pd.Series:
    return serie.isin(_VALORES_SI) if valor == "Si" else serie == valor


def _suma_por(maestra: pd.DataFrame, filtro: pd.Series, nombre_col: str) -> pd.DataFrame:
    return (
        maestra[filtro]
        .groupby("CODIGO_MUNICIPIO", as_index=False)["peso_ganadero"]
        .sum()
        .rename(columns={"peso_ganadero": nombre_col})
    )


def generar_cuadro8(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    maestra = _leer_maestra(ciclo)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(total_ganaderos=("peso_ganadero", "sum"))

    # Bloque general (las 6 tenencias, todos los géneros).
    cols_general = [_TENENCIA_SLUG[t] for t in TENENCIA_ORDEN]
    for tenencia in TENENCIA_ORDEN:
        slug = _TENENCIA_SLUG[tenencia]
        sub = _suma_por(maestra, maestra["PREDIO_CARGO"] == tenencia, slug)
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")

    # 3 bloques por género/persona jurídica x tenencia.
    columnas_totales: dict[str, list[str]] = {}
    for prefijo, genero in _GENERO_PREFIJO:
        subset = maestra[maestra["genero"] == genero]
        cols_bloque = [f"{prefijo}_{_TENENCIA_SLUG[t]}" for t in TENENCIA_ORDEN]
        for tenencia, col in zip(TENENCIA_ORDEN, cols_bloque):
            sub = _suma_por(subset, subset["PREDIO_CARGO"] == tenencia, col)
            agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
        agg[f"{prefijo}_total"] = agg[cols_bloque].sum(axis=1)
        columnas_totales[f"{prefijo}_total"] = cols_bloque

    columnas_nuevas = (
        cols_general
        + [c for prefijo, _ in _GENERO_PREFIJO for c in ([f"{prefijo}_total"] + [f"{prefijo}_{_TENENCIA_SLUG[t]}" for t in TENENCIA_ORDEN])]
    )
    for c in columnas_nuevas:
        agg[c] = agg[c].fillna(0.0)

    # Consistencia horizontal en las 2 direcciones (ver docstring del módulo):
    # total_ganaderos = suma de los 3 "_total" de género; cada tenencia
    # "general" = suma de esa misma tenencia en los 3 bloques de género.
    columnas_totales["total_ganaderos"] = [f"{p}_total" for p, _ in _GENERO_PREFIJO]
    for tenencia in TENENCIA_ORDEN:
        slug = _TENENCIA_SLUG[tenencia]
        columnas_totales[slug] = [f"{p}_{slug}" for p, _ in _GENERO_PREFIJO]

    value_cols = (
        ["total_ganaderos"] + cols_general
        + [f"h_total"] + [f"h_{_TENENCIA_SLUG[t]}" for t in TENENCIA_ORDEN]
        + [f"m_total"] + [f"m_{_TENENCIA_SLUG[t]}" for t in TENENCIA_ORDEN]
        + [f"j_total"] + [f"j_{_TENENCIA_SLUG[t]}" for t in TENENCIA_ORDEN]
    )
    tabla = agregador.generar_cuadro(agg, value_cols, columnas_totales=columnas_totales)
    return tabla, value_cols


def _generar_cuadro_si_no_por_genero(columna_raw: str, ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    """Estructura compartida por Cuadro 9 (`compartelote`) y Cuadro 11
    (`atendioencuesta`): SI/NO x género (general/hombres/mujeres/jurídica),
    sin columna "Total" propia por bloque (SI+NO ya es el total)."""
    maestra = _leer_maestra(ciclo)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(total_ganaderos=("peso_ganadero", "sum"))

    # Bloque general (SI/NO, todos los géneros).
    for valor, slug in [("Si", "general_si"), ("No", "general_no")]:
        sub = _suma_por(maestra, _filtro_valor(maestra[columna_raw], valor), slug)
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")

    # 3 bloques por género/persona jurídica x SI/NO.
    columnas_totales: dict[str, list[str]] = {}
    for prefijo, genero in _GENERO_PREFIJO:
        subset = maestra[maestra["genero"] == genero]
        for valor, sufijo in [("Si", "si"), ("No", "no")]:
            col = f"{prefijo}_{sufijo}"
            sub = _suma_por(subset, _filtro_valor(subset[columna_raw], valor), col)
            agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")

    columnas_nuevas = ["general_si", "general_no"] + [f"{p}_{s}" for p, _ in _GENERO_PREFIJO for s in ("si", "no")]
    for c in columnas_nuevas:
        agg[c] = agg[c].fillna(0.0)

    # Consistencia horizontal en las 2 direcciones - ORDEN importa (ver
    # docstring de `agregador.generar_cuadro`): "general_si"/"general_no"
    # deben derivarse PRIMERO (de sus 3 bloques de género), porque
    # "total_ganaderos" depende del valor YA derivado de esos dos, no del
    # independientemente redondeado.
    columnas_totales["general_si"] = [f"{p}_si" for p, _ in _GENERO_PREFIJO]
    columnas_totales["general_no"] = [f"{p}_no" for p, _ in _GENERO_PREFIJO]
    columnas_totales["total_ganaderos"] = ["general_si", "general_no"]

    value_cols = (
        ["total_ganaderos", "general_si", "general_no"]
        + [f"{p}_{s}" for p, _ in _GENERO_PREFIJO for s in ("si", "no")]
    )
    tabla = agregador.generar_cuadro(agg, value_cols, columnas_totales=columnas_totales)
    return tabla, value_cols


def generar_cuadro9(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    return _generar_cuadro_si_no_por_genero("compartelote", ciclo=ciclo)


def generar_cuadro11(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    return _generar_cuadro_si_no_por_genero("atendioencuesta", ciclo=ciclo)


def generar_cuadro10(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    maestra = _leer_maestra(ciclo)
    # `lugarresidencia` con espacios de sobra: en Ciclo 2 (no en Ciclo 1,
    # verificado) " En otro lugar diferente al predio" viene con un espacio
    # inicial pegado en la fuente - sin `.strip()` esas ~294.678 respuestas no
    # calzaban contra el texto exacto y desaparecían en silencio (detectado
    # 2026-09-22: "Total ganaderos" derivado de este cuadro daba muy por
    # debajo del total real). `.str.strip()` es no-operación segura en C1.
    lugar = maestra["lugarresidencia"].astype(str).str.strip()

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(total_ganaderos=("peso_ganadero", "sum"))

    # Bloque general (2 categorías, todos los géneros) - SIN columna "Total"
    # propia (ver docstring del módulo).
    for valor, slug in [("En el predio visitado", "gen_predio"), ("En otro lugar diferente al predio", "gen_otro")]:
        sub = _suma_por(maestra, lugar == valor, slug)
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")

    # 3 bloques por género/persona jurídica x lugar - cada uno CON su Total.
    columnas_totales_10: dict[str, list[str]] = {}
    for prefijo, genero in _GENERO_PREFIJO:
        subset_mask = maestra["genero"] == genero
        subset, lugar_subset = maestra[subset_mask], lugar[subset_mask]
        cols_bloque = [f"{prefijo}_predio", f"{prefijo}_otro"]
        for valor, col in zip(["En el predio visitado", "En otro lugar diferente al predio"], cols_bloque):
            sub = _suma_por(subset, lugar_subset == valor, col)
            agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
        agg[f"{prefijo}_total"] = agg[cols_bloque].sum(axis=1)
        columnas_totales_10[f"{prefijo}_total"] = cols_bloque

    columnas_nuevas = ["gen_predio", "gen_otro"] + [
        f"{p}_{s}" for p, _ in _GENERO_PREFIJO for s in ("total", "predio", "otro")
    ]
    for c in columnas_nuevas:
        agg[c] = agg[c].fillna(0.0)

    # Consistencia horizontal en las 2 direcciones (h_total/m_total/j_total ya
    # quedaron declarados arriba, antes que total_ganaderos - orden correcto,
    # ver docstring de `agregador.generar_cuadro`).
    columnas_totales_10["gen_predio"] = [f"{p}_predio" for p, _ in _GENERO_PREFIJO]
    columnas_totales_10["gen_otro"] = [f"{p}_otro" for p, _ in _GENERO_PREFIJO]
    columnas_totales_10["total_ganaderos"] = ["gen_predio", "gen_otro"]

    value_cols = (
        ["total_ganaderos", "gen_predio", "gen_otro"]
        + [f"{p}_{s}" for p, _ in _GENERO_PREFIJO for s in ("total", "predio", "otro")]
    )
    tabla = agregador.generar_cuadro(agg, value_cols, columnas_totales=columnas_totales_10)
    return tabla, value_cols


def _generar_cuadro_si_no_general(
    columna_raw: str, valores_no_sabe: list[str], ciclo: str = "C1"
) -> tuple[pd.DataFrame, list[str]]:
    """Estructura compartida por Cuadro 12 (`consensorepidem`) y Cuadro 13
    (`conalertatem`): Total + Sí/No/No sabe-no responde, SIN desagregación
    por sexo/persona jurídica. `valores_no_sabe`: qué valores crudos cuentan
    como "No sabe/no responde" - para `consensorepidem` incluye también la
    respuesta en blanco (ver docstring del módulo y de `generar_cuadro12`)."""
    maestra = _leer_maestra(ciclo)

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(total_ganaderos=("peso_ganadero", "sum"))
    for valor, col in [("Si", "si"), ("No", "no")]:
        sub = _suma_por(maestra, _filtro_valor(maestra[columna_raw], valor), col)
        agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
    # "No sabe/no responde": además de `valores_no_sabe` (lista explícita por
    # cuadro, ver docstring de cada `generar_cuadroN`), se suman acá 2 casos
    # encontrados en Ciclo 2 (verificados, no en Ciclo 1): NaN real (233 filas
    # en `consensorepidem`/`conalertatem`/`debenotificarica`/`signosclinicos`,
    # a diferencia de Ciclo 1 donde el blanco de `consensorepidem` es cadena
    # vacía "" - ya cubierto por `valores_no_sabe`) y una variante con
    # tabulador pegado ("No sabe/no responde\t", 5-8 filas en
    # `conalertatem`/`debenotificarica`) - ambos ajustes son no-operación
    # segura en Ciclo 1 (0 filas afectadas ahí, verificado).
    filtro_no_sabe = (
        maestra[columna_raw].isin(valores_no_sabe)
        | maestra[columna_raw].isna()
        | (maestra[columna_raw].astype(str).str.strip() == "No sabe/no responde")
    )
    sub = _suma_por(maestra, filtro_no_sabe, "no_sabe")
    agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
    for c in ("si", "no", "no_sabe"):
        agg[c] = agg[c].fillna(0.0)

    value_cols = ["total_ganaderos", "si", "no", "no_sabe"]
    columnas_totales = {"total_ganaderos": ["si", "no", "no_sabe"]}
    tabla = agregador.generar_cuadro(agg, value_cols, columnas_totales=columnas_totales)
    return tabla, value_cols


def generar_cuadro12(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    # "" (respuesta en blanco) se suma a "No sabe/no responde" - decisión del
    # usuario, ver docstring del módulo.
    return _generar_cuadro_si_no_general("consensorepidem", ["No sabe/no responde", ""], ciclo=ciclo)


def generar_cuadro13(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    # `conalertatem` no tiene respuestas en blanco (verificado con datos
    # reales: Si/No/No sabe/no responde suman exacto el total) - no hace
    # falta ningún ajuste como en Cuadro 12.
    return _generar_cuadro_si_no_general("conalertatem", ["No sabe/no responde"], ciclo=ciclo)


def generar_cuadro14(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    # `debenotificarica` tampoco tiene respuestas en blanco (verificado).
    return _generar_cuadro_si_no_general("debenotificarica", ["No sabe/no responde"], ciclo=ciclo)


def generar_cuadro15(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    # `signosclinicos` tampoco tiene respuestas en blanco (verificado).
    return _generar_cuadro_si_no_general("signosclinicos", ["No sabe/no responde"], ciclo=ciclo)


def generar_cuadro16() -> tuple[pd.DataFrame, list[str]]:
    # SOLO Ciclo 1: `conformacion`/`intcarrera` no existen en el cuestionario
    # de Ciclo 2 (confirmado 2026-09-22, ver `base_maestra_c2.py`) - sin
    # parámetro `ciclo`, a propósito, para que no se pueda invocar con "C2"
    # por error.
    maestra = _leer_maestra("C1")

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(total_ganaderos=("peso_ganadero", "sum"))
    agg["total_ganaderos2"] = agg["total_ganaderos"]  # mismo total, repetido para el 2do bloque (ver docstring)

    columnas_totales: dict[str, list[str]] = {}
    bloques = [("conoce", "conformacion", "total_ganaderos"), ("interes", "intcarrera", "total_ganaderos2")]
    for prefijo, columna_raw, col_total in bloques:
        col_si, col_no = f"{prefijo}_si", f"{prefijo}_no"
        # "Si"/"Sí" tratados como la misma respuesta - ver docstring del
        # módulo. "Sí" (con tilde) llega truncada a 1 byte desde la fuente
        # (campo de longitud fija demasiado corta, se pierde la tilde) y
        # queda como "S" sola, NO como la "Sí" Unicode normal - verificado
        # byte por byte antes de escribir esto (sin este ajuste, ~3.300
        # respuestas afirmativas de ~730.000 desaparecían silenciosamente).
        sub_si = _suma_por(maestra, maestra[columna_raw].isin(["Si", "S"]), col_si)
        sub_no = _suma_por(maestra, maestra[columna_raw] == "No", col_no)
        agg = agg.merge(sub_si, on="CODIGO_MUNICIPIO", how="left").merge(sub_no, on="CODIGO_MUNICIPIO", how="left")
        agg[col_si] = agg[col_si].fillna(0.0)
        agg[col_no] = agg[col_no].fillna(0.0)
        columnas_totales[col_total] = [col_si, col_no]

    value_cols = ["total_ganaderos", "conoce_si", "conoce_no", "total_ganaderos2", "interes_si", "interes_no"]
    tabla = agregador.generar_cuadro(agg, value_cols, columnas_totales=columnas_totales)
    return tabla, value_cols


# --- Cuadro 7: ganaderos por sexo, persona jurídica y edad ---
# Rangos de edad EXACTOS de `edadganadero` (pregunta "4. Indique la edad del
# ganadero..." - R4 en C1; NO EXISTE en el cuestionario de Ciclo 2, ver
# `base_maestra_c2.py` - por eso este cuadro es solo Ciclo 1, igual que
# Cuadro 16). La plantilla original traía 4 rangos ("Menores 18"/"Entre 18 y
# 58"/"Entre 59 y 68"/"Mayor 69") que NO coinciden con ninguna categoría real
# de los datos (verificado 2026-09-24: los valores reales son estos 7,
# `value_counts()` sobre las 729.875 filas de `base_maestra_c1`, sin nulos)
# - a pedido del usuario ("los límites de edad se deben reportar como están
# construidos en la encuesta"), se usa la categorización REAL, no la de la
# plantilla - la plantilla (`TEMPLATE_GANADERO`, hoja "Cuadro 7") se amplió
# de 5 a 8 columnas por bloque (Total + 7 rangos, antes Total + 4) para que
# quepan.
RANGOS_EDAD_ORDEN = [
    "Menor o igual a 15 años", "De 16 a 25 años", "De 26 a 35 años", "De 36 a 45 años",
    "De 46 a 55 años", "De 56 a 65 años", "Mayor o igual a 66 años",
]
_RANGO_EDAD_SLUG = {
    "Menor o igual a 15 años": "men_15", "De 16 a 25 años": "16_25", "De 26 a 35 años": "26_35",
    "De 36 a 45 años": "36_45", "De 46 a 55 años": "46_55", "De 56 a 65 años": "56_65",
    "Mayor o igual a 66 años": "may_66",
}
# Orden de bloques de la plantilla real (Mujer, Hombres, Persona Jurídica -
# verificado columna por columna, NO es el mismo orden que `_GENERO_PREFIJO`
# usa para otros cuadros de este módulo).
_GENERO_PREFIJO_CUADRO7 = [("muj", "Mujer"), ("hom", "Hombre"), ("jur", config.GENERO_JURIDICA)]


def generar_cuadro7() -> tuple[pd.DataFrame, list[str]]:
    # SOLO Ciclo 1: `edadganadero` no existe en Ciclo 2 - sin parámetro
    # `ciclo`, a propósito (mismo criterio que Cuadro 16).
    maestra = _leer_maestra("C1")

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(total_ganaderos=("peso_ganadero", "sum"))

    columnas_totales: dict[str, list[str]] = {}
    value_cols = ["total_ganaderos"]
    for prefijo, genero in _GENERO_PREFIJO_CUADRO7:
        subset = maestra[maestra["genero"] == genero]
        col_total_bloque = f"{prefijo}_total"
        cols_rango = [f"{prefijo}_{_RANGO_EDAD_SLUG[r]}" for r in RANGOS_EDAD_ORDEN]
        for rango, col in zip(RANGOS_EDAD_ORDEN, cols_rango):
            sub = _suma_por(subset, subset["edadganadero"] == rango, col)
            agg = agg.merge(sub, on="CODIGO_MUNICIPIO", how="left")
        agg[cols_rango] = agg[cols_rango].fillna(0.0)
        agg[col_total_bloque] = agg[cols_rango].sum(axis=1)
        columnas_totales[col_total_bloque] = cols_rango
        value_cols += [col_total_bloque] + cols_rango

    # "total_ganaderos" (columna E) SÍ se deriva como suma de los 3 bloques
    # de género - corregido 2026-09-25 (el usuario detectó el residuo):
    # a diferencia de Cuadro 6 (delitos, categorías NO excluyentes, ahí sí
    # está justificado no forzar la suma), acá Mujer/Hombre/Persona Jurídica
    # SÍ son excluyentes y exhaustivas - la versión anterior dejaba
    # "total_ganaderos" independiente "para coincidir con Cuadro 1/3", pero
    # esa razón no aplicaba: Cuadro 3 (mismo desglose de género, este mismo
    # libro) YA deriva su total igual que acá, y tampoco se valida cruzado
    # contra Cuadro 1 - dejar Cuadro 7 distinto era una inconsistencia, no
    # una decisión real. Con esto, mujeres+hombres+jurídica = total_ganaderos
    # exacto, igual que Cuadro 3.
    columnas_totales["total_ganaderos"] = [f"{p}_total" for p, _ in _GENERO_PREFIJO_CUADRO7]
    tabla = agregador.generar_cuadro(agg, value_cols, columnas_totales=columnas_totales)
    return tabla, value_cols
