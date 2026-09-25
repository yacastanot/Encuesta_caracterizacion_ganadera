"""Acceso cacheado a los `.sas7bdat` de 2023/2024 - SOLO para el Cuadro 4/5
del libro "ganadero" (ningún otro cuadro usa estos años). Mismo patrón que
`fuente_cruda_c1.py` (cachear a Parquet una sola vez, podar columnas por
llamada), generalizado a una lista de rutas en vez de solo Ciclo 1.

Ver `config.py` para el porqué de cada ruta (cuál candidato se eligió y por
qué, entre varias versiones existentes en el servidor).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pyreadstat

from . import config

_RUTA_CACHE = {
    config.RUTA_2024_RUV_CRUDO: config.BASES_CALIBRADAS_DIR / "_cache_2024ruv.parquet",
    config.RUTA_2024_ENCUESTA_C1_CRUDO: config.BASES_CALIBRADAS_DIR / "_cache_2024encuestac1.parquet",
    config.RUTA_2024_ENCUESTA_C2_CRUDO: config.BASES_CALIBRADAS_DIR / "_cache_2024encuestac2.parquet",
    config.RUTA_2023_C1: config.BASES_CALIBRADAS_DIR / "_cache_2023c1.parquet",
    config.RUTA_2023_C2: config.BASES_CALIBRADAS_DIR / "_cache_2023c2.parquet",
}


def _asegurar_cache(ruta_sas7bdat: Path) -> Path:
    ruta_parquet = _RUTA_CACHE[ruta_sas7bdat]
    if not ruta_parquet.exists():
        print(f"(fuente_cruda_historico) generando caché Parquet de {ruta_sas7bdat.name} - puede tardar varios minutos...")
        # UTF-8 primero (correcto para los 3 archivos de 2024, ver
        # `fuente_cruda_c1.py` para el mismo hallazgo en Ciclo 1 2025) - los
        # de 2023 (`c12023.sas7bdat`/`c22023.sas7bdat`) vienen de un pipeline
        # SAS más antiguo y fallan con `ReadstatError` en UTF-8 (secuencia de
        # bytes inválida) - se reintenta con latin1 (cp1252/Windows-1252 es
        # subconjunto de latin1 para los caracteres que importan acá:
        # tildes/ñ), no se asume de entrada para no repetir el bug ya
        # documentado en `fuente_cruda_c1.py` (latin1 corrompía TODO texto
        # con tilde en un archivo que en realidad SÍ era UTF-8).
        try:
            df, _ = pyreadstat.read_sas7bdat(str(ruta_sas7bdat), encoding="utf-8")
        except pyreadstat._readstat_parser.ReadstatError:
            print(f"(fuente_cruda_historico) {ruta_sas7bdat.name}: UTF-8 falló, reintentando con latin1...")
            df, _ = pyreadstat.read_sas7bdat(str(ruta_sas7bdat), encoding="latin1")
        ruta_parquet.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(ruta_parquet, index=False)
        print(f"(fuente_cruda_historico) caché guardado: {ruta_parquet} ({len(df):,} filas)")
    return ruta_parquet


def columnas_disponibles(ruta_sas7bdat: Path) -> list[str]:
    ruta_parquet = _asegurar_cache(ruta_sas7bdat)
    return pq.ParquetFile(ruta_parquet).schema_arrow.names


def leer(ruta_sas7bdat: Path, columns: list[str] | None = None) -> pd.DataFrame:
    ruta_parquet = _asegurar_cache(ruta_sas7bdat)
    return pd.read_parquet(ruta_parquet, columns=columns)
