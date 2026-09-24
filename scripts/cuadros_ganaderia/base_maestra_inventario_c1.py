"""Base maestra de "inventario" de Ciclo 1: una fila por registro RUV+encuesta
(SIN deduplicar por predio-ganadero - los cuadros de inventario suman TODOS
los registros, a diferencia de los de ganadero/predio-ganadero; ver
`base_maestra_c1.py` para esa otra familia y por qué NO comparten una sola
tabla universal), con todas las columnas que usan los 5 cuadros de inventario
(`cuadros/inventario.py`: Cuadro 3/4/6/7/8) ya calibradas donde corresponde.

Por qué una tabla única: cada uno de esos 5 cuadros llamaba, en su propio
proceso, `preparar_base_c1.cargar_base_cruda` + `aplicar_factor_calibracion`
por separado - con el caché en Parquet de `fuente_cruda_c1.py` eso ya es
barato (~2s por proceso), pero seguían siendo 5 puntos de código que repiten
la misma lógica de exclusión + aplicación de factor, con riesgo de que
diverjan sin darse cuenta (ej. que alguno olvide aplicar el factor a alguna
columna nueva). Acá se calcula UNA sola vez y los 5 cuadros solo leen el
Parquet.

Columnas calibradas (multiplicadas por F_AJUSTA_BOVINOS/BUFALINOS, ver
`calibracion_c1.py`): las 13 columnas de tramo de sexo/edad (+ su propia
`_NV`) de bovinos Y de bufalinos (`preparar_base_c1.columnas_inventario`).

Columnas que se guardan SIN calibrar (igual que en el SAS original y en
`cuadros/inventario.py`, no se cambia ese comportamiento acá):
 - "otras especies" (equinos/porcinos/ovinos/caprinos/otros): el SAS original
   nunca las calibra (Cuadro 8).
 - `sistemaproductivo` (Cuadro 6): la variable en sí es categórica, no se
   calibra - lo que se calibra son las columnas de tramo bovino que el
   Cuadro 6 sigue sumando (ya vienen calibradas arriba).

`orientacionhato` (Cuadro 4/5) se guarda ya renombrada/normalizada
(`preparar_base_c1.normalizar_categoricas`) para que esos cuadros no repitan
esa transformación.

Solo Ciclo 1 por ahora (igual que `base_maestra_c1.py`) - Ciclo 2 usa
`preparar_base_c2.py`, que construye su propia base por separado y no pasa
por acá.
"""
from __future__ import annotations

import pandas as pd

from . import config, preparar_base_c1

RUTA_BASE_MAESTRA_INVENTARIO_C1 = config.BASES_CALIBRADAS_DIR / "base_maestra_inventario_C1_2025.parquet"

COLS_OTRAS_ESPECIES = [
    f"{esp}_{sexo}" for esp in ["EQUINOS", "PORCINOS", "OVINOS", "CAPRINOS", "OTROS"] for sexo in ["MACHO", "HEMBRA"]
] + [f"TOTAL_{esp}" for esp in ["EQUINOS", "PORCINOS", "OVINOS", "CAPRINOS", "OTROS"]]


def construir_base_maestra_inventario_c1() -> pd.DataFrame:
    columnas_bov = preparar_base_c1.columnas_inventario("bovinos")
    columnas_buf = preparar_base_c1.columnas_inventario("bufalinos")
    columnas_extra = columnas_bov + columnas_buf + COLS_OTRAS_ESPECIES + ["orientacionhato", "sistemaproductivo"]

    # Bovinos y bufalinos son EL MISMO archivo/filas (`ciclo1encuesta.sas7bdat`,
    # ver `preparar_base_c1.py`) - basta una sola carga con las columnas de
    # ambas especies para no leer/filtrar el archivo dos veces.
    df = preparar_base_c1.cargar_base_cruda("bovinos", columnas_extra=columnas_extra)

    # Cada especie se calibra con SU propio factor, sobre SUS propias columnas
    # de tramo - idéntico a lo que hacía cada cuadro por separado.
    df = preparar_base_c1.aplicar_factor_calibracion(df, "bovinos", columnas_bov)
    df = preparar_base_c1.aplicar_factor_calibracion(df, "bufalinos", columnas_buf)

    df = preparar_base_c1.renombrar_preguntas(df)
    df = preparar_base_c1.normalizar_categoricas(df)

    return df


def generar_y_guardar_c1() -> None:
    maestra = construir_base_maestra_inventario_c1()
    print(f"Filas: {len(maestra):,}")
    print(f"Municipios: {maestra['CODIGO_MUNICIPIO'].nunique():,}")
    cols_bov = preparar_base_c1.columnas_inventario("bovinos")
    cols_bov_con_nv = [col for base in cols_bov for col in (base, f"{base}_NV") if col in maestra.columns]
    print(f"Total bovinos (suma tramos calibrados): {maestra[cols_bov_con_nv].fillna(0).sum().sum():,.1f}")

    RUTA_BASE_MAESTRA_INVENTARIO_C1.parent.mkdir(parents=True, exist_ok=True)
    maestra.to_parquet(RUTA_BASE_MAESTRA_INVENTARIO_C1, index=False)
    print(f"Guardado: {RUTA_BASE_MAESTRA_INVENTARIO_C1}")


if __name__ == "__main__":
    generar_y_guardar_c1()
