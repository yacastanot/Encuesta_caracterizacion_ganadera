"""Orquestador: calcula los cuadros ya disponibles y los guarda en output/.

Dos fases, deliberadamente separadas (ver `ensamblador.py` para el porqué):
 1. CALCULAR: cada cuadro se corre como paso independiente (`--solo <paso>`)
    para que cada invocación sea un proceso nuevo de Python - la máquina
    donde corre esto tiene poca RAM libre (8 GB) y encadenar varios cuadros
    pesados en un mismo proceso ya causó un MemoryError una vez. Un proceso
    por cuadro garantiza que el sistema operativo libera toda la memoria
    entre pasos. Cada paso guarda su resultado como "pendiente" (Parquet +
    JSON en `Bases Calibradas/_pendientes_libro/`), NO escribe el Excel.
 2. ENSAMBLAR: `--ensamblar <libro>` (o el modo sin argumentos, ver abajo)
    arma el .xlsx final: carga la plantilla UNA vez, escribe todos los
    cuadros pendientes de ese libro, guarda UNA vez. Es la ÚNICA fase que
    toca el Excel de salida - evita que el mismo archivo se recargue y
    regrabe por completo en cada cuadro (con el libro de inventario en
    ~22MB, eso llegó a tomar ~17 minutos en total).
"""
from __future__ import annotations

import argparse
import time

from . import config, ensamblador
from .cuadros import comun, ganadero, inventario, predio_ganadero

RUTA_SALIDA_INVENTARIO = config.OUTPUT_DIR / "Cuadros caracterización inventario Ciclos 1 y 2_2025_generado.xlsx"
RUTA_SALIDA_GANADERO = config.OUTPUT_DIR / "Cuadros caracterización del ganadero Ciclos 1 y 2_2025_generado.xlsx"
RUTA_SALIDA_PREDIO_GANADERO = config.OUTPUT_DIR / "Cuadros Caracterización predio-ganadero Ciclos 1 y 2_2025_generado.xlsx"

FILA_NACIONAL_CUADRO1_COMUN = 7
FILA_INICIO_CUADRO2_COMUN = 11

# Columna donde empieza el bloque "Segundo ciclo" en cada hoja (verificado
# contra la plantilla real con openpyxl: Cuadro 3/7 tienen bloque Primer ciclo
# en E-Z y Segundo ciclo en AA-AV -por eso 27-; Cuadro 8 tiene E-S y T-AH
# -por eso 20-). Cuadro 4/5 no comparten hoja: Cuadro 5 es la hoja "Segundo
# ciclo" completa, por eso usa la columna E de siempre.
COLUMNA_SEGUNDO_CICLO_C3_C7 = 27  # AA
COLUMNA_SEGUNDO_CICLO_C8 = 20  # T

# Orden de ensamblado dentro de cada libro - IMPORTA para los bloques
# "Segundo ciclo" (ej. cuadro3_c2 depende de que cuadro3 ya haya escrito el
# esqueleto de la hoja "Cuadro 3" en el mismo `wb`, ver `ensamblador.py`).
#
# "cuadro1_ganadero"/"cuadro2_ganadero" abren la lista a propósito: los
# Cuadros 1 y 2 del libro de inventario son LOS MISMOS que en los libros de
# ganadero/predio-ganadero - misma fila 7 "Total Nacional" (Cuadro 1), misma
# fila 11 de inicio (Cuadro 2), mismas columnas A-E (verificado con la
# plantilla real) - así que los pendientes ya calculados por
# `_paso_cuadro1_ganadero`/`_paso_cuadro2_ganadero` se reutilizan tal cual,
# sin recalcular nada. El Cuadro 2 de inventario trae además una columna F
# "Observación (Segundo ciclo)" que no existe en ganadero/predio-ganadero -
# queda en blanco por ahora, mismo criterio "Ciclo 1 primero" del resto del
# proyecto.
PASOS_INVENTARIO = [
    "cuadro1_ganadero", "cuadro1_ganadero_c2", "cuadro1_ganadero_nuevos", "cuadro2_ganadero",
    # Ciclo 2 (cuadro3_c2/cuadro7_c2/cuadro8_c2) RESTAURADO 2026-09-23 (Fase 7
    # del plan de Ciclo 2): la exclusión de 2026-09-22 fue mientras
    # `preparar_base_c2.py` todavía leía la base heredada pre-calibrada de
    # `01Entrada/2025 II/` (fuente prohibida, ver `config.py`) - ya redirigido
    # a los insumos crudos reales (`preparar_ciclo2encuesta.py`, Fase 4 del
    # plan), no hay motivo para seguir excluyéndolo. Cada "_c2" va
    # inmediatamente después de su bloque "Primer ciclo" (misma hoja, columna
    # distinta - ver `excel_writer._escribir_cuadro_en_wb`).
    "cuadro3", "cuadro3_c2", "cuadro6", "cuadro7", "cuadro7_c2", "cuadro8", "cuadro8_c2", "cuadro4", "cuadro5",
]
# Orden importa: "cuadro1_ganadero_c2" es un bloque adicional (columnas H-J)
# sobre la MISMA hoja "Cuadro 1" que ya escribió "cuadro1_ganadero" (E-G) -
# debe ir después, mismo criterio que "cuadro3_c2"/"cuadro7_c2" en
# PASOS_INVENTARIO (ver `excel_writer._escribir_cuadro_en_wb`).
PASOS_GANADERO_COMUN = ["cuadro1_ganadero", "cuadro1_ganadero_c2", "cuadro1_ganadero_nuevos", "cuadro2_ganadero"]
# Solo del libro "ganadero" (no se comparte con predio-ganadero/inventario).
PASOS_GANADERO = PASOS_GANADERO_COMUN + [
    # "_c2" restaurado 2026-09-23 (Fase 7) inmediatamente después de su
    # bloque C1 (misma hoja, columna distinta). Cuadro 16 no tiene bloque C2
    # (no existe `conformacion`/`intcarrera` en Ciclo 2).
    "cuadro3_ganadero", "cuadro3_ganadero_c2",
    "cuadro6_ganadero", "cuadro6_ganadero_c2",
    "cuadro8_ganadero", "cuadro8_ganadero_c2",
    "cuadro9_ganadero", "cuadro9_ganadero_c2",
    "cuadro10_ganadero", "cuadro10_ganadero_c2",
    "cuadro11_ganadero", "cuadro11_ganadero_c2",
    "cuadro12_ganadero", "cuadro12_ganadero_c2",
    "cuadro13_ganadero", "cuadro13_ganadero_c2",
    "cuadro14_ganadero", "cuadro14_ganadero_c2",
    "cuadro15_ganadero", "cuadro15_ganadero_c2",
    "cuadro16_ganadero",
]

# Solo del libro "predio-ganadero" (no se comparte con ganadero/inventario).
PASOS_PREDIO_GANADERO = PASOS_GANADERO_COMUN + [
    # "_c2" restaurado 2026-09-23 (Fase 7) inmediatamente después de su
    # bloque C1 (misma hoja, columna distinta). Cuadro 5/6/7/8/10/13/14 no
    # tienen bloque C2 (`canttrabaj`/`sistemaproductivo`/colmenas no existen
    # en Ciclo 2).
    "cuadro3_predio_ganadero", "cuadro3_predio_ganadero_c2",
    "cuadro4_predio_ganadero", "cuadro4_predio_ganadero_c2",
    "cuadro5_predio_ganadero",
    "cuadro6_predio_ganadero", "cuadro7_predio_ganadero", "cuadro8_predio_ganadero",
    "cuadro9_predio_ganadero", "cuadro9_predio_ganadero_c2",
    "cuadro10_predio_ganadero",
    "cuadro11_predio_ganadero", "cuadro11_predio_ganadero_c2",
    "cuadro12_predio_ganadero", "cuadro12_predio_ganadero_c2",
    "cuadro13_predio_ganadero", "cuadro14_predio_ganadero",
    # Cuadro 15-19: preguntas NUEVAS del cuestionario de Ciclo 2 (sin
    # equivalente en Ciclo 1, ver `cuadros/predio_ganadero.py`) - hojas de un
    # solo bloque, no C1+C2.
    "cuadro15_predio_ganadero", "cuadro16_predio_ganadero", "cuadro17_predio_ganadero",
    "cuadro18_predio_ganadero", "cuadro19_predio_ganadero",
]

LIBROS = {
    "inventario": (RUTA_SALIDA_INVENTARIO, config.TEMPLATE_INVENTARIO, PASOS_INVENTARIO),
    "ganadero": (RUTA_SALIDA_GANADERO, config.TEMPLATE_GANADERO, PASOS_GANADERO),
    "predio_ganadero": (RUTA_SALIDA_PREDIO_GANADERO, config.TEMPLATE_PREDIO_GANADERO, PASOS_PREDIO_GANADERO),
}


def _paso_cuadro3() -> None:
    t0 = time.time()
    print("Cuadro 3 (bovinos, por sexo y edad) ...")
    tabla = inventario.generar("bovinos")
    ensamblador.guardar_pendiente(
        "cuadro3", tabla, tipo="cuadro", hoja="Cuadro 3", fila_nacional=8, value_cols=inventario.value_cols(),
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_total']:,.1f}")


def _paso_cuadro6() -> None:
    t0 = time.time()
    print("Cuadro 6 (bovinos, por sistema productivo) ...")
    tabla = inventario.generar_sistema_productivo()
    ensamblador.guardar_pendiente(
        "cuadro6", tabla, tipo="cuadro", hoja="Cuadro 6", fila_nacional=7,
        value_cols=inventario.value_cols_sistema_productivo(),
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['sist_total']:,.1f}")


def _paso_cuadro7() -> None:
    t0 = time.time()
    print("Cuadro 7 (bufalinos, por sexo y edad) ...")
    tabla = inventario.generar("bufalinos")
    ensamblador.guardar_pendiente(
        "cuadro7", tabla, tipo="cuadro", hoja="Cuadro 7", fila_nacional=8, value_cols=inventario.value_cols(),
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_total']:,.1f}")


def _paso_cuadro8() -> None:
    t0 = time.time()
    print("Cuadro 8 (otras especies pecuarias) ...")
    tabla = inventario.generar_otras_especies()
    ensamblador.guardar_pendiente(
        "cuadro8", tabla, tipo="cuadro", hoja="Cuadro 8", fila_nacional=9,
        value_cols=inventario.value_cols_otras_especies(),
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional equinos: {tabla.iloc[0]['TOTAL_EQUINOS']:,.1f}")


def _paso_cuadro4() -> None:
    t0 = time.time()
    print("Cuadro 4 (bovinos, por orientación de hato) ...")
    tabla, cols = inventario.generar_por_orientacion("bovinos", ciclo="C1")
    ensamblador.guardar_pendiente("cuadro4", tabla, tipo="cuadro", hoja="Cuadro 4", fila_nacional=8, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional (bloque total): {tabla.iloc[0]['blk_total__total_total']:,.1f}")


# --- Ciclo 2 (base RUV cruda + factor recalculado en `calibracion_c2.py`) ---

def _paso_cuadro3_c2() -> None:
    t0 = time.time()
    print("Cuadro 3, bloque Segundo ciclo (bovinos, por sexo y edad) ...")
    tabla = inventario.generar("bovinos", ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro3_c2", tabla, tipo="cuadro", hoja="Cuadro 3", fila_nacional=8, value_cols=inventario.value_cols(),
        columna_inicio=COLUMNA_SEGUNDO_CICLO_C3_C7,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_total']:,.1f}")


def _paso_cuadro7_c2() -> None:
    t0 = time.time()
    print("Cuadro 7, bloque Segundo ciclo (bufalinos, por sexo y edad) ...")
    tabla = inventario.generar("bufalinos", ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro7_c2", tabla, tipo="cuadro", hoja="Cuadro 7", fila_nacional=8, value_cols=inventario.value_cols(),
        columna_inicio=COLUMNA_SEGUNDO_CICLO_C3_C7,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_total']:,.1f}")


def _paso_cuadro8_c2() -> None:
    t0 = time.time()
    print("Cuadro 8, bloque Segundo ciclo (otras especies pecuarias) ...")
    tabla = inventario.generar_otras_especies(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro8_c2", tabla, tipo="cuadro", hoja="Cuadro 8", fila_nacional=9,
        value_cols=inventario.value_cols_otras_especies(), columna_inicio=COLUMNA_SEGUNDO_CICLO_C8,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional equinos: {tabla.iloc[0]['TOTAL_EQUINOS']:,.1f}")


def _paso_cuadro5() -> None:
    t0 = time.time()
    print("Cuadro 5 (bovinos, por orientación de hato, Segundo ciclo) ...")
    tabla, cols = inventario.generar_por_orientacion("bovinos", ciclo="C2")
    ensamblador.guardar_pendiente("cuadro5", tabla, tipo="cuadro", hoja="Cuadro 5", fila_nacional=8, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional (bloque total): {tabla.iloc[0]['blk_total__total_total']:,.1f}")


def _paso_cuadro1_ganadero() -> None:
    """Cuadro 1 ("Cantidad de predios, ganaderos y predios ganaderos"):
    idéntico en los 3 libros - un solo pendiente, `ensamblar` lo aplica a los
    3. Ver `cuadros/comun.py`. Bloque "Primer ciclo" (columnas E-G)."""
    t0 = time.time()
    print("Cuadro 1 (predios, ganaderos, predios ganaderos - Ciclo 1) ...")
    tabla, cols = comun.generar_cuadro1(ciclo="C1")
    ensamblador.guardar_pendiente(
        "cuadro1_ganadero", tabla, tipo="cuadro", hoja="Cuadro 1",
        fila_nacional=FILA_NACIONAL_CUADRO1_COMUN, value_cols=cols,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional predios ganaderos: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro1_ganadero_c2() -> None:
    """Cuadro 1, bloque "Segundo ciclo" (columnas H-J) - columnas "nuevos"
    (K-N) quedan pendientes, ver docstring de `cuadros/comun.py`."""
    t0 = time.time()
    print("Cuadro 1, bloque Segundo ciclo (predios, ganaderos, predios ganaderos - Ciclo 2) ...")
    tabla, cols = comun.generar_cuadro1(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro1_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 1",
        fila_nacional=FILA_NACIONAL_CUADRO1_COMUN, value_cols=cols, columna_inicio=8,  # H
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional predios ganaderos: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro1_ganadero_nuevos() -> None:
    """Cuadro 1, bloque "nuevos" (columnas K-N) - ver `cuadros/comun.generar_cuadro1_nuevos`."""
    t0 = time.time()
    print("Cuadro 1, bloque nuevos (predios/ganaderos/predios ganaderos/animales nuevos en Ciclo 2) ...")
    tabla, cols = comun.generar_cuadro1_nuevos()
    ensamblador.guardar_pendiente(
        "cuadro1_ganadero_nuevos", tabla, tipo="cuadro", hoja="Cuadro 1",
        fila_nacional=FILA_NACIONAL_CUADRO1_COMUN, value_cols=cols, columna_inicio=11,  # K
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional predios ganaderos nuevos: {tabla.iloc[0]['predios_ganaderos_nuevos']:,.1f}")


def _paso_cuadro2_ganadero() -> None:
    """Cuadro 2 ("Municipios sin información asociada"): idéntico en los 3
    libros. Columna E = Observación Ciclo 1, columna F = Observación Ciclo 2
    (unión de `MUNICIPIOS_EXCLUIDOS_C1`/`_C2`, ver `cuadros/comun.py`)."""
    t0 = time.time()
    print("Cuadro 2 (municipios sin información asociada, Ciclo 1 + Ciclo 2) ...")
    tabla = comun.generar_cuadro2()
    columnas = ["COD_DEPARTAMENTO", "DEPARTAMENTO", "CODIGO_MUNICIPIO", "MUNICIPIO", "Observacion_C1", "Observacion_C2"]
    ensamblador.guardar_pendiente(
        "cuadro2_ganadero", tabla, tipo="lista_plana", hoja="Cuadro 2",
        fila_inicio=FILA_INICIO_CUADRO2_COMUN, columnas=columnas,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Municipios: {len(tabla)}")


def _paso_cuadro3_ganadero() -> None:
    """Cuadro 3 del libro "ganadero" ("Cantidad de ganaderos por sexo y
    persona jurídica") - no confundir con `_paso_cuadro3` (bovinos por sexo y
    edad, libro "inventario"). Ver `cuadros/ganadero.py`."""
    t0 = time.time()
    print("Cuadro 3 (ganaderos por sexo y persona jurídica - Ciclo 1) ...")
    tabla, cols = ganadero.generar_cuadro3()
    ensamblador.guardar_pendiente("cuadro3_ganadero", tabla, tipo="cuadro", hoja="Cuadro 3", fila_nacional=8, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro6_ganadero() -> None:
    """Cuadro 6 del libro "ganadero" ("Cantidad de ganaderos víctimas de
    algún delito") - no confundir con `_paso_cuadro6` (sistema productivo
    bovino, libro "inventario"). Ver `cuadros/ganadero.py`."""
    t0 = time.time()
    print("Cuadro 6 (ganaderos víctimas de delito - Ciclo 1) ...")
    tabla, cols = ganadero.generar_cuadro6()
    ensamblador.guardar_pendiente("cuadro6_ganadero", tabla, tipo="cuadro", hoja="Cuadro 6", fila_nacional=7, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro8_ganadero() -> None:
    """Cuadro 8 del libro "ganadero" ("Cantidad de ganaderos por sexo,
    tenencia del predio y persona jurídica") - no confundir con
    `_paso_cuadro8` (otras especies pecuarias, libro "inventario"). Ver
    `cuadros/ganadero.py`."""
    t0 = time.time()
    print("Cuadro 8 (ganaderos por sexo, tenencia y persona jurídica - Ciclo 1) ...")
    tabla, cols = ganadero.generar_cuadro8()
    ensamblador.guardar_pendiente("cuadro8_ganadero", tabla, tipo="cuadro", hoja="Cuadro 8", fila_nacional=8, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro9_ganadero() -> None:
    """Cuadro 9 del libro "ganadero" ("Cantidad de ganaderos que comparten
    lotes con otros ganaderos, por sexo y persona jurídica"). Ver
    `cuadros/ganadero.py`."""
    t0 = time.time()
    print("Cuadro 9 (ganaderos que comparten lotes - Ciclo 1) ...")
    tabla, cols = ganadero.generar_cuadro9()
    ensamblador.guardar_pendiente("cuadro9_ganadero", tabla, tipo="cuadro", hoja="Cuadro 9", fila_nacional=8, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro10_ganadero() -> None:
    """Cuadro 10 del libro "ganadero" ("Cantidad de ganaderos de acuerdo con
    el lugar de residencia, por sexo y persona jurídica"). Ver
    `cuadros/ganadero.py`."""
    t0 = time.time()
    print("Cuadro 10 (ganaderos por lugar de residencia - Ciclo 1) ...")
    tabla, cols = ganadero.generar_cuadro10()
    ensamblador.guardar_pendiente("cuadro10_ganadero", tabla, tipo="cuadro", hoja="Cuadro 10", fila_nacional=8, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro11_ganadero() -> None:
    """Cuadro 11 del libro "ganadero" ("Cantidad de ganaderos que responden
    directamente la encuesta, por sexo y persona jurídica"). Ver
    `cuadros/ganadero.py`."""
    t0 = time.time()
    print("Cuadro 11 (ganaderos que responden directamente la encuesta - Ciclo 1) ...")
    tabla, cols = ganadero.generar_cuadro11()
    ensamblador.guardar_pendiente("cuadro11_ganadero", tabla, tipo="cuadro", hoja="Cuadro 11", fila_nacional=8, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro12_ganadero() -> None:
    """Cuadro 12 del libro "ganadero" ("Cantidad de ganaderos donde el
    ganadero manifestó conocer qué es un sensor epidemiológico"). Ver
    `cuadros/ganadero.py`."""
    t0 = time.time()
    print("Cuadro 12 (ganaderos que conocen sensor epidemiológico - Ciclo 1) ...")
    tabla, cols = ganadero.generar_cuadro12()
    ensamblador.guardar_pendiente("cuadro12_ganadero", tabla, tipo="cuadro", hoja="Cuadro 12", fila_nacional=8, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro13_ganadero() -> None:
    """Cuadro 13 del libro "ganadero" ("Cantidad de ganaderos que
    manifestaron conocer el sistema de alerta temprana"). Ver
    `cuadros/ganadero.py`."""
    t0 = time.time()
    print("Cuadro 13 (ganaderos que conocen sistema de alerta temprana - Ciclo 1) ...")
    tabla, cols = ganadero.generar_cuadro13()
    ensamblador.guardar_pendiente("cuadro13_ganadero", tabla, tipo="cuadro", hoja="Cuadro 13", fila_nacional=8, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro14_ganadero() -> None:
    """Cuadro 14 del libro "ganadero" ("Cantidad de ganaderos que
    manifestaron conocer la obligación de notificar al ICA"). Ver
    `cuadros/ganadero.py`."""
    t0 = time.time()
    print("Cuadro 14 (ganaderos que conocen obligación de notificar al ICA - Ciclo 1) ...")
    tabla, cols = ganadero.generar_cuadro14()
    ensamblador.guardar_pendiente("cuadro14_ganadero", tabla, tipo="cuadro", hoja="Cuadro 14", fila_nacional=8, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro15_ganadero() -> None:
    """Cuadro 15 del libro "ganadero" ("Cantidad de ganaderos cuyo ganado
    presentó signos clínicos reproductivos"). Ver `cuadros/ganadero.py`."""
    t0 = time.time()
    print("Cuadro 15 (ganaderos con signos clínicos reproductivos - Ciclo 1) ...")
    tabla, cols = ganadero.generar_cuadro15()
    ensamblador.guardar_pendiente("cuadro15_ganadero", tabla, tipo="cuadro", hoja="Cuadro 15", fila_nacional=8, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro16_ganadero() -> None:
    """Cuadro 16 del libro "ganadero" ("Cantidad de ganaderos que conocen los
    programas de formación técnica/tecnológica de la Universidad del Área
    Andina e interés en cursarla"). Ver `cuadros/ganadero.py`."""
    t0 = time.time()
    print("Cuadro 16 (ganaderos que conocen programas Universidad del Área Andina - Ciclo 1) ...")
    tabla, cols = ganadero.generar_cuadro16()
    ensamblador.guardar_pendiente("cuadro16_ganadero", tabla, tipo="cuadro", hoja="Cuadro 16", fila_nacional=7, value_cols=cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional (conoce): {tabla.iloc[0]['total_ganaderos']:,.1f}")


# --- Ciclo 2 (libro "ganadero") ---
# Columna donde empieza el bloque "Segundo ciclo" en cada hoja (verificado
# contra la plantilla real con openpyxl, mismo método que
# COLUMNA_SEGUNDO_CICLO_C3_C7/_C8 arriba). Cuadro 16 no tiene bloque Segundo
# ciclo (no existe `conformacion`/`intcarrera` en Ciclo 2, ver
# `cuadros/ganadero.py`) - sin constante ni paso "_c2".
COLUMNA_SEGUNDO_CICLO_GAN_C3 = 10   # J
COLUMNA_SEGUNDO_CICLO_GAN_C6 = 14   # N
COLUMNA_SEGUNDO_CICLO_GAN_C8 = 34   # AH
COLUMNA_SEGUNDO_CICLO_GAN_C9 = 14   # N
COLUMNA_SEGUNDO_CICLO_GAN_C10 = 17  # Q
COLUMNA_SEGUNDO_CICLO_GAN_C11 = 14  # N
COLUMNA_SEGUNDO_CICLO_GAN_C12 = 9   # I
COLUMNA_SEGUNDO_CICLO_GAN_C13 = 9   # I
COLUMNA_SEGUNDO_CICLO_GAN_C14 = 9   # I
COLUMNA_SEGUNDO_CICLO_GAN_C15 = 9   # I


def _paso_cuadro3_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 3, bloque Segundo ciclo (ganaderos por sexo y persona jurídica - Ciclo 2) ...")
    tabla, cols = ganadero.generar_cuadro3(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro3_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 3", fila_nacional=8, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_GAN_C3,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro6_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 6, bloque Segundo ciclo (ganaderos víctimas de delito - Ciclo 2) ...")
    tabla, cols = ganadero.generar_cuadro6(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro6_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 6", fila_nacional=7, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_GAN_C6,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro8_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 8, bloque Segundo ciclo (ganaderos por sexo, tenencia y persona jurídica - Ciclo 2) ...")
    tabla, cols = ganadero.generar_cuadro8(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro8_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 8", fila_nacional=8, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_GAN_C8,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro9_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 9, bloque Segundo ciclo (ganaderos que comparten lotes - Ciclo 2) ...")
    tabla, cols = ganadero.generar_cuadro9(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro9_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 9", fila_nacional=8, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_GAN_C9,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro10_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 10, bloque Segundo ciclo (ganaderos por lugar de residencia - Ciclo 2) ...")
    tabla, cols = ganadero.generar_cuadro10(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro10_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 10", fila_nacional=8, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_GAN_C10,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro11_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 11, bloque Segundo ciclo (ganaderos que responden directamente la encuesta - Ciclo 2) ...")
    tabla, cols = ganadero.generar_cuadro11(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro11_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 11", fila_nacional=8, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_GAN_C11,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro12_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 12, bloque Segundo ciclo (ganaderos que conocen sensor epidemiológico - Ciclo 2) ...")
    tabla, cols = ganadero.generar_cuadro12(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro12_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 12", fila_nacional=8, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_GAN_C12,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro13_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 13, bloque Segundo ciclo (ganaderos que conocen sistema de alerta temprana - Ciclo 2) ...")
    tabla, cols = ganadero.generar_cuadro13(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro13_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 13", fila_nacional=8, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_GAN_C13,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro14_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 14, bloque Segundo ciclo (ganaderos que conocen obligación de notificar al ICA - Ciclo 2) ...")
    tabla, cols = ganadero.generar_cuadro14(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro14_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 14", fila_nacional=8, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_GAN_C14,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


def _paso_cuadro15_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 15, bloque Segundo ciclo (ganaderos con signos clínicos reproductivos - Ciclo 2) ...")
    tabla, cols = ganadero.generar_cuadro15(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro15_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 15", fila_nacional=8, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_GAN_C15,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_ganaderos']:,.1f}")


# --- Libro "predio-ganadero" ---

def _paso_cuadro3_predio_ganadero() -> None:
    """Cuadro 3 del libro "predio-ganadero" ("Cantidad de predios ganaderos,
    por inventario ganadero bovino o bufalino"). Ver
    `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 3 (predios ganaderos por inventario bovino/bufalino - Ciclo 1) ...")
    tabla, cols = predio_ganadero.generar_cuadro3()
    ensamblador.guardar_pendiente(
        "cuadro3_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 3", fila_nacional=7, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro4_predio_ganadero() -> None:
    """Cuadro 4 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    según la principal orientación del hato"). Ver
    `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 4 (predios ganaderos por orientación del hato - Ciclo 1) ...")
    tabla, cols = predio_ganadero.generar_cuadro4()
    ensamblador.guardar_pendiente(
        "cuadro4_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 4", fila_nacional=9, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro5_predio_ganadero() -> None:
    """Cuadro 5 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    según la cantidad de personas que trabajaron en la actividad ganadera").
    Ver `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 5 (predios ganaderos por cantidad de trabajadores - Ciclo 1) ...")
    tabla, cols = predio_ganadero.generar_cuadro5()
    ensamblador.guardar_pendiente(
        "cuadro5_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 5", fila_nacional=7, value_cols=cols,
        # La plantilla solo trae texto en F6/G6 ("XXX hasta XXXX") pero el
        # formato de celda (bordes/number_format) del bloque de datos llega
        # hasta la columna M: reserva 8 clases (E=Total + F..M), no 2 - ver
        # `cuadros/predio_ganadero.generar_cuadro5`.
        encabezados={
            "F6": "0 trabajadores", "G6": "1 trabajador", "H6": "2 trabajadores",
            "I6": "3 trabajadores", "J6": "4 a 5 trabajadores", "K6": "6 a 10 trabajadores",
            "L6": "11 a 20 trabajadores", "M6": "21 o más trabajadores",
        },
        nota_extra_etiqueta="Nota metodológica",
        nota_extra_texto=(
            "La plantilla original no definía los rangos de esta pregunta (encabezados "
            "\"XXX hasta XXXX\") y solicitaba un análisis de frecuencia previo para definirlos. "
            "Se evaluó la regla de Sturges (k = 1 + log2(n) ≈ 20.5 clases) sobre el rango completo "
            "de `canttrabaj` (0 a 2211), mostrando un ancho de clase (~110) inservible para una "
            "distribución tan concentrada (89.67% de los predios reporta 2 trabajadores o menos) y "
            "con outliers extremos (valores repetidos sospechosos como 1500, 1700, 2000, 2211, "
            "probable error de captura). Con las 8 clases que sí reserva la plantilla, se usaron en "
            "cambio los quiebres naturales de la frecuencia acumulada real: 0 / 1 / 2 / 3 / 4 a 5 / "
            "6 a 10 / 11 a 20 / 21 o más - más resolución donde se concentra la mayoría de los datos "
            "(0 a 3 trabajadores = 95.4%) y clases más anchas en la cola dispersa."
        ),
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro6_predio_ganadero() -> None:
    """Cuadro 6 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    según el sistema productivo, sexo del ganadero y persona jurídica"). Ver
    `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 6 (predios ganaderos por sistema productivo/sexo/persona jurídica - Ciclo 1) ...")
    tabla, cols = predio_ganadero.generar_cuadro6()
    ensamblador.guardar_pendiente(
        "cuadro6_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 6", fila_nacional=8, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro7_predio_ganadero() -> None:
    """Cuadro 7 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    por sistema de producción y principal orientación del hato"). Ver
    `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 7 (predios ganaderos por sistema productivo x orientación del hato - Ciclo 1) ...")
    tabla, cols = predio_ganadero.generar_cuadro7()
    ensamblador.guardar_pendiente(
        "cuadro7_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 7", fila_nacional=9, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro8_predio_ganadero() -> None:
    """Cuadro 8 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    por sexo del ganadero y persona jurídica y sistema de producción"). Ver
    `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 8 (predios ganaderos por sexo/persona jurídica x sistema productivo - Ciclo 1) ...")
    tabla, cols = predio_ganadero.generar_cuadro8()
    ensamblador.guardar_pendiente(
        "cuadro8_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 8", fila_nacional=9, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro9_predio_ganadero() -> None:
    """Cuadro 9 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    por sexo del ganadero, condición jurídica y principal orientación del
    hato" - solo Ciclo 1). Ver `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 9 (predios ganaderos por sexo/condición jurídica x orientación del hato - Ciclo 1) ...")
    tabla, cols = predio_ganadero.generar_cuadro9()
    ensamblador.guardar_pendiente(
        "cuadro9_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 9", fila_nacional=9, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro10_predio_ganadero() -> None:
    """Cuadro 10 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    por tenencia del predio y tipo de sistema productivo"). Ver
    `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 10 (predios ganaderos por tenencia x sistema productivo - Ciclo 1) ...")
    tabla, cols = predio_ganadero.generar_cuadro10()
    ensamblador.guardar_pendiente(
        "cuadro10_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 10", fila_nacional=8, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro11_predio_ganadero() -> None:
    """Cuadro 11 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    por tenencia del predio" - solo Ciclo 1). Ver `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 11 (predios ganaderos por tenencia - Ciclo 1) ...")
    tabla, cols = predio_ganadero.generar_cuadro11()
    ensamblador.guardar_pendiente(
        "cuadro11_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 11", fila_nacional=11, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro12_predio_ganadero() -> None:
    """Cuadro 12 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    por tenencia del predio y principal orientación del hato" - solo
    Ciclo 1). Ver `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 12 (predios ganaderos por tenencia x orientación del hato - Ciclo 1) ...")
    tabla, cols = predio_ganadero.generar_cuadro12()
    ensamblador.guardar_pendiente(
        "cuadro12_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 12", fila_nacional=12, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro13_predio_ganadero() -> None:
    """Cuadro 13 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    por número de niños que residen permanentemente en el predio ganadero").
    Ver `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 13 (predios ganaderos por número de niños residentes - Ciclo 1) ...")
    tabla, cols = predio_ganadero.generar_cuadro13()
    ensamblador.guardar_pendiente(
        "cuadro13_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 13", fila_nacional=8, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro14_predio_ganadero() -> None:
    """Cuadro 14 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    con colmenas y número total de colmenas"). Ver `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 14 (predios ganaderos con colmenas - Ciclo 1) ...")
    tabla, cols = predio_ganadero.generar_cuadro14()
    ensamblador.guardar_pendiente(
        "cuadro14_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 14", fila_nacional=8, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro15_predio_ganadero() -> None:
    """Cuadro 15 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    por tipo de cobertura existente en el predio ganadero y área (ha)") -
    pregunta nueva de Ciclo 2, sin equivalente en Ciclo 1. Ver
    `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 15 (predios ganaderos por cobertura de tierra y área - Ciclo 2) ...")
    tabla, cols = predio_ganadero.generar_cuadro15()
    ensamblador.guardar_pendiente(
        "cuadro15_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 15", fila_nacional=11, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro16_predio_ganadero() -> None:
    """Cuadro 16 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    por área destinada a ganadería bovina o bufalina") - pregunta nueva de
    Ciclo 2. Ver `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 16 (predios ganaderos por área destinada a ganadería bovina/bufalina - Ciclo 2) ...")
    tabla, cols = predio_ganadero.generar_cuadro16()
    ensamblador.guardar_pendiente(
        "cuadro16_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 16", fila_nacional=11, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro17_predio_ganadero() -> None:
    """Cuadro 17 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    ubicados dentro de un área protegida") - pregunta nueva de Ciclo 2. Ver
    `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 17 (predios ganaderos en área protegida - Ciclo 2) ...")
    tabla, cols = predio_ganadero.generar_cuadro17()
    ensamblador.guardar_pendiente(
        "cuadro17_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 17", fila_nacional=12, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro18_predio_ganadero() -> None:
    """Cuadro 18 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    por razas puras o cruces") - pregunta nueva de Ciclo 2. Ver
    `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 18 (predios ganaderos por razas puras o cruces - Ciclo 2) ...")
    tabla, cols = predio_ganadero.generar_cuadro18()
    ensamblador.guardar_pendiente(
        "cuadro18_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 18", fila_nacional=11, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro19_predio_ganadero() -> None:
    """Cuadro 19 del libro "predio-ganadero" ("Cantidad de predios ganaderos
    por tipo de raza pura o cruce predominante") - pregunta nueva de Ciclo 2,
    52 razas puras + 28 cruces. Ver `cuadros/predio_ganadero.py`."""
    t0 = time.time()
    print("Cuadro 19 (predios ganaderos por raza predominante - Ciclo 2) ...")
    tabla, cols = predio_ganadero.generar_cuadro19()
    ensamblador.guardar_pendiente(
        "cuadro19_predio_ganadero", tabla, tipo="cuadro", hoja="Cuadro 19", fila_nacional=11, value_cols=cols
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


# --- Ciclo 2 (libro "predio-ganadero") ---
# Columna donde empieza el bloque "Segundo ciclo" en cada hoja (verificado
# contra la plantilla real con openpyxl). Cuadro 5/6/7/8/10/13/14 no tienen
# bloque Segundo ciclo (`canttrabaj`/`sistemaproductivo`/colmenas no existen
# en Ciclo 2, ver `cuadros/predio_ganadero.py`) - sin constante ni paso "_c2".
COLUMNA_SEGUNDO_CICLO_PG_C3 = 9    # I
COLUMNA_SEGUNDO_CICLO_PG_C4 = 12   # L
COLUMNA_SEGUNDO_CICLO_PG_C9 = 27   # AA
COLUMNA_SEGUNDO_CICLO_PG_C11 = 12  # L
COLUMNA_SEGUNDO_CICLO_PG_C12 = 48  # AV


def _paso_cuadro3_predio_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 3, bloque Segundo ciclo (predios ganaderos por inventario bovino/bufalino - Ciclo 2) ...")
    tabla, cols = predio_ganadero.generar_cuadro3(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro3_predio_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 3", fila_nacional=7, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_PG_C3,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro4_predio_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 4, bloque Segundo ciclo (predios ganaderos por orientación del hato - Ciclo 2) ...")
    tabla, cols = predio_ganadero.generar_cuadro4(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro4_predio_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 4", fila_nacional=9, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_PG_C4,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro9_predio_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 9, bloque Segundo ciclo (predios ganaderos por sexo/condición jurídica x orientación del hato - Ciclo 2) ...")
    tabla, cols = predio_ganadero.generar_cuadro9(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro9_predio_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 9", fila_nacional=9, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_PG_C9,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro11_predio_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 11, bloque Segundo ciclo (predios ganaderos por tenencia - Ciclo 2) ...")
    tabla, cols = predio_ganadero.generar_cuadro11(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro11_predio_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 11", fila_nacional=11, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_PG_C11,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


def _paso_cuadro12_predio_ganadero_c2() -> None:
    t0 = time.time()
    print("Cuadro 12, bloque Segundo ciclo (predios ganaderos por tenencia x orientación del hato - Ciclo 2) ...")
    tabla, cols = predio_ganadero.generar_cuadro12(ciclo="C2")
    ensamblador.guardar_pendiente(
        "cuadro12_predio_ganadero_c2", tabla, tipo="cuadro", hoja="Cuadro 12", fila_nacional=12, value_cols=cols,
        columna_inicio=COLUMNA_SEGUNDO_CICLO_PG_C12,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_predios_ganaderos']:,.1f}")


_PASO_FUNC = {
    "cuadro3": _paso_cuadro3,
    "cuadro6": _paso_cuadro6,
    "cuadro7": _paso_cuadro7,
    "cuadro8": _paso_cuadro8,
    "cuadro4": _paso_cuadro4,
    "cuadro3_c2": _paso_cuadro3_c2,
    "cuadro5": _paso_cuadro5,
    "cuadro7_c2": _paso_cuadro7_c2,
    "cuadro8_c2": _paso_cuadro8_c2,
    "cuadro1_ganadero": _paso_cuadro1_ganadero,
    "cuadro1_ganadero_c2": _paso_cuadro1_ganadero_c2,
    "cuadro1_ganadero_nuevos": _paso_cuadro1_ganadero_nuevos,
    "cuadro2_ganadero": _paso_cuadro2_ganadero,
    "cuadro3_ganadero": _paso_cuadro3_ganadero,
    "cuadro3_ganadero_c2": _paso_cuadro3_ganadero_c2,
    "cuadro6_ganadero": _paso_cuadro6_ganadero,
    "cuadro6_ganadero_c2": _paso_cuadro6_ganadero_c2,
    "cuadro8_ganadero": _paso_cuadro8_ganadero,
    "cuadro8_ganadero_c2": _paso_cuadro8_ganadero_c2,
    "cuadro9_ganadero": _paso_cuadro9_ganadero,
    "cuadro9_ganadero_c2": _paso_cuadro9_ganadero_c2,
    "cuadro10_ganadero": _paso_cuadro10_ganadero,
    "cuadro10_ganadero_c2": _paso_cuadro10_ganadero_c2,
    "cuadro11_ganadero": _paso_cuadro11_ganadero,
    "cuadro11_ganadero_c2": _paso_cuadro11_ganadero_c2,
    "cuadro12_ganadero": _paso_cuadro12_ganadero,
    "cuadro12_ganadero_c2": _paso_cuadro12_ganadero_c2,
    "cuadro13_ganadero": _paso_cuadro13_ganadero,
    "cuadro13_ganadero_c2": _paso_cuadro13_ganadero_c2,
    "cuadro14_ganadero": _paso_cuadro14_ganadero,
    "cuadro14_ganadero_c2": _paso_cuadro14_ganadero_c2,
    "cuadro15_ganadero": _paso_cuadro15_ganadero,
    "cuadro15_ganadero_c2": _paso_cuadro15_ganadero_c2,
    "cuadro16_ganadero": _paso_cuadro16_ganadero,
    "cuadro3_predio_ganadero": _paso_cuadro3_predio_ganadero,
    "cuadro3_predio_ganadero_c2": _paso_cuadro3_predio_ganadero_c2,
    "cuadro4_predio_ganadero": _paso_cuadro4_predio_ganadero,
    "cuadro4_predio_ganadero_c2": _paso_cuadro4_predio_ganadero_c2,
    "cuadro5_predio_ganadero": _paso_cuadro5_predio_ganadero,
    "cuadro6_predio_ganadero": _paso_cuadro6_predio_ganadero,
    "cuadro7_predio_ganadero": _paso_cuadro7_predio_ganadero,
    "cuadro8_predio_ganadero": _paso_cuadro8_predio_ganadero,
    "cuadro9_predio_ganadero": _paso_cuadro9_predio_ganadero,
    "cuadro9_predio_ganadero_c2": _paso_cuadro9_predio_ganadero_c2,
    "cuadro10_predio_ganadero": _paso_cuadro10_predio_ganadero,
    "cuadro11_predio_ganadero": _paso_cuadro11_predio_ganadero,
    "cuadro11_predio_ganadero_c2": _paso_cuadro11_predio_ganadero_c2,
    "cuadro12_predio_ganadero": _paso_cuadro12_predio_ganadero,
    "cuadro12_predio_ganadero_c2": _paso_cuadro12_predio_ganadero_c2,
    "cuadro13_predio_ganadero": _paso_cuadro13_predio_ganadero,
    "cuadro14_predio_ganadero": _paso_cuadro14_predio_ganadero,
    "cuadro15_predio_ganadero": _paso_cuadro15_predio_ganadero,
    "cuadro16_predio_ganadero": _paso_cuadro16_predio_ganadero,
    "cuadro17_predio_ganadero": _paso_cuadro17_predio_ganadero,
    "cuadro18_predio_ganadero": _paso_cuadro18_predio_ganadero,
    "cuadro19_predio_ganadero": _paso_cuadro19_predio_ganadero,
}


def ensamblar_libro(nombre_libro: str) -> None:
    ruta_salida, plantilla, pasos_libro = LIBROS[nombre_libro]
    ensamblador.ensamblar(plantilla, ruta_salida, pasos_libro)


def generar_todo() -> None:
    """Corre TODOS los pasos de cálculo y ensambla los 3 libros, en un solo
    proceso. Conveniente si la RAM alcanza; si no, preferir varios procesos
    `--solo <paso>` (uno por paso) seguidos de `--ensamblar <libro>` (uno por
    libro, una vez que todos sus pasos estén cacheados)."""
    for paso in _PASO_FUNC:
        _PASO_FUNC[paso]()
    for nombre_libro in LIBROS:
        ensamblar_libro(nombre_libro)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--solo", choices=list(_PASO_FUNC.keys()), help="calcular un único paso (cachea a disco, no toca el Excel)")
    grupo.add_argument("--ensamblar", choices=list(LIBROS.keys()), help="ensamblar un libro a partir de sus pasos ya cacheados (única vez que se abre/guarda el Excel)")
    args = parser.parse_args()

    if args.solo:
        _PASO_FUNC[args.solo]()
    elif args.ensamblar:
        ensamblar_libro(args.ensamblar)
    else:
        generar_todo()
