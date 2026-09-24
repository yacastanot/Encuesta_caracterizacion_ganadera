"""Carga y calibración de la base RUV de Ciclo 2 - REDIRIGIDO (2026-09-22,
instrucción explícita del usuario) desde `preparar_ciclo2encuesta.leer()`
(RUV + encuesta unidos desde los insumos crudos reales) en vez de
`config.RUTA_C2` (`base_ruv_calibrada_C2_2025.csv`, la base "ya calibrada"
que ahora solo se usa para comparar al final, nunca como fuente).

A diferencia de `preparar_base_c1.py` (Ciclo 1, donde el CSV ya trae aplicado
el factor de calibración), aquí SIEMPRE se parte de las columnas AFT_* crudas
(sin calibrar) y se multiplican por el factor de `calibracion_c2.py` - las
columnas `*_CAL` que traía el CSV original NO se usaban porque estaban
corruptas (ver docstring de `calibracion_c2.py`); ya no aplica: la fuente
actual (`preparar_ciclo2encuesta`) ni siquiera trae esas columnas `*_CAL`.

Los mapeos de columnas (`_RENOMBRE_INVENTARIO_*_C2`) se verificaron 1 a 1
contra el encabezado real del RUV crudo (`EncabezadoRuv2-2025.xlsx`, no por
posición) - se conservan tal cual, `preparar_ciclo2encuesta.py` ya los
reutiliza para dejar esas columnas con su nombre canónico ANTES de cachear el
join, así que acá ya no hace falta renombrar - solo pedirlas por su nombre
canónico y calibrarlas.

Excluye `config.MUNICIPIOS_EXCLUIDOS_C2` (ZLSV + encuestas repetidas + <80%
de cobertura de encuesta, 64 municipios en total - los 3 motivos, ya
completo, ver `config.py`).

Nivel ganadero/predio-ganadero (nuevo en esta fase, no existía antes):
`cargar_base_ganadero_c2` arma el equivalente de
`preparar_base_c1.cargar_base_cruda` + `renombrar_preguntas` +
`deduplicar_predio_ganadero` para Ciclo 2 - reutiliza
`preparar_base_c1.deduplicar_predio_ganadero` tal cual (la cascada de
desempate no depende de nada específico de Ciclo 1, solo de nombres de
columna canónicos que ya están presentes acá).
"""
from __future__ import annotations

import pandas as pd

from . import config, preparar_base_c1, preparar_ciclo2encuesta

# --- Inventario: raw (SIN "_CAL") -> nombre canónico, igual convención que
# `preparar_base_c1._COLS_INVENTARIO_BOV` / `_COLS_INVENTARIO_BUF`. ---
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


def _cargar_factor_c2() -> pd.DataFrame:
    factor = pd.read_csv(
        config.RUTA_FACTOR_C2, sep=";", decimal=",", encoding="utf-8-sig", dtype={"CODIGO_MUNICIPIO": str}
    )
    factor["CODIGO_MUNICIPIO"] = factor["CODIGO_MUNICIPIO"].str.zfill(5)
    return factor


def cargar_inventario_c2(especie: str, incluir_orientacion: bool = False) -> pd.DataFrame:
    """Bovinos o bufalinos, Segundo Ciclo: columnas AFT_* (ya con nombre
    canónico, ver `preparar_ciclo2encuesta.py`), calibradas aquí mismo con el
    factor de `calibracion_c2.py`."""
    especie = especie.lower()
    renombre = _ESPECIE_A_RENOMBRE[especie]
    col_factor = _ESPECIE_A_COL_FACTOR[especie]

    columnas_canonicas = list(renombre.values())
    cols = ["CODIGO_MUNICIPIO"] + columnas_canonicas + (["R3"] if incluir_orientacion else [])
    df = preparar_ciclo2encuesta.leer(columns=cols)
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)

    factor = _cargar_factor_c2()[["CODIGO_MUNICIPIO", col_factor]]
    df = df.merge(factor, on="CODIGO_MUNICIPIO", how="left")
    df[col_factor] = df[col_factor].fillna(1.0)
    for col in columnas_canonicas:
        df[col] = df[col].fillna(0) * df[col_factor]

    if incluir_orientacion:
        df["orientacionhato"] = df["R3"].replace(config.ORIENTACION_HATO_NORMALIZA)

    # Municipios excluidos del universo de Ciclo 2 - ver config.MUNICIPIOS_EXCLUIDOS_C2.
    df = df[~df["CODIGO_MUNICIPIO"].isin(config.MUNICIPIOS_EXCLUIDOS_C2)]

    return df


def cargar_otras_especies_c2() -> pd.DataFrame:
    """Otras especies pecuarias, Segundo Ciclo: sin calibrar (el RUV/SAS
    original tampoco aplica factor aquí, ver `preparar_base_c1.generar_otras_especies`)."""
    columnas_canonicas = list(_RENOMBRE_OTRAS_ESPECIES_C2.values())
    df = preparar_ciclo2encuesta.leer(columns=["CODIGO_MUNICIPIO"] + columnas_canonicas)
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)
    df = df[~df["CODIGO_MUNICIPIO"].isin(config.MUNICIPIOS_EXCLUIDOS_C2)]
    return df


# --- Ganadero / predio-ganadero (nuevo) ---

# Columnas de identificación/encuesta que necesita la familia ganadero/predio-
# ganadero, más allá de las de inventario - mismo espíritu que
# `preparar_base_c1._COLS_ID`/`_COLS_ENCUESTA_MASTER`, con nombres ya
# canónicos salvo las preguntas R*, que se renombran acá vía
# `config.RENOMBRE_PREGUNTAS_C2`.
_COLS_ID_C2 = [
    "CODIGO_SIT", "IDENT_GANADERO", "GANADERO_ID", "PREDIO_ID", "RUV_ID",
    "DEPARTAMENTO", "MUNICIPIO", "CODIGO_MUNICIPIO", "CICLO", "ANIO",
    "FECHA_CREACION", "GENERO", "TIPO_PROPIEDAD", "PREDIO_CARGO",
    "TOTAL_AFT_BOV", "TOTAL_AFT_BOV_NV", "TOTAL_AFT_BUF", "TOTAL_AFT_BUF_NV",
    "predioganid",
]


def cargar_base_ganadero_c2(columnas_encuesta_extra: list[str] | None = None) -> pd.DataFrame:
    """Equivalente de `preparar_base_c1.cargar_base_cruda("bovinos", ...)` +
    `renombrar_preguntas` para la familia ganadero/predio-ganadero de Ciclo 2:
    identificación/territorio + las preguntas R* pedidas, ya renombradas a su
    nombre de negocio (`config.RENOMBRE_PREGUNTAS_C2`), excluyendo
    `config.MUNICIPIOS_EXCLUIDOS_C2`. NO deduplica por `predioganid` - usar
    `deduplicar_predio_ganadero_c2` aparte (mismo criterio que Ciclo 1: cada
    cuadro decide si necesita la base deduplicada o no)."""
    columnas_encuesta_extra = list(columnas_encuesta_extra or [])
    renombre_pedido = {
        r: nombre for r, nombre in config.RENOMBRE_PREGUNTAS_C2.items() if nombre in columnas_encuesta_extra
    }
    faltantes = set(columnas_encuesta_extra) - set(renombre_pedido.values())
    if faltantes:
        raise ValueError(
            f"columnas_encuesta_extra pide {sorted(faltantes)}, que no están en "
            "config.RENOMBRE_PREGUNTAS_C2 - revisar el nombre o si esa pregunta existe en Ciclo 2."
        )

    cols_crudas = _COLS_ID_C2 + list(renombre_pedido.keys())
    df = preparar_ciclo2encuesta.leer(columns=cols_crudas)
    df = df.rename(columns=renombre_pedido)
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)
    df = df[~df["CODIGO_MUNICIPIO"].isin(config.MUNICIPIOS_EXCLUIDOS_C2)]
    return df


def deduplicar_predio_ganadero_c2(df: pd.DataFrame) -> pd.DataFrame:
    """Reutiliza `preparar_base_c1.deduplicar_predio_ganadero` tal cual - la
    cascada de desempate (mayor `cantvacasord` > mayor `TOTAL_AFT_BOV` >
    `FECHA_CREACION` más reciente) solo depende de nombres de columna
    canónicos, ya presentes acá."""
    return preparar_base_c1.deduplicar_predio_ganadero(df)
