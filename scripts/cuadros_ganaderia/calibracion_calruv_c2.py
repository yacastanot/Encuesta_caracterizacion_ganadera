"""Recalcula `calruv` de Ciclo 2 2025 (2025-II) desde las bases crudas reales
(`ExportarArchivoRuv.csv` / `ExportarArchivoEncuesta2_2025.csv`, vía
`preparar_ciclo2encuesta.py`) - mirror exacto de `calibracion_calruv_c1.py`,
misma fórmula:

    predioganid = CODIGO_SIT || IDENT_GANADERO
    cantpredganruv      = count(distinct predioganid) en el universo RUV
                           completo (`preparar_ciclo2encuesta.leer_ruv_completo`)
    cantpredganencuesta = count(distinct predioganid) en el subconjunto que
                           ADEMÁS respondió la encuesta (`preparar_ciclo2encuesta.leer`)
    calruv = cantpredganruv / cantpredganencuesta   (por municipio)

A diferencia de `calibracion_calruv_c1.py`: no existe ningún archivo heredado
tipo `calibraencuestac1.xlsx` para Ciclo 2 (Carolina nunca calibró ese ciclo)
- no hay contra qué comparar acá. La única validación posible en este módulo
es de sanidad interna (describe(), municipios con calruv extremo). La
comparación real de este factor contra el pipeline legado de R (que sí
calibró Ciclo 2, con sus propias bases ya calculadas) es un contraste
aparte, reservado para la Fase 8 de validación - no la fuente de este cálculo.
"""
from __future__ import annotations

import pandas as pd

from . import config, preparar_ciclo2encuesta

_COLS = ["CODIGO_MUNICIPIO", "predioganid"]


def _contar_predioganid_ruv() -> pd.Series:
    df = preparar_ciclo2encuesta.leer_ruv_completo(columns=_COLS)
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)
    return df.groupby("CODIGO_MUNICIPIO")["predioganid"].nunique()


def _contar_predioganid_encuesta() -> pd.Series:
    df = preparar_ciclo2encuesta.leer(columns=_COLS)
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)
    return df.groupby("CODIGO_MUNICIPIO")["predioganid"].nunique()


def calcular_calruv() -> pd.DataFrame:
    cantpredganruv = _contar_predioganid_ruv().rename("cantpredganruv")
    cantpredganencuesta = _contar_predioganid_encuesta().rename("cantpredganencuesta")

    comp = pd.concat([cantpredganruv, cantpredganencuesta], axis=1).reset_index()
    comp = comp.rename(columns={"index": "CODIGO_MUNICIPIO"})
    # Municipios que aparecen en el RUV pero no en la encuesta (0 respuestas)
    # quedan con cantpredganencuesta=NaN tras el concat - fillna(0) primero
    # para que el "where(...>0)" de abajo los deje en factor=1.0 (sin ajuste),
    # mismo criterio que C1.
    comp["cantpredganruv"] = comp["cantpredganruv"].fillna(0)
    comp["cantpredganencuesta"] = comp["cantpredganencuesta"].fillna(0)
    comp["calruv_calculado"] = (comp["cantpredganruv"] / comp["cantpredganencuesta"]).where(
        comp["cantpredganencuesta"] > 0
    ).fillna(1.0)
    return comp


def _validar(comp: pd.DataFrame) -> None:
    print(f"Municipios: {len(comp)}")
    print("--- describe calruv_calculado ---")
    print(comp["calruv_calculado"].describe())

    # Cobertura real = cantpredganencuesta / cantpredganruv = 1/calruv (donde
    # aplica) - esto es lo que hace falta para decidir, en la Fase 3, si
    # `config.MUNICIPIOS_EXCLUIDOS_C2` necesita el motivo "<80% cobertura"
    # que hoy está pendiente (ver docstring de `config.py`).
    comp["cobertura"] = (comp["cantpredganencuesta"] / comp["cantpredganruv"]).where(comp["cantpredganruv"] > 0)
    baja_cobertura = comp[comp["cobertura"].notna() & (comp["cobertura"] < 0.80)].sort_values("cobertura")
    print(f"\nMunicipios con cobertura de encuesta < 80% (candidatos a exclusión, ver config.MUNICIPIOS_EXCLUIDOS_C2): {len(baja_cobertura)}")
    print(baja_cobertura[["CODIGO_MUNICIPIO", "cantpredganruv", "cantpredganencuesta", "cobertura", "calruv_calculado"]].to_string())

    extremos = comp[comp["calruv_calculado"] > 5].sort_values("calruv_calculado", ascending=False)
    print(f"\nMunicipios con calruv > 5 (posible baja cobertura, revisar): {len(extremos)}")
    print(extremos[["CODIGO_MUNICIPIO", "cantpredganruv", "cantpredganencuesta", "calruv_calculado"]].head(15).to_string())


def generar_y_guardar() -> None:
    comp = calcular_calruv()
    _validar(comp)
    ruta = config.BASES_CALIBRADAS_DIR / "comparacion_calruv_C2_2025.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    comp.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"\nGuardado: {ruta}")


if __name__ == "__main__":
    generar_y_guardar()
