"""Cuadros del libro "Inventario" (animales), calculables ahora porque ya
existe el peso de calibración (F_AJUSTA_BOVINOS / F_AJUSTA_BUFALINOS).

Traducción de "Programas Carolina/4.1. cuadros inventario.sas":
 - Cuadro 3: bovinos por sexo y edad.
 - Cuadro 6 (aquí "cuadro_bufalinos"): bufalinos por sexo y edad (misma lógica).
 - Cuadro 7 (aquí "cuadro_otras_especies"): equinos/porcinos/ovinos/caprinos/otros.
"""
from __future__ import annotations

import pandas as pd

from .. import agregador, base_maestra_inventario_c1, config, preparar_base_c1


def _leer_maestra_c1() -> pd.DataFrame:
    """Base maestra de inventario Ciclo 1 (ver `base_maestra_inventario_c1.py`):
    ya trae las columnas de tramo de bovinos/bufalinos calibradas, y
    orientacionhato/sistemaproductivo/otras especies listas para usar - los
    cuadros de acá solo seleccionan y agregan, no recalculan nada."""
    return pd.read_parquet(base_maestra_inventario_c1.RUTA_BASE_MAESTRA_INVENTARIO_C1)


# Orden EXACTO de columnas tal como aparecen en la plantilla Excel (bloque
# "Primer ciclo nacional de vacunación de 2025", columnas E..Z), fila 6/7 del
# Cuadro 3 (bovinos) y Cuadro 6->7 real (bufalinos, misma estructura de encabezado).
COLUMNAS_TOTAL = ["men_3_mes", "3_9_mes", "9_12_mes", "1_2_ani", "2_3_ani", "may_3_ani"]
COLUMNAS_MACHO = COLUMNAS_TOTAL
COLUMNAS_HEMBRA = ["men_3_mes", "3_9_mes", "9_12_mes", "1_2_ani", "2_3_ani", "3_5_ani", "may_5_ani"]

ETIQUETAS_TOTAL = ["Total", "Menor a 3 meses", "De 3 hasta 9 meses", "De 9 hasta 12 meses",
                   "De 1 hasta 2 años", "De 2 hasta 3 años", "Mayor de 3 años"]
ETIQUETAS_HEMBRA = ["Total hembras", "Menor a 3 meses", "De 3 hasta 9 meses", "De 9 hasta 12 meses",
                    "De 1 hasta 2 años", "De 2 hasta 3 años", "De 3 hasta 5 años", "Mayor de 5 años"]


def _suma_con_nv(df: pd.DataFrame, columna: str) -> pd.Series:
    total = df[columna].fillna(0)
    nv = f"{columna}_NV"
    if nv in df.columns:
        total = total + df[nv].fillna(0)
    return total


def _preparar(especie: str, incluir_orientacion: bool = False, ciclo: str = "C1") -> pd.DataFrame:
    if ciclo == "C2":
        # Ciclo 2 viene de una base cruda distinta (nombres RUV/DMC sin
        # renombrar, un solo archivo bovinos+bufalinos) que ya se calibra y
        # normaliza dentro de `preparar_base_c2` - ver ese módulo.
        from .. import preparar_base_c2
        df = preparar_base_c2.cargar_inventario_c2(especie, incluir_orientacion=incluir_orientacion)
    else:
        # Ya viene calibrada (por especie) y con orientacionhato normalizada -
        # ver `base_maestra_inventario_c1.py`.
        df = _leer_maestra_c1()
    prefijo = "BOV" if especie.lower() == "bovinos" else "BUF"

    macho = {
        "men_3_mes": f"AFT_{prefijo}_MAC_MEN_3_MES",
        "3_9_mes": f"AFT_{prefijo}_MAC_3_8_MES",
        "9_12_mes": f"AFT_{prefijo}_MAC_8_12_MES",
        "1_2_ani": f"AFT_{prefijo}_MAC_1_2_ANI",
        "2_3_ani": f"AFT_{prefijo}_MAC_2_3_ANI",
        "may_3_ani": f"AFT_{prefijo}_MAC_MAY_3_ANI",
    }
    hembra = {
        "men_3_mes": f"AFT_{prefijo}_HEM_MEN_3_MES",
        "3_9_mes": f"AFT_{prefijo}_HEM_MEN_DE_3_8_MES",
        "9_12_mes": f"AFT_{prefijo}_DE_8_12_MES",
        "1_2_ani": f"AFT_{prefijo}_HEM_1_2_ANI",
        "2_3_ani": f"AFT_{prefijo}_HEM_2_3_ANI",
        "3_5_ani": f"AFT_{prefijo}_HEM_3_5_ANI",
        "may_5_ani": f"AFT_{prefijo}_HEM_MAY_5_ANI",
    }

    out = df[["CODIGO_MUNICIPIO"]].copy()
    for clave, col in macho.items():
        out[f"macho_{clave}"] = _suma_con_nv(df, col)
    for clave, col in hembra.items():
        out[f"hembra_{clave}"] = _suma_con_nv(df, col)

    out["total_men_3_mes"] = out["macho_men_3_mes"] + out["hembra_men_3_mes"]
    out["total_3_9_mes"] = out["macho_3_9_mes"] + out["hembra_3_9_mes"]
    out["total_9_12_mes"] = out["macho_9_12_mes"] + out["hembra_9_12_mes"]
    out["total_1_2_ani"] = out["macho_1_2_ani"] + out["hembra_1_2_ani"]
    out["total_2_3_ani"] = out["macho_2_3_ani"] + out["hembra_2_3_ani"]
    out["total_may_3_ani"] = out["macho_may_3_ani"] + out["hembra_3_5_ani"] + out["hembra_may_5_ani"]

    out["macho_total"] = sum(out[f"macho_{c}"] for c in COLUMNAS_MACHO)
    out["hembra_total"] = sum(out[f"hembra_{c}"] for c in COLUMNAS_HEMBRA)
    out["total_total"] = out["macho_total"] + out["hembra_total"]

    if incluir_orientacion:
        # Versión "gruesa" de hembra (colapsa 3-5a/+5a en "Mayor de 3 años") para
        # que los 3 grupos de sexo (Total/Machos/Hembras) del Cuadro 4/5 usen el
        # mismo esquema de 6 tramos etarios (así lo define la plantilla real).
        for c in COLUMNAS_TOTAL:
            if c == "may_3_ani":
                out["hembra_coarse_may_3_ani"] = out["hembra_3_5_ani"] + out["hembra_may_5_ani"]
            else:
                out[f"hembra_coarse_{c}"] = out[f"hembra_{c}"]
        out["hembra_coarse_total"] = out["hembra_total"]
        out["orientacionhato"] = df["orientacionhato"]

    return out


def _value_cols() -> list[str]:
    return (
        ["total_total"] + [f"total_{c}" for c in COLUMNAS_TOTAL]
        + ["macho_total"] + [f"macho_{c}" for c in COLUMNAS_MACHO]
        + ["hembra_total"] + [f"hembra_{c}" for c in COLUMNAS_HEMBRA]
    )


def _columnas_totales() -> dict[str, list[str]]:
    """`total_X = macho_X + hembra_X` (consistencia horizontal, ver
    `agregador.generar_cuadro`) - "macho_total"/"hembra_total" primero,
    porque "total_total" depende de ellos. `total_may_3_ani` es un caso
    especial: el tramo hembra correspondiente en la plantilla real está
    partido en 2 (`hembra_3_5_ani` + `hembra_may_5_ani`), igual que en
    `_preparar`."""
    mapa = {
        "macho_total": [f"macho_{c}" for c in COLUMNAS_MACHO],
        "hembra_total": [f"hembra_{c}" for c in COLUMNAS_HEMBRA],
        "total_total": ["macho_total", "hembra_total"],
    }
    for c in COLUMNAS_TOTAL:
        if c == "may_3_ani":
            mapa[f"total_{c}"] = ["macho_may_3_ani", "hembra_3_5_ani", "hembra_may_5_ani"]
        else:
            mapa[f"total_{c}"] = [f"macho_{c}", f"hembra_{c}"]
    return mapa


def generar(especie: str, ciclo: str = "C1") -> pd.DataFrame:
    """Cuadro 3 (bovinos) / Cuadro 7 real de la plantilla (bufalinos): cantidad
    de animales por sexo y edad, según total nacional/departamento/municipio.

    `ciclo="C1"` llena el bloque "Primer ciclo nacional de vacunación de 2025"
    (columnas E-Z); `ciclo="C2"` llena el bloque "Segundo ciclo" (columnas
    AA-AV), usando `preparar_base_c2` en vez de la base de Ciclo 1.
    """
    base = _preparar(especie, ciclo=ciclo)
    value_cols = _value_cols()
    return agregador.generar_cuadro(base, value_cols, columnas_totales=_columnas_totales())


def value_cols() -> list[str]:
    return _value_cols()


# --- Cuadro 6: bovinos por sistema productivo (R11 -> sistemaproductivo) ---
# Orden EXACTO de la plantilla (fila 6, Cuadro 6): no es alfabético.
SISTEMA_PRODUCTIVO_ORDEN = ["Pastoreo mejorado", "Pastoreo extractivo", "Estabulado", "Silvopastoril"]
_SISTEMA_SLUG = {
    "Pastoreo mejorado": "pastoreo_mejorado",
    "Pastoreo extractivo": "pastoreo_extractivo",
    "Estabulado": "estabulado",
    "Silvopastoril": "silvopastoril",
}


def _total_animales(df: pd.DataFrame, columnas: list[str]) -> pd.Series:
    total = pd.Series(0.0, index=df.index)
    for col in columnas:
        total = total + df[col].fillna(0)
        nv = f"{col}_NV"
        if nv in df.columns:
            total = total + df[nv].fillna(0)
    return total


def generar_sistema_productivo() -> pd.DataFrame:
    """Cuadro 6: cantidad de bovinos según el sistema productivo implementado
    en el predio (pregunta 11/12 del formulario, columna R11 en la base cruda
    -ver nota de desfase en config.RENOMBRE_PREGUNTAS-).

    "sist_total" se reutiliza EXACTO de Cuadro 3 (`generar("bovinos")`) en vez
    de recalcularse independiente - mismo criterio ya usado en
    `generar_por_orientacion` (Cuadro 4/5) para garantizar coincidencia
    exacta con Cuadro 3 por construcción. Antes "sist_total" se declaraba
    `columnas_totales` (derivado de sumar los 4 sistemas productivos, cada
    uno redondeado independiente por municipio) - eso dejaba un residuo de
    ~18 animales (0.0001% nacional) frente a Cuadro 3/4, detectado por el
    usuario 2026-09-25 al comparar el Excel.

    A pedido del usuario (2026-09-25), la suma de los 4 sistemas SÍ debe
    coincidir EXACTO con "sist_total" en los 3 niveles (nacional, depto,
    municipio) - a diferencia del trade-off aceptado en otros cuadros (ver
    `cuadros/ganadero_historico.py`), acá SÍ se puede lograr sin sacrificar
    la coincidencia con Cuadro 3: el residuo de redondeo (~18 animales a
    nivel nacional) se absorbe en el sistema MÁS GRANDE DE CADA MUNICIPIO
    (no siempre "Pastoreo mejorado" - primer intento, revertido: aunque es
    el sistema más grande a nivel NACIONAL, en 7 municipios pequeños domina
    otro sistema localmente, y fijar siempre "Pastoreo mejorado" ahí daba
    valores NEGATIVOS, ej. -2 - inaceptable en un cuadro publicado).
    Departamento/Nacional se recalculan DESPUÉS como suma de los municipios
    ya ajustados (mismo principio de `agregador.py`: redondear/ajustar una
    sola vez, al nivel más fino, y sumar hacia arriba) - así se preserva la
    consistencia vertical automáticamente.
    """
    columnas_inv = preparar_base_c1.columnas_inventario("bovinos")
    df = _leer_maestra_c1()  # ya calibrado y renombrado - ver base_maestra_inventario_c1.py

    out = df[["CODIGO_MUNICIPIO"]].copy()
    total_bov = _total_animales(df, columnas_inv)
    for sistema in SISTEMA_PRODUCTIVO_ORDEN:
        out[f"sist_{_SISTEMA_SLUG[sistema]}"] = total_bov.where(df["sistemaproductivo"] == sistema, 0.0)

    cols_sistemas = [f"sist_{_SISTEMA_SLUG[s]}" for s in SISTEMA_PRODUCTIVO_ORDEN]
    tabla = agregador.generar_cuadro(out, cols_sistemas)

    tabla_total = generar("bovinos", ciclo="C1")
    tabla["sist_total"] = tabla_total["total_total"].reset_index(drop=True)

    es_municipio = tabla["NIVEL"] == agregador.NIVEL_MUNICIPIO
    muni = tabla.loc[es_municipio, ["COD_DEPARTAMENTO", "sist_total"] + cols_sistemas].copy()
    suma_4 = muni[cols_sistemas].sum(axis=1)
    idx_max = muni[cols_sistemas].to_numpy().argmax(axis=1)
    for i, col in enumerate(cols_sistemas):
        filtro = idx_max == i
        muni.loc[filtro, col] = muni.loc[filtro, "sist_total"] - (suma_4[filtro] - muni.loc[filtro, col])
    tabla.loc[es_municipio, cols_sistemas] = muni[cols_sistemas]

    dep_agg = muni.groupby("COD_DEPARTAMENTO")[cols_sistemas].sum()
    es_depto = tabla["NIVEL"] == agregador.NIVEL_DEPARTAMENTO
    for col in cols_sistemas:
        tabla.loc[es_depto, col] = tabla.loc[es_depto, "COD_DEPARTAMENTO"].map(dep_agg[col])
        tabla.loc[tabla["NIVEL"] == agregador.NIVEL_NACIONAL, col] = muni[col].sum()

    value_cols_ = ["sist_total"] + cols_sistemas
    claves = ["NIVEL", "COD_DEPARTAMENTO", "DEPARTAMENTO", "CODIGO_MUNICIPIO", "MUNICIPIO"]
    return tabla[claves + value_cols_]


def value_cols_sistema_productivo() -> list[str]:
    return ["sist_total"] + [f"sist_{_SISTEMA_SLUG[s]}" for s in SISTEMA_PRODUCTIVO_ORDEN]


# --- Cuadro 8: otras especies pecuarias (equinos, porcinos, ovinos, caprinos, otra) ---
# Orden EXACTO de la plantilla (fila 7, Cuadro 8): Equinos, Porcinos, Ovinos, Caprinos, Otra especie.
ESPECIES_ORDEN = ["EQUINOS", "PORCINOS", "OVINOS", "CAPRINOS", "OTROS"]


def generar_otras_especies(ciclo: str = "C1") -> pd.DataFrame:
    """Cuadro 8: animales de otras especies pecuarias, por sexo. Columnas
    nativas del RUV (TOTAL_<especie>, <especie>_MACHO, <especie>_HEMBRA), sin
    factor de calibración (el SAS original tampoco lo aplica aquí)."""
    columnas = []
    for especie in ESPECIES_ORDEN:
        columnas += [f"TOTAL_{especie}", f"{especie}_MACHO", f"{especie}_HEMBRA"]

    if ciclo == "C2":
        from .. import preparar_base_c2
        df = preparar_base_c2.cargar_otras_especies_c2()
    else:
        # Estas columnas nunca se calibran (igual que en el SAS original) -
        # ver base_maestra_inventario_c1.py.
        df = _leer_maestra_c1()

    out = df[["CODIGO_MUNICIPIO"] + columnas].copy()
    for c in columnas:
        out[c] = out[c].fillna(0)

    # TOTAL_<especie> = <especie>_MACHO + <especie>_HEMBRA exacto (verificado
    # con datos reales, sin excepciones) - consistencia horizontal, ver
    # `agregador.generar_cuadro`.
    columnas_totales = {f"TOTAL_{especie}": [f"{especie}_MACHO", f"{especie}_HEMBRA"] for especie in ESPECIES_ORDEN}
    return agregador.generar_cuadro(out, columnas, columnas_totales=columnas_totales)


def value_cols_otras_especies() -> list[str]:
    columnas = []
    for especie in ESPECIES_ORDEN:
        columnas += [f"TOTAL_{especie}", f"{especie}_MACHO", f"{especie}_HEMBRA"]
    return columnas


# --- Cuadros 4/5: inventario bovino por edad, sexo y orientación de hato ---
# Orden EXACTO de la plantilla (fila 5, Cuadro 4/5): Total, Leche, Cría, Ceba,
# Levante, Doble propósito, Genética. OJO: este orden NO coincide con
# config.ORIENTACION_HATO_ORDEN (ese es el orden que usa el SAS para ORDENAR
# FILAS en cuadros donde la orientación es una dimensión de fila; acá la
# orientación es un bloque de columnas y la propia plantilla de Adriana ya
# trae un orden fijo distinto, que es el que hay que respetar para que el
# formato quede idéntico).
ORIENTACIONES_COLUMNA = ["Ganadería de Leche", "Cría", "Ceba", "Levante", "Doble propósito", "Genética"]
_ORIENTACION_SLUG = {
    "Ganadería de Leche": "leche",
    "Cría": "cria",
    "Ceba": "ceba",
    "Levante": "levante",
    "Doble propósito": "doble_proposito",
    "Genética": "genetica",
}

_BLOQUE_SEXO = [
    ("total", COLUMNAS_TOTAL),
    ("macho", COLUMNAS_MACHO),
    ("hembra_coarse", COLUMNAS_TOTAL),
]


def _columnas_bloque_sexo(prefijo: str) -> list[str]:
    cols = []
    for grupo, tramos in _BLOQUE_SEXO:
        cols.append(f"{prefijo}{grupo}_total")
        cols += [f"{prefijo}{grupo}_{t}" for t in tramos]
    return cols


def _columnas_totales_bloque_sexo() -> dict[str, list[str]]:
    """Consistencia horizontal para `cols_sexo` (total_*/macho_*/hembra_coarse_*,
    ver `agregador.generar_cuadro`) - `hembra_coarse` ya viene con los mismos
    6 tramos de `COLUMNAS_TOTAL` (sin el split 3-5a/+5a que sí tiene
    `_columnas_totales`), así que acá no hace falta ningún caso especial."""
    mapa = {
        "macho_total": [f"macho_{c}" for c in COLUMNAS_MACHO],
        "hembra_coarse_total": [f"hembra_coarse_{c}" for c in COLUMNAS_TOTAL],
        "total_total": ["macho_total", "hembra_coarse_total"],
    }
    for c in COLUMNAS_TOTAL:
        mapa[f"total_{c}"] = [f"macho_{c}", f"hembra_coarse_{c}"]
    return mapa


def value_cols_por_orientacion() -> list[str]:
    """Lista ESTÁTICA de columnas de Cuadro 4/5 (`generar_por_orientacion`),
    sin tocar datos - mismo orden con el que se arma `columnas_finales` ahí
    (bloque "Total" primero, luego un bloque de 21 columnas por cada
    orientación, en `ORIENTACIONES_COLUMNA`). Para uso del validador
    estructural (`validacion_estructura_cuadros.py`), que necesita los
    nombres de columna sin recalcular todo el cuadro."""
    total_cols = ["total_total"] + [f"total_{c}" for c in COLUMNAS_TOTAL]
    cols = [f"blk_total__{c}" for c in total_cols]
    cols_sexo = _columnas_bloque_sexo("")
    for orientacion in ORIENTACIONES_COLUMNA:
        slug = _ORIENTACION_SLUG[orientacion]
        cols += [f"blk_{slug}__{c}" for c in cols_sexo]
    return cols


def columnas_totales_por_orientacion() -> dict[str, list[str]]:
    """`columnas_totales` de Cuadro 4/5 para el validador: dentro de cada
    bloque de orientación, `total_X = macho_X + hembra_coarse_X` (mismo
    `_columnas_totales_bloque_sexo()` que usa `agregador.generar_cuadro` para
    cada orientación en `generar_por_orientacion`). El bloque "blk_total__*"
    NO se declara acá (se reutiliza tal cual de Cuadro 3, no se deriva - ver
    docstring de `generar_por_orientacion`). "Doble propósito" TAMPOCO se
    declara: ahí se absorbe a propósito el residuo de redondeo entre el
    bloque "Total" (fijo, = Cuadro 3) y la suma de las 6 orientaciones (ver
    docstring de `generar_por_orientacion`) - su `total_X` NO es exactamente
    `macho_X+hembra_coarse_X` por diseño, así que no se valida ahí."""
    mapa: dict[str, list[str]] = {}
    base = _columnas_totales_bloque_sexo()
    for orientacion in ORIENTACIONES_COLUMNA:
        if orientacion == "Doble propósito":
            continue
        slug = _ORIENTACION_SLUG[orientacion]
        for destino, fuentes in base.items():
            mapa[f"blk_{slug}__{destino}"] = [f"blk_{slug}__{f}" for f in fuentes]
    return mapa


def generar_por_orientacion(especie: str = "bovinos", ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 4 (Primer ciclo) / Cuadro 5 (Segundo ciclo, misma estructura,
    `ciclo="C2"`): inventario bovino por edad, sexo y orientación del hato
    (pregunta 7/8 del formulario en Ciclo 1, R3 en Ciclo 2). Los predios sin
    orientación reportada se redistribuyen proporcionalmente (ver
    `redistribucion.py`), igual que en el SAS original.

    Devuelve (tabla, value_cols) donde `tabla` ya viene en formato ancho, una
    fila por Nacional/Departamento/Municipio, lista para `excel_writer`.
    """
    from .. import redistribucion

    base = _preparar(especie, incluir_orientacion=True, ciclo=ciclo)

    cols_sexo = _columnas_bloque_sexo("")  # total_*, macho_*, hembra_coarse_*  (21 cols)

    # Bloque "Total inventario bovino" (7 cols, NO se redistribuye por
    # orientación): se reutiliza DIRECTO la tabla de `generar()` (Cuadro 3),
    # no se recalcula por separado - antes se recalculaba con su propio
    # `agregador.generar_cuadro` (mismos datos, pero otra `columnas_totales`
    # / otro conjunto de columnas "hoja" que se redondean), lo que dejaba un
    # residuo de ~62 animales contra Cuadro 3 incluso sin tocar nada más -
    # detectado al corregir el residuo de ~1.808 (ver más abajo). Reusar la
    # MISMA tabla garantiza coincidencia EXACTA con Cuadro 3 por construcción
    # (a pedido del usuario, 2026-09-21).
    total_cols = ["total_total"] + [f"total_{c}" for c in COLUMNAS_TOTAL]
    tabla_total = generar(especie, ciclo=ciclo)[
        ["NIVEL", "COD_DEPARTAMENTO", "DEPARTAMENTO", "CODIGO_MUNICIPIO", "MUNICIPIO"] + total_cols
    ].rename(columns={c: f"blk_total__{c}" for c in total_cols})

    redistribuido = redistribucion.redistribuir_por_categoria(
        base[["CODIGO_MUNICIPIO", "orientacionhato"] + cols_sexo],
        "orientacionhato",
        cols_sexo,
        ORIENTACIONES_COLUMNA,
    )

    columnas_finales = list(tabla_total.columns)
    resultado = tabla_total
    for orientacion in ORIENTACIONES_COLUMNA:
        slug = _ORIENTACION_SLUG[orientacion]
        subset = redistribuido[redistribuido["orientacionhato"] == orientacion]
        tabla_or = agregador.generar_cuadro(
            subset[["CODIGO_MUNICIPIO"] + cols_sexo], cols_sexo, columnas_totales=_columnas_totales_bloque_sexo()
        )
        renombre = {c: f"blk_{slug}__{c}" for c in cols_sexo}
        tabla_or = tabla_or.rename(columns=renombre)
        cols_valor_or = list(renombre.values())
        # Incluimos las llaves de fila para pegar por posición: como ambas tablas
        # se construyeron sobre EL MISMO catálogo territorial (mismo orden de
        # Nacional -> Departamento -> Municipio), es seguro concatenar por índice.
        resultado = pd.concat(
            [resultado.reset_index(drop=True), tabla_or[cols_valor_or].reset_index(drop=True)], axis=1
        )
        columnas_finales += cols_valor_or

    # Consistencia horizontal ENTRE bloques: el bloque "Total inventario
    # bovino" (= Cuadro 3, fijo desde arriba) y los 6 bloques de orientación
    # se redondearon cada uno por separado - antes de redondear son EXACTOS
    # (la redistribución de `redistribucion.py` preserva el total sin
    # pérdida), pero al redondear cada bloque de forma independiente queda
    # un residuo (~1.808 animales / 0.006% a nivel nacional, detectado por
    # el usuario 2026-09-21). Decisión del usuario: el bloque "Total" NO se
    # toca (debe seguir coincidiendo exacto con Cuadro 3, ver arriba) - el
    # residuo se absorbe en "Doble propósito" (la orientación más grande, la
    # que mejor lo diluye proporcionalmente) en vez de en el total. Esto
    # deja una inconsistencia interna PEQUEÑA y aceptada dentro del propio
    # bloque "Doble propósito" (su total_X ya no es EXACTO macho_X+hembra_X,
    # queda desviado por el residuo) - no se puede satisfacer simultáneamente
    # "Total = Cuadro 3", "Total = suma orientaciones" y "cada bloque
    # internamente consistente" con redondeo entero simple.
    slug_absorbe = _ORIENTACION_SLUG["Doble propósito"]
    for c in total_cols:
        otras = [
            resultado[f"blk_{_ORIENTACION_SLUG[o]}__{c}"]
            for o in ORIENTACIONES_COLUMNA
            if o != "Doble propósito"
        ]
        resultado[f"blk_{slug_absorbe}__{c}"] = resultado[f"blk_total__{c}"] - sum(otras)

    value_cols_finales = [c for c in columnas_finales if c not in (
        "NIVEL", "COD_DEPARTAMENTO", "DEPARTAMENTO", "CODIGO_MUNICIPIO", "MUNICIPIO"
    )]
    return resultado, value_cols_finales
