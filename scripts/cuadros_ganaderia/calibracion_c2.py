"""Calcula el factor de calibración (F_AJUSTA_BOVINOS / F_AJUSTA_BUFALINOS) del
Ciclo 2 de 2025, por municipio, y lo guarda en `config.RUTA_FACTOR_C2`.

Por qué existe este módulo en vez de usar el `F_AJUSTA_BOVINOS` que ya trae
`base_ruv_calibrada_C2_2025.csv`
------------------------------------------------------------------------------
Ese factor viene corrupto: por ejemplo, para Convención (Norte de Santander)
el CSV trae `F_AJUSTA_BOVINOS = 875070422535211` en vez de `87.507042...`
(verificado leyendo el texto crudo del CSV, no es un problema de parseo de
este script). La causa más probable está en
`Scripts calibración R/1. BASE DEPURADA (PREDIO-GANADERO).R` /
`F_ajusta_bovinos.R`, en el paso:

    `Total Bovinos PM` = ifelse(`Total Bovinos PM` == "-", "0", `Total Bovinos PM`)
    `Total Bovinos PM` = as.numeric(gsub("\\.", "", `Total Bovinos PM`))

El `ifelse` fuerza a R a coaccionar toda la columna numérica a texto; para
números grandes R usa notación científica al hacer esa conversión (ej.
"8.750704e+04"), y el `gsub` siguiente borra el punto de esa notación
científica (no un separador de miles, que es lo que el gsub asume), inflando
el valor varios órdenes de magnitud antes de dividir.

Este módulo recalcula el mismo factor (Total Fedegán / Total RUV crudo por
municipio, Ciclo 2 2025) operando siempre sobre columnas numéricas de pandas,
sin pasar nunca por texto, y valida el resultado contra:
 - Los 2 municipios de Chocó sin match en Fedegán, ya documentados como
   pendientes en el R original.
 - El único municipio (Riosucio, Chocó) donde Fedegán reporta menos que el RUV,
   también documentado en el R original.
 - El total nacional calibrado, que debe quedar cercano al total nacional que
   reporta Fedegán (no idéntico: los municipios sin match o con RUV=0 quedan
   sin poder ajustarse, ver `_factor_seguro` abajo).
"""
from __future__ import annotations

import pandas as pd

from . import catalogo_territorial, config

_COLS_RUV_CRUDO = [
    "CODIGO MUNICIPIO",
    "TOTAL AFTOSA BOVINOS", "TOTAL AFTOSA BOVINOS NV",
    "TOTAL AFTOSA BUFALINOS", "TOTAL AFTOSA BUFALINOS NV",
]


def _cargar_fedegan_ciclo2_2025() -> pd.DataFrame:
    fedegan = pd.read_excel(config.RUTA_FEDEGAN_HISTORICO, sheet_name="Cuadro 2_Cobertura")
    fedegan = fedegan[(fedegan["AÑO"] == 2025) & (fedegan["CICLO"] == "CICLO 2")].copy()

    def _municipio_normalizado(row):
        return config.EXCEPCIONES_MUNICIPIO_FEDEGAN.get(
            (row["Departamento"], row["Municipio"]), row["Municipio"]
        )

    fedegan["Municipio"] = fedegan.apply(_municipio_normalizado, axis=1)
    for col in ("Total Bovinos PM", "Total Bufalinos PM"):
        fedegan[col] = pd.to_numeric(fedegan[col].astype(str).replace("-", "0"), errors="coerce").fillna(0)
    return fedegan


def _cargar_inventario_ruv_crudo() -> pd.DataFrame:
    ruv = pd.read_csv(
        config.RUTA_C2, sep=";", encoding="utf-8-sig", encoding_errors="replace",
        usecols=_COLS_RUV_CRUDO, decimal=",",
    )
    ruv["COD_MPIO"] = ruv["CODIGO MUNICIPIO"].astype(str).str.zfill(5)
    ruv["TOTAL_AFTOSA_BOVINOS"] = ruv["TOTAL AFTOSA BOVINOS"].fillna(0) + ruv["TOTAL AFTOSA BOVINOS NV"].fillna(0)
    ruv["TOTAL_AFTOSA_BUFALINOS"] = ruv["TOTAL AFTOSA BUFALINOS"].fillna(0) + ruv["TOTAL AFTOSA BUFALINOS NV"].fillna(0)
    return ruv.groupby("COD_MPIO", as_index=False)[["TOTAL_AFTOSA_BOVINOS", "TOTAL_AFTOSA_BUFALINOS"]].sum()


def _factor_seguro(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    """Fedegán/RUV donde RUV>0; en cualquier otro caso factor=1.0 (sin ajuste):
    si RUV=0 el resultado calibrado da 0 sin importar el factor (no hay nada
    que escalar - es un hueco de cobertura del RUV, no algo que este factor
    pueda corregir); si no hay match en Fedegán tampoco hay con qué ajustar.
    Misma convención que `preparar_base.aplicar_factor_calibracion` usa para
    Ciclo 1 (`factor = df[factor_col].fillna(1.0)`)."""
    return (numerador / denominador).where(denominador > 0).fillna(1.0)


def calcular_factor_c2() -> pd.DataFrame:
    divipola = catalogo_territorial.cargar_catalogo_municipios().rename(
        columns={"CODIGO_MUNICIPIO": "COD_MPIO", "DEPARTAMENTO": "Departamento", "MUNICIPIO": "Municipio"}
    )
    fedegan = _cargar_fedegan_ciclo2_2025()
    fedegan_join = fedegan.merge(divipola[["COD_MPIO", "Departamento", "Municipio"]], on=["Departamento", "Municipio"], how="left")

    inventario_ruv = _cargar_inventario_ruv_crudo()

    factor = inventario_ruv.merge(
        fedegan_join[["COD_MPIO", "Total Bovinos PM", "Total Bufalinos PM"]], on="COD_MPIO", how="left"
    )
    factor["F_AJUSTA_BOVINOS"] = _factor_seguro(factor["Total Bovinos PM"], factor["TOTAL_AFTOSA_BOVINOS"])
    factor["F_AJUSTA_BUFALINOS"] = _factor_seguro(factor["Total Bufalinos PM"], factor["TOTAL_AFTOSA_BUFALINOS"])
    return factor[["COD_MPIO", "F_AJUSTA_BOVINOS", "F_AJUSTA_BUFALINOS"]].rename(columns={"COD_MPIO": "CODIGO_MUNICIPIO"})


def _validar(factor: pd.DataFrame) -> None:
    print("--- describe F_AJUSTA_BOVINOS ---")
    print(factor["F_AJUSTA_BOVINOS"].describe())
    print("--- describe F_AJUSTA_BUFALINOS ---")
    print(factor["F_AJUSTA_BUFALINOS"].describe())

    conv = factor[factor["CODIGO_MUNICIPIO"] == "54206"]
    print("\nConvención (54206), debe dar ~87.5, no 8.75e14:")
    print(conv.to_string())


def generar_y_guardar() -> None:
    factor = calcular_factor_c2()
    _validar(factor)
    config.RUTA_FACTOR_C2.parent.mkdir(parents=True, exist_ok=True)
    factor.to_csv(config.RUTA_FACTOR_C2, sep=";", decimal=",", index=False)
    print(f"\nGuardado: {config.RUTA_FACTOR_C2}")


if __name__ == "__main__":
    generar_y_guardar()
