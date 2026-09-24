"""Recalcula `cal_bovinos`/`cal_bufalinos` de Ciclo 2 2025 (2025-II), mirror
exacto de `calibracion_bovinos_bufalinos_c1.py`:

    cal_bovinos    = Total Bovinos PM    / bovinos encuesta
    cal_bufalinos  = Total Bufalinos PM  / bufalinos encuesta

`bovinos/bufalinos encuesta` = suma de `TOTAL_AFT_BOV + TOTAL_AFT_BOV_NV` (o
BUF) en el subconjunto que respondió la encuesta (`preparar_ciclo2encuesta.leer`,
ya calibrado 0 veces - estas son las columnas TOTAL crudas, sin calibrar,
igual que hace `calibracion_bovinos_bufalinos_c1.py` con `ciclo1encuesta`).

Reutiliza `calibracion_c2._fedegan_ciclo2_con_codigo_municipio()` - mismo
patrón que `calibracion_predios_c2.py`. Sin comparación contra heredado (no
existe `calibrac12025.xlsx` para Ciclo 2).

RESIDUO CONOCIDO Y ACEPTADO (bufalinos, verificado 2026-09-22): en el mismo
universo de municipios (excluyendo los 64 de `MUNICIPIOS_EXCLUIDOS_C2`), el
total nacional calibrado de bufalinos queda 47 unidades por debajo de
Fedegán (-0.007%, 641.998 vs 642.045) - explicado por completo por 5
municipios donde Fedegán reporta bufalinos pero el RUV/encuesta de Ciclo 2
tiene CERO registros de esa especie: Santa Fe de Antioquia (05042, -2),
La Mesa/Cundinamarca (25386, -2), Leiva/Nariño (52405, -1),
Cajamarca/Tolima (73124, -40), Flandes/Tolima (73275, -2). Cuando el
denominador (bufalinos en la encuesta) es 0, `cal_bufalinos` queda en 1.0
(`_factor_seguro`) y `0 * 1.0 = 0` - no hay ninguna cantidad real que
escalar, el factor no puede inventar animales que no están en la fuente.
Mismo tipo de caso que el residuo de Sibaté ya documentado para Ciclo 1
(`validacion_totales_inventario_c1.py`: "Fedegán con dato, sin ningún predio
en el RUV") - se deja como residuo real, NO se fuerza a cero excluyendo estos
5 municipios (tienen datos válidos de bovinos/otras especies que sí hace
falta conservar) ni fabricando un conteo sintético de bufalinos.
"""
from __future__ import annotations

import pandas as pd

from . import calibracion_c2, config, preparar_ciclo2encuesta

_COLS_ANIMAL = {
    "bovinos": ["TOTAL_AFT_BOV", "TOTAL_AFT_BOV_NV"],
    "bufalinos": ["TOTAL_AFT_BUF", "TOTAL_AFT_BUF_NV"],
}


def _sumar_animales_encuesta(especie: str) -> pd.Series:
    cols_val = _COLS_ANIMAL[especie]
    df = preparar_ciclo2encuesta.leer(columns=["CODIGO_MUNICIPIO"] + cols_val)
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)
    for c in cols_val:
        df[c] = df[c].fillna(0)
    df["total"] = df[cols_val].sum(axis=1)
    return df.groupby("CODIGO_MUNICIPIO")["total"].sum().rename(f"{especie}_encuesta")


def _factor_seguro(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    return (numerador / denominador).where(denominador > 0).fillna(1.0)


def calcular_cal_especie(especie: str) -> pd.DataFrame:
    col_pm = "Total Bovinos PM" if especie == "bovinos" else "Total Bufalinos PM"
    col_cal = "cal_bovinos" if especie == "bovinos" else "cal_bufalinos"

    fedegan_join = calibracion_c2._fedegan_ciclo2_con_codigo_municipio()
    fedegan = fedegan_join[["COD_MPIO", col_pm]].rename(columns={"COD_MPIO": "CODIGO_MUNICIPIO"})

    animales_encuesta = _sumar_animales_encuesta(especie)

    comp = fedegan.merge(animales_encuesta, on="CODIGO_MUNICIPIO", how="left")
    comp[f"{especie}_encuesta"] = comp[f"{especie}_encuesta"].fillna(0)
    comp[col_cal] = _factor_seguro(comp[col_pm], comp[f"{especie}_encuesta"])
    return comp


def _validar(especie: str, comp: pd.DataFrame) -> None:
    col_pm = "Total Bovinos PM" if especie == "bovinos" else "Total Bufalinos PM"
    col_cal = "cal_bovinos" if especie == "bovinos" else "cal_bufalinos"
    print(f"\n=== {especie.upper()} ===")
    print(f"Municipios: {len(comp)}")
    print(f"--- describe {col_cal} ---")
    print(comp[col_cal].describe())

    total_calculado = (comp[f"{especie}_encuesta"] * comp[col_cal]).sum()
    total_fedegan = comp[col_pm].sum()
    print(f"Total nacional calibrado: {total_calculado:,.0f}")
    print(f"Total nacional Fedegán:   {total_fedegan:,.0f}")
    print(f"Diferencia: {total_calculado - total_fedegan:+,.0f} ({(total_calculado - total_fedegan) / total_fedegan:+.3%})")

    # Residuo conocido y aceptado (ver docstring del módulo): municipios con
    # Fedegán > 0 pero 0 registros en el RUV/encuesta - no hay nada que
    # escalar, no se resuelve excluyendo del marco ni fabricando datos.
    sin_dato_ruv = comp[(comp[f"{especie}_encuesta"] == 0) & (comp[col_pm] > 0)]
    if len(sin_dato_ruv):
        print(f"\nMunicipios con Fedegán > 0 pero 0 en RUV/encuesta (residuo real, no se resuelve): {len(sin_dato_ruv)}")
        print(sin_dato_ruv[["CODIGO_MUNICIPIO", col_pm, f"{especie}_encuesta"]].to_string())


def generar_y_guardar() -> None:
    for especie in ("bovinos", "bufalinos"):
        comp = calcular_cal_especie(especie)
        _validar(especie, comp)
        ruta = config.BASES_CALIBRADAS_DIR / f"comparacion_cal_{especie}_C2_2025.csv"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        comp.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig")
        print(f"Guardado: {ruta}")


if __name__ == "__main__":
    generar_y_guardar()
