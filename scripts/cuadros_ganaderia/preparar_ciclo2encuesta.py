"""Reconstruye el equivalente de `ciclo1encuesta.sas7bdat` para Ciclo 2: une
el archivo de encuesta (solo respuestas + clave `ruv_id`) contra el universo
RUV completo (identificación/territorio/inventario), y calcula `predioganid`.

A diferencia de Ciclo 1 (donde `ciclo1ruv.sas7bdat`/`ciclo1encuesta.sas7bdat`
ya venían pre-unidos por SAS), acá `ExportarArchivoRuv.csv` y
`ExportarArchivoEncuesta2_2025.csv` son 2 archivos separados que hay que unir
nosotros - este módulo hace exactamente eso, una sola vez, y cachea el
resultado (mismo patrón de cacheo que `fuente_cruda_c2.py`).

CLAVE DE UNIÓN (verificado 2026-09-22, NO es lo que sugiere el nombre): la
columna `CODIGO RUV` del archivo RUV (posición 2) NO es la clave que
referencia `ruv_id` en el archivo de encuesta - sus rangos de valores ni
siquiera se solapan (`CODIGO RUV`: 177.223-12.500.610; `ruv_id`:
20.993.059-21.782.658). La clave real es la columna `RUV ID` (posición 188)
del archivo RUV: verificado que los 736.149 valores de `ruv_id` en la
encuesta tienen match exacto ahí (0 huérfanos del lado encuesta), y que
`RUV ID` es único en el RUV (750.531 valores únicos = todas las filas). Los
14.382 registros de RUV sin match en la encuesta (750.531 - 736.149) son
predios vacunados que NO respondieron la encuesta de caracterización -
exactamente el mismo patrón que Ciclo 1 (`ciclo1ruv` = universo completo vs.
`ciclo1encuesta` = subconjunto con encuesta).

Columnas de identificación renombradas a los mismos nombres canónicos que usa
el pipeline de Ciclo 1 (`preparar_base_c1._COLS_ID`), para poder reutilizar
`calcular_predioganid`/`deduplicar_predio_ganadero` y la lógica de los
módulos `calibracion_*_c1.py` casi sin cambios en sus equivalentes `_c2`.
`CICLO`/`AÑO` vienen en AMBOS archivos (ya verificados idénticos, `CICLO=2`/
`AÑO=2025` en el 100% de las filas de los dos) - se descarta la copia del
lado RUV tras el merge para no duplicar columnas.
"""
from __future__ import annotations

import pandas as pd

from . import config, fuente_cruda_c2, preparar_base_c2

RUTA_CACHE_JOIN = config.BASES_CALIBRADAS_DIR / "_cache_ciclo2encuesta_join.parquet"

_RENOMBRE_ID_RUV = {
    "CODIGO SIT": "CODIGO_SIT",
    "IDENTIFICACION GANADERO": "IDENT_GANADERO",
    "GANADERO ID": "GANADERO_ID",
    "PREDIO ID": "PREDIO_ID",
    "RUV ID": "RUV_ID",
    "DEPARTAMENTO": "DEPARTAMENTO",
    "MUNICIPIO": "MUNICIPIO",
    "CODIGO MUNICIPIO": "CODIGO_MUNICIPIO",
    "FECHA CREACION": "FECHA_CREACION",
    "GENERO": "GENERO",
    "TIPO PROPIEDAD": "TIPO_PROPIEDAD",
    "PREDIO CARGO": "PREDIO_CARGO",
    "TOTAL AFTOSA BOVINOS": "TOTAL_AFT_BOV",
    "TOTAL AFTOSA BOVINOS NV": "TOTAL_AFT_BOV_NV",
    "TOTAL AFTOSA BUFALINOS": "TOTAL_AFT_BUF",
    "TOTAL AFTOSA BUFALINOS NV": "TOTAL_AFT_BUF_NV",
}


def _asegurar_cache_join() -> None:
    """Construye `RUTA_CACHE_JOIN` si no existe. No devuelve nada - `leer()`
    lee el Parquet ya con poda de columnas (más liviano que cargarlo completo
    acá y podar después, igual que `fuente_cruda_c2.leer`)."""
    if RUTA_CACHE_JOIN.exists():
        return

    print("(preparar_ciclo2encuesta) armando el join RUV + encuesta - una sola vez...")
    encuesta = fuente_cruda_c2.leer_encuesta()
    ruv = fuente_cruda_c2.leer_ruv()

    # Renombrar columnas de tramo AFT_* ANTES del merge, reutilizando los
    # diccionarios ya verificados 1 a 1 de `preparar_base_c2.py` - evita
    # mantener ese mapeo duplicado en 2 módulos.
    ruv = ruv.rename(
        columns={
            **preparar_base_c2._RENOMBRE_INVENTARIO_BOVINOS_C2,
            **preparar_base_c2._RENOMBRE_INVENTARIO_BUFALINOS_C2,
            **preparar_base_c2._RENOMBRE_OTRAS_ESPECIES_C2,
            **_RENOMBRE_ID_RUV,
        }
    )

    n_ruv_id_encuesta = encuesta["ruv_id"].nunique()
    n_ruv_id_ruv = ruv["RUV_ID"].nunique()
    if n_ruv_id_encuesta != len(encuesta):
        raise ValueError(
            f"encuesta: 'ruv_id' no es único ({n_ruv_id_encuesta:,} valores únicos de "
            f"{len(encuesta):,} filas) - el join dejaría de ser 1 fila por encuesta."
        )
    if n_ruv_id_ruv != len(ruv):
        raise ValueError(
            f"RUV: 'RUV_ID' no es único ({n_ruv_id_ruv:,} valores únicos de "
            f"{len(ruv):,} filas) - el join podría duplicar filas de encuesta (fan-out)."
        )
    huerfanos_encuesta = set(encuesta["ruv_id"]) - set(ruv["RUV_ID"])
    if huerfanos_encuesta:
        raise ValueError(
            f"{len(huerfanos_encuesta):,} valores de 'ruv_id' en la encuesta no tienen match "
            f"en 'RUV_ID' del RUV (esperado: 0) - ej. {list(huerfanos_encuesta)[:10]}."
        )

    join = encuesta.merge(
        ruv, left_on="ruv_id", right_on="RUV_ID", how="inner", validate="one_to_one", suffixes=("", "_ruv")
    )
    assert len(join) == len(encuesta), (
        f"el join cambió el número de filas ({len(join):,} vs {len(encuesta):,} de encuesta) - "
        "no debería pasar con validate='one_to_one' + huérfanos ya descartados arriba."
    )

    # CICLO/AÑO vienen en los 2 archivos, ya verificados idénticos (=2/=2025 en
    # el 100%) - se descarta la copia del lado RUV (sufijo "_ruv" tras el merge).
    for col in ("CICLO", "AÑO"):
        col_ruv = f"{col}_ruv"
        if col_ruv in join.columns:
            distintos = (join[col] != join[col_ruv]).sum()
            if distintos:
                raise ValueError(f"{distintos:,} filas con '{col}' distinto entre encuesta y RUV tras el join.")
            join = join.drop(columns=[col_ruv])
    join = join.rename(columns={"AÑO": "ANIO"})

    join["predioganid"] = join["CODIGO_SIT"].astype(str) + join["IDENT_GANADERO"].astype(str)

    RUTA_CACHE_JOIN.parent.mkdir(parents=True, exist_ok=True)
    join.to_parquet(RUTA_CACHE_JOIN, index=False)
    print(f"(preparar_ciclo2encuesta) caché guardado: {RUTA_CACHE_JOIN} ({len(join):,} filas)")


def leer(columns: list[str] | None = None) -> pd.DataFrame:
    """Equivalente de `fuente_cruda_c1.leer(config.RUTA_CICLO1_ENCUESTA_CRUDO,
    ...)` para Ciclo 2 - RUV + encuesta ya unidos, `predioganid` ya calculado.
    Poda de columnas a nivel Parquet (liviano), igual que `fuente_cruda_c2.leer`."""
    _asegurar_cache_join()
    return pd.read_parquet(RUTA_CACHE_JOIN, columns=columns)


def leer_ruv_completo(columns: list[str] | None = None) -> pd.DataFrame:
    """Universo RUV completo (equivalente a `ciclo1ruv.sas7bdat`): TODOS los
    predios vacunados, hayan o no respondido la encuesta - a diferencia de
    `leer()` (solo los que sí respondieron). Mismo renombrado de columnas de
    identificación que `leer()`, con `predioganid` ya calculado. Solo la usa
    `calibracion_calruv_c2.py` (el único factor que necesita AMBOS universos -
    ver `calibracion_calruv_c1.py` para el porqué).

    `columns` poda DESPUÉS de renombrar/calcular `predioganid` (no a nivel
    Parquet, como sí hace `leer()`) - siempre se leen las columnas crudas
    necesarias para el renombrado + `predioganid`, sin importar qué pida
    `columns`; solo evita cargar además las ~260 columnas de tramo/otros
    campos que este universo no necesita."""
    cols_crudas = list(_RENOMBRE_ID_RUV.keys()) + ["AÑO"]
    ruv = fuente_cruda_c2.leer_ruv(columns=cols_crudas)
    ruv = ruv.rename(columns={**_RENOMBRE_ID_RUV, "AÑO": "ANIO"})
    ruv["predioganid"] = ruv["CODIGO_SIT"].astype(str) + ruv["IDENT_GANADERO"].astype(str)
    return ruv[columns] if columns is not None else ruv
