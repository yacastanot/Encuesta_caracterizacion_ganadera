"""Carga y limpieza de las bases RUV calibradas (bovinos / bufalinos).

Traducción a Python de "3. configura base.sas" (renombrado de preguntas,
normalización de texto, variables *Orden) y de la deduplicación por
predio-ganadero que aplican "4.2. cuadros ganadero.sas" / "4.3. cuadros predio
ganadero.sas".

Las bases fuente son CSV separados por ';', codificación UTF-8 con BOM y
decimal ',' (confirmado inspeccionando `Bases Calibradas/*.csv`).
"""
from __future__ import annotations

import pandas as pd

from . import config

# Columnas base de identificación / territorio necesarias en (casi) todos los usos.
_COLS_ID = [
    "CODIGO_SIT",
    "IDENT_GANADERO",
    "GANADERO_ID",
    "PREDIO_ID",
    "RUV_ID",
    "DEPARTAMENTO",
    "MUNICIPIO",
    "CODIGO_MUNICIPIO",
    "CICLO",
    "PERIODOCICLO",
    "FECHA_CREACION",
    "GENERO",
    "TIPO_PROPIEDAD",
    "PREDIO_CARGO",
    "F_AJUSTA_BOVINOS",
    "F_AJUSTA_BUFALINOS",
    "TOTAL_AFT_BOV",
    "TOTAL_AFTOSA_BOVINOS",
    "TOTAL_AFTOSA_BUFALINOS",
]

_TRAMOS_HEMBRA = ["MEN_3_MES", "MEN_DE_3_8_MES", None, "1_2_ANI", "2_3_ANI", "3_5_ANI", "MAY_5_ANI"]
# NOTA: el tramo "9-12 meses" hembra no lleva prefijo HEM en el esquema original
# del RUV (columna compartida `AFT_<ESP>_DE_8_12_MES`) - ver `columnas_inventario`.

_COLS_INVENTARIO_BOV = (
    [f"AFT_BOV_HEM_{t}" for t in ["MEN_3_MES", "MEN_DE_3_8_MES", "1_2_ANI", "2_3_ANI", "3_5_ANI", "MAY_5_ANI"]]
    + ["AFT_BOV_DE_8_12_MES"]
    + [f"AFT_BOV_MAC_{t}" for t in ["MEN_3_MES", "3_8_MES", "8_12_MES", "1_2_ANI", "2_3_ANI", "MAY_3_ANI"]]
)
_COLS_INVENTARIO_BUF = (
    [f"AFT_BUF_HEM_{t}" for t in ["MEN_3_MES", "MEN_DE_3_8_MES", "1_2_ANI", "2_3_ANI", "3_5_ANI", "MAY_5_ANI"]]
    + ["AFT_BUF_DE_8_12_MES"]
    + [f"AFT_BUF_MAC_{t}" for t in ["MEN_3_MES", "3_8_MES", "8_12_MES", "1_2_ANI", "2_3_ANI", "MAY_3_ANI"]]
)

_COLS_OTRAS_ESPECIES = [
    f"{esp}_{sexo}" for esp in ["EQUINOS", "PORCINOS", "OVINOS", "CAPRINOS", "OTROS"] for sexo in ["MACHO", "HEMBRA"]
] + [f"TOTAL_{esp}" for esp in ["EQUINOS", "PORCINOS", "OVINOS", "CAPRINOS", "OTROS"]]

_COLS_ENCUESTA = [f"R{i}" for i in range(1, 6)] + [f"R6_{i}" for i in range(1, 9)] + [f"R{i}" for i in range(7, 21)]


def _ruta(especie: str):
    especie = especie.lower()
    if especie == "bovinos":
        return config.RUTA_BOVINOS
    if especie == "bufalinos":
        return config.RUTA_BUFALINOS
    raise ValueError(f"especie desconocida: {especie!r} (use 'bovinos' o 'bufalinos')")


def columnas_inventario(especie: str) -> list[str]:
    return _COLS_INVENTARIO_BOV if especie.lower() == "bovinos" else _COLS_INVENTARIO_BUF


def _leer_csv(ruta, usecols=None) -> pd.DataFrame:
    # `encoding_errors="replace"`: algunas filas de la base (mezcla histórica de
    # encuesta en papel + DMC) traen bytes que no son UTF-8 válido. Se reemplazan
    # en vez de abortar la carga completa; no afecta columnas numéricas/códigos.
    #
    # `low_memory` se deja en su valor por defecto (True, lectura por bloques):
    # esta máquina tiene poca RAM libre y `low_memory=False` fuerza a pandas a
    # materializar el archivo completo en memoria antes de inferir tipos, lo que
    # ya causó un `MemoryError` cargando la base de bovinos (~750k filas). Con
    # `usecols` ya reducimos bastante el ancho, así que el ahorro por bloques
    # importa más que el warning ocasional de tipo mixto.
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", pd.errors.DtypeWarning)
        return pd.read_csv(
            ruta,
            sep=";",
            encoding="utf-8-sig",
            encoding_errors="replace",
            decimal=",",
            usecols=usecols,
        )


def cargar_base_cruda(especie: str, columnas_extra: list[str] | None = None) -> pd.DataFrame:
    """Carga la base calibrada con las columnas de identificación + las pedidas.

    `columnas_extra`: columnas adicionales específicas del cuadro que se va a
    construir (ej. columnas AFT_BOV_* para inventario, o R8/genero para
    cuadros de ganadero). Si es None, se cargan TODAS las columnas del CSV
    (útil para explorar, pero pesado en memoria).
    """
    ruta = _ruta(especie)
    if columnas_extra is None:
        usecols = None
    else:
        cabecera = pd.read_csv(
            ruta, sep=";", encoding="utf-8-sig", encoding_errors="replace", nrows=0
        ).columns.tolist()
        pedidas = set(_COLS_ID) | set(columnas_extra)
        usecols = [c for c in cabecera if c in pedidas]
    df = _leer_csv(ruta, usecols=usecols)
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(str).str.zfill(5)
    df["ESPECIE_BASE"] = especie.lower()
    return df


def renombrar_preguntas(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica el rename R1..R20 -> nombres de negocio (igual a `3. configura base.sas`)."""
    renombres = {k: v for k, v in config.RENOMBRE_PREGUNTAS.items() if k in df.columns}
    return df.rename(columns=renombres)


def normalizar_categoricas(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza texto de genero/orientacionhato/predio_cargo y agrega columnas *Orden.

    Réplica de la sección 8 del preámbulo SAS (idéntica en los 3 programas).
    """
    df = df.copy()

    if "orientacionhato" in df.columns:
        df["orientacionhato"] = df["orientacionhato"].replace(config.ORIENTACION_HATO_NORMALIZA)
        df["ohOrden"] = (
            df["orientacionhato"].map(config.ORIENTACION_HATO_ORDEN).fillna(config.ORIENTACION_HATO_ORDEN_DEFAULT)
        )

    if "GENERO" in df.columns:
        genero = df["GENERO"].replace(config.GENERO_NORMALIZA)
        es_juridica = genero.isna() | (genero.astype(str).str.lower() == "false") | (genero.astype(str).str.strip() == "")
        genero = genero.where(~es_juridica, config.GENERO_JURIDICA)
        df["genero"] = genero
        df["generoOrden"] = df["genero"].map(config.GENERO_ORDEN).fillna(config.GENERO_ORDEN_DEFAULT)

    if "PREDIO_CARGO" in df.columns:
        df["predioCargoOrden"] = (
            df["PREDIO_CARGO"].map(config.PREDIO_CARGO_ORDEN).fillna(config.PREDIO_CARGO_ORDEN_DEFAULT)
        )

    return df


def calcular_predioganid(df: pd.DataFrame) -> pd.DataFrame:
    """predioganid = CODIGO_SIT || ident_ganadero (idéntico a los 3 programas SAS)."""
    df = df.copy()
    df["predioganid"] = df["CODIGO_SIT"].astype(str) + df["IDENT_GANADERO"].astype(str)
    return df


def deduplicar_predio_ganadero(df: pd.DataFrame) -> pd.DataFrame:
    """Cascada de desempate por `predioganid` duplicado (4.2 / 4.3 cuadros *.sas):

    1) mayor `cantvacasord`; 2) entre empatados, mayor `total_aft_bov`;
    3) entre empatados, `fecha_creacion` más reciente.

    Solo debe usarse para cuadros de GANADERO / PREDIO-GANADERO. Los cuadros
    de INVENTARIO (4.1) no aplican esta deduplicación en el SAS original.
    """
    df = calcular_predioganid(df)
    total_col = "TOTAL_AFT_BOV" if "TOTAL_AFT_BOV" in df.columns else "TOTAL_AFTOSA_BOVINOS"
    orden_cols = []
    if "cantvacasord" in df.columns:
        orden_cols.append("cantvacasord")
    if total_col in df.columns:
        orden_cols.append(total_col)
    if "FECHA_CREACION" in df.columns:
        orden_cols.append("FECHA_CREACION")

    if not orden_cols:
        return df.drop_duplicates(subset="predioganid", keep="first")

    df_ordenado = df.sort_values(orden_cols, ascending=False, na_position="last")
    return df_ordenado.drop_duplicates(subset="predioganid", keep="first")


_FACTOR_C1_INVENTARIO_CACHE: pd.DataFrame | None = None


def _cargar_factor_c1_calculado() -> pd.DataFrame:
    """F_AJUSTA_BOVINOS/BUFALINOS CALCULADO por nosotros (`calibracion_c1.py`),
    no el que ya trae el CSV. Coincide exacto con el heredado (validado
    municipio por municipio, diferencia a nivel de precisión de punto
    flotante) pero se usa el propio por pedido explícito del usuario: no
    heredar un factor de calibración sin poder calcularlo y compararlo de
    forma independiente primero - mismo criterio que se aplicó para Ciclo 2
    (donde el heredado sí estaba corrupto)."""
    global _FACTOR_C1_INVENTARIO_CACHE
    if _FACTOR_C1_INVENTARIO_CACHE is None:
        factor = pd.read_csv(config.RUTA_FACTOR_C1_INVENTARIO, sep=";", decimal=",", dtype={"CODIGO_MUNICIPIO": str})
        factor["CODIGO_MUNICIPIO"] = factor["CODIGO_MUNICIPIO"].str.zfill(5)
        _FACTOR_C1_INVENTARIO_CACHE = factor
    return _FACTOR_C1_INVENTARIO_CACHE


def aplicar_factor_calibracion(df: pd.DataFrame, especie: str, columnas: list[str]) -> pd.DataFrame:
    """Multiplica cada columna de inventario (y su variante _NV) por el factor
    municipal F_AJUSTA_BOVINOS / F_AJUSTA_BUFALINOS, calculado por nosotros
    (ver `_cargar_factor_c1_calculado`), no el que ya trae el CSV.

    Réplica del paso del preámbulo SAS que multiplica todas las AFT_BOV_*/AFT_BUF_*
    por `cal_bovinos`/`cal_bufalinos`.
    """
    df = df.copy()
    factor_col = "F_AJUSTA_BOVINOS" if especie.lower() == "bovinos" else "F_AJUSTA_BUFALINOS"
    factor_tabla = _cargar_factor_c1_calculado()[["CODIGO_MUNICIPIO", factor_col]]
    df = df.drop(columns=[factor_col]).merge(factor_tabla, on="CODIGO_MUNICIPIO", how="left")
    factor = df[factor_col].fillna(1.0)
    for base_col in columnas:
        for col in (base_col, f"{base_col}_NV"):
            if col in df.columns:
                df[col] = df[col].fillna(0) * factor
    return df
