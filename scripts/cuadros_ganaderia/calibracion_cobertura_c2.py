"""Recalcula `cal_cobertura` de Ciclo 2 2025 (2025-II), mirror exacto de
`calibracion_cobertura_c1.py`:

    cal_cobertura = 1 / Total Predios Cobertura (Fedegán, CICLO 2)

No depende de RUV/encuesta - transformación directa de un dato que Fedegán ya
entrega calculado. Reutiliza `calibracion_c2._fedegan_ciclo2_con_codigo_municipio()`.
Sin comparación contra heredado (no existe `calibrac12025.xlsx` para Ciclo 2).

**Corrección 2026-09-23** (ver `calibracion_cobertura_c1.py` para la prueba
completa): la fórmula anterior (`2-C`) era la aproximación lineal de primer
orden de `1/C`, válida solo cuando C≈1 - se reemplaza por `1/C`, la inversión
exacta de la definición de Fedegán `C = Vacunados/PM`. Validado en C1 contra
`Total Predios PM` municipio a municipio: `1/C` reduce el error a la mitad
frente a `2-C` (486.7 vs 917.9 de error absoluto acumulado en 1055
municipios), y es exacto en los casos de cobertura muy baja.
"""
from __future__ import annotations

import pandas as pd

from . import calibracion_c2, config


def calcular_cal_cobertura() -> pd.DataFrame:
    fedegan_join = calibracion_c2._fedegan_ciclo2_con_codigo_municipio()
    comp = fedegan_join[["COD_MPIO", "Total Predios Cobertura"]].rename(columns={"COD_MPIO": "CODIGO_MUNICIPIO"})
    comp["cal_cobertura"] = (1.0 / comp["Total Predios Cobertura"]).where(comp["Total Predios Cobertura"] > 0).fillna(1.0)
    return comp


def _validar(comp: pd.DataFrame) -> None:
    print(f"Municipios: {len(comp)}")
    print("--- describe cal_cobertura ---")
    print(comp["cal_cobertura"].describe())
    extremos = comp[(comp["cal_cobertura"] < 0.5) | (comp["cal_cobertura"] > 2.0)]
    print(f"\nMunicipios con cal_cobertura fuera de [0.5, 2.0] (revisar): {len(extremos)}")
    if len(extremos):
        print(extremos[["CODIGO_MUNICIPIO", "Total Predios Cobertura", "cal_cobertura"]].to_string())


def generar_y_guardar() -> None:
    comp = calcular_cal_cobertura()
    _validar(comp)
    ruta = config.BASES_CALIBRADAS_DIR / "comparacion_cal_cobertura_C2_2025.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    comp.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"\nGuardado: {ruta}")


if __name__ == "__main__":
    generar_y_guardar()
