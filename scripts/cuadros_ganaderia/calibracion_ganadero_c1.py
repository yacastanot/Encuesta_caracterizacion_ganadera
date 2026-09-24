"""`cal_cobertura`, `calruv`, `cal_predios`, `cal_bovinos`, `cal_bufalinos` de
Ciclo 1 2025 - ya NO reconstruidos por aproximación (ver historial: una
primera versión de este módulo los estimaba a partir de `Total Predios
PM/Vacunados` del archivo histórico de Fedegán, válida pero aproximada). El
usuario encontró los 2 archivos originales de Carolina, que sirven como punto
de partida (crosswalk municipio_id/CODIGO_MUNICIPIO y `cal_bovinos`/
`cal_bufalinos`/`cal_cobertura` heredados) y como referencia de comparación
para `calruv` y `cal_predios`, que ya se recalculan de forma independiente
(ver `calibracion_calruv_c1.py` / `calibracion_predios_c1.py`):

 - `Programas Carolina/calibrac12025.xlsx` (= "calibra1" en el SAS): trae
   `Departamento`/`Municipio` (nombre, cruzan 100% contra DIVIPOLA con las
   mismas 3 excepciones de `calibracion_c2.py`), `municipio_id`, y los 4
   factores `cal_predios`/`cal_bovinos`/`cal_bufalinos`/`cal_cobertura`.
   Su columna `predios ruv` (pese al nombre) equivale a contar `CODIGO_SIT`
   únicos en `ciclo1encuesta.sas7bdat` (predios que además respondieron la
   encuesta), NO en el universo RUV completo (`ciclo1ruv.sas7bdat`) - ver
   `calibracion_predios_c1.py` para la prueba que lo confirmó (coincide
   EXACTO en 1055/1055 municipios una vez se usa la base correcta).
 - `Programas Carolina/calibraencuestac1.xlsx` (= "calibraencuestac1" en el
   SAS): trae `MUNICIPIO_ID` (mismo esquema que el archivo anterior,
   verificado: 1055/1055 filas cruzan por `municipio_id` sin ningún caso sin
   match) y `calruv = cantpredganruv / cantpredganencuesta`.

De paso, `municipio_id` deja resuelta la lista de 8 "municipios ND" que
`4.2`/`4.3` excluían (43, 185, 822, 826, 829, 833, 843, 848 -> Anorí,
Altos del Rosario, Convención, El Tarra, Hacarí, La Playa, San Calixto,
Teorama) - coincide con los municipios que salieron como outliers extremos en
la calibración de bovinos de Ciclo 2 (ver `calibracion_c2.py`), lo cual tiene
sentido: son zonas de baja cobertura RUV.

Las otras 2 listas de códigos centinela (88888: 35 municipios; 44444: 31
municipios) NO aparecen en NINGUNO de estos 2 archivos - son municipios sin
ningún registro RUV (0 predios), así que ya deberían salir en 0 en cualquier
cuadro nuestro sin necesidad de un código especial. Solo se pudieron
identificar 2 de los 31 de la lista 44444 (Inírida y Barrancominas, Guainía)
por aparecer en otro contexto; los 33 restantes quedan sin identificar por
nombre - no bloquea nada porque de todas formas no tienen datos que mostrar.
"""
from __future__ import annotations

import pandas as pd

from . import catalogo_territorial, config

RUTA_CALIBRA_PREDIOS_C1 = config.BASE_DIR / "Programas Carolina" / "calibrac12025.xlsx"
RUTA_CALIBRA_ENCUESTA_C1 = config.BASE_DIR / "Programas Carolina" / "calibraencuestac1.xlsx"

MUNICIPIOS_ND_ID_INTERNO = [43, 185, 822, 826, 829, 833, 843, 848]


def _cargar_crosswalk_municipio_id() -> pd.DataFrame:
    """Departamento/Municipio (nombre) -> CODIGO_MUNICIPIO (DIVIPOLA) + municipio_id,
    y los 4 factores cal_predios/cal_bovinos/cal_bufalinos/cal_cobertura."""
    cal = pd.read_excel(RUTA_CALIBRA_PREDIOS_C1, sheet_name="Hoja1")
    cal["Municipio"] = cal.apply(
        lambda r: config.EXCEPCIONES_MUNICIPIO_FEDEGAN.get((r["Departamento"], r["Municipio"]), r["Municipio"]),
        axis=1,
    )

    divipola = catalogo_territorial.cargar_catalogo_municipios().rename(
        columns={"DEPARTAMENTO": "Departamento", "MUNICIPIO": "Municipio"}
    )
    cruce = cal.merge(divipola[["CODIGO_MUNICIPIO", "Departamento", "Municipio"]], on=["Departamento", "Municipio"], how="left")

    sin_match = cruce["CODIGO_MUNICIPIO"].isna().sum()
    if sin_match:
        raise ValueError(
            f"{sin_match} filas de calibrac12025.xlsx no cruzaron contra DIVIPOLA - "
            "revisar excepciones de nombre antes de confiar en este factor."
        )
    return cruce


def calcular_factores_ganadero_c1() -> pd.DataFrame:
    """`calruv`, `cal_predios`, `cal_bovinos`, `cal_bufalinos` y `cal_cobertura`
    se recalculan de forma independiente a partir de las bases crudas
    (`calibracion_calruv_c1.py` / `calibracion_predios_c1.py` /
    `calibracion_bovinos_bufalinos_c1.py` / `calibracion_cobertura_c1.py`) en
    vez de heredarlos de `calibraencuestac1.xlsx` / `calibrac12025.xlsx` - ver
    esos módulos para la fórmula y la validación contra lo heredado."""
    from . import (
        calibracion_bovinos_bufalinos_c1,
        calibracion_calruv_c1,
        calibracion_cobertura_c1,
        calibracion_predios_c1,
    )

    cruce = _cargar_crosswalk_municipio_id().drop(
        columns=["cal_predios", "cal_bovinos", "cal_bufalinos", "cal_cobertura"]
    )

    calruv_propio = calibracion_calruv_c1.calcular_calruv()[["CODIGO_MUNICIPIO", "calruv_calculado"]].rename(
        columns={"calruv_calculado": "calruv"}
    )
    predios_propio = calibracion_predios_c1.calcular_cal_predios()[
        ["CODIGO_MUNICIPIO", "cal_predios_calculado"]
    ].rename(columns={"cal_predios_calculado": "cal_predios"})
    bovinos_propio = calibracion_bovinos_bufalinos_c1.calcular_cal_especie("bovinos")[["CODIGO_MUNICIPIO", "cal_bovinos"]]
    bufalinos_propio = calibracion_bovinos_bufalinos_c1.calcular_cal_especie("bufalinos")[["CODIGO_MUNICIPIO", "cal_bufalinos"]]
    cobertura_propio = calibracion_cobertura_c1.calcular_cal_cobertura()[["CODIGO_MUNICIPIO", "cal_cobertura"]]

    factor = cruce.merge(calruv_propio, on="CODIGO_MUNICIPIO", how="left")
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
        ["CODIGO_MUNICIPIO", "Departamento", "Municipio", "municipio_id",
         "cal_predios", "cal_bovinos", "cal_bufalinos", "cal_cobertura", "calruv"]
    ]


def _validar(factor: pd.DataFrame) -> None:
    for c in ["cal_predios", "cal_bovinos", "cal_bufalinos", "cal_cobertura", "calruv"]:
        print(f"--- describe {c} ---")
        print(factor[c].describe())

    print("\n--- Municipios ND (deben aparecer, coinciden con outliers de Ciclo 2) ---")
    print(factor[factor["municipio_id"].isin(MUNICIPIOS_ND_ID_INTERNO)][
        ["Departamento", "Municipio", "municipio_id", "cal_cobertura", "calruv"]
    ].to_string())


def generar_y_guardar() -> None:
    factor = calcular_factores_ganadero_c1()
    _validar(factor)
    config.RUTA_FACTOR_GANADERO_C1.parent.mkdir(parents=True, exist_ok=True)
    factor.to_csv(config.RUTA_FACTOR_GANADERO_C1, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"\nGuardado: {config.RUTA_FACTOR_GANADERO_C1}")


if __name__ == "__main__":
    generar_y_guardar()
