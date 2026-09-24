"""Cuadro 1 y Cuadro 2: idénticos en los 3 libros de publicación (inventario,
ganadero, predio-ganadero) - se calculan una sola vez acá y se escriben en
cada libro.

Cuadro 1 - "Cantidad de predios, ganaderos y predios ganaderos": el SAS
original (`Programas Carolina/4.3. cuadros predio ganadero.sas`, líneas
607-765) usa `count(distinct predioganid) * calruv * cal_cobertura` para
"totalpredios" Y "totalprediosgan" por igual - es decir, TRATA "Total
predios" y "Total predios ganaderos" como la misma cantidad, contando PARES
predio-ganadero. Se detectó (validado contra Fedegán, ver
`validacion_totales_cuadro1_c1.py`) que replicar eso literalmente sobreestima
"Total predios" ~+25% frente al "Total Predios PM" de Fedegán, porque cuenta
2 veces cualquier predio con 2 ganaderos registrados - Fedegán mide predios
FÍSICOS, no relaciones predio-ganadero. Decisión del usuario (2026-09-18):
separar las 2 columnas en sus unidades reales:
 - "Total predios" = `peso_predio_fisico` (predios físicos, reconciliado
   exacto con Fedegán vía `cal_predios` - ver `base_maestra_c1.py`).
 - "Total predios ganaderos" = `peso_predio_ganadero` (pares predio-ganadero,
   como en el SAS original - sin comparación directa posible con Fedegán, que
   no reporta esa unidad).
"Total ganaderos" usa `peso_ganadero` (también en `base_maestra_c1`) - la
única diferencia frente al SAS original (`4.2. cuadros ganadero.sas`, líneas
328-342) es que ahí se agrupa por `GANADERO_ID` (id interno RUV) y acá por
`IDENT_GANADERO` (documentado en `base_maestra_c1.py`: 13 casos con el mismo
documento bajo 2 `GANADERO_ID` distintos - mejora deliberada, no un descuido).

Columnas E-G = Ciclo 1, H-J = Ciclo 2 (misma fórmula, `base_maestra_c2`) -
parametrizado por `ciclo` igual que `cuadros/inventario.py`.

Columnas K-N ("Total predios/ganaderos/predios ganaderos/animales NUEVOS",
ver `generar_cuadro1_nuevos`): predios/ganaderos/pares que aparecen en Ciclo
2 pero NO en Ciclo 1 - 3 IDENTIDADES DISTINTAS (predio físico `CODIGO_SIT`,
ganadero `IDENT_GANADERO`, par `predioganid`), cada una comparada por
separado contra su propio universo de C1, no basta con "predioganid nuevo"
para las 3. "Total de animales en los predios nuevos" = suma de
`TOTAL_AFT_BOV(+_NV)`/`TOTAL_AFT_BUF(+_NV)` en esos predios físicos nuevos,
SIN calibrar (`base_maestra` no trae esas columnas calibradas por F_AJUSTA_*,
ver docstring de `base_maestra_c1.py`) - es un recuento informativo, NO
comparable con el "Total bovinos"/"Total bufalinos" de Cuadro 3/7 de
inventario (esos sí están calibrados).

OJO - hallazgo verificado 2026-09-22 antes de calcular esto: `CODIGO_SIT`/
`IDENT_GANADERO`/`predioganid` vienen en TIPOS DISTINTOS entre C1 (`float`,
que al convertir a texto arrastra ".0": `predioganid` = "100008.091300457.0")
y C2 (ya texto limpio: "15623460015199222") - comparar sin normalizar daba
100% de `IDENT_GANADERO`/`predioganid` como "nuevos" en C2 (falso positivo
total, detectado ANTES de confiar en el resultado, no asumido). Se normalizan
ambos lados a texto de entero limpio antes de comparar.

Cuadro 2 - "Municipios sin información asociada": columna E = Observación
Ciclo 1 (`config.RAZON_EXCLUSION_C1`), columna F = Observación Ciclo 2
(`config.RAZON_EXCLUSION_C2`) - la lista de municipios es la UNIÓN de los 2
ciclos (un municipio excluido solo en uno de los 2 queda con la otra columna
en blanco, no con las 2). Confirmado contra el SAS original que los 8 de
<80% cobertura de C1 son excluidos idéntico (`4.2. cuadros ganadero.sas`
línea 313: `municipio_id not in (43, 185, 822, 826, 829, 833, 843, 848)`); el
resto (ZLSV/"o.c." + encuestas repetidas, en los 2 ciclos) son exclusiones
nuevas que el SAS original no tenía (ver `config.py`).
"""
from __future__ import annotations

import pandas as pd

from .. import agregador, base_maestra_c1, base_maestra_c2, catalogo_territorial, config

_RUTA_BASE_MAESTRA = {"C1": base_maestra_c1.RUTA_BASE_MAESTRA_C1, "C2": base_maestra_c2.RUTA_BASE_MAESTRA_C2}


def generar_cuadro1(ciclo: str = "C1") -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 1: Total predios / Total ganaderos / Total predios ganaderos.
    `ciclo="C1"` llena E-G, `ciclo="C2"` llena H-J (columnas "nuevos" K-N
    pendientes, ver docstring del módulo)."""
    maestra = pd.read_parquet(_RUTA_BASE_MAESTRA[ciclo])

    agg = maestra.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_predios=("peso_predio_fisico", "sum"),
        total_ganaderos=("peso_ganadero", "sum"),
        total_predios_ganaderos=("peso_predio_ganadero", "sum"),
    )

    value_cols = ["total_predios", "total_ganaderos", "total_predios_ganaderos"]
    tabla = agregador.generar_cuadro(agg, value_cols)
    return tabla, value_cols


def _ids_c1_normalizados() -> tuple[set[str], set[str], set[str]]:
    """`(CODIGO_SIT, IDENT_GANADERO, predioganid)` de C1 como texto de
    entero limpio (ver docstring del módulo - C1 los guarda como `float`,
    que arrastra ".0" al convertir a texto directo)."""
    m1 = pd.read_parquet(base_maestra_c1.RUTA_BASE_MAESTRA_C1, columns=["CODIGO_SIT", "IDENT_GANADERO"])
    codigo_sit = pd.to_numeric(m1["CODIGO_SIT"]).astype("Int64").astype(str)
    ident_ganadero = pd.to_numeric(m1["IDENT_GANADERO"]).astype("Int64").astype(str)
    predioganid = codigo_sit + ident_ganadero
    return set(codigo_sit), set(ident_ganadero), set(predioganid)


def generar_cuadro1_nuevos() -> tuple[pd.DataFrame, list[str]]:
    """Cuadro 1, columnas K-N ("... nuevos") - ver docstring del módulo."""
    codigo_sit_c1, ident_ganadero_c1, predioganid_c1 = _ids_c1_normalizados()

    m2 = pd.read_parquet(
        base_maestra_c2.RUTA_BASE_MAESTRA_C2,
        columns=[
            "CODIGO_MUNICIPIO", "CODIGO_SIT", "IDENT_GANADERO", "predioganid",
            "peso_predio_fisico", "peso_ganadero", "peso_predio_ganadero",
            "TOTAL_AFT_BOV", "TOTAL_AFT_BOV_NV", "TOTAL_AFT_BUF", "TOTAL_AFT_BUF_NV",
        ],
    ).copy()

    es_predio_nuevo = ~m2["CODIGO_SIT"].astype(str).isin(codigo_sit_c1)
    es_ganadero_nuevo = ~m2["IDENT_GANADERO"].astype(str).isin(ident_ganadero_c1)
    es_predioganid_nuevo = ~m2["predioganid"].isin(predioganid_c1)
    m2["total_animales"] = (
        m2["TOTAL_AFT_BOV"].fillna(0) + m2["TOTAL_AFT_BOV_NV"].fillna(0)
        + m2["TOTAL_AFT_BUF"].fillna(0) + m2["TOTAL_AFT_BUF_NV"].fillna(0)
    )

    def _suma(filtro: pd.Series, col_peso: str, col_nueva: str) -> pd.DataFrame:
        return (
            m2[filtro]
            .groupby("CODIGO_MUNICIPIO", as_index=False)[col_peso]
            .sum()
            .rename(columns={col_peso: col_nueva})
        )

    agg = m2[["CODIGO_MUNICIPIO"]].drop_duplicates()
    for filtro, col_peso, col_nueva in [
        (es_predio_nuevo, "peso_predio_fisico", "predios_nuevos"),
        (es_ganadero_nuevo, "peso_ganadero", "ganaderos_nuevos"),
        (es_predioganid_nuevo, "peso_predio_ganadero", "predios_ganaderos_nuevos"),
        (es_predio_nuevo, "total_animales", "animales_predios_nuevos"),
    ]:
        agg = agg.merge(_suma(filtro, col_peso, col_nueva), on="CODIGO_MUNICIPIO", how="left")

    value_cols = ["predios_nuevos", "ganaderos_nuevos", "predios_ganaderos_nuevos", "animales_predios_nuevos"]
    for c in value_cols:
        agg[c] = agg[c].fillna(0.0)

    # SIN `columnas_totales`: las 4 columnas son universos/pesos distintos
    # (ver docstring del módulo), no tiene sentido que una sea "suma" de otra.
    tabla = agregador.generar_cuadro(agg, value_cols)
    return tabla, value_cols


def generar_cuadro2() -> pd.DataFrame:
    """Cuadro 2: listado plano (sin jerarquía Nacional/Departamento) de la
    UNIÓN de `config.MUNICIPIOS_EXCLUIDOS_C1`/`_C2`, con la razón real de
    cada exclusión en columnas separadas por ciclo ("Observacion_C1"/
    "Observacion_C2" - `None`, no NaN, cuando ese municipio no se excluyó en
    ese ciclo en particular, para que la celda quede en blanco al escribir)."""
    divipola = catalogo_territorial.cargar_catalogo_municipios()
    todos_excluidos = sorted(set(config.MUNICIPIOS_EXCLUIDOS_C1) | set(config.MUNICIPIOS_EXCLUIDOS_C2))
    sub = divipola[divipola["CODIGO_MUNICIPIO"].isin(todos_excluidos)].copy()
    sub["Observacion_C1"] = sub["CODIGO_MUNICIPIO"].map(config.RAZON_EXCLUSION_C1)
    sub["Observacion_C2"] = sub["CODIGO_MUNICIPIO"].map(config.RAZON_EXCLUSION_C2)
    # `.map` deja `float('nan')` (no `None`) donde no hubo match - se reemplaza
    # explícito por columna (`.where`/`.mask` a nivel de DataFrame completo no
    # lo hacía de forma confiable, verificado) para que `excel_writer` escriba
    # la celda realmente en blanco, no el texto "nan".
    for col in ("Observacion_C1", "Observacion_C2"):
        sub[col] = sub[col].astype(object)
        sub.loc[sub[col].isna(), col] = None
    return sub.sort_values(["COD_DEPARTAMENTO", "CODIGO_MUNICIPIO"]).reset_index(drop=True)
