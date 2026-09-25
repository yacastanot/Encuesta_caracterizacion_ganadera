"""Base mínima "ganadero" (identidad + `peso_ganadero`) por ciclo histórico -
SOLO para el Cuadro 4/5 del libro "ganadero" (`cuadros/ganadero_historico.py`),
que únicamente necesitan "Total de ganaderos" por municipio y la identidad de
cada ganadero (`IDENT_GANADERO`) para el cruce de altas/bajas entre ciclos -
a diferencia de `base_maestra_c1.py`/`_c2.py` (2025), NO hace falta ninguna
pregunta de encuesta ni las otras 2 unidades de conteo (`peso_predio_fisico`/
`peso_predio_ganadero`), así que esta base es deliberadamente mucho más
liviana.

2024 (`construir_2024`): reconstruido desde cero, misma disciplina que 2025
- únicamente `cal_cobertura` (el único factor que necesita `peso_ganadero`,
ver `base_maestra_c1.py`), calculado independiente en
`calibracion_cobertura_historico.py`. Deduplicado por `predioganid` con
`preparar_base_c1.deduplicar_predio_ganadero` (misma cascada; sin
`cantvacasord` disponible acá, cae a `TOTAL_AFT_BOV` > `FECHA_CREACION`, ver
docstring de esa función - comportamiento ya previsto, no un caso especial).

2023 (`leer_2023`): decisión del usuario (2026-09-24) - se usa el archivo
`c12023.sas7bdat`/`c22023.sas7bdat` (el más reciente de la carpeta, ver
`config.py`) TAL CUAL, incluyendo su columna `gan_cal` ya calibrada por el
pipeline legado (NO se recalcula `cal_cobertura` para este año) - 2023 solo
sirve de referencia para el "ciclo anterior"/"año anterior" de Cuadro 4/5, no
se publica ningún cuadro de 2023 en este libro.

EXCLUSIÓN DE MUNICIPIOS (2024/2023) - a pedido del usuario (2026-09-24):
mismos 2 motivos que ya se excluyen en 2025 (`config.MUNICIPIOS_EXCLUIDOS_C1`/
`_C2`), aplicados a los 4 ciclos históricos:
 - **ZLSV/"o.c."** (`config._EXCLUIDOS_C1_ZLSV`, 27 municipios): se reutiliza
   LA MISMA lista que 2025 - es una designación de zona libre de vacunación/
   fuera de control geográfica y regulatoria, no específica de un ciclo o año
   (ya es idéntica entre C1 y C2 2025 en el archivo oficial) - no hay
   evidencia de que cambie año a año, pero tampoco se verificó contra un
   archivo oficial específico de 2023/2024 (no existe uno en el servidor)
   - asunción explícita, no un hecho confirmado por archivo propio del año.
 - **<80% cobertura**: NO es el mismo criterio exacto que 2025 (tasa de
   RESPUESTA de encuesta sobre el universo RUV) - acá se usa la tasa de
   VACUNACIÓN de Fedegán (`Total Predios Cobertura`, la misma que ya
   alimenta `cal_cobertura`) por disponibilidad uniforme en 2023/2024, ver
   `calibracion_cobertura_historico.municipios_baja_cobertura`. Da muy pocos
   municipios (0-3 por ciclo, contra 17 en C2 2025) porque son criterios
   distintos - la tasa de vacunación de Fedegán rara vez es tan baja como la
   tasa de respuesta de encuesta.

No se excluyen "encuestas repetidas" (motivo 3 de 2025): es un hallazgo de
control de calidad operativo específico de cada ciclo, no hay archivo
oficial de esa clase para 2023/2024 en el servidor.
"""
from __future__ import annotations

import pandas as pd

from . import calibracion_cobertura_historico, config, fuente_cruda_historico, preparar_base_c1, preparar_historico_2024

_RUTA_2023 = {1: config.RUTA_2023_C1, 2: config.RUTA_2023_C2}
_COLS_2023 = ["predioganid", "CODIGO_SIT", "IDENT_GANADERO", "CODIGO_MUNICIPIO", "TOTAL_AFT_BOV", "FECHA_CREACION", "gan_cal"]


def _municipios_excluidos(anio: int, ciclo: int) -> dict[str, str]:
    excluidos = dict(config._EXCLUIDOS_C1_ZLSV)
    excluidos.update(calibracion_cobertura_historico.municipios_baja_cobertura(anio, ciclo))
    return excluidos


def construir_2024(ciclo: int) -> pd.DataFrame:
    df = preparar_historico_2024.leer(ciclo)
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)
    df = df[~df["CODIGO_MUNICIPIO"].isin(_municipios_excluidos(2024, ciclo))]
    df = preparar_base_c1.deduplicar_predio_ganadero(df)

    conteo_predios_ganadero = df.groupby("IDENT_GANADERO")["predioganid"].transform("count").fillna(1)

    factor = calibracion_cobertura_historico.calcular_cal_cobertura(2024, ciclo)
    df = df.merge(factor, on="CODIGO_MUNICIPIO", how="left")
    df["cal_cobertura"] = df["cal_cobertura"].fillna(1.0)

    df["peso_ganadero"] = (1.0 / conteo_predios_ganadero) * df["cal_cobertura"]
    return df[["predioganid", "IDENT_GANADERO", "CODIGO_MUNICIPIO", "peso_ganadero"]]


def leer_2023(ciclo: int) -> pd.DataFrame:
    df = fuente_cruda_historico.leer(_RUTA_2023[ciclo], columns=_COLS_2023)
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)
    df = df[~df["CODIGO_MUNICIPIO"].isin(_municipios_excluidos(2023, ciclo))]

    duplicados = df["predioganid"].duplicated().sum()
    if duplicados:
        # No verificado de antemano que `c12023`/`c22023` ya vengan
        # deduplicados por `predioganid` - se aplica la misma cascada por si
        # acaso, en vez de asumirlo (mismo criterio del resto del proyecto).
        df = preparar_base_c1.deduplicar_predio_ganadero(df.drop(columns=["predioganid"]))

    return df[["predioganid", "IDENT_GANADERO", "CODIGO_MUNICIPIO"]].assign(peso_ganadero=df["gan_cal"])
