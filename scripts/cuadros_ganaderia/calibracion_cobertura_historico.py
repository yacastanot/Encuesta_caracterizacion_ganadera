"""`cal_cobertura` para cualquier (año, ciclo) del histórico de Fedegán - SOLO
para el Cuadro 4/5 del libro "ganadero" (2024, ver `base_maestra_ganadero_historico.py`).
Misma fórmula ya corregida y validada en `calibracion_cobertura_c1.py`/`_c2.py`
(`cal_cobertura = 1 / Total Predios Cobertura`, ver docstring de ese módulo
para la prueba completa) - generalizada acá a cualquier año/ciclo en vez de
estar fija a 2025, reutilizando el mismo archivo histórico de Fedegán
(`config.RUTA_FEDEGAN_HISTORICO`, que ya trae 2019-2025 completos).
"""
from __future__ import annotations

import pandas as pd

from . import catalogo_territorial, config


def calcular_cal_cobertura(anio: int, ciclo: int) -> pd.DataFrame:
    fedegan = pd.read_excel(config.RUTA_FEDEGAN_HISTORICO, sheet_name="Cuadro 2_Cobertura")
    fedegan = fedegan[(fedegan["AÑO"] == anio) & (fedegan["CICLO"] == f"CICLO {ciclo}")].copy()
    if fedegan.empty:
        raise ValueError(f"Fedegán histórico no trae filas para AÑO={anio}, CICLO=CICLO {ciclo}.")

    fedegan["Municipio"] = fedegan.apply(
        lambda r: config.EXCEPCIONES_MUNICIPIO_FEDEGAN.get((r["Departamento"], r["Municipio"]), r["Municipio"]),
        axis=1,
    )
    divipola = catalogo_territorial.cargar_catalogo_municipios().rename(
        columns={"CODIGO_MUNICIPIO": "COD_MPIO", "DEPARTAMENTO": "Departamento", "MUNICIPIO": "Municipio"}
    )
    fedegan_join = fedegan.merge(divipola[["COD_MPIO", "Departamento", "Municipio"]], on=["Departamento", "Municipio"], how="left")
    huerfanas = fedegan_join[fedegan_join["COD_MPIO"].isna()]
    if len(huerfanas):
        raise ValueError(
            f"{len(huerfanas)} filas de Fedegán (AÑO={anio}, CICLO {ciclo}) no cruzaron contra DIVIPOLA: "
            f"{list(huerfanas[['Departamento', 'Municipio']].itertuples(index=False, name=None))} - "
            "revisar config.EXCEPCIONES_MUNICIPIO_FEDEGAN antes de confiar en este factor."
        )

    comp = fedegan_join[["COD_MPIO", "Total Predios Cobertura"]].rename(columns={"COD_MPIO": "CODIGO_MUNICIPIO"})
    comp["cal_cobertura"] = (1.0 / comp["Total Predios Cobertura"]).where(comp["Total Predios Cobertura"] > 0).fillna(1.0)
    return comp


def municipios_baja_cobertura(anio: int, ciclo: int, umbral: float = 0.80) -> dict[str, str]:
    """`{CODIGO_MUNICIPIO: motivo}` con `Total Predios Cobertura` (Fedegán)
    por debajo de `umbral` - para Cuadro 4/5 del libro "ganadero"
    (`base_maestra_ganadero_historico.py`), a pedido del usuario (2026-09-24):
    excluir de 2024/2023 el mismo tipo de motivo "<80% cobertura" que ya se
    excluye en 2025 (`config._EXCLUIDOS_C1_COBERTURA`/`_C2_COBERTURA`).

    OJO - no es el mismo criterio exacto que 2025: ahí "cobertura" es la tasa
    de RESPUESTA de encuesta sobre el universo RUV vacunado
    (`cantpredganencuesta/cantpredganruv`, `calibracion_calruv_c2._validar`);
    acá se usa la tasa de VACUNACIÓN de Fedegán (`Total Predios Cobertura` =
    Vacunados/PM, la misma que ya alimenta `cal_cobertura`) porque es la
    única disponible de forma uniforme para 2023/2024 (los archivos de esos
    años no permiten separar "universo RUV completo" de "solo los que
    respondieron encuesta" con la misma limpieza que 2025 - ver docstring de
    `base_maestra_ganadero_historico.py`)."""
    comp = calcular_cal_cobertura(anio, ciclo)
    bajos = comp[comp["cal_cobertura"] > 1.0 / umbral]
    return {
        row["CODIGO_MUNICIPIO"]: f"{anio} Ciclo {ciclo} ({row['Total Predios Cobertura']:.1%} cobertura Fedegán)"
        for _, row in bajos.iterrows()
    }
