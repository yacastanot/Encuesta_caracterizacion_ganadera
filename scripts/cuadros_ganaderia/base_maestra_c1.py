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

Tres pesos, tres unidades de conteo distintas (ver `4.2`/`4.3` y
`validacion_totales_cuadro1_c1.py`):
 - `peso_ganadero` = (1 / cantidad de predios del mismo IDENT_GANADERO) * cal_cobertura.
   Evita que un ganadero con predios en varios municipios cuente más de una
   vez a nivel nacional, repartiéndolo proporcionalmente entre sus municipios.
   Se agrupa por IDENT_GANADERO (número de identificación real), NO por
   GANADERO_ID (id interno del RUV): hay 13 casos donde el mismo documento
   tiene 2 GANADERO_ID distintos. Solo para cuadros que cuentan GANADEROS
   (personas).
 - `peso_predio_ganadero` = calruv * cal_cobertura. Para "Total predios
   ganaderos" (`COUNT(DISTINCT predioganid) * peso_predio_ganadero`) - cuenta
   PARES predio-ganadero (relaciones), no predios físicos: un mismo predio
   con 2 ganaderos registrados cuenta 2 veces. Réplica fiel de `4.2`/`4.3`
   (que usan la misma fórmula para "totalpredios" y "totalprediosgan").
 - `peso_predio_fisico` = (1 / cantidad de ganaderos del mismo CODIGO_SIT) *
   cal_predios. Para "Total predios" (predios FÍSICOS, no pares
   predio-ganadero) - agregado 2026-09-18 al confirmar que replicar la
   fórmula del SAS para "Total predios" (usando `peso_predio_ganadero`, igual
   que "Total predios ganaderos") sobreestimaba ~+25% frente al "Total
   Predios PM" de Fedegán: la brecha coincidía casi exacto con la diferencia
   entre nunique(predioganid) y nunique(CODIGO_SIT) (ambas +~25%). Mismo
   patrón de reparto que `peso_ganadero`, pero por predio en vez de por
   ganadero.

`cal_cobertura`, `calruv`, `cal_predios` (`cal_bovinos`/`cal_bufalinos` que
esta tabla todavía no usa) se recalculan de forma independiente a partir de
las bases crudas - ya NO se heredan directo de los Excel originales de
Carolina. Ver `calibracion_ganadero_c1.py` y los módulos
`calibracion_calruv_c1.py`/`calibracion_predios_c1.py`/
`calibracion_bovinos_bufalinos_c1.py`/`calibracion_cobertura_c1.py`.

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

from . import config, preparar_base_c1

_COLS_ENCUESTA_MASTER = [
    "edadganadero", "orientacionhato", "canttrabaj", "sistemaproductivo", "compartelote", "R1", "R2",
    "consensorepidem", "conalertatem", "debenotificarica", "signosclinicos", "conformacion", "intcarrera",
    "menores18", "tienecolmenas", "numcolmenas",
] + [
    "abigeato", "carneo", "extorsion", "hurto", "invasiontierra", "secuestro", "otro", "ninguno",
]

RUTA_BASE_MAESTRA_C1 = config.BASES_CALIBRADAS_DIR / "base_maestra_C1_2025.parquet"


def _cargar_especie_dedup(especie: str, columnas_encuesta_extra: list[str] | None = None) -> pd.DataFrame:
    columnas_inv = preparar_base_c1.columnas_inventario(especie)
    columnas_extra = columnas_inv + list(columnas_encuesta_extra or [])
    df = preparar_base_c1.cargar_base_cruda(especie, columnas_extra=columnas_extra)
    df = preparar_base_c1.aplicar_factor_calibracion(df, especie, columnas_inv)
    return preparar_base_c1.deduplicar_predio_ganadero(df)


def construir_base_maestra_c1() -> pd.DataFrame:
    """Bovinos aporta identificación/territorio/encuesta (idénticos entre
    especies, se toman de una sola fuente); bufalinos solo aporta sus propias
    columnas de inventario animal, que bovinos no trae."""
    bov = _cargar_especie_dedup("bovinos", columnas_encuesta_extra=_COLS_ENCUESTA_MASTER)
    bov = preparar_base_c1.renombrar_preguntas(bov)
    bov = preparar_base_c1.normalizar_categoricas(bov)

    # "TOTAL_AFT_BUF" (+ su propia "_NV", auto-incluida): igual que
    # "TOTAL_AFT_BOV" ya trae bovinos vía `_COLS_ID` - hace falta para el
    # Cuadro 3 del libro predio-ganadero ("con bovinos"/"con bufalinos"/"con
    # ambos"), ver `cuadros/predio_ganadero.py`.
    buf = _cargar_especie_dedup("bufalinos", columnas_encuesta_extra=["TOTAL_AFT_BUF"])
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

    factor = pd.read_csv(
        config.RUTA_FACTOR_GANADERO_C1, sep=";", decimal=",", encoding="utf-8-sig", dtype={"CODIGO_MUNICIPIO": str}
    )
    factor["CODIGO_MUNICIPIO"] = factor["CODIGO_MUNICIPIO"].str.zfill(5)
    maestra = maestra.merge(factor, on="CODIGO_MUNICIPIO", how="left")
    maestra["cal_cobertura"] = maestra["cal_cobertura"].fillna(1.0)
    maestra["calruv"] = maestra["calruv"].fillna(1.0)
    maestra["cal_predios"] = maestra["cal_predios"].fillna(1.0)

    maestra["peso_ganadero"] = (1.0 / conteo_predios_ganadero) * maestra["cal_cobertura"]
    maestra["peso_predio_ganadero"] = maestra["calruv"] * maestra["cal_cobertura"]

    # `peso_predio_ganadero` pesa PARES predio-ganadero (predioganid), no
    # predios físicos: si un mismo CODIGO_SIT tiene 2 ganaderos registrados,
    # cuenta ese predio 2 veces - eso es correcto para "Total predios
    # ganaderos" (cuenta relaciones, no parcelas), pero NO reconcilia con
    # "Total Predios PM" de Fedegán, que sí cuenta predios físicos únicos
    # (confirmado: la brecha de +24,96% entre nunique(predioganid) y
    # nunique(CODIGO_SIT) explica casi exacto la brecha de +24,97% que había
    # entre el Cuadro 1 y Fedegán - ver `validacion_totales_cuadro1_c1.py`).
    #
    # `peso_predio_fisico` es el equivalente de `peso_predio_ganadero` pero
    # para "Total predios" (predios físicos, reconciliado con Fedegán vía
    # `cal_predios` - ver `calibracion_predios_c1.py`): se reparte el peso de
    # cada predio físico entre sus N ganaderos registrados (mismo patrón que
    # `peso_ganadero`/`conteo_predios_ganadero` para no contar de más), así
    # que sumar `peso_predio_fisico` por predioganid da el conteo de predios
    # FÍSICOS, no de pares predio-ganadero.
    conteo_ganaderos_por_predio = maestra.groupby("CODIGO_SIT")["predioganid"].transform("count").fillna(1)
    maestra["conteo_ganaderos_por_predio"] = conteo_ganaderos_por_predio
    maestra["peso_predio_fisico"] = (1.0 / conteo_ganaderos_por_predio) * maestra["cal_predios"]

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
