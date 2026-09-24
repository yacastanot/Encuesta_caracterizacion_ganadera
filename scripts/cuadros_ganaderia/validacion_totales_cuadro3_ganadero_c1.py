"""Valida Cuadro 3 del libro "ganadero" ("Cantidad de ganaderos por sexo y
persona jurídica") - a diferencia de Cuadro 3/7 (bovinos/bufalinos, libro
inventario) y Cuadro 1 (Total predios), acá NO hay ningún total de Fedegán
contra el cual reconciliar: Fedegán reporta predios y animales, nunca
ganaderos (personas) - ver columnas de `Cuadro 2_Cobertura` en
`config.RUTA_FEDEGAN_HISTORICO`, confirmado también al validar Cuadro 1.

Lo que SÍ se puede (y debe) validar acá es consistencia interna:
 1. "Total ganaderos" de Cuadro 3 debe coincidir EXACTO con "Total ganaderos"
    de Cuadro 1 (`cuadros/comun.py`) - ambos sacan la misma suma de
    `peso_ganadero` sobre la misma `base_maestra_c1`, solo que Cuadro 3 además
    la desagrega por género/persona jurídica. Cualquier diferencia indicaría
    un bug real (agrupación distinta, filtro que se coló, etc.).
 2. mujeres + hombres + jurídica debe sumar exacto el total, en cada
    municipio (las 3 categorías son mutuamente excluyentes y exhaustivas -
    `genero` no tiene nulos, ver `preparar_base_c1.normalizar_categoricas`).
 3. Los `config.MUNICIPIOS_EXCLUIDOS_C1` deben dar 0 en todas las columnas
    (sus predios ni siquiera entran a `base_maestra_c1`).
"""
from __future__ import annotations

import pandas as pd

from . import agregador, config
from .cuadros import comun, ganadero


def comparar() -> pd.DataFrame:
    tabla3, _ = ganadero.generar_cuadro3()
    tabla1, _ = comun.generar_cuadro1()

    m3 = tabla3[tabla3["NIVEL"] == agregador.NIVEL_MUNICIPIO][
        ["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO", "total_ganaderos", "natural_total", "mujeres", "hombres", "juridica"]
    ].copy()
    m1 = tabla1[tabla1["NIVEL"] == agregador.NIVEL_MUNICIPIO][["CODIGO_MUNICIPIO", "total_ganaderos"]].rename(
        columns={"total_ganaderos": "total_ganaderos_cuadro1"}
    )
    comp = m3.merge(m1, on="CODIGO_MUNICIPIO", how="left")

    comp["dif_vs_cuadro1"] = comp["total_ganaderos"] - comp["total_ganaderos_cuadro1"]
    comp["dif_componentes"] = comp["total_ganaderos"] - (comp["mujeres"] + comp["hombres"] + comp["juridica"])
    comp["excluido_del_universo_ruv"] = comp["CODIGO_MUNICIPIO"].isin(config.MUNICIPIOS_EXCLUIDOS_C1)

    return comp


def _validar(comp: pd.DataFrame) -> None:
    print(f"Municipios comparados: {len(comp)}")

    dif_c1 = comp[comp["dif_vs_cuadro1"].abs() > 1e-6]
    print(f"\n1) Cuadro 3 vs Cuadro 1 (deben coincidir exacto): {len(dif_c1)} municipios con diferencia")
    if len(dif_c1):
        print(dif_c1[["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO", "total_ganaderos", "total_ganaderos_cuadro1", "dif_vs_cuadro1"]].to_string())

    dif_comp = comp[comp["dif_componentes"].abs() > 1e-6]
    print(f"\n2) mujeres + hombres + jurídica == total (deben coincidir exacto): {len(dif_comp)} municipios con diferencia")
    if len(dif_comp):
        print(dif_comp[["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO", "total_ganaderos", "mujeres", "hombres", "juridica"]].to_string())

    excluidos = comp[comp["excluido_del_universo_ruv"]]
    con_dato = excluidos[excluidos["total_ganaderos"].abs() > 1e-9]
    print(f"\n3) Municipios excluidos del universo con algún ganadero > 0 (debe ser 0): {len(con_dato)} / {len(excluidos)}")
    if len(con_dato):
        print(con_dato[["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO", "total_ganaderos"]].to_string())

    total_nacional = comp["total_ganaderos"].sum()
    print(f"\nTotal nacional de ganaderos: {total_nacional:,.1f}")
    print("(sin cifra de Fedegán con la cual comparar este total - ver docstring del módulo)")


def generar_y_guardar() -> None:
    comp = comparar()
    _validar(comp)
    ruta = config.BASES_CALIBRADAS_DIR / "validacion_cuadro3_ganadero_C1_2025.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    comp.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"\nGuardado: {ruta}")


if __name__ == "__main__":
    generar_y_guardar()
