"""Orquestador: genera los cuadros ya calculables y los guarda en output/.

Cada cuadro se puede correr como paso independiente (`--solo <paso>`) para que
cada invocación sea un proceso nuevo de Python: la máquina donde corre esto
tiene poca RAM libre (8 GB) y encadenar varios cuadros pesados en un mismo
proceso ya causó un MemoryError una vez. Un proceso por cuadro garantiza que
el sistema operativo libera toda la memoria entre pasos.
"""
from __future__ import annotations

import argparse
import time

from . import config, excel_writer
from .cuadros import inventario

RUTA_SALIDA_INVENTARIO = config.OUTPUT_DIR / "Cuadros caracterización inventario Ciclos 1 y 2_2025_generado.xlsx"

# Columna donde empieza el bloque "Segundo ciclo" en cada hoja (verificado
# contra la plantilla real con openpyxl: Cuadro 3/7 tienen bloque Primer ciclo
# en E-Z y Segundo ciclo en AA-AV -por eso 27-; Cuadro 8 tiene E-S y T-AH
# -por eso 20-). Cuadro 4/5 no comparten hoja: Cuadro 5 es la hoja "Segundo
# ciclo" completa, por eso usa la columna E de siempre.
COLUMNA_SEGUNDO_CICLO_C3_C7 = 27  # AA
COLUMNA_SEGUNDO_CICLO_C8 = 20  # T

PASOS_INVENTARIO = [
    "cuadro3", "cuadro6", "cuadro7", "cuadro8", "cuadro4",
    "cuadro3_c2", "cuadro5", "cuadro7_c2", "cuadro8_c2",
]


def _origen_para(ruta_salida) -> object:
    """La primera vez se parte de la plantilla original; si el archivo de
    salida ya existe (de una corrida anterior/otro paso), se sigue acumulando
    sobre él."""
    return ruta_salida if ruta_salida.exists() else config.TEMPLATE_INVENTARIO


def _paso_cuadro3() -> None:
    ruta_salida = RUTA_SALIDA_INVENTARIO
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print("Cuadro 3 (bovinos, por sexo y edad) ...")
    tabla = inventario.generar("bovinos")
    excel_writer.escribir_cuadro(_origen_para(ruta_salida), ruta_salida, "Cuadro 3", 8, tabla, inventario.value_cols())
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_total']:,.1f}")


def _paso_cuadro6() -> None:
    ruta_salida = RUTA_SALIDA_INVENTARIO
    t0 = time.time()
    print("Cuadro 6 (bovinos, por sistema productivo) ...")
    tabla = inventario.generar_sistema_productivo()
    excel_writer.escribir_cuadro(
        _origen_para(ruta_salida), ruta_salida, "Cuadro 6", 7, tabla, inventario.value_cols_sistema_productivo()
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['sist_total']:,.1f}")


def _paso_cuadro7() -> None:
    ruta_salida = RUTA_SALIDA_INVENTARIO
    t0 = time.time()
    print("Cuadro 7 (bufalinos, por sexo y edad) ...")
    tabla = inventario.generar("bufalinos")
    excel_writer.escribir_cuadro(_origen_para(ruta_salida), ruta_salida, "Cuadro 7", 8, tabla, inventario.value_cols())
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_total']:,.1f}")


def _paso_cuadro8() -> None:
    ruta_salida = RUTA_SALIDA_INVENTARIO
    t0 = time.time()
    print("Cuadro 8 (otras especies pecuarias) ...")
    tabla = inventario.generar_otras_especies()
    excel_writer.escribir_cuadro(
        _origen_para(ruta_salida), ruta_salida, "Cuadro 8", 9, tabla, inventario.value_cols_otras_especies()
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional equinos: {tabla.iloc[0]['TOTAL_EQUINOS']:,.1f}")


def _paso_cuadro4() -> None:
    ruta_salida = RUTA_SALIDA_INVENTARIO
    t0 = time.time()
    print("Cuadro 4 (bovinos, por orientación de hato) ...")
    tabla, cols = inventario.generar_por_orientacion("bovinos", ciclo="C1")
    excel_writer.escribir_cuadro(_origen_para(ruta_salida), ruta_salida, "Cuadro 4", 8, tabla, cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional (bloque total): {tabla.iloc[0]['blk_total__total_total']:,.1f}")


# --- Ciclo 2 (base RUV cruda + factor recalculado en `calibracion_c2.py`) ---

def _paso_cuadro3_c2() -> None:
    ruta_salida = RUTA_SALIDA_INVENTARIO
    t0 = time.time()
    print("Cuadro 3, bloque Segundo ciclo (bovinos, por sexo y edad) ...")
    tabla = inventario.generar("bovinos", ciclo="C2")
    excel_writer.escribir_cuadro(
        _origen_para(ruta_salida), ruta_salida, "Cuadro 3", 8, tabla, inventario.value_cols(),
        columna_inicio=COLUMNA_SEGUNDO_CICLO_C3_C7,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_total']:,.1f}")


def _paso_cuadro7_c2() -> None:
    ruta_salida = RUTA_SALIDA_INVENTARIO
    t0 = time.time()
    print("Cuadro 7, bloque Segundo ciclo (bufalinos, por sexo y edad) ...")
    tabla = inventario.generar("bufalinos", ciclo="C2")
    excel_writer.escribir_cuadro(
        _origen_para(ruta_salida), ruta_salida, "Cuadro 7", 8, tabla, inventario.value_cols(),
        columna_inicio=COLUMNA_SEGUNDO_CICLO_C3_C7,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional: {tabla.iloc[0]['total_total']:,.1f}")


def _paso_cuadro8_c2() -> None:
    ruta_salida = RUTA_SALIDA_INVENTARIO
    t0 = time.time()
    print("Cuadro 8, bloque Segundo ciclo (otras especies pecuarias) ...")
    tabla = inventario.generar_otras_especies(ciclo="C2")
    excel_writer.escribir_cuadro(
        _origen_para(ruta_salida), ruta_salida, "Cuadro 8", 9, tabla, inventario.value_cols_otras_especies(),
        columna_inicio=COLUMNA_SEGUNDO_CICLO_C8,
    )
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional equinos: {tabla.iloc[0]['TOTAL_EQUINOS']:,.1f}")


def _paso_cuadro5() -> None:
    ruta_salida = RUTA_SALIDA_INVENTARIO
    t0 = time.time()
    print("Cuadro 5 (bovinos, por orientación de hato, Segundo ciclo) ...")
    tabla, cols = inventario.generar_por_orientacion("bovinos", ciclo="C2")
    excel_writer.escribir_cuadro(_origen_para(ruta_salida), ruta_salida, "Cuadro 5", 8, tabla, cols)
    print(f"  listo ({time.time()-t0:.1f}s). Filas: {len(tabla)}. Total nacional (bloque total): {tabla.iloc[0]['blk_total__total_total']:,.1f}")


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
}


def generar_libro_inventario(pasos: list[str] | None = None) -> None:
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for paso in pasos or PASOS_INVENTARIO:
        _PASO_FUNC[paso]()
    print(f"Guardado: {RUTA_SALIDA_INVENTARIO}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo", choices=list(_PASO_FUNC.keys()), help="correr un único paso (un proceso por paso)")
    args = parser.parse_args()
    generar_libro_inventario([args.solo] if args.solo else None)
