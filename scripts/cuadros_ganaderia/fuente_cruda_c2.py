"""Acceso cacheado a los archivos crudos de Ciclo 2 (RUV completo y encuesta) -
equivalente de `fuente_cruda_c1.py` para Ciclo 1, pero para un formato distinto:
2 CSV exportados directo del RUV/DMC, SIN fila de encabezado (los nombres de
columna vienen posicionales, en un diccionario Excel aparte).

Diferencia clave con Ciclo 1: `ciclo1encuesta.sas7bdat` ya venía pre-unido
(identificación + territorio + inventario + respuestas de encuesta, todo en
una fila) - acá el archivo de encuesta SOLO trae respuestas + una clave de
unión (`CODIGO_RUV`) hacia el archivo RUV (columna `CODIGO RUV` ahí). Este
módulo solo expone lectura cacheada de cada archivo POR SEPARADO; el join que
reconstruye el equivalente de `ciclo1encuesta.sas7bdat` vive en
`preparar_ciclo2encuesta.py`.

Verificado esta sesión (2026-09-22), directo contra los archivos reales en
`S:\\01Entrada\\2025 II\\` (antes de copiarlos localmente):
 - `ExportarArchivoRuv.csv`: 750.531 filas, 285 columnas, separador `;`.
 - `ExportarArchivoEncuesta2_2025.csv`: 736.149 filas, 77 columnas, separador `;`.
 - Los diccionarios de columnas (`EncabezadoRuv2-2025.xlsx` /
   `EncabezadoExportarArchivoEncuesta2-2025.xlsx`, hoja "Hoja1") traen una
   ÚNICA fila con los nombres en el mismo orden posicional que las columnas
   del CSV - se verificaron 2 versiones distintas de `EncabezadoRuv2-2025*`
   en el servidor (tamaños de archivo distintos) y su "Hoja1" es IDÉNTICA
   (0 diferencias en las 285 columnas) - no importa cuál se use.
 - Encoding UTF-8 (mismo criterio que Ciclo 1 - ver `fuente_cruda_c1.py` para el
   bug que corrigió esa elección).

Regenerar el caché: borrar el `.parquet` correspondiente en `Bases Calibradas/`.
"""
from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd
import pyarrow.parquet as pq

from . import config

_RUTA_CACHE = {
    config.RUTA_CICLO2_RUV_CRUDO: config.BASES_CALIBRADAS_DIR / "_cache_ciclo2ruv.parquet",
    config.RUTA_CICLO2_ENCUESTA_CRUDO: config.BASES_CALIBRADAS_DIR / "_cache_ciclo2encuesta.parquet",
}
_RUTA_DICCIONARIO = {
    config.RUTA_CICLO2_RUV_CRUDO: config.RUTA_CICLO2_DICC_RUV,
    config.RUTA_CICLO2_ENCUESTA_CRUDO: config.RUTA_CICLO2_DICC_ENCUESTA,
}


def _columnas_desde_diccionario(ruta_diccionario: Path) -> list[str]:
    """Lee la fila única de `Hoja1` (nombres de columna en orden posicional)."""
    wb = openpyxl.load_workbook(ruta_diccionario, data_only=True, read_only=True)
    ws = wb["Hoja1"]
    fila = next(ws.iter_rows(min_row=1, max_row=1))
    columnas = [c.value for c in fila]
    wb.close()
    if any(c is None for c in columnas):
        raise ValueError(
            f"{ruta_diccionario.name}: la fila de encabezados de 'Hoja1' trae celdas vacías - "
            "no se puede mapear de forma posicional sin nombre para cada columna."
        )
    return columnas


def _asegurar_cache(ruta_csv: Path) -> Path:
    ruta_parquet = _RUTA_CACHE[ruta_csv]
    if not ruta_parquet.exists():
        columnas = _columnas_desde_diccionario(_RUTA_DICCIONARIO[ruta_csv])
        print(
            f"(fuente_cruda_c2) generando caché Parquet de {ruta_csv.name} "
            f"({len(columnas)} columnas) - una sola vez, puede tardar varios minutos..."
        )
        df = pd.read_csv(
            ruta_csv, sep=";", header=None, names=columnas, encoding="utf-8", low_memory=False,
        )
        if len(df.columns) != len(columnas):
            raise ValueError(
                f"{ruta_csv.name}: el CSV trae {len(df.columns)} columnas pero el diccionario "
                f"({_RUTA_DICCIONARIO[ruta_csv].name}) define {len(columnas)} - desincronizados."
            )
        ruta_parquet.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(ruta_parquet, index=False)
        print(f"(fuente_cruda_c2) caché guardado: {ruta_parquet} ({len(df):,} filas)")
    return ruta_parquet


def columnas_disponibles(ruta_csv: Path) -> list[str]:
    ruta_parquet = _asegurar_cache(ruta_csv)
    return pq.ParquetFile(ruta_parquet).schema_arrow.names


def leer(ruta_csv: Path, columns: list[str] | None = None) -> pd.DataFrame:
    ruta_parquet = _asegurar_cache(ruta_csv)
    return pd.read_parquet(ruta_parquet, columns=columns)


def leer_ruv(columns: list[str] | None = None) -> pd.DataFrame:
    return leer(config.RUTA_CICLO2_RUV_CRUDO, columns=columns)


def leer_encuesta(columns: list[str] | None = None) -> pd.DataFrame:
    return leer(config.RUTA_CICLO2_ENCUESTA_CRUDO, columns=columns)
