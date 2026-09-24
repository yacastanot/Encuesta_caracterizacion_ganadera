"""Ensambla `calruv`, `cal_predios`, `cal_bovinos`, `cal_bufalinos` y
`cal_cobertura` de Ciclo 2 2025 (2025-II) en un único CSV
(`config.RUTA_FACTOR_GANADERO_C2`) - equivalente de `calibracion_ganadero_c1.py`,
pero MÁS SIMPLE: no hace falta ningún crosswalk de `municipio_id` heredado
(no existe archivo de Carolina para Ciclo 2) - el RUV crudo de C2 ya trae
`CODIGO_MUNICIPIO` DIVIPOLA directo (verificado en `fuente_cruda_c2.py`), así
que el universo territorial de partida es simplemente
`catalogo_territorial.cargar_catalogo_municipios()`.

Los 5 factores YA se recalculan de forma independiente en sus propios módulos
(`calibracion_calruv_c2.py` / `calibracion_predios_c2.py` /
`calibracion_bovinos_bufalinos_c2.py` / `calibracion_cobertura_c2.py`) - acá
solo se juntan. Sin comparación contra heredado (no existe ningún archivo
Carolina para Ciclo 2, ver esos 4 módulos).
"""
from __future__ import annotations

import pandas as pd

from . import (
    calibracion_bovinos_bufalinos_c2,
    calibracion_calruv_c2,
    calibracion_cobertura_c2,
    calibracion_predios_c2,
    catalogo_territorial,
    config,
)


def calcular_factores_ganadero_c2() -> pd.DataFrame:
    universo = catalogo_territorial.cargar_catalogo_municipios()[["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO"]]

    calruv_propio = calibracion_calruv_c2.calcular_calruv()[["CODIGO_MUNICIPIO", "calruv_calculado"]].rename(
        columns={"calruv_calculado": "calruv"}
    )
    predios_propio = calibracion_predios_c2.calcular_cal_predios()[
        ["CODIGO_MUNICIPIO", "cal_predios_calculado"]
    ].rename(columns={"cal_predios_calculado": "cal_predios"})
    bovinos_propio = calibracion_bovinos_bufalinos_c2.calcular_cal_especie("bovinos")[["CODIGO_MUNICIPIO", "cal_bovinos"]]
    bufalinos_propio = calibracion_bovinos_bufalinos_c2.calcular_cal_especie("bufalinos")[["CODIGO_MUNICIPIO", "cal_bufalinos"]]
    cobertura_propio = calibracion_cobertura_c2.calcular_cal_cobertura()[["CODIGO_MUNICIPIO", "cal_cobertura"]]

    factor = universo.merge(calruv_propio, on="CODIGO_MUNICIPIO", how="left")
    factor = factor.merge(predios_propio, on="CODIGO_MUNICIPIO", how="left")
    factor = factor.merge(bovinos_propio, on="CODIGO_MUNICIPIO", how="left")
    factor = factor.merge(bufalinos_propio, on="CODIGO_MUNICIPIO", how="left")
    factor = factor.merge(cobertura_propio, on="CODIGO_MUNICIPIO", how="left")

    for col, etiqueta in [
        ("calruv", "las bases crudas de RUV/encuesta"),
        ("cal_predios", "Fedegán/encuesta"),
        ("cal_bovinos", "Fedegán/encuesta"),
        ("cal_bufalinos", "Fedegán/encuesta"),
        ("cal_cobertura", "Fedegán"),
    ]:
        sin_match = factor[col].isna().sum()
        if sin_match:
            print(f"AVISO: {sin_match} municipios sin match en {etiqueta} - {col} queda en 1.0 para esos.")
        factor[col] = factor[col].fillna(1.0)

    return factor[
        ["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO",
         "cal_predios", "cal_bovinos", "cal_bufalinos", "cal_cobertura", "calruv"]
    ]


def _validar(factor: pd.DataFrame) -> None:
    print(f"Municipios: {len(factor)}")
    for c in ["cal_predios", "cal_bovinos", "cal_bufalinos", "cal_cobertura", "calruv"]:
        print(f"--- describe {c} ---")
        print(factor[c].describe())


def generar_y_guardar() -> None:
    factor = calcular_factores_ganadero_c2()
    _validar(factor)
    config.RUTA_FACTOR_GANADERO_C2.parent.mkdir(parents=True, exist_ok=True)
    factor.to_csv(config.RUTA_FACTOR_GANADERO_C2, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"\nGuardado: {config.RUTA_FACTOR_GANADERO_C2}")


if __name__ == "__main__":
    generar_y_guardar()
