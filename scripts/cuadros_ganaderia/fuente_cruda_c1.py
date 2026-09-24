"""Acceso cacheado a los archivos crudos `.sas7bdat` de Ciclo 1 (RUV completo
y RUV+encuesta).

Por qué: 5 módulos distintos (`preparar_base_c1.py`, `calibracion_c1.py`,
`calibracion_predios_c1.py`, `calibracion_bovinos_bufalinos_c1.py`,
`calibracion_calruv_c1.py`) leen el MISMO `.sas7bdat` con `pyreadstat`, cada
uno con su propio subconjunto de columnas - y como cada cuadro corre en su
propio proceso (ver `main.py`), nada se comparte entre ellos: el archivo
completo (~750 mil filas, 335 columnas) se vuelve a parsear desde cero en
CADA módulo, de CADA proceso. `pyreadstat` parseando `.sas7bdat` es bastante
más lento que leer Parquet.

Estrategia: la primera vez que se pide este archivo, se lee completo UNA vez
con `pyreadstat` y se cachea en Parquet (`Bases Calibradas/_cache_*.parquet`,
gitignored igual que el resto de `Bases Calibradas/`). De ahí en adelante,
`leer()` usa `pd.read_parquet(..., columns=...)` - mucho más rápido, y sigue
permitiendo podar columnas por llamada igual que antes con `usecols`.

Regenerar el caché: borrar el `.parquet` correspondiente en
`Bases Calibradas/` (por ejemplo, si el `.sas7bdat` de origen cambió).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pyreadstat

from . import config

_RUTA_CACHE = {
    config.RUTA_CICLO1_RUV_CRUDO: config.BASES_CALIBRADAS_DIR / "_cache_ciclo1ruv.parquet",
    config.RUTA_CICLO1_ENCUESTA_CRUDO: config.BASES_CALIBRADAS_DIR / "_cache_ciclo1encuesta.parquet",
}


def _asegurar_cache(ruta_sas7bdat: Path) -> Path:
    ruta_parquet = _RUTA_CACHE[ruta_sas7bdat]
    if not ruta_parquet.exists():
        print(
            f"(fuente_cruda_c1) generando caché Parquet de {ruta_sas7bdat.name} "
            "- una sola vez, puede tardar varios minutos..."
        )
        # encoding="utf-8" - CORREGIDO 2026-09-21: la fuente real está en
        # UTF-8 (confirmado leyendo el archivo completo sin errores, y
        # verificando byte a byte que "orientacionhato" decodifica correcto
        # solo así - "Cría"/"Ganadería"/"Genética"/"propósito"). El código
        # anterior usaba encoding="latin1" por un UnicodeDecodeError que ya
        # no se pudo reproducir (puede haber sido de otro archivo o de una
        # selección de columnas distinta) - esa elección corrompía TODA
        # columna de texto con tildes: cada caracter multibyte UTF-8 se
        # decodificaba mal como 2 caracteres latin1, y al volver a guardarse
        # como UTF-8 en el Parquet quedaba doblemente mal codificado
        # (ej. "í" -> "Ã" + soft-hyphen -> 4 bytes en vez de 2). Esto rompía
        # en silencio cualquier comparación exacta de texto contra esas
        # columnas (`redistribucion.py` vía `orientacionhato`: Cuadro 4/5 del
        # libro de inventario perdían ~84% del inventario bovino, las 4
        # categorías con tilde de 6 quedaban en 0 - detectado al construir
        # Cuadro 4 de predio-ganadero, que también necesita esta columna).
        df, _ = pyreadstat.read_sas7bdat(str(ruta_sas7bdat), encoding="utf-8")
        ruta_parquet.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(ruta_parquet, index=False)
        print(f"(fuente_cruda_c1) caché guardado: {ruta_parquet}")
    return ruta_parquet


def columnas_disponibles(ruta_sas7bdat: Path) -> list[str]:
    """Nombres de columna del archivo, sin cargar los datos (lee solo el
    esquema del Parquet) - reemplaza a `pyreadstat.read_sas7bdat(...,
    metadataonly=True)`."""
    ruta_parquet = _asegurar_cache(ruta_sas7bdat)
    return pq.ParquetFile(ruta_parquet).schema_arrow.names


def leer(ruta_sas7bdat: Path, columns: list[str] | None = None) -> pd.DataFrame:
    ruta_parquet = _asegurar_cache(ruta_sas7bdat)
    return pd.read_parquet(ruta_parquet, columns=columns)
