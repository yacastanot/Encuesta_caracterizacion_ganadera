"""Reconstruye el equivalente de `ciclo1encuesta.sas7bdat` para 2024 (Ciclo 1
y Ciclo 2 por separado) - SOLO para el Cuadro 4/5 del libro "ganadero"
("nuevos/salieron/se mantienen" ganaderos respecto al ciclo anterior/al mismo
ciclo del año anterior). Mismo patrón que `preparar_ciclo2encuesta.py`: RUV y
encuesta son 2 archivos separados que hay que unir nosotros, vía `RUV_ID`
(acá sin la confusión de nombre que tuvo Ciclo 2 2025 - ambos archivos ya
traen la columna `RUV_ID` con ese nombre exacto).

A diferencia de Ciclo 2 2025 (un solo RUV para los 2 ciclos + un solo archivo
de encuesta por ciclo, con diccionario de columnas propio), acá:
 - RUV: un solo archivo `ruv.sas7bdat` para los 2 ciclos de 2024 (con columnas
   `CICLO`/`ANIO` para separar), ya con nombres de columna canónicos (mismo
   esquema corto `AFT_BOV_*`/`TOTAL_AFT_BOV` que usa `preparar_base_c1.py`,
   no hace falta ningún diccionario posicional).
 - Encuesta: un archivo POR CICLO (`encuestac1corregida.sas7bdat` /
   `encuestac2_.sas7bdat`, ver `config.py` para por qué se eligió cada uno
   entre varios candidatos).

Solo se conservan las columnas de identificación que necesita Cuadro 4/5
(`CODIGO_SIT`, `IDENT_GANADERO`, `CODIGO_MUNICIPIO`, `TOTAL_AFT_BOV`,
`FECHA_CREACION` - estas 2 últimas para la cascada de desempate de
`preparar_base_c1.deduplicar_predio_ganadero`) - a diferencia de la base
maestra completa de 2025, acá NO hace falta ninguna pregunta de encuesta
(Cuadro 4/5 no desagregan por sexo/tenencia/orientación, solo cuentan
"Total de ganaderos" + su identidad para el cruce entre ciclos).
"""
from __future__ import annotations

import pandas as pd

from . import config, fuente_cruda_historico, preparar_base_c1

_RUTA_ENCUESTA = {1: config.RUTA_2024_ENCUESTA_C1_CRUDO, 2: config.RUTA_2024_ENCUESTA_C2_CRUDO}
_RUTA_CACHE_JOIN = {
    1: config.BASES_CALIBRADAS_DIR / "_cache_2024ciclo1_join.parquet",
    2: config.BASES_CALIBRADAS_DIR / "_cache_2024ciclo2_join.parquet",
}

# La columna `CICLO` de los archivos crudos de 2024 NO usa 1/2 (ciclo
# calendario) - es un contador interno que no se reinicia cada año.
# Verificado (2026-09-24): `ruv.sas7bdat` trae CICLO=2 (757.103 filas) y
# CICLO=3 (753.313 filas) - coinciden EXACTO con las filas de `ruvc1.sas7bdat`/
# `ruvc2.sas7bdat` por separado (metadata ya confirmada, ver `config.py`), y
# `encuestac1corregida.sas7bdat`/`encuestac2_.sas7bdat` traen CICLO=2/CICLO=3
# respectivamente en el 100% de sus filas - consistente con el RUV, no hay
# mezcla ni archivo mal etiquetado. Se traduce acá (ciclo calendario -> valor
# real de la columna) en vez de asumir que "CICLO 1" en el archivo significa
# literalmente 1.
_CICLO_CALENDARIO_A_VALOR_REAL = {1: 2, 2: 3}

_COLS_ID_RUV = [
    "RUV_ID", "CODIGO_SIT", "IDENT_GANADERO", "CODIGO_MUNICIPIO", "CICLO", "ANIO",
    "FECHA_CREACION", "TOTAL_AFT_BOV",
]


def _asegurar_cache_join(ciclo: int) -> None:
    ruta_cache = _RUTA_CACHE_JOIN[ciclo]
    if ruta_cache.exists():
        return

    valor_real = _CICLO_CALENDARIO_A_VALOR_REAL[ciclo]
    print(f"(preparar_historico_2024) armando el join RUV + encuesta 2024 Ciclo {ciclo} (CICLO={valor_real}) - una sola vez...")
    ruv = fuente_cruda_historico.leer(config.RUTA_2024_RUV_CRUDO, columns=_COLS_ID_RUV)
    ruv = ruv[ruv["CICLO"] == valor_real]
    anio_malo = ruv[ruv["ANIO"] != 2024]
    if len(anio_malo):
        raise ValueError(f"{len(anio_malo):,} filas de ruv.sas7bdat con CICLO={valor_real} pero ANIO != 2024 - revisar antes de confiar en este filtro.")

    encuesta = fuente_cruda_historico.leer(_RUTA_ENCUESTA[ciclo], columns=["RUV_ID", "CICLO", "ANIO"])
    ciclo_malo = encuesta[encuesta["CICLO"] != valor_real]
    if len(ciclo_malo):
        raise ValueError(
            f"{_RUTA_ENCUESTA[ciclo].name}: {len(ciclo_malo):,} filas con CICLO != {valor_real} - "
            "no se puede asumir que el archivo viene puro de este ciclo, hay que filtrar explícito."
        )

    n_ruv_id_encuesta = encuesta["RUV_ID"].nunique()
    if n_ruv_id_encuesta != len(encuesta):
        raise ValueError(
            f"encuesta 2024 C{ciclo}: 'RUV_ID' no es único ({n_ruv_id_encuesta:,} de {len(encuesta):,} filas) - "
            "el join dejaría de ser 1 fila por encuesta."
        )
    # Se excluyen los `RUV_ID` nulos del chequeo de unicidad: no representan
    # un duplicado real (2 filas que competirían por el mismo match), sino un
    # predio sin esa llave diligenciada - simplemente nunca hace match en el
    # join (mismo resultado que cualquier otro huérfano del lado RUV, ya
    # esperado, ver `preparar_ciclo2encuesta.py`). Verificado 2026-09-24: en
    # RUV 2024 Ciclo 2 hay exactamente 1 fila así (de 753.313).
    ruv_con_id = ruv[ruv["RUV_ID"].notna()]
    n_ruv_id_ruv = ruv_con_id["RUV_ID"].nunique()
    if n_ruv_id_ruv != len(ruv_con_id):
        raise ValueError(
            f"RUV 2024 C{ciclo}: 'RUV_ID' no es único ({n_ruv_id_ruv:,} de {len(ruv_con_id):,} filas con RUV_ID "
            "no nulo) - el join podría duplicar filas de encuesta (fan-out)."
        )
    huerfanos = set(encuesta["RUV_ID"]) - set(ruv["RUV_ID"])
    pct_huerfanos = len(huerfanos) / len(encuesta)
    if pct_huerfanos > 0.02:
        raise ValueError(
            f"{len(huerfanos):,} valores de RUV_ID en la encuesta 2024 C{ciclo} sin match en el RUV "
            f"({pct_huerfanos:.1%} de {len(encuesta):,} filas, umbral 2%) - demasiado alto para asumir que "
            f"es ruido esperado, ej. {list(huerfanos)[:10]}."
        )
    if huerfanos:
        # A diferencia de Ciclo 2 2025 (join perfecto, 0 huérfanos), acá SÍ
        # aparece un remanente pequeño (verificado 2026-09-24: 5.804/743.939 =
        # 0.78% en Ciclo 1) - `encuestac1corregida.sas7bdat` pasó por varias
        # rondas de corrección (ver `config.py`) y probablemente se corrigió
        # contra un snapshot de RUV ligeramente distinto al que tenemos acá.
        # Se documenta y se descarta (join inner), no se investiga más: este
        # histórico solo sirve de referencia para Cuadro 4/5, no es la fuente
        # de ningún cuadro publicado directamente.
        print(
            f"(preparar_historico_2024) AVISO: {len(huerfanos):,} de {len(encuesta):,} filas "
            f"({pct_huerfanos:.2%}) de la encuesta 2024 C{ciclo} sin match en el RUV - se descartan (join inner)."
        )

    join = encuesta[["RUV_ID"]].merge(ruv, on="RUV_ID", how="inner", validate="one_to_one")
    esperadas = len(encuesta) - len(huerfanos)
    assert len(join) == esperadas, f"el join dio {len(join):,} filas, se esperaban {esperadas:,} (encuesta - huérfanos)."

    join = preparar_base_c1.calcular_predioganid(join)

    ruta_cache.parent.mkdir(parents=True, exist_ok=True)
    join.to_parquet(ruta_cache, index=False)
    print(f"(preparar_historico_2024) caché guardado: {ruta_cache} ({len(join):,} filas)")


def leer(ciclo: int, columns: list[str] | None = None) -> pd.DataFrame:
    _asegurar_cache_join(ciclo)
    return pd.read_parquet(_RUTA_CACHE_JOIN[ciclo], columns=columns)
