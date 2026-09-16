"""`cal_cobertura`, `calruv`, `cal_predios`, `cal_bovinos`, `cal_bufalinos` de
Ciclo 1 2025, tal como los usaba Carolina - ya NO reconstruidos por
aproximación (ver historial: una primera versión de este módulo los estimaba
a partir de `Total Predios PM/Vacunados` del archivo histórico de Fedegán,
válida pero aproximada). El usuario encontró los 2 archivos originales:

 - `Programas Carolina/calibrac12025.xlsx` (= "calibra1" en el SAS): trae
   `Departamento`/`Municipio` (nombre, cruzan 100% contra DIVIPOLA con las
   mismas 3 excepciones de `calibracion_c2.py`), `municipio_id`, y los 4
   factores `cal_predios`/`cal_bovinos`/`cal_bufalinos`/`cal_cobertura`.
   Verificado: su columna `predios ruv` para un municipio coincide EXACTO con
   nuestro conteo de `CODIGO_SIT` únicos en ese municipio (ej. Abejorral: 963
   en ambos) - confirma que `municipio_id` es el mismo universo que nuestra
   base.
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
    cruce = _cargar_crosswalk_municipio_id()
    calruv = pd.read_excel(RUTA_CALIBRA_ENCUESTA_C1, sheet_name="Hoja1")

    factor = cruce.merge(
        calruv[["MUNICIPIO_ID", "calruv"]], left_on="municipio_id", right_on="MUNICIPIO_ID", how="left"
    )
    sin_calruv = factor["calruv"].isna().sum()
    if sin_calruv:
        print(f"AVISO: {sin_calruv} municipios sin match en calibraencuestac1.xlsx - calruv queda en 1.0 para esos.")
    factor["calruv"] = factor["calruv"].fillna(1.0)

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
    factor.to_csv(config.RUTA_FACTOR_GANADERO_C1, sep=";", decimal=",", index=False)
    print(f"\nGuardado: {config.RUTA_FACTOR_GANADERO_C1}")


if __name__ == "__main__":
    generar_y_guardar()
