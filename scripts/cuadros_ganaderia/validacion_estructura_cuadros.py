"""Valida, sobre el archivo Excel REAL ya escrito (no la tabla en memoria),
que cada cuadro cumple:

 1. Vertical: cada departamento = suma exacta de sus municipios; nacional =
    suma exacta de los departamentos.
 2. Horizontal: cada relación total/componentes declarada en `columnas_totales`
    (la misma que recibió `agregador.generar_cuadro` al construir el cuadro)
    se cumple en TODAS las filas (nacional, departamentos, municipios).
 3. Universo completo: exactamente los municipios/departamentos de
    `catalogo_territorial`, sin duplicados ni faltantes.

Por qué validar el Excel y no la tabla en memoria: `agregador.generar_cuadro`
ya GARANTIZA 1 y 2 por construcción (redondeo único al nivel más fino +
derivación de columnas "total" a partir de sus componentes YA redondeados -
ver su docstring) - validar la tabla en memoria sería tautológico, siempre
pasaría. Lo que SÍ puede fallar es la escritura a Excel (`excel_writer.py`):
ya se encontraron 2 bugs reales ahí, ninguno visible en la tabla en memoria -
celdas combinadas fantasma que truncaban Cuadro 2 a 16 de 67 filas; notas al
pie mal ubicadas que se perdían por completo en Cuadro 8/9/10. Esta
validación lee el archivo final, la única forma de detectar ese tipo de bug.

Alcance actual: cuadros con estructura "lista de columnas + relaciones
total/componentes" (la mayoría). NO cubre Cuadro 4/5 (inventario, bloques
anidados por orientación de hato - estructura distinta) ni Cuadro 2 (lista
plana de municipios excluidos, sin relaciones numéricas que validar aquí -
ver `validacion_totales_cuadro1_c1.py` y las validaciones de
`config.MUNICIPIOS_EXCLUIDOS_C1` para eso).

Uso:
    python -m scripts.cuadros_ganaderia.validacion_estructura_cuadros
Guarda `Bases Calibradas/validacion_estructura_cuadros.csv` (una fila por
problema encontrado; vacío = todo correcto en todos los cuadros).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
import pandas as pd

from . import catalogo_territorial, config, main as m
from .cuadros import comun, ganadero, ganadero_historico, inventario, predio_ganadero


@dataclass
class DefinicionCuadro:
    nombre: str
    ruta_libro: Path
    hoja: str
    fila_nacional: int
    value_cols: list[str]
    columnas_totales: dict[str, list[str]] = field(default_factory=dict)
    columna_inicio: int = 5


def _definiciones() -> list[DefinicionCuadro]:
    """Un `DefinicionCuadro` por cuadro ya construido (con estructura
    columnas+totales) - misma `value_cols`/`columnas_totales` con la que se
    llamó a `agregador.generar_cuadro` en `cuadros/*.py`, para no duplicar la
    lógica de negocio acá, solo la geometría de la hoja."""
    inv = m.RUTA_SALIDA_INVENTARIO
    gan = m.RUTA_SALIDA_GANADERO
    pg = m.RUTA_SALIDA_PREDIO_GANADERO

    especies_cols = []
    for especie in inventario.ESPECIES_ORDEN:
        especies_cols += [f"TOTAL_{especie}", f"{especie}_MACHO", f"{especie}_HEMBRA"]
    columnas_totales_especies = {f"TOTAL_{e}": [f"{e}_MACHO", f"{e}_HEMBRA"] for e in inventario.ESPECIES_ORDEN}

    # Misma geometría con la que `predio_ganadero.generar_cuadro6` construyó
    # el cuadro (4 bloques de sistema productivo x Total/natural/h/m/jurídica).
    value_cols_cuadro6_pg = ["total_predios_ganaderos"]
    columnas_totales_cuadro6_pg: dict[str, list[str]] = {}
    for sistema in predio_ganadero.SISTEMAS_PRODUCTIVOS_ORDEN:
        slug = predio_ganadero._SISTEMA_SLUG[sistema]
        col_h, col_m, col_j = f"{slug}_h", f"{slug}_m", f"{slug}_j"
        col_natural, col_total = f"{slug}_natural", f"{slug}_total"
        value_cols_cuadro6_pg += [col_total, col_natural, col_h, col_m, col_j]
        columnas_totales_cuadro6_pg[col_natural] = [col_h, col_m]
        # OJO - "{sistema}_total = {sistema}_natural + {sistema}_j" NO se
        # declara acá (a diferencia de "{sistema}_natural = h + m", que sí se
        # mantiene): el sistema que absorbe el residuo del margen entre
        # sistemas (ver "total_predios_ganaderos" más abajo y docstring de
        # `generar_cuadro6` en `cuadros/predio_ganadero.py`) varía fila a
        # fila (no siempre el mismo, para evitar negativos) y queda con su
        # propio "_total" ajustado sin que "_natural + _j" lo reproduzca
        # exacto - mismo trade-off aceptado en "Doble propósito" de Cuadro
        # 4/5 del libro inventario.
    # "total_predios_ganaderos" = suma de los 4 "{sistema}_total" (margen de
    # sistema productivo, exhaustivo) - a pedido del usuario 2026-10-02, ver
    # `agregador.forzar_suma_exacta` en `cuadros/predio_ganadero.py`.
    columnas_totales_cuadro6_pg["total_predios_ganaderos"] = [
        f"{predio_ganadero._SISTEMA_SLUG[s]}_total" for s in predio_ganadero.SISTEMAS_PRODUCTIVOS_ORDEN
    ]

    # Misma geometría con la que `predio_ganadero.generar_cuadro7` construyó
    # el cuadro (bloque "Total" + 6 bloques de orientación, cada uno x 4
    # sistemas productivos).
    value_cols_cuadro7_pg = ["total_predios_ganaderos"] + [
        f"total_{predio_ganadero._SISTEMA_SLUG[s]}" for s in predio_ganadero.SISTEMAS_PRODUCTIVOS_ORDEN
    ]
    # "total_predios_ganaderos" tiene 2 relaciones de suma (margen de sistema
    # Y margen de orientación - ambas exactas por construcción, ver
    # `cuadros/predio_ganadero.generar_cuadro7`) - un `dict` solo admite una
    # relación por columna, así que la 2da (margen de orientación) se declara
    # en un `DefinicionCuadro` aparte más abajo
    # ("predio_ganadero_cuadro7_margen_orientacion").
    columnas_totales_cuadro7_pg: dict[str, list[str]] = {
        "total_predios_ganaderos": [f"total_{predio_ganadero._SISTEMA_SLUG[s]}" for s in predio_ganadero.SISTEMAS_PRODUCTIVOS_ORDEN],
    }
    for orientacion in predio_ganadero.ORIENTACIONES_ORDEN:
        oslug = predio_ganadero._ORIENTACION_SLUG[orientacion]
        value_cols_cuadro7_pg.append(f"{oslug}_total")
        value_cols_cuadro7_pg += [f"{oslug}_{predio_ganadero._SISTEMA_SLUG[s]}" for s in predio_ganadero.SISTEMAS_PRODUCTIVOS_ORDEN]
        columnas_totales_cuadro7_pg[f"{oslug}_total"] = [f"{oslug}_{predio_ganadero._SISTEMA_SLUG[s]}" for s in predio_ganadero.SISTEMAS_PRODUCTIVOS_ORDEN]
    columnas_totales_cuadro7_margen_orientacion = {
        "total_predios_ganaderos": [f"{predio_ganadero._ORIENTACION_SLUG[o]}_total" for o in predio_ganadero.ORIENTACIONES_ORDEN],
    }

    # Misma geometría con la que `predio_ganadero.generar_cuadro8` construyó
    # el cuadro (bloque "Total" + 3 bloques de sexo/persona jurídica, cada
    # uno x 4 sistemas productivos).
    value_cols_cuadro8_pg = ["total_predios_ganaderos"] + [
        f"total_{predio_ganadero._SISTEMA_SLUG[s]}" for s in predio_ganadero.SISTEMAS_PRODUCTIVOS_ORDEN
    ]
    # 2 márgenes para "total_predios_ganaderos" (sistema Y género) - mismo
    # motivo que Cuadro 7, la 2da relación (género) va en un
    # `DefinicionCuadro` aparte ("predio_ganadero_cuadro8_margen_genero").
    columnas_totales_cuadro8_pg: dict[str, list[str]] = {
        "total_predios_ganaderos": [f"total_{predio_ganadero._SISTEMA_SLUG[s]}" for s in predio_ganadero.SISTEMAS_PRODUCTIVOS_ORDEN],
    }
    for genero in predio_ganadero._GENERO_BLOQUE_ORDEN:
        gslug = predio_ganadero._GENERO_BLOQUE_SLUG[genero]
        value_cols_cuadro8_pg.append(f"{gslug}_total")
        value_cols_cuadro8_pg += [f"{gslug}_{predio_ganadero._SISTEMA_SLUG[s]}" for s in predio_ganadero.SISTEMAS_PRODUCTIVOS_ORDEN]
        columnas_totales_cuadro8_pg[f"{gslug}_total"] = [f"{gslug}_{predio_ganadero._SISTEMA_SLUG[s]}" for s in predio_ganadero.SISTEMAS_PRODUCTIVOS_ORDEN]
    columnas_totales_cuadro8_margen_genero = {
        "total_predios_ganaderos": [f"{predio_ganadero._GENERO_BLOQUE_SLUG[g]}_total" for g in predio_ganadero._GENERO_BLOQUE_ORDEN],
    }

    # Misma geometría con la que `predio_ganadero.generar_cuadro9` construyó
    # el cuadro (columna "Total" general + 3 bloques de sexo/persona
    # jurídica, en el orden Mujer/Hombre/jurídica, cada uno x 6 orientaciones).
    value_cols_cuadro9_pg = ["total_predios_ganaderos"]
    columnas_totales_cuadro9_pg: dict[str, list[str]] = {
        "total_predios_ganaderos": [f"{predio_ganadero._GENERO_BLOQUE_SLUG[g]}_total" for g in predio_ganadero._GENERO_ORDEN_CUADRO9],
    }
    for genero in predio_ganadero._GENERO_ORDEN_CUADRO9:
        gslug = predio_ganadero._GENERO_BLOQUE_SLUG[genero]
        value_cols_cuadro9_pg.append(f"{gslug}_total")
        value_cols_cuadro9_pg += [f"{gslug}_{predio_ganadero._ORIENTACION_SLUG[o]}" for o in predio_ganadero.ORIENTACIONES_ORDEN]
        columnas_totales_cuadro9_pg[f"{gslug}_total"] = [f"{gslug}_{predio_ganadero._ORIENTACION_SLUG[o]}" for o in predio_ganadero.ORIENTACIONES_ORDEN]

    # Misma geometría con la que `predio_ganadero.generar_cuadro10` construyó
    # el cuadro (columna "Total" general + 6 bloques de tenencia, cada uno x
    # 4 sistemas productivos).
    value_cols_cuadro10_pg = ["total_predios_ganaderos"]
    columnas_totales_cuadro10_pg: dict[str, list[str]] = {
        "total_predios_ganaderos": [f"{predio_ganadero._TENENCIA_SLUG[t]}_total" for t in predio_ganadero.TENENCIA_ORDEN],
    }
    for tenencia in predio_ganadero.TENENCIA_ORDEN:
        tslug = predio_ganadero._TENENCIA_SLUG[tenencia]
        value_cols_cuadro10_pg.append(f"{tslug}_total")
        value_cols_cuadro10_pg += [f"{tslug}_{predio_ganadero._SISTEMA_SLUG[s]}" for s in predio_ganadero.SISTEMAS_PRODUCTIVOS_ORDEN]
        columnas_totales_cuadro10_pg[f"{tslug}_total"] = [f"{tslug}_{predio_ganadero._SISTEMA_SLUG[s]}" for s in predio_ganadero.SISTEMAS_PRODUCTIVOS_ORDEN]

    # Misma geometría con la que `predio_ganadero.generar_cuadro11` construyó
    # el cuadro (Total + 6 columnas de tenencia, sin cruce).
    value_cols_cuadro11_pg = ["total_predios_ganaderos"] + [
        predio_ganadero._TENENCIA_SLUG[t] for t in predio_ganadero.TENENCIA_ORDEN
    ]
    columnas_totales_cuadro11_pg = {
        "total_predios_ganaderos": [predio_ganadero._TENENCIA_SLUG[t] for t in predio_ganadero.TENENCIA_ORDEN],
    }

    # Misma geometría con la que `predio_ganadero.generar_cuadro12` construyó
    # el cuadro (columna "Total" general + 6 bloques de tenencia, cada uno x
    # 6 orientaciones).
    value_cols_cuadro12_pg = ["total_predios_ganaderos"]
    columnas_totales_cuadro12_pg: dict[str, list[str]] = {
        "total_predios_ganaderos": [f"{predio_ganadero._TENENCIA_SLUG[t]}_total" for t in predio_ganadero.TENENCIA_ORDEN],
    }
    for tenencia in predio_ganadero.TENENCIA_ORDEN:
        tslug = predio_ganadero._TENENCIA_SLUG[tenencia]
        value_cols_cuadro12_pg.append(f"{tslug}_total")
        value_cols_cuadro12_pg += [f"{tslug}_{predio_ganadero._ORIENTACION_SLUG[o]}" for o in predio_ganadero.ORIENTACIONES_ORDEN]
        columnas_totales_cuadro12_pg[f"{tslug}_total"] = [f"{tslug}_{predio_ganadero._ORIENTACION_SLUG[o]}" for o in predio_ganadero.ORIENTACIONES_ORDEN]

    # Misma geometría con la que `predio_ganadero.generar_cuadro13` construyó
    # el cuadro (Total + 8 rangos de `menores18`, sin cruce).
    value_cols_cuadro13_pg = [
        "total_predios_ganaderos", "cero", "de_1_a_5", "de_6_a_10", "de_11_a_15",
        "de_16_a_20", "de_21_a_50", "mas_50", "no_sabe",
    ]
    columnas_totales_cuadro13_pg = {"total_predios_ganaderos": value_cols_cuadro13_pg[1:]}

    # Misma geometría con la que `predio_ganadero.generar_cuadro14` construyó
    # el cuadro (Total + con colmenas + 6 rangos de cantidad de colmenas).
    value_cols_cuadro14_pg = [
        "total_predios_ganaderos", "con_colmenas", "cero", "de_1_a_10",
        "de_11_a_30", "de_31_a_50", "mas_50", "no_sabe",
    ]
    # "con_colmenas" NO participa (marcador aparte, no categoría de esta
    # partición - ver docstring de `cuadros/predio_ganadero.generar_cuadro14`).
    columnas_totales_cuadro14_pg = {"total_predios_ganaderos": value_cols_cuadro14_pg[2:]}

    return [
        DefinicionCuadro(
            "inventario_cuadro1", inv, "Cuadro 1", 7,
            ["total_predios", "total_ganaderos", "total_predios_ganaderos"],
        ),
        DefinicionCuadro(
            "inventario_cuadro1_c2", inv, "Cuadro 1", 7,
            ["total_predios", "total_ganaderos", "total_predios_ganaderos"],
            columna_inicio=8,
        ),
        DefinicionCuadro(
            # Bloque "nuevos" (columnas K-N, `comun.generar_cuadro1_nuevos`) -
            # idéntico en los 3 libros (un solo pendiente), ver `main.py`.
            "inventario_cuadro1_nuevos", inv, "Cuadro 1", 7,
            ["predios_nuevos", "ganaderos_nuevos", "predios_ganaderos_nuevos", "animales_predios_nuevos"],
            columna_inicio=11,
        ),
        DefinicionCuadro(
            "inventario_cuadro3_bovinos", inv, "Cuadro 3", 8,
            inventario.value_cols(), inventario._columnas_totales(),
        ),
        DefinicionCuadro(
            # "blk_total__*" se reutiliza exacto de Cuadro 3 (ver docstring
            # de `generar_por_orientacion`) - no se declara acá, solo el
            # detalle interno de cada bloque de orientación.
            "inventario_cuadro4_orientacion", inv, "Cuadro 4", 8,
            inventario.value_cols_por_orientacion(), inventario.columnas_totales_por_orientacion(),
        ),
        DefinicionCuadro(
            "inventario_cuadro5_orientacion", inv, "Cuadro 5", 8,
            inventario.value_cols_por_orientacion(), inventario.columnas_totales_por_orientacion(),
        ),
        DefinicionCuadro(
            # "sist_total" se reutiliza exacto de Cuadro 3 (no se deriva de
            # sumar los 4 sistemas) - PERO la suma de los 4 sí debe coincidir
            # exacto con "sist_total" (a pedido del usuario 2026-09-25): el
            # residuo de redondeo se absorbe en "Pastoreo mejorado", ver
            # docstring de `generar_sistema_productivo`.
            "inventario_cuadro6_sistema_productivo", inv, "Cuadro 6", 7,
            inventario.value_cols_sistema_productivo(),
            {"sist_total": [f"sist_{inventario._SISTEMA_SLUG[s]}" for s in inventario.SISTEMA_PRODUCTIVO_ORDEN]},
        ),
        DefinicionCuadro(
            "inventario_cuadro7_bufalinos", inv, "Cuadro 7", 8,
            inventario.value_cols(), inventario._columnas_totales(),
        ),
        DefinicionCuadro(
            "inventario_cuadro8_otras_especies", inv, "Cuadro 8", 9,
            especies_cols, columnas_totales_especies,
        ),
        DefinicionCuadro(
            # Bloque "Segundo ciclo" (Fase 7, 2026-09-24) - misma geometría
            # que "inventario_cuadro3_bovinos", columna de inicio distinta
            # (verificada contra la plantilla real, ver `main.py`).
            "inventario_cuadro3_bovinos_c2", inv, "Cuadro 3", 8,
            inventario.value_cols(), inventario._columnas_totales(),
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_C3_C7,
        ),
        DefinicionCuadro(
            "inventario_cuadro7_bufalinos_c2", inv, "Cuadro 7", 8,
            inventario.value_cols(), inventario._columnas_totales(),
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_C3_C7,
        ),
        DefinicionCuadro(
            "inventario_cuadro8_otras_especies_c2", inv, "Cuadro 8", 9,
            especies_cols, columnas_totales_especies,
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_C8,
        ),
        DefinicionCuadro(
            "ganadero_cuadro1", gan, "Cuadro 1", 7,
            ["total_predios", "total_ganaderos", "total_predios_ganaderos"],
        ),
        DefinicionCuadro(
            "ganadero_cuadro1_c2", gan, "Cuadro 1", 7,
            ["total_predios", "total_ganaderos", "total_predios_ganaderos"],
            columna_inicio=8,
        ),
        DefinicionCuadro(
            "ganadero_cuadro1_nuevos", gan, "Cuadro 1", 7,
            ["predios_nuevos", "ganaderos_nuevos", "predios_ganaderos_nuevos", "animales_predios_nuevos"],
            columna_inicio=11,
        ),
        DefinicionCuadro(
            "predio_ganadero_cuadro1", pg, "Cuadro 1", 7,
            ["total_predios", "total_ganaderos", "total_predios_ganaderos"],
        ),
        DefinicionCuadro(
            # Bloque "Segundo ciclo" (columnas H-J, ver `cuadros/comun.py`).
            "predio_ganadero_cuadro1_c2", pg, "Cuadro 1", 7,
            ["total_predios", "total_ganaderos", "total_predios_ganaderos"],
            columna_inicio=8,
        ),
        DefinicionCuadro(
            "predio_ganadero_cuadro1_nuevos", pg, "Cuadro 1", 7,
            ["predios_nuevos", "ganaderos_nuevos", "predios_ganaderos_nuevos", "animales_predios_nuevos"],
            columna_inicio=11,
        ),
        DefinicionCuadro(
            # Sin `columnas_totales`: "total_predios_ganaderos" se redondea
            # independiente (para coincidir exacto con Cuadro 1 - ver
            # "total_predios_ganaderos" se redondea independiente (coincide
            # exacto con Cuadro 1), pero la suma de las 3 categorías SÍ debe
            # coincidir con él (ajustado con `agregador.forzar_suma_exacta`
            # en `cuadros/predio_ganadero.py`, a pedido del usuario 2026-10-02).
            "predio_ganadero_cuadro3", pg, "Cuadro 3", 7,
            ["total_predios_ganaderos", "con_bovinos", "con_bufalinos", "con_ambos"],
            {"total_predios_ganaderos": ["con_bovinos", "con_bufalinos", "con_ambos"]},
        ),
        DefinicionCuadro(
            # Bloque "Segundo ciclo" (Fase 7, 2026-09-24) - mismo criterio sin
            # `columnas_totales` que el bloque C1.
            "predio_ganadero_cuadro3_c2", pg, "Cuadro 3", 7,
            ["total_predios_ganaderos", "con_bovinos", "con_bufalinos", "con_ambos"],
            {"total_predios_ganaderos": ["con_bovinos", "con_bufalinos", "con_ambos"]},
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_PG_C3,
        ),
        DefinicionCuadro(
            # Mismo criterio que Cuadro 3 (ver arriba).
            "predio_ganadero_cuadro4", pg, "Cuadro 4", 9,
            ["total_predios_ganaderos"] + [predio_ganadero._ORIENTACION_SLUG[o] for o in predio_ganadero.ORIENTACIONES_ORDEN],
            {"total_predios_ganaderos": [predio_ganadero._ORIENTACION_SLUG[o] for o in predio_ganadero.ORIENTACIONES_ORDEN]},
        ),
        DefinicionCuadro(
            "predio_ganadero_cuadro4_c2", pg, "Cuadro 4", 9,
            ["total_predios_ganaderos"] + [predio_ganadero._ORIENTACION_SLUG[o] for o in predio_ganadero.ORIENTACIONES_ORDEN],
            {"total_predios_ganaderos": [predio_ganadero._ORIENTACION_SLUG[o] for o in predio_ganadero.ORIENTACIONES_ORDEN]},
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_PG_C4,
        ),
        DefinicionCuadro(
            # Mismo criterio que Cuadro 3/4 (ver `cuadros/predio_ganadero.py`).
            "predio_ganadero_cuadro5", pg, "Cuadro 5", 7,
            ["total_predios_ganaderos"] + [c for c, _ in predio_ganadero.CLASES_CUADRO5],
            {"total_predios_ganaderos": [c for c, _ in predio_ganadero.CLASES_CUADRO5]},
        ),
        DefinicionCuadro(
            # "total_predios_ganaderos" = suma de los 4 "{sistema}_total"
            # (margen de sistema productivo) - resto de `columnas_totales`
            # ya declaraba la consistencia interna de cada bloque.
            "predio_ganadero_cuadro6", pg, "Cuadro 6", 8,
            value_cols_cuadro6_pg, columnas_totales_cuadro6_pg,
        ),
        DefinicionCuadro(
            # Margen de sistema productivo + consistencia interna de cada
            # bloque de orientación - el margen de orientación va aparte
            # (ver "predio_ganadero_cuadro7_margen_orientacion" abajo).
            "predio_ganadero_cuadro7", pg, "Cuadro 7", 9,
            value_cols_cuadro7_pg, columnas_totales_cuadro7_pg,
        ),
        DefinicionCuadro(
            # 2do margen de Cuadro 7 (orientación) - mismo cuadro/hoja, solo
            # para declarar esta 2da relación (ver nota arriba).
            "predio_ganadero_cuadro7_margen_orientacion", pg, "Cuadro 7", 9,
            value_cols_cuadro7_pg, columnas_totales_cuadro7_margen_orientacion,
        ),
        DefinicionCuadro(
            # Margen de sistema productivo + consistencia interna de cada
            # bloque de género - el margen de género va aparte (ver
            # "predio_ganadero_cuadro8_margen_genero" abajo).
            "predio_ganadero_cuadro8", pg, "Cuadro 8", 9,
            value_cols_cuadro8_pg, columnas_totales_cuadro8_pg,
        ),
        DefinicionCuadro(
            # 2do margen de Cuadro 8 (género).
            "predio_ganadero_cuadro8_margen_genero", pg, "Cuadro 8", 9,
            value_cols_cuadro8_pg, columnas_totales_cuadro8_margen_genero,
        ),
        DefinicionCuadro(
            # Margen de género + consistencia interna de cada bloque con sus
            # 6 orientaciones.
            "predio_ganadero_cuadro9", pg, "Cuadro 9", 9,
            value_cols_cuadro9_pg, columnas_totales_cuadro9_pg,
        ),
        DefinicionCuadro(
            "predio_ganadero_cuadro9_c2", pg, "Cuadro 9", 9,
            value_cols_cuadro9_pg, columnas_totales_cuadro9_pg,
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_PG_C9,
        ),
        DefinicionCuadro(
            # Margen de tenencia + consistencia interna de cada bloque con
            # sus 4 sistemas productivos.
            "predio_ganadero_cuadro10", pg, "Cuadro 10", 8,
            value_cols_cuadro10_pg, columnas_totales_cuadro10_pg,
        ),
        DefinicionCuadro(
            "predio_ganadero_cuadro11", pg, "Cuadro 11", 11,
            value_cols_cuadro11_pg, columnas_totales_cuadro11_pg,
        ),
        DefinicionCuadro(
            "predio_ganadero_cuadro11_c2", pg, "Cuadro 11", 11,
            value_cols_cuadro11_pg, columnas_totales_cuadro11_pg,
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_PG_C11,
        ),
        DefinicionCuadro(
            # Margen de tenencia + consistencia interna de cada bloque con
            # sus 6 orientaciones.
            "predio_ganadero_cuadro12", pg, "Cuadro 12", 12,
            value_cols_cuadro12_pg, columnas_totales_cuadro12_pg,
        ),
        DefinicionCuadro(
            "predio_ganadero_cuadro12_c2", pg, "Cuadro 12", 12,
            value_cols_cuadro12_pg, columnas_totales_cuadro12_pg,
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_PG_C12,
        ),
        DefinicionCuadro(
            "predio_ganadero_cuadro13", pg, "Cuadro 13", 8,
            value_cols_cuadro13_pg, columnas_totales_cuadro13_pg,
        ),
        DefinicionCuadro(
            # "con_colmenas" no participa (ver `columnas_totales_cuadro14_pg`).
            "predio_ganadero_cuadro14", pg, "Cuadro 14", 8,
            value_cols_cuadro14_pg, columnas_totales_cuadro14_pg,
        ),
        DefinicionCuadro(
            # Solo Ciclo 2 (no existe en C1) - Total + 5 bloques de cobertura
            # de tierra, sin `columnas_totales` (mismo criterio que el resto
            # del libro). `value_cols` tomado directo de `generar_cuadro15`
            # para no duplicar a mano el orden de las 11 columnas.
            "predio_ganadero_cuadro15", pg, "Cuadro 15", 11,
            predio_ganadero.generar_cuadro15()[1],
        ),
        DefinicionCuadro(
            # Solo Ciclo 2 - Total + con producción animales + 2 columnas de
            # hectáreas, sin `columnas_totales` ("ha_ganaderia_bovbuf" es
            # subconjunto real de "ha_produccion_animales" pero cada una se
            # redondea independiente, ver docstring de `generar_cuadro16`).
            "predio_ganadero_cuadro16", pg, "Cuadro 16", 11,
            ["total_predios_ganaderos", "con_produccion_animales", "ha_produccion_animales", "ha_ganaderia_bovbuf"],
        ),
        DefinicionCuadro(
            # Solo Ciclo 2 - Total + Sí/No/No sabe (área protegida). SIN
            # `columnas_totales` (corregido 2026-09-24 - ver docstring de
            # `generar_cuadro17`): "total_predios_ganaderos" se redondea
            # independiente, igual que el resto del libro.
            "predio_ganadero_cuadro17", pg, "Cuadro 17", 12,
            ["total_predios_ganaderos", "si", "no", "no_sabe"],
            {"total_predios_ganaderos": ["si", "no", "no_sabe"]},
        ),
        DefinicionCuadro(
            # Solo Ciclo 2 - Total + con razas puras + con cruces (no
            # excluyentes, sin `columnas_totales`).
            "predio_ganadero_cuadro18", pg, "Cuadro 18", 11,
            ["total_predios_ganaderos", "con_puras", "con_cruces"],
        ),
        DefinicionCuadro(
            # Solo Ciclo 2 - Total + 52 razas puras + 28 cruces (prefijo
            # "pura_"/"cruce_" para evitar colisión de slugs, ver docstring
            # de `generar_cuadro19`). `value_cols` tomado directo de la
            # función para no duplicar a mano las 81 columnas.
            "predio_ganadero_cuadro19", pg, "Cuadro 19", 11,
            predio_ganadero.generar_cuadro19()[1],
        ),
        DefinicionCuadro(
            # Histórico 2023-2025 ("nuevos/salieron/se mantienen" vs. ciclo
            # anterior / mismo ciclo año anterior) - ver
            # `cuadros/ganadero_historico.py`. "total" = "nuevos" +
            # "mantienen" SOLO en los bloques 2025 (cálculo propio, corregido
            # 2026-09-25) - los bloques 2024 (copiados del libro publicado)
            # NO se fuerzan (su "total" es el valor oficial publicado, queda
            # un residuo pequeño frente a nuevos+mantienen, aceptado). `value_cols`
            # tomado directo de la función para no duplicar a mano las 16 columnas.
            "ganadero_cuadro4_historico", gan, "Cuadro 4", 7,
            ganadero_historico.generar_cuadro4()[1],
            {"c2025c1_total": ["c2025c1_nuevos", "c2025c1_mantienen"], "c2025c2_total": ["c2025c2_nuevos", "c2025c2_mantienen"]},
        ),
        DefinicionCuadro(
            "ganadero_cuadro5_historico", gan, "Cuadro 5", 7,
            ganadero_historico.generar_cuadro5()[1],
            {"c2025c1_total": ["c2025c1_nuevos", "c2025c1_mantienen"], "c2025c2_total": ["c2025c2_nuevos", "c2025c2_mantienen"]},
        ),
        DefinicionCuadro(
            "ganadero_cuadro3_sexo", gan, "Cuadro 3", 8,
            ["total_ganaderos", "natural_total", "mujeres", "hombres", "juridica"],
            {"natural_total": ["mujeres", "hombres"], "total_ganaderos": ["natural_total", "juridica"]},
        ),
        DefinicionCuadro(
            "ganadero_cuadro3_sexo_c2", gan, "Cuadro 3", 8,
            ["total_ganaderos", "natural_total", "mujeres", "hombres", "juridica"],
            {"natural_total": ["mujeres", "hombres"], "total_ganaderos": ["natural_total", "juridica"]},
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_GAN_C3,
        ),
        DefinicionCuadro(
            "ganadero_cuadro6_delitos", gan, "Cuadro 6", 7,
            ["total_ganaderos"] + ganadero._DELITOS + ["ninguno"],
        ),
        DefinicionCuadro(
            "ganadero_cuadro6_delitos_c2", gan, "Cuadro 6", 7,
            ["total_ganaderos"] + ganadero._DELITOS + ["ninguno"],
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_GAN_C6,
        ),
        DefinicionCuadro(
            # Ganaderos por sexo/persona jurídica x edad - solo Ciclo 1
            # (`edadganadero` no existe en Ciclo 2). 7 rangos de edad reales
            # (no los 4 que traía la plantilla original, ver docstring de
            # `generar_cuadro7`) - cada bloque suma exacto sus 7 rangos, y
            # "total_ganaderos" (E) suma exacto los 3 bloques de género
            # (corregido 2026-09-25, igual que Cuadro 3).
            "ganadero_cuadro7_edad", gan, "Cuadro 7", 11,
            *_definicion_cuadro7_ganadero(),
        ),
        DefinicionCuadro(
            "ganadero_cuadro8_tenencia", gan, "Cuadro 8", 8,
            *_definicion_cuadro8_ganadero(),
        ),
        DefinicionCuadro(
            "ganadero_cuadro8_tenencia_c2", gan, "Cuadro 8", 8,
            *_definicion_cuadro8_ganadero(),
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_GAN_C8,
        ),
        DefinicionCuadro(
            "ganadero_cuadro9_comparte_lote", gan, "Cuadro 9", 8,
            *_definicion_cuadro9_ganadero(),
        ),
        DefinicionCuadro(
            "ganadero_cuadro9_comparte_lote_c2", gan, "Cuadro 9", 8,
            *_definicion_cuadro9_ganadero(),
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_GAN_C9,
        ),
        DefinicionCuadro(
            "ganadero_cuadro10_lugar_residencia", gan, "Cuadro 10", 8,
            *_definicion_cuadro10_ganadero(),
        ),
        DefinicionCuadro(
            "ganadero_cuadro10_lugar_residencia_c2", gan, "Cuadro 10", 8,
            *_definicion_cuadro10_ganadero(),
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_GAN_C10,
        ),
        DefinicionCuadro(
            # Misma estructura value_cols/columnas_totales que Cuadro 9 (SI/NO
            # x género) - solo cambia la columna cruda de origen, que no
            # afecta la geometría de la hoja que se valida acá.
            "ganadero_cuadro11_atendio_encuesta", gan, "Cuadro 11", 8,
            *_definicion_cuadro9_ganadero(),
        ),
        DefinicionCuadro(
            "ganadero_cuadro11_atendio_encuesta_c2", gan, "Cuadro 11", 8,
            *_definicion_cuadro9_ganadero(),
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_GAN_C11,
        ),
        DefinicionCuadro(
            "ganadero_cuadro12_sensor_epidemiologico", gan, "Cuadro 12", 8,
            ["total_ganaderos", "si", "no", "no_sabe"],
            {"total_ganaderos": ["si", "no", "no_sabe"]},
        ),
        DefinicionCuadro(
            "ganadero_cuadro12_sensor_epidemiologico_c2", gan, "Cuadro 12", 8,
            ["total_ganaderos", "si", "no", "no_sabe"],
            {"total_ganaderos": ["si", "no", "no_sabe"]},
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_GAN_C12,
        ),
        DefinicionCuadro(
            "ganadero_cuadro13_alerta_temprana", gan, "Cuadro 13", 8,
            ["total_ganaderos", "si", "no", "no_sabe"],
            {"total_ganaderos": ["si", "no", "no_sabe"]},
        ),
        DefinicionCuadro(
            "ganadero_cuadro13_alerta_temprana_c2", gan, "Cuadro 13", 8,
            ["total_ganaderos", "si", "no", "no_sabe"],
            {"total_ganaderos": ["si", "no", "no_sabe"]},
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_GAN_C13,
        ),
        DefinicionCuadro(
            "ganadero_cuadro14_notificar_ica", gan, "Cuadro 14", 8,
            ["total_ganaderos", "si", "no", "no_sabe"],
            {"total_ganaderos": ["si", "no", "no_sabe"]},
        ),
        DefinicionCuadro(
            "ganadero_cuadro14_notificar_ica_c2", gan, "Cuadro 14", 8,
            ["total_ganaderos", "si", "no", "no_sabe"],
            {"total_ganaderos": ["si", "no", "no_sabe"]},
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_GAN_C14,
        ),
        DefinicionCuadro(
            "ganadero_cuadro15_signos_clinicos", gan, "Cuadro 15", 8,
            ["total_ganaderos", "si", "no", "no_sabe"],
            {"total_ganaderos": ["si", "no", "no_sabe"]},
        ),
        DefinicionCuadro(
            "ganadero_cuadro15_signos_clinicos_c2", gan, "Cuadro 15", 8,
            ["total_ganaderos", "si", "no", "no_sabe"],
            {"total_ganaderos": ["si", "no", "no_sabe"]},
            columna_inicio=m.COLUMNA_SEGUNDO_CICLO_GAN_C15,
        ),
        DefinicionCuadro(
            # Sin bloque C2 (no existe `conformacion`/`intcarrera` en Ciclo 2,
            # ver `cuadros/ganadero.py`).
            "ganadero_cuadro16_universidad_area_andina", gan, "Cuadro 16", 7,
            ["total_ganaderos", "conoce_si", "conoce_no", "total_ganaderos2", "interes_si", "interes_no"],
            {"total_ganaderos": ["conoce_si", "conoce_no"], "total_ganaderos2": ["interes_si", "interes_no"]},
        ),
    ]


def _definicion_cuadro7_ganadero() -> tuple[list[str], dict[str, list[str]]]:
    value_cols = ["total_ganaderos"]
    columnas_totales: dict[str, list[str]] = {}
    for prefijo, _ in ganadero._GENERO_PREFIJO_CUADRO7:
        col_total_bloque = f"{prefijo}_total"
        cols_rango = [f"{prefijo}_{ganadero._RANGO_EDAD_SLUG[r]}" for r in ganadero.RANGOS_EDAD_ORDEN]
        value_cols += [col_total_bloque] + cols_rango
        columnas_totales[col_total_bloque] = cols_rango
    # Corregido 2026-09-25: "total_ganaderos" SÍ se deriva como suma de los 3
    # bloques de género (igual que Cuadro 3) - ver docstring de
    # `generar_cuadro7`.
    columnas_totales["total_ganaderos"] = [f"{p}_total" for p, _ in ganadero._GENERO_PREFIJO_CUADRO7]
    return value_cols, columnas_totales


def _definicion_cuadro8_ganadero() -> tuple[list[str], dict[str, list[str]]]:
    cols_general = [ganadero._TENENCIA_SLUG[t] for t in ganadero.TENENCIA_ORDEN]
    value_cols = (
        ["total_ganaderos"] + cols_general
        + ["h_total"] + [f"h_{ganadero._TENENCIA_SLUG[t]}" for t in ganadero.TENENCIA_ORDEN]
        + ["m_total"] + [f"m_{ganadero._TENENCIA_SLUG[t]}" for t in ganadero.TENENCIA_ORDEN]
        + ["j_total"] + [f"j_{ganadero._TENENCIA_SLUG[t]}" for t in ganadero.TENENCIA_ORDEN]
    )
    columnas_totales: dict[str, list[str]] = {}
    for p, _ in ganadero._GENERO_PREFIJO:
        columnas_totales[f"{p}_total"] = [f"{p}_{ganadero._TENENCIA_SLUG[t]}" for t in ganadero.TENENCIA_ORDEN]
    columnas_totales["total_ganaderos"] = [f"{p}_total" for p, _ in ganadero._GENERO_PREFIJO]
    for t in ganadero.TENENCIA_ORDEN:
        slug = ganadero._TENENCIA_SLUG[t]
        columnas_totales[slug] = [f"{p}_{slug}" for p, _ in ganadero._GENERO_PREFIJO]
    return value_cols, columnas_totales


def _definicion_cuadro9_ganadero() -> tuple[list[str], dict[str, list[str]]]:
    value_cols = ["total_ganaderos", "general_si", "general_no"] + [
        f"{p}_{s}" for p, _ in ganadero._GENERO_PREFIJO for s in ("si", "no")
    ]
    columnas_totales = {
        "general_si": [f"{p}_si" for p, _ in ganadero._GENERO_PREFIJO],
        "general_no": [f"{p}_no" for p, _ in ganadero._GENERO_PREFIJO],
        "total_ganaderos": ["general_si", "general_no"],
    }
    return value_cols, columnas_totales


def _definicion_cuadro10_ganadero() -> tuple[list[str], dict[str, list[str]]]:
    value_cols = ["total_ganaderos", "gen_predio", "gen_otro"] + [
        f"{p}_{s}" for p, _ in ganadero._GENERO_PREFIJO for s in ("total", "predio", "otro")
    ]
    columnas_totales: dict[str, list[str]] = {}
    for p, _ in ganadero._GENERO_PREFIJO:
        columnas_totales[f"{p}_total"] = [f"{p}_predio", f"{p}_otro"]
    columnas_totales["gen_predio"] = [f"{p}_predio" for p, _ in ganadero._GENERO_PREFIJO]
    columnas_totales["gen_otro"] = [f"{p}_otro" for p, _ in ganadero._GENERO_PREFIJO]
    columnas_totales["total_ganaderos"] = ["gen_predio", "gen_otro"]
    return value_cols, columnas_totales


def _leer_filas(d: DefinicionCuadro, municipios_validos: set, deptos_validos: set) -> list[tuple]:
    wb = openpyxl.load_workbook(d.ruta_libro, data_only=True)
    ws = wb[d.hoja]
    n = len(d.value_cols)
    filas = []
    r = d.fila_nacional
    while True:
        cod_dep = str(ws.cell(row=r, column=1).value or "").strip()
        cod_mun = str(ws.cell(row=r, column=3).value or "").strip()
        if r == d.fila_nacional:
            nivel = "Nacional"
        elif cod_mun in municipios_validos:
            nivel = "Municipio"
        elif cod_dep in deptos_validos and cod_mun == "":
            nivel = "Departamento"
        else:
            break  # primera fila que no es dato real (notas al pie) -> fin
        vals = [ws.cell(row=r, column=d.columna_inicio + j).value or 0 for j in range(n)]
        filas.append((r, nivel, cod_dep, cod_mun, vals))
        r += 1
    return filas


def validar(d: DefinicionCuadro) -> pd.DataFrame:
    municipios_validos = set(catalogo_territorial.cargar_catalogo_municipios()["CODIGO_MUNICIPIO"])
    deptos_validos = set(catalogo_territorial.cargar_catalogo_departamentos()["COD_DEPARTAMENTO"])
    filas = _leer_filas(d, municipios_validos, deptos_validos)

    problemas = []
    nacional = filas[0]
    deptos = [f for f in filas[1:] if f[1] == "Departamento"]
    municipios = [f for f in filas[1:] if f[1] == "Municipio"]

    # --- Universo completo, sin duplicados ni faltantes ---
    cods_mun = [f[3] for f in municipios]
    faltan_mun = municipios_validos - set(cods_mun)
    dup_mun = {c for c in cods_mun if cods_mun.count(c) > 1}
    if faltan_mun:
        problemas.append({"tipo": "universo", "detalle": f"{len(faltan_mun)} municipios faltantes: {sorted(faltan_mun)[:10]}..."})
    if dup_mun:
        problemas.append({"tipo": "universo", "detalle": f"{len(dup_mun)} municipios duplicados: {sorted(dup_mun)[:10]}"})
    cods_dep = [f[2] for f in deptos]
    faltan_dep = deptos_validos - set(cods_dep)
    if faltan_dep:
        problemas.append({"tipo": "universo", "detalle": f"{len(faltan_dep)} departamentos faltantes: {sorted(faltan_dep)}"})

    # --- Vertical: cada depto = suma de sus municipios ---
    por_depto: dict[str, list] = {}
    for f in municipios:
        por_depto.setdefault(f[2], []).append(f)
    for f_dep in deptos:
        suma = [sum(mm[4][j] for mm in por_depto.get(f_dep[2], [])) for j in range(len(d.value_cols))]
        for j, (a, b) in enumerate(zip(f_dep[4], suma)):
            if a != b:
                problemas.append({
                    "tipo": "vertical_departamento", "fila_excel": f_dep[0], "columna": d.value_cols[j],
                    "detalle": f"depto {f_dep[2]}: {a} != suma municipios {b} (dif {a-b:+g})",
                })

    # --- Vertical: nacional = suma de departamentos ---
    suma_deptos = [sum(f[4][j] for f in deptos) for j in range(len(d.value_cols))]
    for j, (a, b) in enumerate(zip(nacional[4], suma_deptos)):
        if a != b:
            problemas.append({
                "tipo": "vertical_nacional", "fila_excel": nacional[0], "columna": d.value_cols[j],
                "detalle": f"nacional: {a} != suma deptos {b} (dif {a-b:+g})",
            })

    # --- Horizontal: cada relación total/componentes, en TODAS las filas ---
    idx = {c: j for j, c in enumerate(d.value_cols)}
    for col_total, componentes in d.columnas_totales.items():
        for r_, nivel, cd, cm, vals in filas:
            total = vals[idx[col_total]]
            suma = sum(vals[idx[c]] for c in componentes)
            if total != suma:
                problemas.append({
                    "tipo": "horizontal", "fila_excel": r_, "columna": col_total,
                    "detalle": f"{nivel} {cd}{cm}: {col_total}={total} != suma({componentes})={suma} (dif {total-suma:+g})",
                })

    out = pd.DataFrame(problemas)
    if len(out):
        out.insert(0, "cuadro", d.nombre)
    return out


@dataclass
class ComparacionCruzada:
    """Dos cuadros (a veces del mismo libro, a veces de libros distintos)
    reportan la MISMA cantidad real bajo dos columnas - deben coincidir
    EXACTO en los 3 niveles (municipio, departamento, nacional), no solo a
    nivel nacional agregado (a pedido explícito del usuario, 2026-09-21,
    tras detectar que Cuadro 1 y Cuadro 3 de predio-ganadero no coincidían
    a nivel nacional por caminos de redondeo distintos - ver
    `cuadros/predio_ganadero.py`)."""

    nombre: str
    def1: DefinicionCuadro
    col1: str
    def2: DefinicionCuadro
    col2: str


def _comparaciones_cruzadas() -> list[ComparacionCruzada]:
    defs = {d.nombre: d for d in _definiciones()}
    return [
        # --- Cuadro 1 ENTRE LOS 3 LIBROS (inventario/ganadero/predio-ganadero) ---
        # Los 3 libros comparten el MISMO pendiente para Cuadro 1 (ver
        # `_paso_cuadro1_ganadero` en `main.py`: "idéntico en los 3 libros -
        # un solo pendiente, `ensamblar` lo aplica a los 3") - deben coincidir
        # EXACTO, a pedido del usuario 2026-10-02 (validar predio-ganadero
        # contra inventario y ganadero). Se comparan los 2 pares que cubren
        # los 3 libros de forma transitiva (inventario=ganadero,
        # ganadero=predio_ganadero implica inventario=predio_ganadero), más
        # el par directo inventario vs predio_ganadero por claridad.
        *[
            ComparacionCruzada(
                f"Cuadro 1: {col} (inventario vs ganadero{sufijo_nombre})",
                defs[f"inventario_cuadro1{sufijo_def}"], col,
                defs[f"ganadero_cuadro1{sufijo_def}"], col,
            )
            for col in ["total_predios", "total_ganaderos", "total_predios_ganaderos"]
            for sufijo_nombre, sufijo_def in [(" - C1", ""), (" - C2", "_c2")]
        ],
        *[
            ComparacionCruzada(
                f"Cuadro 1: {col} (ganadero vs predio_ganadero{sufijo_nombre})",
                defs[f"ganadero_cuadro1{sufijo_def}"], col,
                defs[f"predio_ganadero_cuadro1{sufijo_def}"], col,
            )
            for col in ["total_predios", "total_ganaderos", "total_predios_ganaderos"]
            for sufijo_nombre, sufijo_def in [(" - C1", ""), (" - C2", "_c2")]
        ],
        *[
            ComparacionCruzada(
                f"Cuadro 1: {col} (inventario vs predio_ganadero{sufijo_nombre})",
                defs[f"inventario_cuadro1{sufijo_def}"], col,
                defs[f"predio_ganadero_cuadro1{sufijo_def}"], col,
            )
            for col in ["total_predios", "total_ganaderos", "total_predios_ganaderos"]
            for sufijo_nombre, sufijo_def in [(" - C1", ""), (" - C2", "_c2")]
        ],
        # --- Cuadro 1, bloque "nuevos" (K-N) ENTRE LOS 3 LIBROS - mismo
        # pendiente compartido, ver `_paso_cuadro1_ganadero_nuevos` en main.py.
        *[
            ComparacionCruzada(
                f"Cuadro 1 nuevos: {col} (inventario vs ganadero)",
                defs["inventario_cuadro1_nuevos"], col,
                defs["ganadero_cuadro1_nuevos"], col,
            )
            for col in ["predios_nuevos", "ganaderos_nuevos", "predios_ganaderos_nuevos", "animales_predios_nuevos"]
        ],
        *[
            ComparacionCruzada(
                f"Cuadro 1 nuevos: {col} (ganadero vs predio_ganadero)",
                defs["ganadero_cuadro1_nuevos"], col,
                defs["predio_ganadero_cuadro1_nuevos"], col,
            )
            for col in ["predios_nuevos", "ganaderos_nuevos", "predios_ganaderos_nuevos", "animales_predios_nuevos"]
        ],
        # --- ganadero: Cuadro 4 vs Cuadro 5 (histórico, bloques 2025) ---
        # OJO - ya NO se compara contra Cuadro 1/3, NI Cuadro 4 contra Cuadro 5
        # (corregido 2026-09-25, ver docstring de `cuadros/ganadero_historico.py`):
        # "total" de estos bloques ahora se DERIVA de nuevos+mantienen
        # (consistencia interna fila por fila, a pedido explícito del
        # usuario), en vez de redondearse independiente. Cuadro 4 y Cuadro 5
        # usan un ciclo de referencia distinto para "nuevos"/"mantienen"
        # (Cuadro 4 = ciclo inmediatamente anterior; Cuadro 5 = mismo ciclo
        # del año anterior) - son 2 particiones distintas de la misma
        # población 2025, así que al redondear cada una de forma
        # independiente por municipio, sus sumas ya NO coinciden exactamente
        # entre Cuadro 4 y Cuadro 5 (residuo de ~0.005%, ej. 32/682.243 en
        # 2025-C1 nacional). El usuario priorizó la identidad interna de
        # cada cuadro (Total=Nuevos+Mantienen) sobre la coincidencia cruzada
        # Cuadro4↔Cuadro5, así que esa comparación cruzada ya no se declara
        # aquí (antes sí, cuando "total" se rondeaba independiente y por
        # construcción coincidía).
        # --- ganadero: Cuadro 1 vs Cuadro 3/7/8/9/10/11/12/13/14/15/16 ---
        # "total_ganaderos" se reutiliza exacto de Cuadro 1 en estos 11
        # cuadros (corregido 2026-10-02, a pedido del usuario - antes cada
        # uno lo derivaba de sus propias categorías, con un residuo de 1 a
        # 213 unidades frente a Cuadro 1, ver `cuadros/ganadero.py`).
        *[
            ComparacionCruzada(
                f"ganadero: total_ganaderos (Cuadro 1 vs Cuadro {n})",
                defs["ganadero_cuadro1"], "total_ganaderos",
                defs[nombre_def], "total_ganaderos",
            )
            for n, nombre_def in [
                (3, "ganadero_cuadro3_sexo"), (7, "ganadero_cuadro7_edad"),
                (8, "ganadero_cuadro8_tenencia"), (9, "ganadero_cuadro9_comparte_lote"),
                (10, "ganadero_cuadro10_lugar_residencia"), (11, "ganadero_cuadro11_atendio_encuesta"),
                (12, "ganadero_cuadro12_sensor_epidemiologico"), (13, "ganadero_cuadro13_alerta_temprana"),
                (14, "ganadero_cuadro14_notificar_ica"), (15, "ganadero_cuadro15_signos_clinicos"),
                (16, "ganadero_cuadro16_universidad_area_andina"),
            ]
        ],
        *[
            ComparacionCruzada(
                f"ganadero: total_ganaderos (Cuadro 1 vs Cuadro {n} - Ciclo 2)",
                defs["ganadero_cuadro1_c2"], "total_ganaderos",
                defs[nombre_def], "total_ganaderos",
            )
            for n, nombre_def in [
                (3, "ganadero_cuadro3_sexo_c2"), (8, "ganadero_cuadro8_tenencia_c2"),
                (9, "ganadero_cuadro9_comparte_lote_c2"), (10, "ganadero_cuadro10_lugar_residencia_c2"),
                (11, "ganadero_cuadro11_atendio_encuesta_c2"), (12, "ganadero_cuadro12_sensor_epidemiologico_c2"),
                (13, "ganadero_cuadro13_alerta_temprana_c2"), (14, "ganadero_cuadro14_notificar_ica_c2"),
                (15, "ganadero_cuadro15_signos_clinicos_c2"),
            ]
        ],
        ComparacionCruzada(
            # "total_ganaderos2" (2do bloque de Cuadro 16) también reutiliza
            # Cuadro 1 (mismo total, repetido - ver docstring del módulo).
            "ganadero: total_ganaderos2 (Cuadro 1 vs Cuadro 16, bloque interés)",
            defs["ganadero_cuadro1"], "total_ganaderos",
            defs["ganadero_cuadro16_universidad_area_andina"], "total_ganaderos2",
        ),
        ComparacionCruzada(
            # sist_total se reutiliza exacto de Cuadro 3 (ver
            # `generar_sistema_productivo`) - deben coincidir siempre.
            "inventario: total bovinos (Cuadro 3 vs Cuadro 6)",
            defs["inventario_cuadro3_bovinos"], "total_total",
            defs["inventario_cuadro6_sistema_productivo"], "sist_total",
        ),
        ComparacionCruzada(
            # blk_total__total_total se reutiliza exacto de Cuadro 3 C1 (ver
            # docstring de `generar_por_orientacion`) - deben coincidir siempre.
            "inventario: total bovinos (Cuadro 3 vs Cuadro 4, C1)",
            defs["inventario_cuadro3_bovinos"], "total_total",
            defs["inventario_cuadro4_orientacion"], "blk_total__total_total",
        ),
        ComparacionCruzada(
            "inventario: total bovinos (Cuadro 3 vs Cuadro 5, C2)",
            defs["inventario_cuadro3_bovinos_c2"], "total_total",
            defs["inventario_cuadro5_orientacion"], "blk_total__total_total",
        ),
        ComparacionCruzada(
            "predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro 3)",
            defs["predio_ganadero_cuadro1"], "total_predios_ganaderos",
            defs["predio_ganadero_cuadro3"], "total_predios_ganaderos",
        ),
        ComparacionCruzada(
            "predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro 4)",
            defs["predio_ganadero_cuadro1"], "total_predios_ganaderos",
            defs["predio_ganadero_cuadro4"], "total_predios_ganaderos",
        ),
        ComparacionCruzada(
            "predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro 5)",
            defs["predio_ganadero_cuadro1"], "total_predios_ganaderos",
            defs["predio_ganadero_cuadro5"], "total_predios_ganaderos",
        ),
        ComparacionCruzada(
            "predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro 6)",
            defs["predio_ganadero_cuadro1"], "total_predios_ganaderos",
            defs["predio_ganadero_cuadro6"], "total_predios_ganaderos",
        ),
        ComparacionCruzada(
            "predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro 7)",
            defs["predio_ganadero_cuadro1"], "total_predios_ganaderos",
            defs["predio_ganadero_cuadro7"], "total_predios_ganaderos",
        ),
        ComparacionCruzada(
            "predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro 8)",
            defs["predio_ganadero_cuadro1"], "total_predios_ganaderos",
            defs["predio_ganadero_cuadro8"], "total_predios_ganaderos",
        ),
        ComparacionCruzada(
            "predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro 9)",
            defs["predio_ganadero_cuadro1"], "total_predios_ganaderos",
            defs["predio_ganadero_cuadro9"], "total_predios_ganaderos",
        ),
        ComparacionCruzada(
            "predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro 10)",
            defs["predio_ganadero_cuadro1"], "total_predios_ganaderos",
            defs["predio_ganadero_cuadro10"], "total_predios_ganaderos",
        ),
        ComparacionCruzada(
            "predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro 11)",
            defs["predio_ganadero_cuadro1"], "total_predios_ganaderos",
            defs["predio_ganadero_cuadro11"], "total_predios_ganaderos",
        ),
        ComparacionCruzada(
            "predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro 12)",
            defs["predio_ganadero_cuadro1"], "total_predios_ganaderos",
            defs["predio_ganadero_cuadro12"], "total_predios_ganaderos",
        ),
        ComparacionCruzada(
            "predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro 13)",
            defs["predio_ganadero_cuadro1"], "total_predios_ganaderos",
            defs["predio_ganadero_cuadro13"], "total_predios_ganaderos",
        ),
        ComparacionCruzada(
            "predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro 14)",
            defs["predio_ganadero_cuadro1"], "total_predios_ganaderos",
            defs["predio_ganadero_cuadro14"], "total_predios_ganaderos",
        ),
    ] + [
        ComparacionCruzada(
            f"predio_ganadero: {predio_ganadero._ORIENTACION_SLUG[o]} (Cuadro 4 vs Cuadro 7)",
            defs["predio_ganadero_cuadro4"], predio_ganadero._ORIENTACION_SLUG[o],
            defs["predio_ganadero_cuadro7"], f"{predio_ganadero._ORIENTACION_SLUG[o]}_total",
        )
        for o in predio_ganadero.ORIENTACIONES_ORDEN
    ] + [
        ComparacionCruzada(
            f"predio_ganadero: {predio_ganadero._GENERO_BLOQUE_SLUG[g]}_total (Cuadro 8 vs Cuadro 9)",
            defs["predio_ganadero_cuadro8"], f"{predio_ganadero._GENERO_BLOQUE_SLUG[g]}_total",
            defs["predio_ganadero_cuadro9"], f"{predio_ganadero._GENERO_BLOQUE_SLUG[g]}_total",
        )
        for g in predio_ganadero._GENERO_BLOQUE_ORDEN
    ] + [
        ComparacionCruzada(
            f"predio_ganadero: {predio_ganadero._TENENCIA_SLUG[t]} (Cuadro 10 vs Cuadro 11)",
            defs["predio_ganadero_cuadro10"], f"{predio_ganadero._TENENCIA_SLUG[t]}_total",
            defs["predio_ganadero_cuadro11"], predio_ganadero._TENENCIA_SLUG[t],
        )
        for t in predio_ganadero.TENENCIA_ORDEN
    ] + [
        ComparacionCruzada(
            f"predio_ganadero: {predio_ganadero._TENENCIA_SLUG[t]}_total (Cuadro 11 vs Cuadro 12)",
            defs["predio_ganadero_cuadro11"], predio_ganadero._TENENCIA_SLUG[t],
            defs["predio_ganadero_cuadro12"], f"{predio_ganadero._TENENCIA_SLUG[t]}_total",
        )
        for t in predio_ganadero.TENENCIA_ORDEN
    ] + [
        # --- Ciclo 2 (Fase 8, 2026-09-24) ---
        # Cuadro 1 bloque C2 (H-J) vs los 5 cuadros de predio-ganadero que sí
        # tienen bloque C2 (3/4/9/11/12) + los 5 cuadros nuevos de Ciclo 2
        # (15-19, ver `cuadros/predio_ganadero.py`) - mismo criterio que las
        # comparaciones C1 de arriba: cada total se redondeó independiente,
        # deben coincidir exacto en los 3 niveles.
        ComparacionCruzada(
            f"predio_ganadero: total_predios_ganaderos (Cuadro 1 vs Cuadro {n} - Ciclo 2)",
            defs["predio_ganadero_cuadro1_c2"], "total_predios_ganaderos",
            defs[nombre_def], "total_predios_ganaderos",
        )
        for n, nombre_def in [
            (3, "predio_ganadero_cuadro3_c2"), (4, "predio_ganadero_cuadro4_c2"),
            (9, "predio_ganadero_cuadro9_c2"), (11, "predio_ganadero_cuadro11_c2"),
            (12, "predio_ganadero_cuadro12_c2"), (15, "predio_ganadero_cuadro15"),
            (16, "predio_ganadero_cuadro16"), (17, "predio_ganadero_cuadro17"),
            (18, "predio_ganadero_cuadro18"), (19, "predio_ganadero_cuadro19"),
        ]
    ] + [
        ComparacionCruzada(
            f"predio_ganadero: {predio_ganadero._TENENCIA_SLUG[t]}_total (Cuadro 11 vs Cuadro 12 - Ciclo 2)",
            defs["predio_ganadero_cuadro11_c2"], predio_ganadero._TENENCIA_SLUG[t],
            defs["predio_ganadero_cuadro12_c2"], f"{predio_ganadero._TENENCIA_SLUG[t]}_total",
        )
        for t in predio_ganadero.TENENCIA_ORDEN
    ]


def comparar_cruzado(c: ComparacionCruzada) -> pd.DataFrame:
    municipios_validos = set(catalogo_territorial.cargar_catalogo_municipios()["CODIGO_MUNICIPIO"])
    deptos_validos = set(catalogo_territorial.cargar_catalogo_departamentos()["COD_DEPARTAMENTO"])
    filas1 = _leer_filas(c.def1, municipios_validos, deptos_validos)
    filas2 = _leer_filas(c.def2, municipios_validos, deptos_validos)

    idx1 = c.def1.value_cols.index(c.col1)
    idx2 = c.def2.value_cols.index(c.col2)
    d1 = {(nivel, cd, cm): vals[idx1] for _, nivel, cd, cm, vals in filas1}
    d2 = {(nivel, cd, cm): vals[idx2] for _, nivel, cd, cm, vals in filas2}

    problemas = []
    for clave in sorted(set(d1) | set(d2)):
        v1, v2 = d1.get(clave), d2.get(clave)
        if v1 != v2:
            nivel, cd, cm = clave
            problemas.append({
                "comparacion": c.nombre, "nivel": nivel, "cod_departamento": cd, "cod_municipio": cm,
                "detalle": f"{c.def1.nombre}.{c.col1}={v1} != {c.def2.nombre}.{c.col2}={v2} (dif {(v1 or 0)-(v2 or 0):+g})",
            })
    return pd.DataFrame(problemas)


def generar_y_guardar() -> None:
    resultados = []
    for d in _definiciones():
        print(f"Validando {d.nombre} ({d.ruta_libro.name} / {d.hoja}) ...")
        problemas = validar(d)
        if len(problemas):
            print(f"  {len(problemas)} problema(s) encontrado(s)")
        else:
            print("  OK - sin inconsistencias")
        resultados.append(problemas)

    for c in _comparaciones_cruzadas():
        print(f"Comparando {c.nombre} (municipio + departamento + nacional) ...")
        problemas = comparar_cruzado(c)
        if len(problemas):
            print(f"  {len(problemas)} problema(s) encontrado(s)")
            print(problemas.to_string())
        else:
            print("  OK - coincide exacto en los 3 niveles")
        resultados.append(problemas)

    todo = pd.concat(resultados, ignore_index=True) if any(len(r) for r in resultados) else pd.DataFrame(
        columns=["cuadro", "tipo", "fila_excel", "columna", "detalle"]
    )
    ruta = config.BASES_CALIBRADAS_DIR / "validacion_estructura_cuadros.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    todo.to_csv(ruta, sep=";", index=False, encoding="utf-8-sig")
    print(f"\n{'Sin ninguna inconsistencia en ningún cuadro.' if todo.empty else f'{len(todo)} problema(s) en total.'}")
    print(f"Guardado: {ruta}")


if __name__ == "__main__":
    generar_y_guardar()
