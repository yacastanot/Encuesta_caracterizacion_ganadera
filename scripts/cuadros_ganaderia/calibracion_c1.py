"""Recalcula F_AJUSTA_BOVINOS / F_AJUSTA_BUFALINOS de Ciclo 1 2025.

Metodología base tomada de los programas R oficiales
(`02Programas/2025 I/R/F_ajusta_bovinos_C1 2025.R` /
`F_ajusta_bufalinos_C1 2025.R_03082026.R`, leídos como referencia de
metodología - no se usó ningún dato/salida de esos programas, solo la
lógica), con UN AJUSTE deliberado confirmado con el usuario (2026-09-17):

    F_AJUSTA_<especie> = Total <especie> PM (Fedegán) / total_ruv (por municipio)
    total_ruv = suma de los 13 tramos de sexo/edad (+ su propia `_NV`) de
                `preparar_base_c1.columnas_inventario(especie)`

El R original usa como denominador `TOTAL_AFT_<especie> + TOTAL_BRU_<especie>_NV`
(un agregado/proxy) en vez de sumar los 13 tramos reales. Se detectó que ese
proxy NO coincide con la suma real de tramos (`TOTAL_AFT_BOV_NV` nacional =
139.239 vs `TOTAL_BRU_BOV_NV` = 1.800) - y como `aplicar_factor_calibracion`
multiplica el factor contra esos 13 tramos reales (no contra el proxy), usar
el proxy como denominador dejaba una brecha residual del total calibrado
contra Fedegán incluso en municipios con match perfecto (~48.242 en bovinos,
~85 en bufalinos). Por decisión explícita del usuario: el denominador se
calcula con el MISMO detalle al que se aplica el factor, para que el total
calibrado coincida exacto con Fedegán en todo municipio con match - ya no es
la fórmula literal del R oficial, es una corrección deliberada sobre ella.

Municipios sin match en Fedegán ese ciclo (Acandí/Unguía, Chocó): el R
original los deja en NA (bovinos: el `left_join` no encuentra `Total Bovinos
PM`, el producto final da NA y `sum(..., na.rm=TRUE)` los excluye) o en 0
explícito (bufalinos: vía `case_when`) - EN AMBOS CASOS el municipio aporta
CERO al total nacional, nunca su inventario crudo sin escalar. Acá se
replica ese comportamiento con `factor_calculado = 0` para esos municipios
(matemáticamente equivalente: 0 * crudo = 0 = NA * crudo con na.rm=TRUE).

Fuente RUV: `ciclo1encuesta.sas7bdat` (no `ciclo1ruv.sas7bdat` - mismo
criterio que el resto del pipeline C1, ver `preparar_base_c1.py`).
"""
from __future__ import annotations

import pandas as pd

from . import catalogo_territorial, config, fuente_cruda_c1, preparar_base_c1


def _cargar_fedegan_ciclo1_2025() -> pd.DataFrame:
    fedegan = pd.read_excel(config.RUTA_FEDEGAN_HISTORICO, sheet_name="Cuadro 2_Cobertura")
    fedegan = fedegan[(fedegan["AÑO"] == 2025) & (fedegan["CICLO"] == "CICLO 1")].copy()

    fedegan["Municipio"] = fedegan.apply(
        lambda r: config.EXCEPCIONES_MUNICIPIO_FEDEGAN.get((r["Departamento"], r["Municipio"]), r["Municipio"]),
        axis=1,
    )
    for col in ("Total Bovinos PM", "Total Bufalinos PM"):
        fedegan[col] = pd.to_numeric(fedegan[col].astype(str).replace("-", "0"), errors="coerce").fillna(0)
    return fedegan


def _fedegan_ciclo1_con_codigo_municipio() -> pd.DataFrame:
    """Cruza Fedegán (solo trae Departamento/Municipio en texto, sin código
    DIVIPOLA propio) contra el catálogo DIVIPOLA para obtener CODIGO_MUNICIPIO.
    Falla fuerte si algún nombre no cruza - si no, esa fila se perdería en
    silencio más adelante (nunca se uniría a nuestro inventario RUV)."""
    divipola = catalogo_territorial.cargar_catalogo_municipios().rename(
        columns={"CODIGO_MUNICIPIO": "COD_MPIO", "DEPARTAMENTO": "Departamento", "MUNICIPIO": "Municipio"}
    )
    fedegan = _cargar_fedegan_ciclo1_2025()
    fedegan_join = fedegan.merge(divipola[["COD_MPIO", "Departamento", "Municipio"]], on=["Departamento", "Municipio"], how="left")

    huerfanas = fedegan_join[fedegan_join["COD_MPIO"].isna()]
    if len(huerfanas):
        raise ValueError(
            f"{len(huerfanas)} filas de Fedegán (Cuadro 2_Cobertura, Ciclo 1 2025) no cruzaron contra "
            f"DIVIPOLA: {list(huerfanas[['Departamento', 'Municipio']].itertuples(index=False, name=None))} - "
            "revisar `config.EXCEPCIONES_MUNICIPIO_FEDEGAN` antes de confiar en este factor."
        )
    assert len(fedegan_join) == len(fedegan), "el cruce contra DIVIPOLA duplicó filas de Fedegán (fan-out inesperado)"

    sin_fedegan = set(divipola["COD_MPIO"]) - set(fedegan_join["COD_MPIO"].dropna())
    print(
        f"Municipios DIVIPOLA sin fila en Fedegán Ciclo 1 2025: {len(sin_fedegan)} "
        "(esperado: municipios sin ningún registro RUV, no un fallo de cruce de nombres)"
    )
    return fedegan_join


def _sumar_total_aftosa_ruv(especie: str) -> pd.Series:
    """Suma de los 13 tramos de sexo/edad (+ su propia `_NV`) por municipio -
    EL MISMO detalle que `preparar_base_c1.aplicar_factor_calibracion`
    multiplica por este factor (ver docstring del módulo: por qué no se usa
    el proxy `TOTAL_AFT_<especie> + TOTAL_BRU_<especie>_NV` del R original)."""
    columnas_inv = preparar_base_c1.columnas_inventario(especie)
    cols_val = [c for c in columnas_inv] + [f"{c}_NV" for c in columnas_inv]
    df = fuente_cruda_c1.leer(config.RUTA_CICLO1_ENCUESTA_CRUDO, columns=["CODIGO_MUNICIPIO", "CICLO", "ANIO"] + cols_val)

    mal_ciclo = df[df["CICLO"].notna() & (df["CICLO"] != 1)]
    mal_anio = df[df["ANIO"].notna() & (df["ANIO"] != 2025)]
    if len(mal_ciclo) or len(mal_anio):
        raise ValueError(
            f"ciclo1encuesta.sas7bdat trae {len(mal_ciclo)} filas con CICLO != 1 y {len(mal_anio)} con ANIO != 2025 - "
            "ya no se puede asumir que el archivo viene puro Ciclo 1 2025, hay que filtrar explícito."
        )

    df = df.dropna(subset=["CODIGO_MUNICIPIO"]).copy()
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)
    df["total_ruv"] = df[[c for c in cols_val if c in df.columns]].fillna(0).sum(axis=1)
    return df.groupby("CODIGO_MUNICIPIO")["total_ruv"].sum()


def comparar_especie(especie: str) -> pd.DataFrame:
    col_pm = "Total Bovinos PM" if especie == "bovinos" else "Total Bufalinos PM"

    fedegan_join = _fedegan_ciclo1_con_codigo_municipio()
    fedegan = fedegan_join[["COD_MPIO", col_pm]].rename(columns={"COD_MPIO": "CODIGO_MUNICIPIO"})

    total_ruv = _sumar_total_aftosa_ruv(especie).rename("total_ruv").reset_index()

    comp = total_ruv.merge(fedegan, on="CODIGO_MUNICIPIO", how="left")

    # RUV=0 -> factor=1.0 (no importa: no hay animales que multiplicar).
    # Sin match en Fedegán (col_pm sigue NaN tras el merge - no se hace
    # fillna(0)) -> factor=0, el municipio aporta cero al total (ver
    # docstring del módulo: réplica del comportamiento NA/na.rm del R
    # original, no un "sin ajuste").
    factor = (comp[col_pm] / comp["total_ruv"]).where(comp["total_ruv"] > 0, 1.0)
    factor = factor.where(comp[col_pm].notna(), 0.0)
    comp["factor_calculado"] = factor
    comp["sin_match_fedegan"] = comp[col_pm].isna()
    comp[col_pm] = comp[col_pm].fillna(0)
    return comp


def _validar(especie: str, comp: pd.DataFrame) -> None:
    col_pm = "Total Bovinos PM" if especie == "bovinos" else "Total Bufalinos PM"
    print(f"\n=== {especie.upper()} ===")
    print(f"Municipios comparados: {len(comp)}")
    print("--- factor_calculado ---")
    print(comp["factor_calculado"].describe())

    sin_match = comp[comp["sin_match_fedegan"]]
    print(f"\nMunicipios sin match en Fedegán (factor=0, excluidos del total): {len(sin_match)}")
    print(sin_match[["CODIGO_MUNICIPIO", "total_ruv", "factor_calculado"]].to_string())

    total_calculado = (comp["total_ruv"] * comp["factor_calculado"]).sum()
    total_fedegan = comp[col_pm].sum()
    print(f"\nTotal nacional calibrado: {total_calculado:,.0f}")
    print(f"Total nacional Fedegán:   {total_fedegan:,.0f}")
    print(f"Diferencia: {total_calculado - total_fedegan:+,.0f} ({(total_calculado - total_fedegan) / total_fedegan:+.3%})")


def generar_comparacion() -> None:
    for especie in ("bovinos", "bufalinos"):
        comp = comparar_especie(especie)
        _validar(especie, comp)
        ruta = config.BASES_CALIBRADAS_DIR / f"comparacion_factor_{especie}_C1_2025.csv"
        comp.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig")
        print(f"\nGuardado: {ruta}")


def generar_y_guardar_factor_oficial() -> None:
    """Guarda F_AJUSTA_BOVINOS/BUFALINOS calculados - los que usa el resto
    del pipeline, ver `preparar_base_c1.aplicar_factor_calibracion`."""
    bov = comparar_especie("bovinos")[["CODIGO_MUNICIPIO", "factor_calculado"]].rename(columns={"factor_calculado": "F_AJUSTA_BOVINOS"})
    buf = comparar_especie("bufalinos")[["CODIGO_MUNICIPIO", "factor_calculado"]].rename(columns={"factor_calculado": "F_AJUSTA_BUFALINOS"})
    factor = bov.merge(buf, on="CODIGO_MUNICIPIO", how="outer")
    config.RUTA_FACTOR_C1_INVENTARIO.parent.mkdir(parents=True, exist_ok=True)
    factor.to_csv(config.RUTA_FACTOR_C1_INVENTARIO, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"Guardado: {config.RUTA_FACTOR_C1_INVENTARIO} ({len(factor)} municipios)")


if __name__ == "__main__":
    generar_comparacion()
    generar_y_guardar_factor_oficial()
