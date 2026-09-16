"""Redistribución proporcional de registros "sin dato" en una variable de cruce.

Traducción a Python del bloque de imputación que usa "4.1. cuadros
inventario.sas" para el Cuadro 4 (inventario bovino por orientación de hato):
los predios que no reportaron `orientacionhato` no se descartan; su inventario
se reparte entre las orientaciones existentes según la mezcla de orientaciones
que sí se conoce en su mismo municipio (y si el municipio no tiene ninguna
orientación conocida, según la mezcla nacional).

Este mismo patrón se reutiliza más adelante para los cuadros de "ganadero" que
tienen la misma lógica de imputación (ej. Cuadro 7/8 de
"4.2. cuadros ganadero.sas": delitos con y sin orientación conocida).
"""
from __future__ import annotations

import pandas as pd


def redistribuir_por_categoria(
    df: pd.DataFrame,
    columna_categoria: str,
    columnas_valor: list[str],
    categorias: list[str],
) -> pd.DataFrame:
    """Reparte proporcionalmente el valor de los registros con `columna_categoria`
    vacía/nula entre las `categorias` conocidas, según la mezcla municipal (o
    nacional si el municipio no tiene ninguna categoría conocida).

    Requiere que `df` tenga columna "CODIGO_MUNICIPIO".

    Devuelve un DataFrame con columnas: CODIGO_MUNICIPIO, `columna_categoria`
    (una fila por cada categoría de `categorias`, para cada municipio presente
    en `df`) + `columnas_valor` ya con el reparto sumado.
    """
    cat = df[columna_categoria].astype(str).str.strip()
    tiene_categoria = df[columna_categoria].notna() & (cat != "") & (cat.str.lower() != "nan")

    validos = df[tiene_categoria]
    sin_categoria = df[~tiene_categoria]

    municipios = df["CODIGO_MUNICIPIO"].unique()
    universo = pd.MultiIndex.from_product(
        [municipios, categorias], names=["CODIGO_MUNICIPIO", columna_categoria]
    ).to_frame(index=False)

    base_mun = (
        validos.groupby(["CODIGO_MUNICIPIO", columna_categoria], as_index=False)[columnas_valor]
        .sum()
    )
    base = universo.merge(base_mun, on=["CODIGO_MUNICIPIO", columna_categoria], how="left")
    base[columnas_valor] = base[columnas_valor].fillna(0.0)

    total_mun = (
        validos.groupby("CODIGO_MUNICIPIO")[columnas_valor]
        .sum()
        .rename(columns={c: f"{c}__tot_mun" for c in columnas_valor})
    )
    base = base.merge(total_mun, on="CODIGO_MUNICIPIO", how="left")
    for c in columnas_valor:
        base[f"{c}__tot_mun"] = base[f"{c}__tot_mun"].fillna(0.0)

    total_nac = validos[columnas_valor].sum()
    base_nac = (
        validos.groupby(columna_categoria, as_index=False)[columnas_valor]
        .sum()
        .set_index(columna_categoria)
    )
    prop_nac = base_nac[columnas_valor].div(total_nac.replace(0, pd.NA), axis=1).fillna(0.0)
    prop_nac = prop_nac.rename(columns={c: f"{c}__prop_nac" for c in columnas_valor})
    base = base.merge(prop_nac, left_on=columna_categoria, right_index=True, how="left")
    for c in columnas_valor:
        base[f"{c}__prop_nac"] = base[f"{c}__prop_nac"].fillna(0.0)

    sin_mun = (
        sin_categoria.groupby("CODIGO_MUNICIPIO")[columnas_valor]
        .sum()
        .rename(columns={c: f"{c}__sin" for c in columnas_valor})
    )
    base = base.merge(sin_mun, on="CODIGO_MUNICIPIO", how="left")
    for c in columnas_valor:
        base[f"{c}__sin"] = base[f"{c}__sin"].fillna(0.0)

    for c in columnas_valor:
        prop_municipal = (base[c] / base[f"{c}__tot_mun"]).where(base[f"{c}__tot_mun"] > 0)
        prop = prop_municipal.fillna(base[f"{c}__prop_nac"]).fillna(0.0)
        base[c] = base[c] + base[f"{c}__sin"] * prop

    return base[["CODIGO_MUNICIPIO", columna_categoria] + columnas_valor]
