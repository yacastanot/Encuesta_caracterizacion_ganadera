"""Valida el total nacional calibrado de Cuadro 1 - específicamente "Total
predios" (predios FÍSICOS, `peso_predio_fisico`) - contra Fedegán, municipio
por municipio. Mismo patrón que `validacion_totales_inventario_c1.py` para
bovinos/bufalinos.

Historia (2026-09-18): la primera versión de Cuadro 1 replicaba el SAS
original y usaba `peso_predio_ganadero = calruv * cal_cobertura` (cuenta
PARES predio-ganadero) también para "Total predios" - esta validación
detectó que eso sobreestimaba ~+25% frente al "Total Predios PM" de Fedegán,
porque un mismo predio con 2 ganaderos registrados contaba 2 veces. Se
confirmó que `peso_predio_fisico = (1/ganaderos por CODIGO_SIT) * cal_predios`
(ver `base_maestra_c1.py`) SÍ reconcilia exacto con Fedegán, igual que
F_AJUSTA_BOVINOS/BUFALINOS - por decisión del usuario, "Total predios" ahora
usa ese peso; "Total predios ganaderos" se queda con `peso_predio_ganadero`
(sin comparación directa posible con Fedegán, que no reporta esa unidad).

"Total ganaderos" tampoco se valida acá: Fedegán no reporta ninguna cifra de
ganaderos (personas), solo predios y animales (ver columnas de
`Cuadro 2_Cobertura` en `config.RUTA_FEDEGAN_HISTORICO`).
"""
from __future__ import annotations

import pandas as pd

from . import base_maestra_c1, calibracion_predios_c1, catalogo_territorial, config


def _calibrado_por_municipio() -> pd.Series:
    maestra = pd.read_parquet(base_maestra_c1.RUTA_BASE_MAESTRA_C1)
    return maestra.groupby("CODIGO_MUNICIPIO")["peso_predio_fisico"].sum().rename("calibrado")


def comparar() -> pd.DataFrame:
    fedegan = calibracion_predios_c1._cargar_total_predios_pm_fedegan()
    calibrado = _calibrado_por_municipio().reset_index()

    comp = fedegan.merge(calibrado, on="CODIGO_MUNICIPIO", how="outer")
    comp["calibrado"] = comp["calibrado"].fillna(0)
    comp["Total Predios PM"] = comp["Total Predios PM"].fillna(0)
    comp["dif_absoluta"] = comp["calibrado"] - comp["Total Predios PM"]

    comp["caso"] = "coincide (ambas fuentes tienen dato)"
    comp.loc[(comp["Total Predios PM"] == 0) & (comp["calibrado"] > 0), "caso"] = "RUV con datos, sin fila en Fedegán"
    comp.loc[(comp["Total Predios PM"] > 0) & (comp["calibrado"] == 0), "caso"] = "Fedegán con dato, sin ningún predio en el RUV"

    excluidos = comp["CODIGO_MUNICIPIO"].isin(config.MUNICIPIOS_EXCLUIDOS_C1)
    comp["excluido_del_universo_ruv"] = excluidos
    comp.loc[excluidos, "caso"] = (
        "Excluido del universo: " + comp.loc[excluidos, "CODIGO_MUNICIPIO"].map(config.RAZON_EXCLUSION_C1)
    )

    divipola = catalogo_territorial.cargar_catalogo_municipios().rename(columns={"CODIGO_MUNICIPIO": "COD_MPIO"})
    comp = comp.merge(
        divipola[["COD_MPIO", "DEPARTAMENTO", "MUNICIPIO"]], left_on="CODIGO_MUNICIPIO", right_on="COD_MPIO", how="left"
    ).drop(columns="COD_MPIO")

    cols_nombre = ["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO"]
    return comp[cols_nombre + [c for c in comp.columns if c not in cols_nombre]]


def _validar(comp: pd.DataFrame) -> None:
    total_calibrado = comp["calibrado"].sum()
    total_fedegan = comp["Total Predios PM"].sum()
    dif = total_calibrado - total_fedegan

    print("Total calibrado (Cuadro 1 - Total predios, peso_predio_fisico):", f"{total_calibrado:,.0f}")
    print(f"Total Fedegán (Total Predios PM):                              {total_fedegan:,.0f}")
    print(f"Diferencia: {dif:+,.0f} ({dif / total_fedegan:+.3%})")

    excluidos = comp["excluido_del_universo_ruv"]
    total_fedegan_comparable = comp.loc[~excluidos, "Total Predios PM"].sum()
    dif_comparable = total_calibrado - total_fedegan_comparable
    print(f"\n--- Mismo universo de municipios (excluyendo también del marco de Fedegán los {excluidos.sum()} municipios fuera del universo RUV) ---")
    print(f"Total Fedegán (mismo universo): {total_fedegan_comparable:,.0f}")
    print(f"Diferencia: {dif_comparable:+,.0f} ({dif_comparable / total_fedegan_comparable:+.3%})")

    no_excluidos = comp[~excluidos]
    con_dif = no_excluidos[no_excluidos["dif_absoluta"].abs() > 0.5]
    print(
        f"\nMunicipios NO excluidos con alguna diferencia residual: {len(con_dif)} / {len(no_excluidos)} "
        "(esperado ~0 igual que Cuadro 3/7, ya que peso_predio_fisico usa cal_predios, construido para "
        "reconciliar exacto con Fedegán - ver base_maestra_c1.py)"
    )
    if len(con_dif):
        print(con_dif[["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO", "calibrado", "Total Predios PM", "caso"]].to_string())


def generar_y_guardar() -> None:
    comp = comparar()
    _validar(comp)
    ruta = config.BASES_CALIBRADAS_DIR / "validacion_totales_cuadro1_C1_2025.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    comp.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"\nGuardado: {ruta}")


if __name__ == "__main__":
    generar_y_guardar()
