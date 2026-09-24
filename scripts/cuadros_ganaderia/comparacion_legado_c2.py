r"""Comparación de CONTRASTE (nunca de fuente) entre el pipeline propio de
Ciclo 2 y las bases ya calibradas del pipeline legado en R
(`\\systema20\MUESTRAS\Agropecuarias\RUV_ECG\01Entrada\2025 II\`) - Fase 8
del plan de reconstrucción de Ciclo 2. Ninguno de los archivos que lee este
módulo se usó como fuente de ningún cálculo del pipeline (ver docstring de
`preparar_ciclo2encuesta.py`/`calibracion_c2.py`) - se copiaron localmente a
`01Entrada/2025 II/_solo_comparar/` únicamente para este contraste, siguiendo
la regla explícita del usuario de no escribir nunca en `S:\`.

Archivos copiados y su rol acá:
 - `base_ruv_calibrada_C2_2025.csv` (996 MB, 740.652 filas, separador ";"):
   universo RUV con inventario bovino calibrado fila a fila por el pipeline
   legado (`F_AJUSTA_BOVINOS`, columnas `*_CAL`). NO calibra bufalinos (no
   trae columnas `F_AJUSTA_BUFALINOS`/`*_CAL` para esa especie) ni trae
   `cal_predios`/`cal_cobertura`/`calruv` (calibración a nivel ganadero) - su
   alcance es solo el inventario bovino.
 - `Consolidado_ECG_Nacional_Ciclo2_2025.xlsx` (4.9 MB): pese al nombre, NO
   es un consolidado nacional completo - su hoja `ECG_Nacional_Completo`
   trae solo 11.000 filas y `Verificación_RUV_vs_ECG` solo 13.057 (vs. las
   736.149 respuestas reales de `ExportarArchivoEncuesta2_2025.csv`) - es un
   extracto parcial (una coordinación o un lote de QA), no sirve para un
   contraste a nivel nacional y NO se usa en este módulo.

HALLAZGO 1 - `F_AJUSTA_BOVINOS`/`*_CAL` de `base_ruv_calibrada_C2_2025.csv`
están corruptos (confirmado, no una sospecha): el factor trae valores como
1.0023e14 u 8.7507e14 en vez de un número cercano a 1 - el mismo patrón de
corrupción ya documentado en `calibracion_c1.py`/`calibracion_c2.py` para el
CSV heredado de Ciclo 1/2 ("el valor corrupto 8.75e14 del CSV heredado que
motivó este módulo"), reproducido acá con evidencia nueva de Ciclo 2: el
máximo real de `F_AJUSTA_BOVINOS` en este archivo es exactamente 8.750704e14.
Esto confirma - con un archivo que el usuario nunca había mirado en esta
sesión - que la instrucción de reconstruir Ciclo 2 desde cero sin heredar
ningún factor ya calculado fue la decisión correcta: cualquier cuadro que
hubiera usado las columnas `*_CAL` de este archivo habría heredado el mismo
bug. La columna cruda SIN calibrar (`TOTAL AFTOSA BOVINOS`) sí es utilizable
y es la que se usa abajo.

HALLAZGO 2 - universo RUV crudo (sin calibrar), propio vs. legado: mismo
orden de magnitud, diferencias de ~0.6-1.3% explicables por que ambos
extractos de `ExportarArchivoRuv.csv` no son necesariamente el mismo
snapshot exacto (el nuestro copiado 2026-09-22, fecha de archivo 2025-06-02;
el legado calibrado generado 2025-08-25, pudo re-extraerse el RUV en esa
fecha con registros nuevos/depurados) - documentado, no se intenta forzar a
cero (ver `_validar` para las cifras exactas).

Uso:
    python -m scripts.cuadros_ganaderia.comparacion_legado_c2
"""
from __future__ import annotations

import pandas as pd

from . import config, preparar_ciclo2encuesta

RUTA_LEGADO_RUV_CALIBRADO_C2 = config.BASE_DIR / "01Entrada" / "2025 II" / "_solo_comparar" / "base_ruv_calibrada_C2_2025.csv"

_COLS_LEGADO = [
    "CODIGO SIT", "CODIGO MUNICIPIO", "F_AJUSTA_BOVINOS", "TOTAL AFTOSA BOVINOS_CAL",
    "TOTAL AFTOSA BOVINOS", "TOTAL AFTOSA BOVINOS NV", "TOTAL AFTOSA BUFALINOS", "TOTAL AFTOSA BUFALINOS NV",
]


def _leer_legado() -> pd.DataFrame:
    return pd.read_csv(
        RUTA_LEGADO_RUV_CALIBRADO_C2, sep=";", usecols=_COLS_LEGADO, encoding="utf-8-sig",
        low_memory=False, decimal=",",
    )


def _resumen_propio() -> dict:
    df = preparar_ciclo2encuesta.leer_ruv_completo(
        columns=["CODIGO_SIT", "CODIGO_MUNICIPIO", "TOTAL_AFT_BOV", "TOTAL_AFT_BOV_NV", "TOTAL_AFT_BUF", "TOTAL_AFT_BUF_NV"]
    )
    return {
        "filas": len(df),
        "predios_unicos": df["CODIGO_SIT"].nunique(),
        "municipios_unicos": df["CODIGO_MUNICIPIO"].nunique(),
        "bovinos_raw": df["TOTAL_AFT_BOV"].fillna(0).sum() + df["TOTAL_AFT_BOV_NV"].fillna(0).sum(),
        "bufalinos_raw": df["TOTAL_AFT_BUF"].fillna(0).sum() + df["TOTAL_AFT_BUF_NV"].fillna(0).sum(),
    }


def _resumen_legado(legado: pd.DataFrame) -> dict:
    return {
        "filas": len(legado),
        "predios_unicos": legado["CODIGO SIT"].nunique(),
        "municipios_unicos": legado["CODIGO MUNICIPIO"].nunique(),
        "bovinos_raw": legado["TOTAL AFTOSA BOVINOS"].sum() + legado["TOTAL AFTOSA BOVINOS NV"].sum(),
        "bufalinos_raw": legado["TOTAL AFTOSA BUFALINOS"].sum() + legado["TOTAL AFTOSA BUFALINOS NV"].sum(),
    }


def _validar(legado: pd.DataFrame) -> None:
    print("--- HALLAZGO 1: F_AJUSTA_BOVINOS/_CAL corruptos en el legado (ver docstring) ---")
    print(f"F_AJUSTA_BOVINOS: min={legado['F_AJUSTA_BOVINOS'].min():.4f}, max={legado['F_AJUSTA_BOVINOS'].max():.6e}, "
          f"mediana={legado['F_AJUSTA_BOVINOS'].median():.6e}")
    print(f"TOTAL AFTOSA BOVINOS_CAL: min={legado['TOTAL AFTOSA BOVINOS_CAL'].min():.4f}, "
          f"max={legado['TOTAL AFTOSA BOVINOS_CAL'].max():.6e} (valores plausibles: decenas a pocos miles)")
    print("-> confirmado: NO se puede usar ninguna columna '*_CAL' de este archivo para ningún contraste numérico.\n")

    propio = _resumen_propio()
    leg = _resumen_legado(legado)
    print("--- HALLAZGO 2: universo RUV crudo (SIN calibrar), propio vs. legado ---")
    print(f"{'':20s}{'propio':>15s}{'legado':>15s}{'dif %':>10s}")
    for k in ["filas", "predios_unicos", "municipios_unicos", "bovinos_raw", "bufalinos_raw"]:
        dif_pct = 100 * (propio[k] - leg[k]) / leg[k]
        print(f"{k:20s}{propio[k]:15,.0f}{leg[k]:15,.0f}{dif_pct:9.2f}%")


def generar_y_guardar() -> None:
    legado = _leer_legado()
    _validar(legado)


if __name__ == "__main__":
    generar_y_guardar()
