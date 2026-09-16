"""Carga y calibración de la base RUV cruda del Ciclo 2 (formato distinto al
de Ciclo 1: nombres de columna crudos del RUV/DMC, bovinos+bufalinos en un
solo archivo).

A diferencia de `preparar_base.py` (Ciclo 1, donde el CSV ya trae aplicado el
factor de calibración), aquí SIEMPRE se parte de las columnas AFT_* crudas
(sin calibrar) y se multiplican por el factor de `calibracion_c2.py` - las
columnas `*_CAL` que trae el CSV original NO se usan porque están corruptas
(ver docstring de `calibracion_c2.py`).

Los mapeos de columnas se verificaron 1 a 1 contra el encabezado real del CSV
(no por posición), igual que se hizo para R7/R11 en Ciclo 1.
"""
from __future__ import annotations

import warnings

import pandas as pd

from . import config

# --- Inventario: raw (SIN "_CAL") -> nombre canónico, igual convención que
# `preparar_base._COLS_INVENTARIO_BOV` / `_COLS_INVENTARIO_BUF`. ---
_RENOMBRE_INVENTARIO_BOVINOS_C2 = {
    "AFTOSA BOVINOS HEMBRAS MENORES A 3 MESES": "AFT_BOV_HEM_MEN_3_MES",
    "AFTOSA BOVINOS HEMBRAS MENORES DE 3 A 8 MESES": "AFT_BOV_HEM_MEN_DE_3_8_MES",
    "AFTOSA BOVINOS DE 8 A 12 MESES": "AFT_BOV_DE_8_12_MES",
    "AFTOSA BOVINOS HEMBRAS 1 - 2 AÑOS": "AFT_BOV_HEM_1_2_ANI",
    "AFTOSA BOVINOS HEMBRAS 2 - 3 AÑOS": "AFT_BOV_HEM_2_3_ANI",
    "AFTOSA BOVINOS HEMBRAS 3 - 5 AÑOS": "AFT_BOV_HEM_3_5_ANI",
    "AFTOSA BOVINOS HEMBRAS MAYORES A 5 AÑOS": "AFT_BOV_HEM_MAY_5_ANI",
    "AFTOSA BOVINOS MACHOS 1 - 2 AÑOS": "AFT_BOV_MAC_1_2_ANI",
    "AFTOSA BOVINOS MACHOS 2 - 3 AÑOS": "AFT_BOV_MAC_2_3_ANI",
    "AFTOSA BOVINOS MACHOS MAYORES A 3 AÑOS": "AFT_BOV_MAC_MAY_3_ANI",
    "AFTOSA BOVINOS MACHOS MENORES A 3 MESES": "AFT_BOV_MAC_MEN_3_MES",
    "AFTOSA BOVINOS MACHOS 3 HASTA 8 MESES": "AFT_BOV_MAC_3_8_MES",
    "AFTOSA BOVINOS MACHOS 8 HASTA 12 MESES": "AFT_BOV_MAC_8_12_MES",
    "AFTOSA BOVINOS HEMBRAS MENORES A 3 MESES NV": "AFT_BOV_HEM_MEN_3_MES_NV",
    "AFTOSA BOVINOS HEMBRAS MENORES DE 3 A 8 MESES NV": "AFT_BOV_HEM_MEN_DE_3_8_MES_NV",
    "AFTOSA BOVINOS DE 8 A 12 MESES NV": "AFT_BOV_DE_8_12_MES_NV",
    "AFTOSA BOVINOS HEMBRAS 1 - 2 AÑOS NV": "AFT_BOV_HEM_1_2_ANI_NV",
    "AFTOSA BOVINOS HEMBRAS 2 - 3 AÑOS NV": "AFT_BOV_HEM_2_3_ANI_NV",
    "AFTOSA BOVINOS HEMBRAS 3 - 5 AÑOS NV": "AFT_BOV_HEM_3_5_ANI_NV",
    "AFTOSA BOVINOS HEMBRAS MAYORES A 5 AÑOS NV": "AFT_BOV_HEM_MAY_5_ANI_NV",
    "AFTOSA BOVINOS MACHOS 1 - 2 AÑOS NV": "AFT_BOV_MAC_1_2_ANI_NV",
    "AFTOSA BOVINOS MACHOS 2 - 3 AÑOS NV": "AFT_BOV_MAC_2_3_ANI_NV",
    "AFTOSA BOVINOS MACHOS MAYORES A 3 AÑOS NV": "AFT_BOV_MAC_MAY_3_ANI_NV",
    "AFTOSA BOVINOS MACHOS MENORES A 3 MESES NV": "AFT_BOV_MAC_MEN_3_MES_NV",
    "AFTOSA BOVINOS MACHOS 3 HASTA 8 MESES NV": "AFT_BOV_MAC_3_8_MES_NV",
    "AFTOSA BOVINOS MACHOS 8 HASTA 12 MESES NV": "AFT_BOV_MAC_8_12_MES_NV",
}

_RENOMBRE_INVENTARIO_BUFALINOS_C2 = {
    "AFTOSA BUFALINOS HEMBRAS MENORES A 3 MESES": "AFT_BUF_HEM_MEN_3_MES",
    "AFTOSA BUFALINOS HEMBRAS MENORES DE 3 A 8 MESES": "AFT_BUF_HEM_MEN_DE_3_8_MES",
    "AFTOSA BUFALINOS DE 8 A 12 MESES": "AFT_BUF_DE_8_12_MES",
    "AFTOSA BUFALINOS HEMBRAS 1 - 2 AÑOS": "AFT_BUF_HEM_1_2_ANI",
    "AFTOSA BUFALINOS HEMBRAS 2 - 3 AÑOS": "AFT_BUF_HEM_2_3_ANI",
    "AFTOSA BUFALINOS HEMBRAS 3 - 5 AÑOS": "AFT_BUF_HEM_3_5_ANI",
    "AFTOSA BUFALINOS HEMBRAS MAYORES A 5 AÑOS": "AFT_BUF_HEM_MAY_5_ANI",
    "AFTOSA BUFALINOS MACHOS 1 - 2 AÑOS": "AFT_BUF_MAC_1_2_ANI",
    "AFTOSA BUFALINOS MACHOS 2 - 3 AÑOS": "AFT_BUF_MAC_2_3_ANI",
    "AFTOSA BUFALINOS MACHOS MAYORES A 3 AÑOS": "AFT_BUF_MAC_MAY_3_ANI",
    "AFTOSA BUFALINOS MACHOS MENORES A 3 MESES": "AFT_BUF_MAC_MEN_3_MES",
    "AFTOSA BUFALINOS MACHOS 3 HASTA 8 MESES": "AFT_BUF_MAC_3_8_MES",
    "AFTOSA BUFALINOS MACHOS 8 HASTA 12 MESES": "AFT_BUF_MAC_8_12_MES",
    "AFTOSA BUFALINOS HEMBRAS MENORES A 3 MESES NV": "AFT_BUF_HEM_MEN_3_MES_NV",
    "AFTOSA BUFALINOS HEMBRAS MENORES DE 3 A 8 MESES NV": "AFT_BUF_HEM_MEN_DE_3_8_MES_NV",
    "AFTOSA BUFALINOS DE 8 A 12 MESES NV": "AFT_BUF_DE_8_12_MES_NV",
    "AFTOSA BUFALINOS HEMBRAS 1 - 2 AÑOS NV": "AFT_BUF_HEM_1_2_ANI_NV",
    "AFTOSA BUFALINOS HEMBRAS 2 - 3 AÑOS NV": "AFT_BUF_HEM_2_3_ANI_NV",
    "AFTOSA BUFALINOS HEMBRAS 3 - 5 AÑOS NV": "AFT_BUF_HEM_3_5_ANI_NV",
    "AFTOSA BUFALINOS HEMBRAS MAYORES A 5 AÑOS NV": "AFT_BUF_HEM_MAY_5_ANI_NV",
    "AFTOSA BUFALINOS MACHOS 1 - 2 AÑOS NV": "AFT_BUF_MAC_1_2_ANI_NV",
    "AFTOSA BUFALINOS MACHOS 2 - 3 AÑOS NV": "AFT_BUF_MAC_2_3_ANI_NV",
    "AFTOSA BUFALINOS MACHOS MAYORES A 3 AÑOS NV": "AFT_BUF_MAC_MAY_3_ANI_NV",
    "AFTOSA BUFALINOS MACHOS MENORES A 3 MESES NV": "AFT_BUF_MAC_MEN_3_MES_NV",
    "AFTOSA BUFALINOS MACHOS 3 HASTA 8 MESES NV": "AFT_BUF_MAC_3_8_MES_NV",
    "AFTOSA BUFALINOS MACHOS 8 HASTA 12 MESES NV": "AFT_BUF_MAC_8_12_MES_NV",
}

_RENOMBRE_OTRAS_ESPECIES_C2 = {
    "TOTAL EQUINOS": "TOTAL_EQUINOS", "EQUINOS MACHO": "EQUINOS_MACHO", "EQUINOS HEMBRA": "EQUINOS_HEMBRA",
    "TOTAL PORCINOS": "TOTAL_PORCINOS", "PORCINOS MACHO": "PORCINOS_MACHO", "PORCINOS HEMBRA": "PORCINOS_HEMBRA",
    "TOTAL OVINOS": "TOTAL_OVINOS", "OVINOS MACHO": "OVINOS_MACHO", "OVINOS HEMBRA": "OVINOS_HEMBRA",
    "TOTAL CAPRINOS": "TOTAL_CAPRINOS", "CAPRINOS MACHO": "CAPRINOS_MACHO", "CAPRINOS HEMBRA": "CAPRINOS_HEMBRA",
    "TOTAL OTROS": "TOTAL_OTROS", "OTROS MACHO": "OTROS_MACHO", "OTROS HEMBRA": "OTROS_HEMBRA",
}

_ESPECIE_A_RENOMBRE = {"bovinos": _RENOMBRE_INVENTARIO_BOVINOS_C2, "bufalinos": _RENOMBRE_INVENTARIO_BUFALINOS_C2}
_ESPECIE_A_COL_FACTOR = {"bovinos": "F_AJUSTA_BOVINOS", "bufalinos": "F_AJUSTA_BUFALINOS"}


def _leer_csv_c2(usecols: list[str]) -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", pd.errors.DtypeWarning)
        return pd.read_csv(
            config.RUTA_C2, sep=";", encoding="utf-8-sig", encoding_errors="replace",
            decimal=",", usecols=usecols,
        )


def _cargar_factor_c2() -> pd.DataFrame:
    factor = pd.read_csv(config.RUTA_FACTOR_C2, sep=";", decimal=",", dtype={"CODIGO_MUNICIPIO": str})
    factor["CODIGO_MUNICIPIO"] = factor["CODIGO_MUNICIPIO"].str.zfill(5)
    return factor


def cargar_inventario_c2(especie: str, incluir_orientacion: bool = False) -> pd.DataFrame:
    """Bovinos o bufalinos, Segundo Ciclo: columnas AFT_* crudas del RUV,
    calibradas aquí mismo con el factor de `calibracion_c2.py` (NO con las
    columnas `_CAL` del CSV original, que están corruptas)."""
    especie = especie.lower()
    renombre = _ESPECIE_A_RENOMBRE[especie]
    col_factor = _ESPECIE_A_COL_FACTOR[especie]

    columnas_raw = list(renombre.keys())
    usecols = ["CODIGO MUNICIPIO"] + columnas_raw + (["R3"] if incluir_orientacion else [])
    df = _leer_csv_c2(usecols)
    df = df.rename(columns=renombre)
    df["CODIGO_MUNICIPIO"] = df["CODIGO MUNICIPIO"].astype(str).str.zfill(5)

    factor = _cargar_factor_c2()[["CODIGO_MUNICIPIO", col_factor]]
    df = df.merge(factor, on="CODIGO_MUNICIPIO", how="left")
    df[col_factor] = df[col_factor].fillna(1.0)
    for col in renombre.values():
        df[col] = df[col].fillna(0) * df[col_factor]

    if incluir_orientacion:
        df["orientacionhato"] = df["R3"].replace(config.ORIENTACION_HATO_NORMALIZA)

    return df


def cargar_otras_especies_c2() -> pd.DataFrame:
    """Otras especies pecuarias, Segundo Ciclo: sin calibrar (el RUV/SAS
    original tampoco aplica factor aquí, ver `preparar_base.generar_otras_especies`)."""
    columnas_raw = list(_RENOMBRE_OTRAS_ESPECIES_C2.keys())
    df = _leer_csv_c2(["CODIGO MUNICIPIO"] + columnas_raw)
    df = df.rename(columns=_RENOMBRE_OTRAS_ESPECIES_C2)
    df["CODIGO_MUNICIPIO"] = df["CODIGO MUNICIPIO"].astype(str).str.zfill(5)
    return df
