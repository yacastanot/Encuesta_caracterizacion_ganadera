"""Recalcula `cal_bovinos`/`cal_bufalinos` de Ciclo 1 2025 de forma
independiente, con la misma política del proyecto ya aplicada a `calruv`
(`calibracion_calruv_c1.py`) y `cal_predios` (`calibracion_predios_c1.py`).

Regla (mismo patrón que `cal_predios`, ver ese módulo para el porqué):

    cal_bovinos    = Total Bovinos PM    / bovinos encuesta
    cal_bufalinos  = Total Bufalinos PM  / bufalinos encuesta

 - `Total Bovinos/Bufalinos PM`: Fedegán, Cuadro 2_Cobertura, Ciclo 1 2025 -
   MISMO insumo que ya carga `calibracion_c1._fedegan_ciclo1_con_codigo_municipio`
   (se reutiliza esa función en vez de duplicar la carga+validación del cruce
   contra DIVIPOLA).
 - `bovinos/bufalinos encuesta`: suma de `TOTAL_AFT_BOV + TOTAL_AFT_BOV_NV`
   (o BUF) en `ciclo1encuesta.sas7bdat` - NO en `ciclo1ruv.sas7bdat`. Se
   verificó explícitamente antes de escribir este módulo: la columna heredada
   `bovinos ruv`/`bufalos ruv` de `calibrac12025.xlsx` (pese al nombre)
   coincide EXACTO con la suma calculada desde `ciclo1encuesta.sas7bdat` en
   1054/1054 municipios, y solo parcialmente (598/1054 y 999/1054) contra
   `ciclo1ruv.sas7bdat` - mismo error de universo que ya se encontró y
   corrigió en `cal_predios`, confirmado ANTES de repetirlo acá.

Validado contra el heredado (`calibrac12025.xlsx`): numerador y denominador
coinciden EXACTO en la práctica totalidad de municipios (ver `_validar`).
"""
from __future__ import annotations

import pandas as pd

from . import calibracion_c1, calibracion_ganadero_c1, catalogo_territorial, config, fuente_cruda_c1

_COLS_ANIMAL = {
    "bovinos": ["TOTAL_AFT_BOV", "TOTAL_AFT_BOV_NV"],
    "bufalinos": ["TOTAL_AFT_BUF", "TOTAL_AFT_BUF_NV"],
}


def _sumar_animales_encuesta(especie: str) -> pd.Series:
    cols_val = _COLS_ANIMAL[especie]
    df = fuente_cruda_c1.leer(config.RUTA_CICLO1_ENCUESTA_CRUDO, columns=["CODIGO_MUNICIPIO", "CICLO", "ANIO"] + cols_val)

    # Mismo blindaje ya aplicado en `calibracion_predios_c1._contar_predios_encuesta`:
    # no asumir que el archivo viene puro Ciclo 1 2025 solo por el nombre.
    mal_ciclo = df[df["CICLO"].notna() & (df["CICLO"] != 1)]
    mal_anio = df[df["ANIO"].notna() & (df["ANIO"] != 2025)]
    if len(mal_ciclo) or len(mal_anio):
        raise ValueError(
            f"ciclo1encuesta.sas7bdat trae {len(mal_ciclo)} filas con CICLO != 1 y {len(mal_anio)} con ANIO != 2025 - "
            "ya no se puede asumir que el archivo viene puro Ciclo 1 2025, hay que filtrar explícito."
        )

    df = df.dropna(subset=["CODIGO_MUNICIPIO"]).copy()
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

    fedegan_join = calibracion_c1._fedegan_ciclo1_con_codigo_municipio()
    fedegan = fedegan_join[["COD_MPIO", col_pm]].rename(columns={"COD_MPIO": "CODIGO_MUNICIPIO"})

    animales_encuesta = _sumar_animales_encuesta(especie)

    comp = fedegan.merge(animales_encuesta, on="CODIGO_MUNICIPIO", how="left")
    comp[col_cal] = _factor_seguro(comp[col_pm], comp[f"{especie}_encuesta"])
    return comp


def _cargar_heredado(especie: str) -> pd.DataFrame:
    """`cal_bovinos`/`cal_bufalinos` tal como venían en calibrac12025.xlsx
    (heredado de Carolina). Solo para comparar - el pipeline ya no usa este
    valor."""
    col_ruv = "bovinos ruv" if especie == "bovinos" else "bufalos ruv"
    col_pm = "Total Bovinos PM" if especie == "bovinos" else "Total Bufalinos PM"
    col_cal = "cal_bovinos" if especie == "bovinos" else "cal_bufalinos"

    cruce = calibracion_ganadero_c1._cargar_crosswalk_municipio_id()
    return cruce[["CODIGO_MUNICIPIO", col_pm, col_ruv, col_cal]].rename(
        columns={
            col_pm: f"{col_pm}_heredado",
            col_ruv: f"{especie}_encuesta_heredado",
            col_cal: f"{col_cal}_heredado",
        }
    )


def comparar_con_heredado(especie: str) -> pd.DataFrame:
    col_pm = "Total Bovinos PM" if especie == "bovinos" else "Total Bufalinos PM"
    col_cal = "cal_bovinos" if especie == "bovinos" else "cal_bufalinos"

    calculado = calcular_cal_especie(especie)
    heredado = _cargar_heredado(especie)
    comp = calculado.merge(heredado, on="CODIGO_MUNICIPIO", how="outer")
    comp["dif_relativa_cal"] = (comp[col_cal] - comp[f"{col_cal}_heredado"]) / comp[f"{col_cal}_heredado"].replace(0, pd.NA)

    divipola = catalogo_territorial.cargar_catalogo_municipios().rename(columns={"CODIGO_MUNICIPIO": "COD_MPIO"})
    comp = comp.merge(
        divipola[["COD_MPIO", "DEPARTAMENTO", "MUNICIPIO"]], left_on="CODIGO_MUNICIPIO", right_on="COD_MPIO", how="left"
    ).drop(columns="COD_MPIO")

    cols_nombre = ["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO"]
    return comp[cols_nombre + [c for c in comp.columns if c not in cols_nombre]]


def _validar(especie: str, comp: pd.DataFrame) -> None:
    col_cal = "cal_bovinos" if especie == "bovinos" else "cal_bufalinos"
    print(f"\n=== {especie.upper()} ===")
    print(f"Municipios comparados: {len(comp)}")
    print(f"Sin match en heredado: {comp[f'{col_cal}_heredado'].isna().sum()}")

    umbral = 0.01  # 1%
    grandes = comp[comp["dif_relativa_cal"].abs() > umbral].sort_values("dif_relativa_cal", key=abs, ascending=False)
    print(f"Municipios con diferencia en {col_cal} > {umbral:.0%}: {len(grandes)} / {len(comp)}")
    if len(grandes):
        print(grandes[["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO", col_cal, f"{col_cal}_heredado", "dif_relativa_cal"]].head(15).to_string())


def generar_y_guardar() -> None:
    for especie in ("bovinos", "bufalinos"):
        comp = comparar_con_heredado(especie)
        _validar(especie, comp)
        ruta = config.BASES_CALIBRADAS_DIR / f"comparacion_cal_{especie}_C1_2025.csv"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        comp.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig")
        print(f"\nGuardado: {ruta}")


if __name__ == "__main__":
    generar_y_guardar()
