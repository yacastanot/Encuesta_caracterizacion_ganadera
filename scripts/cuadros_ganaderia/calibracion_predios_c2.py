"""Recalcula `cal_predios` de Ciclo 2 2025 (2025-II) desde las bases crudas
reales, mirror exacto de `calibracion_predios_c1.py`:

    cal_predios = Total Predios PM (Fedegán, CICLO 2) / predios encuesta

`predios encuesta` = count(distinct CODIGO_SIT) en el subconjunto que
respondió la encuesta (`preparar_ciclo2encuesta.leer`, NO el universo RUV
completo) - mismo criterio que C1 (ver docstring de `calibracion_predios_c1.py`
para el porqué: usar el universo RUV completo en vez del que respondió
encuesta rompía en los municipios de baja cobertura).

Reutiliza `calibracion_c2._fedegan_ciclo2_con_codigo_municipio()` (ya carga
Fedegán Ciclo 2 + cruce DIVIPOLA con las validaciones de nombre) en vez de
duplicar esa carga - mismo patrón que `calibracion_predios_c1.py` reutiliza
`calibracion_c1._fedegan_ciclo1_con_codigo_municipio` conceptualmente (acá se
reutiliza literal, ya que existe una función equivalente para C2).

Sin comparación contra heredado (no existe `calibrac12025.xlsx` para Ciclo 2)
- ver `calibracion_calruv_c2.py`.
"""
from __future__ import annotations

import pandas as pd

from . import calibracion_c2, config, preparar_ciclo2encuesta


def _contar_predios_encuesta() -> pd.Series:
    df = preparar_ciclo2encuesta.leer(columns=["CODIGO_MUNICIPIO", "CODIGO_SIT"])
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)
    return df.groupby("CODIGO_MUNICIPIO")["CODIGO_SIT"].nunique().rename("predios_encuesta")


def _cargar_total_predios_pm_fedegan() -> pd.DataFrame:
    fedegan_join = calibracion_c2._fedegan_ciclo2_con_codigo_municipio()
    fedegan_join = fedegan_join.copy()
    fedegan_join["Total Predios PM"] = pd.to_numeric(
        fedegan_join["Total Predios PM"].astype(str).replace("-", "0"), errors="coerce"
    ).fillna(0)
    return fedegan_join[["COD_MPIO", "Total Predios PM"]].rename(columns={"COD_MPIO": "CODIGO_MUNICIPIO"})


def _factor_seguro(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    return (numerador / denominador).where(denominador > 0).fillna(1.0)


def calcular_cal_predios() -> pd.DataFrame:
    fedegan = _cargar_total_predios_pm_fedegan()
    predios_encuesta = _contar_predios_encuesta()

    comp = fedegan.merge(predios_encuesta, on="CODIGO_MUNICIPIO", how="left")
    comp["predios_encuesta"] = comp["predios_encuesta"].fillna(0)
    comp["cal_predios_calculado"] = _factor_seguro(comp["Total Predios PM"], comp["predios_encuesta"])
    return comp


def _validar(comp: pd.DataFrame) -> None:
    print(f"Municipios: {len(comp)}")
    print("--- describe cal_predios_calculado ---")
    print(comp["cal_predios_calculado"].describe())

    total_calculado = (comp["predios_encuesta"] * comp["cal_predios_calculado"]).sum()
    total_fedegan = comp["Total Predios PM"].sum()
    print(f"\nTotal nacional calibrado: {total_calculado:,.0f}")
    print(f"Total nacional Fedegán:   {total_fedegan:,.0f}")
    print(f"Diferencia: {total_calculado - total_fedegan:+,.0f} ({(total_calculado - total_fedegan) / total_fedegan:+.3%})")

    extremos = comp[comp["cal_predios_calculado"] > 5].sort_values("cal_predios_calculado", ascending=False)
    print(f"\nMunicipios con cal_predios > 5 (posible baja cobertura): {len(extremos)}")
    print(extremos[["CODIGO_MUNICIPIO", "Total Predios PM", "predios_encuesta", "cal_predios_calculado"]].head(15).to_string())


def generar_y_guardar() -> None:
    comp = calcular_cal_predios()
    _validar(comp)
    ruta = config.BASES_CALIBRADAS_DIR / "comparacion_cal_predios_C2_2025.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    comp.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"\nGuardado: {ruta}")


if __name__ == "__main__":
    generar_y_guardar()
