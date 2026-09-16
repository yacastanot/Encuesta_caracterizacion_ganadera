"""Base calibrada "maestra" de un ciclo: una fila por predio-ganadero
(`predioganid`, ya deduplicado), con el inventario animal calibrado (bovino +
bufalino) y los pesos de conteo que usan los cuadros de "ganadero" y
"predio-ganadero" (`Programas Carolina/4.2.../4.3...`).

Por qué una tabla única: hoy cada familia de cuadros (inventario / ganadero /
predio-ganadero) repetía su propia carga + dedup + normalización desde el CSV
crudo. Bovinos y bufalinos de Ciclo 1 son, verificado con los datos reales, EL
MISMO universo de predios (745.993 `predioganid` únicos en los dos archivos,
100% de traslape en ambos sentidos) - por eso se pueden unir en una sola fila
sin perder ni duplicar predios.

Dos pesos, dos unidades de conteo distintas (ver `4.2`/`4.3`):
 - `peso_ganadero` = (1 / cantidad de predios del mismo IDENT_GANADERO) * cal_cobertura.
   Evita que un ganadero con predios en varios municipios cuente más de una
   vez a nivel nacional, repartiéndolo proporcionalmente entre sus municipios.
   Se agrupa por IDENT_GANADERO (número de identificación real), NO por
   GANADERO_ID (id interno del RUV): hay 13 casos donde el mismo documento
   tiene 2 GANADERO_ID distintos. Solo para cuadros que cuentan GANADEROS
   (personas).
 - `peso_predio_ganadero` = calruv * cal_cobertura. Para cuadros que cuentan
   PREDIOS-GANADERO (`COUNT(DISTINCT predioganid) * peso_predio_ganadero`) -
   no necesita el 1/conteo porque cada predio-ganadero ya vive en un solo
   municipio.

`cal_cobertura` y `calruv` ya NO son estimados: el usuario encontró los 2
Excel originales de Carolina (`Programas Carolina/calibraencuestac1.xlsx` y
`calibrac12025.xlsx`) y se usan directo - ver `calibracion_ganadero_c1.py`.

Los códigos centinela 99999/88888/44444 (`ajustar_valores_municipios`) también
quedaron resueltos: el usuario encontró `Divipola/divipola_mpio.sas7bdat` (la
misma tabla que usaba el SAS), lo que permitió reconstruir el `municipio_id`
interno por fórmula y traducir las 3 listas a CODIGO_MUNICIPIO real - ver
`crosswalk_municipio_id_c1.py`. Esta base todavía NO les aplica el código
centinela (queda para cuando se escriban los cuadros de ganadero/predio-ganadero
que los necesiten); la traducción ya está guardada y lista en
`config.RUTA_MUNICIPIOS_CENTINELA_C1`.
"""
from __future__ import annotations

import pandas as pd

from . import config, preparar_base

_COLS_ENCUESTA_MASTER = ["R4", "R7", "R10", "R11"] + [f"R6_{i}" for i in range(1, 9)]

RUTA_BASE_MAESTRA_C1 = config.BASES_CALIBRADAS_DIR / "base_maestra_C1_2025.parquet"


def _cargar_especie_dedup(especie: str, columnas_encuesta_extra: list[str] | None = None) -> pd.DataFrame:
    columnas_inv = preparar_base.columnas_inventario(especie)
    columnas_extra = columnas_inv + list(columnas_encuesta_extra or [])
    df = preparar_base.cargar_base_cruda(especie, columnas_extra=columnas_extra)
    df = preparar_base.aplicar_factor_calibracion(df, especie, columnas_inv)
    return preparar_base.deduplicar_predio_ganadero(df)


def construir_base_maestra_c1() -> pd.DataFrame:
    """Bovinos aporta identificación/territorio/encuesta (idénticos entre
    especies, se toman de una sola fuente); bufalinos solo aporta sus propias
    columnas de inventario animal, que bovinos no trae."""
    bov = _cargar_especie_dedup("bovinos", columnas_encuesta_extra=_COLS_ENCUESTA_MASTER)
    bov = preparar_base.renombrar_preguntas(bov)
    bov = preparar_base.normalizar_categoricas(bov)

    buf = _cargar_especie_dedup("bufalinos")
    columnas_solo_buf = ["predioganid"] + [c for c in buf.columns if c not in bov.columns]

    maestra = bov.merge(buf[columnas_solo_buf], on="predioganid", how="outer", validate="one_to_one")

    # Se agrupa por IDENT_GANADERO (número de identificación, la identidad real
    # de la persona/empresa) y NO por GANADERO_ID (id interno del RUV): son casi
    # siempre lo mismo, pero hay 13 IDENT_GANADERO con 2 GANADERO_ID internos
    # distintos - agrupar por GANADERO_ID subcontaría a esas 13 personas como 2
    # ganaderos en vez de 1.
    # 1 fila (de 745.993) no trae IDENT_GANADERO -> queda fuera de cualquier
    # grupo y el conteo da NaN; se trata como conteo=1 (sin reducir su peso)
    # en vez de propagar NaN a peso_ganadero.
    conteo_predios_ganadero = maestra.groupby("IDENT_GANADERO")["predioganid"].transform("count").fillna(1)
    maestra["conteo_predios_ganadero"] = conteo_predios_ganadero

    factor = pd.read_csv(config.RUTA_FACTOR_GANADERO_C1, sep=";", decimal=",", dtype={"CODIGO_MUNICIPIO": str})
    factor["CODIGO_MUNICIPIO"] = factor["CODIGO_MUNICIPIO"].str.zfill(5)
    maestra = maestra.merge(factor, on="CODIGO_MUNICIPIO", how="left")
    maestra["cal_cobertura"] = maestra["cal_cobertura"].fillna(1.0)
    maestra["calruv"] = maestra["calruv"].fillna(1.0)

    maestra["peso_ganadero"] = (1.0 / conteo_predios_ganadero) * maestra["cal_cobertura"]
    maestra["peso_predio_ganadero"] = maestra["calruv"] * maestra["cal_cobertura"]

    return maestra


def generar_y_guardar_c1() -> None:
    maestra = construir_base_maestra_c1()
    print(f"Filas (predio-ganadero únicos): {len(maestra):,}")
    print(f"Ganaderos únicos (por IDENT_GANADERO): {maestra['IDENT_GANADERO'].nunique():,}")
    print(f"Suma peso_ganadero (ganaderos únicos * cal_cobertura, no es 1:1 exacto): {maestra['peso_ganadero'].sum():,.1f}")
    print(f"Predios con >1 registro por ganadero: {(maestra['conteo_predios_ganadero'] > 1).sum():,}")

    RUTA_BASE_MAESTRA_C1.parent.mkdir(parents=True, exist_ok=True)
    maestra.to_parquet(RUTA_BASE_MAESTRA_C1, index=False)
    print(f"Guardado: {RUTA_BASE_MAESTRA_C1}")


if __name__ == "__main__":
    generar_y_guardar_c1()
