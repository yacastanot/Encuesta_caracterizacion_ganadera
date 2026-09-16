"""Universo territorial completo (departamentos y municipios DIVIPOLA).

Equivalente en Python a las tablas `departamentos` / `divipolamunicipios` que se
arman en el preámbulo de los 3 programas SAS ("Programas Carolina"), usadas para
que cada cuadro muestre TODOS los municipios/departamentos aunque no tengan datos
(join completo, no inner).

Fuente local: "Scripts calibración R/INSUMOS/DIVIPOLA_Municipios.xlsx", hoja
"Hoja2" (limpia: COD_DEPTO, Departamento, COD_MPIO, Municipio).
"""
from functools import lru_cache

import pandas as pd

from . import config


@lru_cache(maxsize=1)
def cargar_catalogo_municipios() -> pd.DataFrame:
    """Universo completo de municipios (~1122), uno por fila.

    Columnas: COD_DEPARTAMENTO (str, 2 dígitos), DEPARTAMENTO,
    CODIGO_MUNICIPIO (str, 5 dígitos), MUNICIPIO.
    """
    df = pd.read_excel(config.RUTA_DIVIPOLA, sheet_name="Hoja2", dtype=str)
    df = df.rename(
        columns={
            "COD_DEPTO": "COD_DEPARTAMENTO",
            "Departamento": "DEPARTAMENTO",
            "COD_MPIO": "CODIGO_MUNICIPIO",
            "Municipio": "MUNICIPIO",
        }
    )[["COD_DEPARTAMENTO", "DEPARTAMENTO", "CODIGO_MUNICIPIO", "MUNICIPIO"]]
    df["COD_DEPARTAMENTO"] = df["COD_DEPARTAMENTO"].str.zfill(2)
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].str.zfill(5)
    df = df.drop_duplicates(subset="CODIGO_MUNICIPIO").sort_values(
        ["COD_DEPARTAMENTO", "CODIGO_MUNICIPIO"]
    ).reset_index(drop=True)
    return df


@lru_cache(maxsize=1)
def cargar_catalogo_departamentos() -> pd.DataFrame:
    """Universo completo de departamentos (~33), uno por fila.

    Columnas: COD_DEPARTAMENTO (str, 2 dígitos), DEPARTAMENTO.
    """
    mun = cargar_catalogo_municipios()
    dep = (
        mun[["COD_DEPARTAMENTO", "DEPARTAMENTO"]]
        .drop_duplicates()
        .sort_values("COD_DEPARTAMENTO")
        .reset_index(drop=True)
    )
    return dep
