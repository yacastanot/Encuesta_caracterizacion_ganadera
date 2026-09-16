"""Escritura de resultados dentro de las plantillas Excel originales.

Estrategia para que el formato quede EXACTAMENTE igual al de Adriana: nunca se
construye un archivo desde cero. Se abre la plantilla real (título,
encabezados multinivel, merges, notas al pie ya existen ahí) y solo se
inserta/llena el bloque de filas de datos (nacional + departamentos +
municipios), clonando el estilo de celda que ya trae la fila de ejemplo
"Total Nacional" / "Total por departamento" de cada hoja.

IDEMPOTENCIA: como cada libro se arma cuadro por cuadro (a veces en procesos
Python separados, por límites de memoria de la máquina), es normal tener que
re-escribir la MISMA hoja más de una vez (ej. para corregir un bug). Por eso
los estilos de la fila "Total Nacional", de la fila de departamento, y el
contenido/estilo de las notas al pie SIEMPRE se leen de la plantilla PRÍSTINA
(`ruta_plantilla`), nunca de lo que ya haya en `ruta_salida` - y antes de
escribir, se borra por completo cualquier fila que una corrida anterior haya
dejado en esa hoja (desde `fila_nacional` en adelante). Así, escribir un
cuadro por segunda vez da exactamente el mismo resultado que la primera vez,
en vez de ir acumulando filas huérfanas.
"""
from __future__ import annotations

from copy import copy

import openpyxl
import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet

from . import agregador

COL_A_COD_DEPARTAMENTO = 1
COL_B_DEPARTAMENTO = 2
COL_C_COD_MUNICIPIO = 3
COL_D_MUNICIPIO = 4
PRIMERA_COLUMNA_DATOS = 5  # columna E


def _clonar_estilo_celda(origen, destino) -> None:
    destino.font = copy(origen.font)
    destino.border = copy(origen.border)
    destino.fill = copy(origen.fill)
    destino.number_format = origen.number_format
    destino.alignment = copy(origen.alignment)
    destino.protection = copy(origen.protection)


def _clonar_estilo_fila(ws_origen: Worksheet, fila_origen: int, ws_destino: Worksheet, fila_destino: int, n_columnas: int) -> None:
    for c in range(1, n_columnas + 1):
        _clonar_estilo_celda(ws_origen.cell(row=fila_origen, column=c), ws_destino.cell(row=fila_destino, column=c))


def _buscar_fila_notas(ws: Worksheet, fila_desde: int, limite: int = 20000) -> int | None:
    """Busca la primera fila con contenido real en o después de `fila_desde`
    en la hoja PRÍSTINA (nunca en una hoja que ya hayamos escrito nosotros)."""
    for r in range(fila_desde, min(ws.max_row, limite) + 1):
        if any(ws.cell(row=r, column=c).value not in (None, "") for c in range(1, ws.max_column + 1)):
            return r
    return None


def _capturar_bloque_notas(ws_pristina: Worksheet, fila_desde: int, n_columnas: int):
    """Devuelve la lista de filas de notas al pie de la plantilla PRÍSTINA
    (valores + estilos), como bloque contiguo a partir de la primera fila con
    contenido encontrada desde `fila_desde`. None si no hay ninguna."""
    fila_inicio = _buscar_fila_notas(ws_pristina, fila_desde)
    if fila_inicio is None:
        return None
    filas = []
    r = fila_inicio
    vacio_consecutivo = 0
    while r <= ws_pristina.max_row and vacio_consecutivo < 3:
        vals = [ws_pristina.cell(row=r, column=c).value for c in range(1, max(n_columnas, ws_pristina.max_column) + 1)]
        if any(v not in (None, "") for v in vals):
            filas.append(r)
            vacio_consecutivo = 0
        else:
            vacio_consecutivo += 1
        r += 1
    return filas


def escribir_cuadro(
    ruta_plantilla,
    ruta_salida,
    hoja: str,
    fila_nacional: int,
    tabla: pd.DataFrame,
    value_cols: list[str],
    formato_numero: str = "#,##0",
    columna_inicio: int = PRIMERA_COLUMNA_DATOS,
) -> None:
    """Inserta `tabla` (salida de `agregador.generar_cuadro`) dentro de `hoja`,
    a partir de la columna `columna_inicio` (por defecto E, la del bloque
    "Primer ciclo"; usar la columna real del bloque "Segundo ciclo" - ej. AA=27
    en Cuadro 3/7, T=20 en Cuadro 8 - para llenar ese otro bloque de la MISMA
    hoja sin tocar el ya escrito).

    `fila_nacional`: número de fila donde va la fila "Total Nacional" (según
    la plantilla PRÍSTINA original - exista ya ese rótulo ahí o no).

    Si `columna_inicio` es la del "Primer ciclo" (el valor por defecto), la
    hoja se reconstruye desde cero: se borra todo lo que haya desde
    `fila_nacional` en adelante y se vuelve a armar el esqueleto (filas +
    notas al pie), así que es segura de llamar más de una vez sobre el mismo
    `ruta_salida` para ESE bloque. Si es la de un bloque adicional (ej.
    "Segundo ciclo") sobre una hoja que ya tiene su esqueleto escrito, NO se
    borran filas: solo se clona el estilo y se llenan los valores de esas
    columnas nuevas, dejando intacto lo que ya había.
    """
    origen = ruta_salida if ruta_salida.exists() else ruta_plantilla
    wb = openpyxl.load_workbook(origen)
    ws = wb[hoja]
    n_columnas = columna_inicio + len(value_cols) - 1

    wb_pristina = openpyxl.load_workbook(ruta_plantilla)
    ws_pristina = wb_pristina[hoja]

    nacional = tabla[tabla["NIVEL"] == agregador.NIVEL_NACIONAL].reset_index(drop=True)
    depmun = tabla[tabla["NIVEL"] != agregador.NIVEL_NACIONAL].reset_index(drop=True)
    filas_nacional_usadas = max(len(nacional), 1)
    fila_dept_inicio = fila_nacional + filas_nacional_usadas

    bloque_adicional = columna_inicio != PRIMERA_COLUMNA_DATOS and ws.max_row >= fila_dept_inicio

    if not bloque_adicional:
        filas_notas_pristina = _capturar_bloque_notas(ws_pristina, fila_nacional + 2, n_columnas)

        # --- Limpieza idempotente: borrar cualquier resto de una corrida anterior ---
        if ws.max_row >= fila_nacional:
            ws.delete_rows(fila_nacional, amount=ws.max_row - fila_nacional + 1)

        # --- Bloque nacional (puede ser 1 fila, o varias si el cuadro desagrega
        # por una categoría extra a nivel nacional). Estilo SIEMPRE desde la
        # plantilla prístina, fila `fila_nacional`. ---
        for i in range(filas_nacional_usadas):
            f = fila_nacional + i
            _clonar_estilo_fila(ws_pristina, fila_nacional, ws, f, n_columnas)
            ws.cell(row=f, column=COL_A_COD_DEPARTAMENTO, value="")
            ws.cell(row=f, column=COL_B_DEPARTAMENTO, value="Total Nacional")

        # --- Notas al pie: se vuelven a pegar tal cual estaban en la plantilla
        # prístina, inmediatamente después de donde va a terminar el bloque de
        # datos (más abajo se inserta el espacio que necesitan los datos). ---
        n_necesarias = len(depmun)
        if filas_notas_pristina:
            for offset, r_pristina in enumerate(filas_notas_pristina):
                f_destino = fila_dept_inicio + offset
                for c in range(1, max(n_columnas, ws_pristina.max_column) + 1):
                    src = ws_pristina.cell(row=r_pristina, column=c)
                    dst = ws.cell(row=f_destino, column=c, value=src.value)
                    _clonar_estilo_celda(src, dst)
            ws.insert_rows(fila_dept_inicio, amount=n_necesarias)

        # --- Bloque departamentos + municipios. Estilo SIEMPRE desde la
        # plantilla prístina, fila `fila_nacional + 1` (rótulo original "Total
        # por departamento" o la primera fila vacía si ese placeholder no
        # existía). ---
        estilo_depto_origen = fila_nacional + 1
        for i, row in depmun.iterrows():
            f = fila_dept_inicio + i
            _clonar_estilo_fila(ws_pristina, estilo_depto_origen, ws, f, n_columnas)
            ws.cell(row=f, column=COL_A_COD_DEPARTAMENTO, value=row["COD_DEPARTAMENTO"])
            ws.cell(row=f, column=COL_B_DEPARTAMENTO, value=row["DEPARTAMENTO"])
            if row["NIVEL"] == agregador.NIVEL_MUNICIPIO:
                ws.cell(row=f, column=COL_C_COD_MUNICIPIO, value=row["CODIGO_MUNICIPIO"])
                ws.cell(row=f, column=COL_D_MUNICIPIO, value=row["MUNICIPIO"])
            else:
                ws.cell(row=f, column=COL_C_COD_MUNICIPIO, value=None)
                ws.cell(row=f, column=COL_D_MUNICIPIO, value=None)
    else:
        # Bloque adicional (ej. "Segundo ciclo") sobre una hoja cuyo esqueleto
        # (filas + notas) ya escribió el bloque "Primer ciclo": solo se clona
        # el estilo de ESTAS columnas nuevas, sin borrar/mover nada existente.
        for i in range(filas_nacional_usadas):
            f = fila_nacional + i
            for c in range(columna_inicio, n_columnas + 1):
                _clonar_estilo_celda(ws_pristina.cell(row=fila_nacional, column=c), ws.cell(row=f, column=c))
        for i in range(len(depmun)):
            f = fila_dept_inicio + i
            for c in range(columna_inicio, n_columnas + 1):
                _clonar_estilo_celda(ws_pristina.cell(row=fila_nacional + 1, column=c), ws.cell(row=f, column=c))

    for i, row in nacional.iterrows():
        f = fila_nacional + i
        for j, col in enumerate(value_cols):
            celda = ws.cell(row=f, column=columna_inicio + j, value=float(row[col]))
            celda.number_format = formato_numero

    for i, row in depmun.iterrows():
        f = fila_dept_inicio + i
        for j, col in enumerate(value_cols):
            celda = ws.cell(row=f, column=columna_inicio + j, value=float(row[col]))
            celda.number_format = formato_numero

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ruta_salida)
