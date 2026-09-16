"""Recalcula F_AJUSTA_BOVINOS / F_AJUSTA_BUFALINOS de Ciclo 1 2025 con la
MISMA metodología ya validada para Ciclo 2 (`calibracion_c2.py`: Total
<especie> PM de Fedegán / nuestro propio total RUV crudo, por municipio), en
vez de heredar el factor que ya trae `ruv_bovinos_calibrado_C1_2025.csv` /
`ruv_bufalinos_calibrado_C1_2025.csv`.

Por qué: no se debe asumir que un factor ya presente en un archivo está bien
calculado solo porque "ya viene ahí" - ese fue exactamente el bug encontrado
en el `F_AJUSTA_BOVINOS` de Ciclo 2 (corrupto ~14 órdenes de magnitud). Este
módulo permite comparar el heredado contra uno calculado de forma
independiente, con el mismo insumo (Fedegán) y la misma lógica que ya se
validó en Ciclo 2.

Confirmado antes de calcular: `TOTAL_AFTOSA_BOVINOS_CALIBRADO` (ya en el CSV)
= `TOTAL_AFTOSA_BOVINOS` (crudo) * `F_AJUSTA_BOVINOS` (heredado), exacto - o
sea que `TOTAL_AFTOSA_BOVINOS`/`TOTAL_AFTOSA_BUFALINOS` SÍ son los totales
crudos (pre-calibración) que hay que comparar contra Fedegán.
"""
from __future__ import annotations

import pandas as pd

from . import catalogo_territorial, config


def _cargar_fedegan_ciclo1_2025() -> pd.DataFrame:
    fedegan = pd.read_excel(config.RUTA_FEDEGAN_HISTORICO, sheet_name="Cuadro 2_Cobertura")
    fedegan = fedegan[(fedegan["AÑO"] == 2025) & (fedegan["CICLO"] == "CICLO 1")].copy()

    def _municipio_normalizado(row):
        return config.EXCEPCIONES_MUNICIPIO_FEDEGAN.get((row["Departamento"], row["Municipio"]), row["Municipio"])

    fedegan["Municipio"] = fedegan.apply(_municipio_normalizado, axis=1)
    for col in ("Total Bovinos PM", "Total Bufalinos PM"):
        fedegan[col] = pd.to_numeric(fedegan[col].astype(str).replace("-", "0"), errors="coerce").fillna(0)
    return fedegan


def _cargar_inventario_ruv_c1(especie: str) -> pd.DataFrame:
    ruta = config.RUTA_BOVINOS if especie == "bovinos" else config.RUTA_BUFALINOS
    col_total = "TOTAL_AFTOSA_BOVINOS" if especie == "bovinos" else "TOTAL_AFTOSA_BUFALINOS"
    col_factor_heredado = "F_AJUSTA_BOVINOS" if especie == "bovinos" else "F_AJUSTA_BUFALINOS"

    df = pd.read_csv(
        ruta, sep=";", encoding="utf-8-sig", encoding_errors="replace", decimal=",",
        usecols=["CODIGO_MUNICIPIO", col_total, col_factor_heredado],
    )
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(str).str.zfill(5)
    agg = df.groupby("CODIGO_MUNICIPIO", as_index=False).agg(
        total_ruv=(col_total, "sum"),
        factor_heredado=(col_factor_heredado, "first"),
    )
    return agg


def _factor_seguro(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    return (numerador / denominador).where(denominador > 0).fillna(1.0)


def comparar_especie(especie: str) -> pd.DataFrame:
    col_pm = "Total Bovinos PM" if especie == "bovinos" else "Total Bufalinos PM"

    divipola = catalogo_territorial.cargar_catalogo_municipios().rename(
        columns={"CODIGO_MUNICIPIO": "COD_MPIO", "DEPARTAMENTO": "Departamento", "MUNICIPIO": "Municipio"}
    )
    fedegan = _cargar_fedegan_ciclo1_2025()
    fedegan_join = fedegan.merge(divipola[["COD_MPIO", "Departamento", "Municipio"]], on=["Departamento", "Municipio"], how="left")

    nuestro = _cargar_inventario_ruv_c1(especie)

    comp = nuestro.merge(
        fedegan_join[["COD_MPIO", col_pm]], left_on="CODIGO_MUNICIPIO", right_on="COD_MPIO", how="left"
    )
    comp["factor_calculado"] = _factor_seguro(comp[col_pm], comp["total_ruv"])
    comp["dif_absoluta"] = comp["factor_calculado"] - comp["factor_heredado"]
    comp["dif_relativa"] = comp["dif_absoluta"] / comp["factor_heredado"].replace(0, pd.NA)
    return comp.drop(columns="COD_MPIO")


def _validar(especie: str, comp: pd.DataFrame) -> None:
    print(f"\n=== {especie.upper()} ===")
    print(f"Municipios comparados: {len(comp)}")
    print("--- factor_calculado (nuestro, Fedegán/RUV) ---")
    print(comp["factor_calculado"].describe())
    print("--- factor_heredado (ya en el CSV) ---")
    print(comp["factor_heredado"].describe())
    print("--- dif_relativa ((calculado - heredado) / heredado) ---")
    print(comp["dif_relativa"].describe())

    umbral = 0.01  # 1%
    grandes = comp[comp["dif_relativa"].abs() > umbral].sort_values("dif_relativa", key=abs, ascending=False)
    print(f"\nMunicipios con diferencia > {umbral:.0%}: {len(grandes)} / {len(comp)}")
    print(grandes[["CODIGO_MUNICIPIO", "total_ruv", "factor_calculado", "factor_heredado", "dif_relativa"]].head(15).to_string())

    total_col = "TOTAL_AFTOSA_BOVINOS" if especie == "bovinos" else "TOTAL_AFTOSA_BUFALINOS"
    total_calculado = (comp["total_ruv"] * comp["factor_calculado"]).sum()
    total_heredado = (comp["total_ruv"] * comp["factor_heredado"]).sum()
    print(f"\nTotal nacional calibrado CON factor calculado: {total_calculado:,.0f}")
    print(f"Total nacional calibrado CON factor heredado:  {total_heredado:,.0f}")
    print(f"Diferencia: {(total_calculado-total_heredado)/total_heredado:+.2%}")


def generar_comparacion() -> None:
    for especie in ("bovinos", "bufalinos"):
        comp = comparar_especie(especie)
        _validar(especie, comp)
        ruta = config.BASES_CALIBRADAS_DIR / f"comparacion_factor_{especie}_C1_2025.csv"
        comp.to_csv(ruta, sep=";", decimal=",", index=False)
        print(f"\nGuardado: {ruta}")


def generar_y_guardar_factor_oficial() -> None:
    """Guarda el factor CALCULADO por nosotros (no el heredado del CSV) como
    el que usa el resto del pipeline - ver `preparar_base.aplicar_factor_calibracion`."""
    bov = comparar_especie("bovinos")[["CODIGO_MUNICIPIO", "factor_calculado"]].rename(columns={"factor_calculado": "F_AJUSTA_BOVINOS"})
    buf = comparar_especie("bufalinos")[["CODIGO_MUNICIPIO", "factor_calculado"]].rename(columns={"factor_calculado": "F_AJUSTA_BUFALINOS"})
    factor = bov.merge(buf, on="CODIGO_MUNICIPIO", how="outer")
    config.RUTA_FACTOR_C1_INVENTARIO.parent.mkdir(parents=True, exist_ok=True)
    factor.to_csv(config.RUTA_FACTOR_C1_INVENTARIO, sep=";", decimal=",", index=False)
    print(f"Guardado: {config.RUTA_FACTOR_C1_INVENTARIO} ({len(factor)} municipios)")


if __name__ == "__main__":
    generar_comparacion()
    generar_y_guardar_factor_oficial()
