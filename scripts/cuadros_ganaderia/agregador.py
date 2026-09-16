"""Motor genérico de agregación territorial (municipio -> departamento -> nacional).

Traducción a Python de la macro SAS `%generar_cuadro_custom3`, presente e
idéntica en los 3 programas de "Programas Carolina":

1. Agrega a nivel municipal.
2. Cruza (join COMPLETO, no inner) contra el catálogo DIVIPOLA de municipios,
   para que aparezcan todos los municipios aunque no tengan datos (quedan en 0,
   no se pierden filas).
3. Reagrega el nivel municipal ya completo a nivel departamental, y lo cruza
   contra el catálogo completo de departamentos.
4. Reagrega a nivel nacional (una sola fila, o una fila por categoría extra si
   el cuadro desagrega por una variable adicional como `orientacionhato`).
5. Apila nacional + departamental + municipal, en ese orden, y dentro de cada
   departamento deja primero su fila de subtotal y luego sus municipios
   (equivalente al orden que produce SAS al ordenar por COD_DEPARTAMENTO /
   COD_MUNICIPIO, donde los valores missing del subtotal departamental ordenan
   primero).
"""
from __future__ import annotations

import pandas as pd

from . import catalogo_territorial

NIVEL_NACIONAL = "Nacional"
NIVEL_DEPARTAMENTO = "Departamento"
NIVEL_MUNICIPIO = "Municipio"


def generar_cuadro(
    df: pd.DataFrame,
    value_cols: list[str],
    group_extra: list[str] | None = None,
    catalogo_mun: pd.DataFrame | None = None,
    catalogo_dep: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Genera un cuadro con jerarquía Nacional -> Departamento -> Municipio.

    Parameters
    ----------
    df: base ya preparada (filtrada, recodificada), con columnas
        CODIGO_MUNICIPIO + `value_cols` + `group_extra`.
    value_cols: columnas numéricas a sumar.
    group_extra: columnas de categoría adicionales que se convierten en
        dimensión de fila extra (ej. ["ohOrden", "orientacionhato"]). El orden
        de la lista determina el orden de clasificación final (poner primero
        la columna *Orden numérica). Si es None, no hay desagregación extra.

    Returns
    -------
    DataFrame con columnas: NIVEL, COD_DEPARTAMENTO, DEPARTAMENTO,
    CODIGO_MUNICIPIO, MUNICIPIO, [group_extra...], [value_cols...], ya
    ordenado Nacional -> (Departamento, sus Municipios) por cada departamento.
    """
    group_extra = list(group_extra or [])
    catalogo_mun = catalogo_mun if catalogo_mun is not None else catalogo_territorial.cargar_catalogo_municipios()
    catalogo_dep = catalogo_dep if catalogo_dep is not None else catalogo_territorial.cargar_catalogo_departamentos()

    group_cols_mun = ["CODIGO_MUNICIPIO"] + group_extra
    mun_agg = df.groupby(group_cols_mun, as_index=False, dropna=False)[value_cols].sum()

    if group_extra:
        categorias = df[group_extra].drop_duplicates()
        universo_mun = catalogo_mun.merge(categorias, how="cross")
    else:
        categorias = None
        universo_mun = catalogo_mun.copy()

    mun_full = universo_mun.merge(mun_agg, on=group_cols_mun, how="left")
    mun_full[value_cols] = mun_full[value_cols].fillna(0)

    dep_group_cols = ["COD_DEPARTAMENTO"] + group_extra
    dep_agg = mun_full.groupby(dep_group_cols, as_index=False, dropna=False)[value_cols].sum()
    universo_dep = catalogo_dep.merge(categorias, how="cross") if group_extra else catalogo_dep.copy()
    dep_full = universo_dep.merge(dep_agg, on=dep_group_cols, how="left")
    dep_full[value_cols] = dep_full[value_cols].fillna(0)

    if group_extra:
        nac_agg = mun_full.groupby(group_extra, as_index=False, dropna=False)[value_cols].sum()
        nac_full = categorias.merge(nac_agg, on=group_extra, how="left")
        nac_full[value_cols] = nac_full[value_cols].fillna(0)
    else:
        nac_full = pd.DataFrame([mun_full[value_cols].sum()])

    mun_full = mun_full.copy()
    mun_full["NIVEL"] = NIVEL_MUNICIPIO

    dep_full = dep_full.merge(catalogo_dep, on="COD_DEPARTAMENTO", how="left", suffixes=("", "_cat"))
    dep_full["NIVEL"] = NIVEL_DEPARTAMENTO
    dep_full["CODIGO_MUNICIPIO"] = ""
    dep_full["MUNICIPIO"] = ""

    nac_full["NIVEL"] = NIVEL_NACIONAL
    nac_full["COD_DEPARTAMENTO"] = "00"
    nac_full["DEPARTAMENTO"] = "Total Nacional"
    nac_full["CODIGO_MUNICIPIO"] = ""
    nac_full["MUNICIPIO"] = ""

    cols_orden = ["NIVEL", "COD_DEPARTAMENTO", "DEPARTAMENTO", "CODIGO_MUNICIPIO", "MUNICIPIO"] + group_extra + value_cols

    depmun = pd.concat([dep_full[cols_orden], mun_full[cols_orden]], ignore_index=True)
    depmun["_nivel_rank"] = (depmun["NIVEL"] == NIVEL_MUNICIPIO).astype(int)
    orden_cols = ["COD_DEPARTAMENTO", "_nivel_rank", "CODIGO_MUNICIPIO"] + group_extra
    depmun = depmun.sort_values(orden_cols).drop(columns="_nivel_rank")

    nac_full = nac_full[cols_orden]
    if group_extra:
        nac_full = nac_full.sort_values(group_extra)

    resultado = pd.concat([nac_full, depmun], ignore_index=True)
    return resultado.reset_index(drop=True)
