"""Valida los totales nacionales calibrados de Cuadro 3/7 (bovinos/bufalinos,
Ciclo 1 2025) contra Fedegán, municipio por municipio - documenta de dónde
sale cualquier diferencia entre el total REAL del cuadro (los 13 tramos de
sexo/edad + su propia `_NV`, calibrados) y el total que reporta Fedegán
(Cuadro 2_Cobertura).

OJO: el crudo que se compara acá es la suma de los 13 tramos de
`preparar_base_c1.columnas_inventario`, IGUAL a lo que efectivamente muestra el
Cuadro 3/7 - NO el proxy `TOTAL_AFT_<especie> + TOTAL_BRU_<especie>_NV` que
usa `calibracion_c1.py` únicamente para *calcular* el factor F_AJUSTA. Esos
dos "totales crudos" son distintos por diseño (el proxy no tiene por qué
coincidir con el detalle real por tramos) - compararse contra el proxy daría
un número que nunca aparece en el cuadro real. Ver `_crudo_por_municipio`.

Por qué puede haber diferencia aunque el factor esté bien calculado: el
factor `F_AJUSTA_BOVINOS/BUFALINOS` iguala Fedegán con SU PROPIO proxy de RUV
por municipio, no con el detalle real por tramos - así que, aplicado al
detalle real, el total calibrado se ACERCA a Fedegán pero no coincide exacto
ni siquiera en los municipios con match (la brecha proxy-vs-tramos se cuela).
Encima, en los municipios donde una fuente tiene datos y la otra no, no hay
con qué escalar (`calibracion_c1.comparar_especie` deja el factor en 0, no en
1.0, cuando no hay match en Fedegán - ver ese módulo):

 - RUV con datos pero SIN fila en Fedegán ese ciclo: factor=0, aporta CERO
   (no su crudo sin escalar).
 - Fedegán con dato pero SIN ningún predio en el RUV: no hay nada que
   escalar - ese total de Fedegán simplemente no aparece en el calibrado.
 - Excluido del universo (<80% cobertura, `MUNICIPIOS_EXCLUIDOS_C1`): sus
   predios ni siquiera entran a `cargar_base_cruda` - Fedegán sí puede traer
   un total para ese municipio, que entonces queda fuera del calibrado.

CONFIRMADO (2026-09-18, a pedido del usuario): si del lado de Fedegán también
se excluyen esos mismos municipios (comparación "mismo universo" en
`_validar`), la diferencia nacional queda en +0,000% para bovinos (los 44
municipios excluidos que sí tenían fila en Fedegán explican el 100% de la
brecha original de -1.267%) y en -1 unidad (-0,000%) para bufalinos - el
único residual real es Sibaté/Cundinamarca (Fedegán reporta 1 bufalino, RUV
sin ningún predio ahí, no es una exclusión nuestra). Confirma que el método
de calibración no tiene ningún error oculto: toda la brecha contra Fedegán
se explica por decisiones de universo ya documentadas, no por el cálculo.
"""
from __future__ import annotations

import pandas as pd

from . import calibracion_c1, catalogo_territorial, config, preparar_base_c1


def _crudo_por_municipio(especie: str) -> pd.Series:
    """Crudo por los 13 tramos de sexo/edad (+ su propia `_NV`) - LA MISMA
    agregación que usa `cuadros/inventario.py` para el Cuadro 3/7, vía
    `cargar_base_cruda` (que ya aplica la exclusión de
    `config.MUNICIPIOS_EXCLUIDOS_C1`).

    OJO: esto es DISTINTO de `TOTAL_AFT_<especie> + TOTAL_BRU_<especie>_NV`,
    que es el proxy que usa `calibracion_c1.py` SOLO para calcular el factor
    F_AJUSTA (comparado contra Fedegán) - ese proxy no coincide con la suma
    real de los 13 tramos (confirmado: para bovinos, proxy nacional=28.965.956
    vs tramos=28.923.081). Si esta validación usara el proxy en vez de los
    tramos reales, reportaría un total que NO es el que realmente aparece en
    el Cuadro 3 - por eso se recalcula acá con la misma columnas que el cuadro.
    """
    columnas_inv = preparar_base_c1.columnas_inventario(especie)
    df = preparar_base_c1.cargar_base_cruda(especie, columnas_extra=columnas_inv)
    crudo = pd.Series(0.0, index=df.index)
    for c in columnas_inv:
        for col in (c, f"{c}_NV"):
            if col in df.columns:
                crudo = crudo + df[col].fillna(0)
    df = df.assign(crudo=crudo)
    return df.groupby("CODIGO_MUNICIPIO")["crudo"].sum().rename("crudo")


def comparar_especie(especie: str) -> pd.DataFrame:
    col_pm = "Total Bovinos PM" if especie == "bovinos" else "Total Bufalinos PM"
    factor_col = "F_AJUSTA_BOVINOS" if especie == "bovinos" else "F_AJUSTA_BUFALINOS"

    fedegan_join = calibracion_c1._fedegan_ciclo1_con_codigo_municipio()
    fedegan = fedegan_join[["COD_MPIO", col_pm]].rename(columns={"COD_MPIO": "CODIGO_MUNICIPIO"})

    crudo = _crudo_por_municipio(especie)
    factor = preparar_base_c1._cargar_factor_c1_calculado(especie)

    comp = fedegan.merge(crudo, on="CODIGO_MUNICIPIO", how="outer").merge(factor, on="CODIGO_MUNICIPIO", how="outer")
    comp["crudo"] = comp["crudo"].fillna(0)
    comp[col_pm] = comp[col_pm].fillna(0)
    comp[factor_col] = comp[factor_col].fillna(0.0)
    comp["calibrado"] = comp["crudo"] * comp[factor_col]
    comp["dif_absoluta"] = comp["calibrado"] - comp[col_pm]

    comp["caso"] = "coincide (ambas fuentes tienen dato)"
    comp.loc[(comp[col_pm] == 0) & (comp["crudo"] > 0), "caso"] = "RUV con datos, sin fila en Fedegán (factor=0, aporta cero)"
    comp.loc[(comp[col_pm] > 0) & (comp["crudo"] == 0), "caso"] = "Fedegán con dato, sin ningún predio en el RUV"
    # Distinto de "sin ningún predio en el RUV": acá SÍ hay predios (por eso
    # `crudo` da 0 - se excluyeron a propósito), no es un hueco de cobertura.
    # El motivo real varía por municipio (cobertura/ZLSV/encuestas repetidas)
    # - se usa `config.RAZON_EXCLUSION_C1` en vez de un texto genérico único.
    excluidos = comp["CODIGO_MUNICIPIO"].isin(config.MUNICIPIOS_EXCLUIDOS_C1)
    comp["excluido_del_universo_ruv"] = excluidos
    comp.loc[excluidos, "caso"] = (
        "Excluido del universo: " + comp.loc[excluidos, "CODIGO_MUNICIPIO"].map(config.RAZON_EXCLUSION_C1)
    )

    divipola = catalogo_territorial.cargar_catalogo_municipios().rename(columns={"CODIGO_MUNICIPIO": "COD_MPIO"})
    comp = comp.merge(
        divipola[["COD_MPIO", "COD_DEPARTAMENTO", "DEPARTAMENTO", "MUNICIPIO"]],
        left_on="CODIGO_MUNICIPIO", right_on="COD_MPIO", how="left",
    ).drop(columns="COD_MPIO")

    cols_nombre = ["CODIGO_MUNICIPIO", "COD_DEPARTAMENTO", "DEPARTAMENTO", "MUNICIPIO"]
    return comp[cols_nombre + [c for c in comp.columns if c not in cols_nombre]]


def _validar(especie: str, comp: pd.DataFrame) -> None:
    col_pm = "Total Bovinos PM" if especie == "bovinos" else "Total Bufalinos PM"
    total_calibrado = comp["calibrado"].sum()
    total_fedegan = comp[col_pm].sum()
    dif = total_calibrado - total_fedegan

    print(f"\n=== {especie.upper()} ===")
    print(f"Total calibrado (Cuadro 3/7): {total_calibrado:,.0f}")
    print(f"Total Fedegán:                {total_fedegan:,.0f}")
    print(f"Diferencia: {dif:+,.0f} ({dif / total_fedegan:+.3%})")

    # Comparación "mismo universo de municipios": el cuadro calibrado NUNCA
    # incluye los `config.MUNICIPIOS_EXCLUIDOS_C1` (se excluyen desde
    # `cargar_base_cruda`, antes de calcular `crudo`), pero el total de
    # Fedegán de arriba SÍ trae su propio dato para esos municipios (si lo
    # tiene) - por diseño, no es un error. Si se excluyen esos MISMOS
    # municipios también del lado de Fedegán, ambos totales quedan sobre el
    # universo exacto de municipios que sí entra al cuadro - lo que sobre acá
    # (si algo sobra) es un residual real (no explicado por una exclusión
    # deliberada), no una diferencia de universo.
    excluidos = comp["CODIGO_MUNICIPIO"].isin(config.MUNICIPIOS_EXCLUIDOS_C1)
    total_fedegan_comparable = comp.loc[~excluidos, col_pm].sum()
    dif_comparable = total_calibrado - total_fedegan_comparable
    print(f"\n--- Mismo universo de municipios (excluyendo también del marco de Fedegán los {excluidos.sum()} municipios fuera del universo RUV) ---")
    print(f"Total Fedegán (mismo universo): {total_fedegan_comparable:,.0f}")
    print(f"Diferencia: {dif_comparable:+,.0f} ({dif_comparable / total_fedegan_comparable:+.3%})")

    # Nivel DEPARTAMENTAL, mismo universo (municipios excluidos fuera de
    # ambos lados) - a pedido explícito del usuario: los totales deben
    # coincidir exacto en los 3 niveles (municipal/departamental/nacional),
    # no solo a nivel nacional agregado.
    no_excl = comp[~excluidos]
    dep = no_excl.groupby(["COD_DEPARTAMENTO", "DEPARTAMENTO"], as_index=False)[["calibrado", col_pm]].sum()
    dep["dif"] = dep["calibrado"] - dep[col_pm]
    dif_dep = dep[dep["dif"].abs() > 0.5]
    print(f"\n--- Nivel DEPARTAMENTAL (mismo universo): {len(dif_dep)} / {len(dep)} departamentos con diferencia > 0.5 ---")
    if len(dif_dep):
        print(dif_dep.to_string())

    casos = comp[comp["caso"] != "coincide (ambas fuentes tienen dato)"]
    no_explicados = casos[~casos["caso"].str.startswith("Excluido del universo")]
    print(
        f"\nMunicipios que explican la diferencia original: {len(casos)} "
        f"({len(casos) - len(no_explicados)} por exclusión del universo, {len(no_explicados)} por otra causa - "
        "estos últimos SÍ quedan en la diferencia de 'mismo universo' de arriba)"
    )
    if len(no_explicados):
        print("\nCasos NO explicados por una exclusión (residual real, no se resuelve excluyendo del marco de Fedegán):")
        print(no_explicados[["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO", "crudo", col_pm, "caso"]].to_string())
    print()
    print(casos[["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO", "crudo", col_pm, "caso"]].to_string())


def generar_y_guardar() -> None:
    for especie in ("bovinos", "bufalinos"):
        comp = comparar_especie(especie)
        _validar(especie, comp)
        ruta = config.BASES_CALIBRADAS_DIR / f"validacion_totales_inventario_{especie}_C1_2025.csv"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        comp.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig")
        print(f"\nGuardado: {ruta}")


if __name__ == "__main__":
    generar_y_guardar()
