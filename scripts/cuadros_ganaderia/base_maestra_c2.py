"""Base calibrada "maestra" de Ciclo 2 2025 (2025-II): mirror exacto de
`base_maestra_c1.py` (misma estructura, mismas 3 fórmulas de peso), pero
construida desde `preparar_base_c2.py`/`preparar_ciclo2encuesta.py` (insumos
crudos reales) en vez de `preparar_base_c1.py`.

Diferencia clave de ALCANCE con Ciclo 1 (confirmado 2026-09-22, leyendo el
texto literal de las 29 preguntas del cuestionario real de C2 - ver
`config.RENOMBRE_PREGUNTAS_C2`): el cuestionario de Ciclo 2 NO tiene
preguntas equivalentes a `edadganadero`, `canttrabaj`, `sistemaproductivo`,
`conformacion`, `intcarrera`, `menores18`, `tienecolmenas`/`numcolmenas` - las
sustituyó por preguntas nuevas (razas, área/cobertura de suelo, área
protegida, medios de comunicación). Por eso `_COLS_ENCUESTA_MASTER_C2` NO es
un subconjunto/superconjunto trivial de `base_maestra_c1._COLS_ENCUESTA_MASTER`:
se reconstruyó completo a partir de lo que SÍ existe en C2.

**Importante para las fases siguientes**: como no existe `sistemaproductivo`
en C2, NINGÚN cuadro que dependa de "sistema productivo implementado en el
predio" tiene equivalente en Ciclo 2 - esto incluye Cuadro 6 del libro
inventario y Cuadro 6/7/8/10 del libro predio-ganadero (a diferencia de lo ya
identificado antes, que solo cubría Cuadro 5/13/14 de predio-ganadero y
Cuadro 16 de ganadero). Confirmar con el usuario antes de la Fase 6.

Igual que `base_maestra_c1.py`: `cal_bovinos`/`cal_bufalinos` se calculan en
`calibracion_bovinos_bufalinos_c2.py` pero esta tabla todavía no los usa.
"""
from __future__ import annotations

import pandas as pd

from . import config, preparar_base_c1, preparar_base_c2

# Preguntas de Ciclo 2 que SÍ existen (confirmadas contra `config.RENOMBRE_PREGUNTAS_C2`
# - ver docstring del módulo para las que NO existen). Incluye tanto las que
# tienen equivalente en C1 (compartelote, delitos, etc.) como las genuinamente
# nuevas de C2 (razas, área/cobertura, área protegida, medios de comunicación)
# que hacen falta para los Cuadros 15-19 de predio-ganadero (Fase 6).
_COLS_ENCUESTA_MASTER_C2 = [
    "orientacionhato", "compartelote", "atendioencuesta", "lugarresidencia",
    "consensorepidem", "conalertatem", "debenotificarica", "signosclinicos",
    "promliterosdiarios", "preciolitro",
    "tienerazapura", "tienerazacruce", "razapurapredominante", "otrarazapuracual",
    "razacrucepredominante", "otrarazacrucecual",
    "unidadmedidaarea", "areatotalfinca", "areaagricola", "areaproducanimales",
    "areaforestal", "areaconstrucciones", "areaotrosusos", "areaganaderiabovbuf",
    "areaprotegida",
] + [
    "abigeato", "carneo", "extorsion", "hurto", "invasiontierra", "secuestro", "otro", "ninguno", "cualotrodelito",
] + [f"medio_comunicacion_{i}" for i in range(1, 7)]

RUTA_BASE_MAESTRA_C2 = config.BASES_CALIBRADAS_DIR / "base_maestra_C2_2025.parquet"


def _cargar_especie_dedup(columnas_encuesta_extra: list[str] | None = None) -> pd.DataFrame:
    df = preparar_base_c2.cargar_base_ganadero_c2(columnas_encuesta_extra=columnas_encuesta_extra)
    return preparar_base_c2.deduplicar_predio_ganadero_c2(df)


def construir_base_maestra_c2() -> pd.DataFrame:
    """A diferencia de `base_maestra_c1.construir_base_maestra_c1` (que carga
    bovinos y bufalinos por separado porque `preparar_base_c1.cargar_base_cruda`
    pide columnas AFT_* específicas de cada especie), acá
    `cargar_base_ganadero_c2` ya trae `TOTAL_AFT_BOV`/`TOTAL_AFT_BUF` (+ sus
    `_NV`) en una sola pasada (ambos vienen en `_COLS_ID_C2`) - no hace falta
    una segunda carga+merge por bufalinos."""
    maestra = _cargar_especie_dedup(columnas_encuesta_extra=_COLS_ENCUESTA_MASTER_C2)

    # Reutiliza `preparar_base_c1.normalizar_categoricas` tal cual - opera
    # sobre nombres de columna canónicos (GENERO/orientacionhato/PREDIO_CARGO)
    # y diccionarios de `config.py` que no dependen del ciclo (mismas
    # variantes de texto "HOMBRE"/"Hombre"/nulo->jurídica en los 2 ciclos).
    maestra = preparar_base_c1.normalizar_categoricas(maestra)

    conteo_predios_ganadero = maestra.groupby("IDENT_GANADERO")["predioganid"].transform("count").fillna(1)
    maestra["conteo_predios_ganadero"] = conteo_predios_ganadero

    factor = pd.read_csv(
        config.RUTA_FACTOR_GANADERO_C2, sep=";", decimal=",", encoding="utf-8-sig", dtype={"CODIGO_MUNICIPIO": str}
    )
    factor["CODIGO_MUNICIPIO"] = factor["CODIGO_MUNICIPIO"].str.zfill(5)
    maestra = maestra.merge(factor, on="CODIGO_MUNICIPIO", how="left")
    maestra["cal_cobertura"] = maestra["cal_cobertura"].fillna(1.0)
    maestra["calruv"] = maestra["calruv"].fillna(1.0)
    maestra["cal_predios"] = maestra["cal_predios"].fillna(1.0)

    maestra["peso_ganadero"] = (1.0 / conteo_predios_ganadero) * maestra["cal_cobertura"]
    maestra["peso_predio_ganadero"] = maestra["calruv"] * maestra["cal_cobertura"]

    conteo_ganaderos_por_predio = maestra.groupby("CODIGO_SIT")["predioganid"].transform("count").fillna(1)
    maestra["conteo_ganaderos_por_predio"] = conteo_ganaderos_por_predio
    maestra["peso_predio_fisico"] = (1.0 / conteo_ganaderos_por_predio) * maestra["cal_predios"]

    return maestra


def generar_y_guardar_c2() -> None:
    maestra = construir_base_maestra_c2()
    print(f"Filas (predio-ganadero únicos): {len(maestra):,}")
    print(f"Ganaderos únicos (por IDENT_GANADERO): {maestra['IDENT_GANADERO'].nunique():,}")
    print(f"Suma peso_ganadero (ganaderos únicos * cal_cobertura, no es 1:1 exacto): {maestra['peso_ganadero'].sum():,.1f}")
    print(f"Predios con >1 registro por ganadero: {(maestra['conteo_predios_ganadero'] > 1).sum():,}")

    RUTA_BASE_MAESTRA_C2.parent.mkdir(parents=True, exist_ok=True)
    maestra.to_parquet(RUTA_BASE_MAESTRA_C2, index=False)
    print(f"Guardado: {RUTA_BASE_MAESTRA_C2}")


if __name__ == "__main__":
    generar_y_guardar_c2()
