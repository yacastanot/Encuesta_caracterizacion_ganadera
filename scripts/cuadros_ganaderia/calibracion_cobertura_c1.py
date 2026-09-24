"""Recalcula `cal_cobertura` de Ciclo 1 2025 de forma independiente, con la
misma política del proyecto ya aplicada a `calruv`/`cal_predios`/`cal_bovinos`/
`cal_bufalinos`.

Regla (CORREGIDA 2026-09-23, ver hallazgo abajo):

    cal_cobertura = 1 / Total Predios Cobertura

`Total Predios Cobertura` es el porcentaje que ya trae Fedegán en Cuadro
2_Cobertura (Ciclo 1 2025) - MISMO insumo que ya carga
`calibracion_c1._fedegan_ciclo1_con_codigo_municipio` (se reutiliza esa
función en vez de duplicar la carga+validación del cruce contra DIVIPOLA). A
diferencia de `cal_predios`/`cal_bovinos`/`cal_bufalinos`, este factor no
depende de ningún conteo propio del RUV/encuesta - es una transformación
directa de un dato que Fedegán ya entrega calculado.

**Corrección 2026-09-23**: la fórmula original (`2 - C`, heredada tal cual de
`calibrac12025.xlsx`, con la que coincidía EXACTO en 1055/1055 municipios)
quedó descartada tras una prueba directa contra Fedegán - no basta con
reproducir el heredado si el heredado mismo está mal. Fedegán define
`Total Predios Cobertura` = `Total Predios Vacunados / Total Predios PM`
(verificado columna por columna en `Cuadro 2_Cobertura`), es decir C =
Vacunados/PM por construcción - luego el factor de expansión matemáticamente
correcto para llevar un conteo de "vacunados" al universo "PM" es su inversa
exacta, `1/C`, no la aproximación lineal de primer orden `2-C` (válida solo
cuando C≈1, que es coincidencialmente donde coincidía con el heredado en la
mayoría de municipios - ~97% de los municipios tienen C>0.90).

Prueba (municipio a municipio, `predios_ruv_unicos` de `ciclo1ruv.sas7bdat`
expandido con cada fórmula, contra `Total Predios PM`):
 - `1/C`: suma de error absoluto = 486.7 (1055 municipios)
 - `2-C`: suma de error absoluto = 917.9 (~el doble)
La diferencia es más marcada justo en baja cobertura, donde más importa el
ajuste: municipio 52418 (C=0.142) - `1/C` da 295.0 (EXACTO contra Fedegán,
294.99...), `2-C` da apenas 78 (subestima 74%).

Ya NO se compara contra el heredado como criterio de validez (ver
`comparar_con_heredado` - se conserva solo como registro de la diferencia,
esperada y grande en baja cobertura, no como una alarma).
"""
from __future__ import annotations

import pandas as pd

from . import calibracion_c1, calibracion_ganadero_c1, catalogo_territorial, config


def calcular_cal_cobertura() -> pd.DataFrame:
    fedegan_join = calibracion_c1._fedegan_ciclo1_con_codigo_municipio()
    comp = fedegan_join[["COD_MPIO", "Total Predios Cobertura"]].rename(columns={"COD_MPIO": "CODIGO_MUNICIPIO"})
    comp["cal_cobertura"] = (1.0 / comp["Total Predios Cobertura"]).where(comp["Total Predios Cobertura"] > 0).fillna(1.0)
    return comp


def _cargar_heredado() -> pd.DataFrame:
    """`cal_cobertura` tal como venía en calibrac12025.xlsx (heredado de
    Carolina). Solo para comparar - el pipeline ya no usa este valor."""
    cruce = calibracion_ganadero_c1._cargar_crosswalk_municipio_id()
    return cruce[["CODIGO_MUNICIPIO", "cal_cobertura"]].rename(columns={"cal_cobertura": "cal_cobertura_heredado"})


def comparar_con_heredado() -> pd.DataFrame:
    calculado = calcular_cal_cobertura()
    heredado = _cargar_heredado()
    comp = calculado.merge(heredado, on="CODIGO_MUNICIPIO", how="outer")
    comp["dif_absoluta"] = comp["cal_cobertura"] - comp["cal_cobertura_heredado"]

    divipola = catalogo_territorial.cargar_catalogo_municipios().rename(columns={"CODIGO_MUNICIPIO": "COD_MPIO"})
    comp = comp.merge(
        divipola[["COD_MPIO", "DEPARTAMENTO", "MUNICIPIO"]], left_on="CODIGO_MUNICIPIO", right_on="COD_MPIO", how="left"
    ).drop(columns="COD_MPIO")

    cols_nombre = ["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO"]
    return comp[cols_nombre + [c for c in comp.columns if c not in cols_nombre]]


def _validar(comp: pd.DataFrame) -> None:
    print(f"Municipios comparados: {len(comp)}")
    print(f"Sin match en heredado: {comp['cal_cobertura_heredado'].isna().sum()}")

    # Ya NO se espera coincidencia con el heredado (ver docstring del módulo -
    # el heredado usaba `2-C`, una aproximación descartada). Se reporta la
    # diferencia como información, no como alarma; el umbral queda amplio
    # solo para no imprimir los ~970 municipios de cobertura alta donde `1/C`
    # y `2-C` casi coinciden.
    umbral = 0.01
    grandes = comp[comp["dif_absoluta"].abs() > umbral].sort_values("dif_absoluta", key=abs, ascending=False)
    print(f"Municipios con diferencia en cal_cobertura > {umbral} frente al heredado (ESPERADO, ver docstring): {len(grandes)} / {len(comp)}")
    if len(grandes):
        print(grandes[["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO", "cal_cobertura", "cal_cobertura_heredado", "dif_absoluta"]].head(15).to_string())


def generar_y_guardar() -> None:
    comp = comparar_con_heredado()
    _validar(comp)
    ruta = config.BASES_CALIBRADAS_DIR / "comparacion_cal_cobertura_C1_2025.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    comp.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"\nGuardado: {ruta}")


if __name__ == "__main__":
    generar_y_guardar()
