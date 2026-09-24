"""Cachea en disco lo que calcula cada paso de `main.py` (una tabla + los
parámetros de escritura que necesita `excel_writer`), y ensambla los libros
completos leyendo esos "pendientes" - la ÚNICA vez que cada libro Excel se
carga y se guarda completo.

Por qué: antes, cada uno de los 9 pasos del libro de inventario llamaba a
`excel_writer.escribir_cuadro`, que carga y vuelve a guardar el libro
COMPLETO (que va creciendo con cada paso) - con el libro ya en ~22MB, eso
llegó a tomar ~17 minutos en total para un solo libro. La causa no es cuánto
tarda CALCULAR cada cuadro (eso ya es rápido, ver `base_maestra_inventario_c1.py`
y `fuente_cruda_c1.py`), sino cuántas veces se recarga/regraba el archivo Excel.

Separar "calcular" (sigue siendo un proceso Python por paso, por la RAM
limitada de la máquina - ver `main.py`) de "escribir en el Excel" (un solo
proceso, que carga la plantilla UNA vez, escribe TODOS los cuadros pendientes,
y guarda UNA vez) resuelve eso sin tocar la separación por proceso.

Un pendiente puede pertenecer a más de un libro (ej. Cuadro 1/2, que son
idénticos en los libros de ganadero y predio-ganadero - ver `main.LIBROS`):
es solo una tabla + parámetros de escritura, no sabe a qué libro va.

SEGURIDAD (evitar el riesgo ya identificado antes de que dos procesos
escriban el mismo .xlsx a la vez): con este diseño, el ÚNICO momento en que
un libro de salida se abre para escritura es dentro de `ensamblar()` - nunca
dentro de los pasos de cálculo. Mientras se corra `--ensamblar <libro>` como
una invocación explícita y no en paralelo con otra sobre el MISMO libro
(igual que antes), no hay riesgo de escritura concurrente.
"""
from __future__ import annotations

import json
from pathlib import Path

import openpyxl
import pandas as pd

from . import config, excel_writer

RUTA_PENDIENTES = config.BASES_CALIBRADAS_DIR / "_pendientes_libro"


def _ruta_parquet(nombre: str) -> Path:
    return RUTA_PENDIENTES / f"{nombre}.parquet"


def _ruta_specs(nombre: str) -> Path:
    return RUTA_PENDIENTES / f"{nombre}.json"


def guardar_pendiente(nombre: str, tabla: pd.DataFrame, **specs) -> None:
    """Cachea el resultado de un paso: `tabla` (a Parquet) + `specs` (a JSON) -
    los parámetros con los que `ensamblar` debe llamar a `excel_writer`
    después. `specs` siempre trae `tipo` ("cuadro" o "lista_plana") más los
    argumentos de `excel_writer._escribir_cuadro_en_wb` /
    `_escribir_lista_plana_en_wb` que apliquen (`hoja`, `fila_nacional` o
    `fila_inicio`, `value_cols`/`columnas`, `columna_inicio` si no es la
    default, etc.)."""
    RUTA_PENDIENTES.mkdir(parents=True, exist_ok=True)
    tabla.to_parquet(_ruta_parquet(nombre), index=False)
    _ruta_specs(nombre).write_text(json.dumps(specs, ensure_ascii=False), encoding="utf-8")


def pendiente_disponible(nombre: str) -> bool:
    return _ruta_parquet(nombre).exists() and _ruta_specs(nombre).exists()


def _cargar_pendiente(nombre: str) -> tuple[pd.DataFrame, dict]:
    tabla = pd.read_parquet(_ruta_parquet(nombre))
    specs = json.loads(_ruta_specs(nombre).read_text(encoding="utf-8"))
    return tabla, specs


def ensamblar(ruta_plantilla: Path, ruta_salida: Path, nombres_pasos: list[str]) -> None:
    """Carga `ruta_plantilla` UNA vez (como libro a escribir, y por separado
    como referencia de estilos "prístinos"), aplica los pendientes de
    `nombres_pasos` EN ESE ORDEN, y guarda UNA sola vez.

    El orden importa: un bloque "Segundo ciclo" depende de que su bloque
    "Primer ciclo" ya esté escrito en el mismo `wb` (mismo proceso, misma
    corrida) - ver `excel_writer._escribir_cuadro_en_wb`. `nombres_pasos`
    debe venir en el mismo orden que antes usaba `main.PASOS_INVENTARIO`.

    Siempre parte de la plantilla PRÍSTINA (nunca de un `ruta_salida`
    preexistente): como todos los pasos ya quedaron cacheados en
    `RUTA_PENDIENTES`, no hace falta acumular sobre una salida parcial
    anterior - reconstruir desde cero es más simple y más robusto (idempotente
    de verdad: correr esto dos veces da el mismo archivo)."""
    faltantes = [n for n in nombres_pasos if not pendiente_disponible(n)]
    if faltantes:
        raise FileNotFoundError(
            f"Faltan pasos por calcular antes de ensamblar {ruta_salida.name}: {faltantes} - "
            "correr `python -m scripts.cuadros_ganaderia.main --solo <paso>` para cada uno."
        )

    wb = openpyxl.load_workbook(ruta_plantilla)
    wb_pristina = openpyxl.load_workbook(ruta_plantilla)

    for nombre in nombres_pasos:
        tabla, specs = _cargar_pendiente(nombre)
        specs = dict(specs)
        tipo = specs.pop("tipo")
        if tipo == "cuadro":
            excel_writer._escribir_cuadro_en_wb(wb, wb_pristina, tabla=tabla, **specs)
        elif tipo == "lista_plana":
            excel_writer._escribir_lista_plana_en_wb(wb, tabla=tabla, **specs)
        else:
            raise ValueError(f"tipo de pendiente desconocido: {tipo!r} (paso {nombre!r})")

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ruta_salida)
    print(f"Guardado: {ruta_salida}")
