"""Traduce el `municipio_id` INTERNO que usan los programas SAS de Carolina
(`4.1`/`4.2`/`4.3`, incluida la macro `ajustar_valores_municipios` con sus 3
listas de códigos centinela 99999/88888/44444) a nuestro `CODIGO_MUNICIPIO`
(DIVIPOLA de 5 dígitos).

Fuente: `Programas Carolina/para calibrar formulado fedegan.xlsx`, hoja
"Hoja3" - trae DIRECTO `COD_DEPARTAMENTO`/`COD_MUNICIPIO` (DIVIPOLA) junto con
`municipio_id`/`DEPARTAMENTO_ID` (el id interno) para los 1121 municipios, sin
restringirse a los que tienen datos RUV. Es la fuente de verdad; no hace falta
adivinar nada.

(Antes de encontrar este archivo se había reconstruido una fórmula a partir de
`Divipola/divipola_mpio.sas7bdat` + `calibrac12025.xlsx`, validada al 99.5%
contra este archivo real - los pocos casos que fallaban eran por un municipio
adicional en Guainía, "San Felipe", que no estaba en `divipola_mpio.sas7bdat`.
Ya no se necesita: se deja de referencia en el historial de git.)

Con esto, las 3 listas de códigos centinela quedan traducidas:
 - ND (8): 8/8 resueltos.
 - 88888 (35): 35/35 resueltos.
 - 44444 (31): 31/31 resueltos (el id 1141 = Morichal, Guainía).
"""
from __future__ import annotations

import pandas as pd

from . import config

RUTA_CROSSWALK_FUENTE = config.BASE_DIR / "Programas Carolina" / "para calibrar formulado fedegan.xlsx"

MUNICIPIOS_ND_ID = [43, 185, 822, 826, 829, 833, 843, 848]
MUNICIPIOS_88888_ID = [
    104, 153, 408, 413, 433, 608, 610, 611, 612, 614, 616, 618, 619, 621, 622,
    624, 625, 626, 627, 628, 629, 630, 631, 633, 634, 635, 637, 765, 780, 785,
    787, 789, 791, 798, 805,
]
MUNICIPIOS_44444_ID = [
    613, 615, 623, 1120, 1121, 1122, 1123, 1124, 1125, 1126, 1127, 1128, 1129,
    1130, 1131, 1132, 1133, 1134, 1136, 1137, 1138, 1139, 1140, 1141, 1145,
    1146, 1147, 1148, 1149, 1150, 1151,
]


def construir_crosswalk_municipio_id() -> pd.DataFrame:
    h3 = pd.read_excel(RUTA_CROSSWALK_FUENTE, sheet_name="Hoja3")
    h3["CODIGO_MUNICIPIO"] = h3["COD_MUNICIPIO"].astype(str).str.zfill(5)
    h3["COD_DEPARTAMENTO"] = h3["COD_DEPARTAMENTO"].astype(str).str.zfill(2)
    h3["municipio_id"] = h3["municipio_id"].astype(int)

    return h3[["municipio_id", "CODIGO_MUNICIPIO", "COD_DEPARTAMENTO", "Departamento", "Municipio"]]


def _traducir(crosswalk: pd.DataFrame, ids: list[int], nombre: str) -> pd.DataFrame:
    sub = crosswalk[crosswalk["municipio_id"].isin(ids)]
    faltantes = set(ids) - set(sub["municipio_id"])
    print(f"{nombre}: {len(sub)}/{len(ids)} resueltos" + (f" - faltan municipio_id {sorted(faltantes)}" if faltantes else ""))
    return sub


def generar_y_guardar() -> None:
    crosswalk = construir_crosswalk_municipio_id()

    config.RUTA_CROSSWALK_MUNICIPIO_ID_C1.parent.mkdir(parents=True, exist_ok=True)
    crosswalk.to_csv(config.RUTA_CROSSWALK_MUNICIPIO_ID_C1, sep=";", index=False)
    print(f"Guardado: {config.RUTA_CROSSWALK_MUNICIPIO_ID_C1} ({len(crosswalk)} municipios)\n")

    nd = _traducir(crosswalk, MUNICIPIOS_ND_ID, "ND")
    l88888 = _traducir(crosswalk, MUNICIPIOS_88888_ID, "88888")
    l44444 = _traducir(crosswalk, MUNICIPIOS_44444_ID, "44444")

    codigos = pd.concat([
        nd.assign(lista="ND"), l88888.assign(lista="88888"), l44444.assign(lista="44444"),
    ])[["lista", "municipio_id", "CODIGO_MUNICIPIO", "Departamento", "Municipio"]]
    codigos.to_csv(config.RUTA_MUNICIPIOS_CENTINELA_C1, sep=";", index=False)
    print(f"\nGuardado: {config.RUTA_MUNICIPIOS_CENTINELA_C1}")


if __name__ == "__main__":
    generar_y_guardar()
