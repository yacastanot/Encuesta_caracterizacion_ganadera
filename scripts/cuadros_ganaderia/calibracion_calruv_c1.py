"""Recalcula `calruv` de Ciclo 1 2025 a partir de las bases crudas
(`ciclo1ruv.sas7bdat` / `ciclo1encuesta.sas7bdat`), en vez de heredarlo de
`calibraencuestac1.xlsx` - misma filosofía que `calibracion_c1.py` para
F_AJUSTA_BOVINOS/BUFALINOS: no asumir que un factor ya presente en un archivo
está bien calculado solo porque "ya viene ahí".

Fórmula (de "Programas Carolina/3. configura base.sas", líneas ~258-284):

    predioganid = CODIGO_SIT || IDENT_GANADERO   (ya viene precalculado en las
                                                   2 bases crudas)
    cantpredganruv      = count(distinct predioganid) en ciclo1ruv      (universo
                           RUV completo: todo predio-ganadero vacunado)
    cantpredganencuesta = count(distinct predioganid) en ciclo1encuesta (subconjunto
                           de esos predio-ganadero que ADEMÁS respondieron la
                           encuesta de caracterización)
    calruv = cantpredganruv / cantpredganencuesta   (por municipio)

Validado: el calculado aquí coincide EXACTO con el heredado de
calibraencuestac1.xlsx municipio por municipio (ej. Anorí, id 43: 1.388467 en
ambos) - confirma la fórmula y el que `predioganid` no necesite recalcularse.
"""
from __future__ import annotations

import pandas as pd

from . import calibracion_ganadero_c1, config, fuente_cruda_c1

_COLS_CRUDO = ["CODIGO_MUNICIPIO", "predioganid"]


def _contar_predioganid(ruta) -> pd.Series:
    df = fuente_cruda_c1.leer(ruta, columns=_COLS_CRUDO + ["CICLO", "ANIO"])

    # `ciclo1ruv.sas7bdat`/`ciclo1encuesta.sas7bdat` vienen (según su nombre) ya
    # filtrados a Ciclo 1 2025, pero eso no está garantizado por el código - se
    # verifica en vez de asumirlo (mismo criterio que el cruce con Fedegán).
    # `ciclo1encuesta.sas7bdat` trae ~10 filas con CICLO/ANIO en blanco (sin
    # metadata) - se dejan pasar, no son un ciclo distinto, solo falta el dato;
    # si CODIGO_MUNICIPIO también viene vacío ahí, el `dropna` de abajo ya las
    # descarta igual.
    mal_ciclo = df[df["CICLO"].notna() & (df["CICLO"] != 1)]
    mal_anio = df[df["ANIO"].notna() & (df["ANIO"] != 2025)]
    if len(mal_ciclo) or len(mal_anio):
        raise ValueError(
            f"{ruta}: {len(mal_ciclo)} filas con CICLO != 1 y {len(mal_anio)} con ANIO != 2025 - "
            "ya no se puede asumir que el archivo viene puro Ciclo 1 2025, hay que filtrar explícito."
        )

    df = df.dropna(subset=["CODIGO_MUNICIPIO"]).copy()
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)
    return df.groupby("CODIGO_MUNICIPIO")["predioganid"].nunique()


def calcular_calruv() -> pd.DataFrame:
    cantpredganruv = _contar_predioganid(config.RUTA_CICLO1_RUV_CRUDO).rename("cantpredganruv")
    cantpredganencuesta = _contar_predioganid(config.RUTA_CICLO1_ENCUESTA_CRUDO).rename("cantpredganencuesta")

    comp = pd.concat([cantpredganruv, cantpredganencuesta], axis=1).reset_index()
    comp = comp.rename(columns={"index": "CODIGO_MUNICIPIO"})
    comp["calruv_calculado"] = (comp["cantpredganruv"] / comp["cantpredganencuesta"]).where(
        comp["cantpredganencuesta"] > 0
    ).fillna(1.0)
    return comp


def _cargar_calruv_heredado() -> pd.DataFrame:
    """`calruv` tal como venía en calibraencuestac1.xlsx (heredado de Carolina),
    cruzado a CODIGO_MUNICIPIO vía el crosswalk de municipio_id. Solo para
    comparar contra el recalculado - el pipeline ya no usa este valor."""
    cruce = calibracion_ganadero_c1._cargar_crosswalk_municipio_id()
    calruv = pd.read_excel(calibracion_ganadero_c1.RUTA_CALIBRA_ENCUESTA_C1, sheet_name="Hoja1")
    heredado = cruce.merge(
        calruv[["MUNICIPIO_ID", "calruv"]], left_on="municipio_id", right_on="MUNICIPIO_ID", how="left"
    )
    return heredado[["CODIGO_MUNICIPIO", "calruv"]].rename(columns={"calruv": "calruv_heredado"})


def comparar_con_heredado() -> pd.DataFrame:
    calculado = calcular_calruv()
    heredado = _cargar_calruv_heredado()
    comp = calculado.merge(heredado, on="CODIGO_MUNICIPIO", how="outer")
    comp["dif_absoluta"] = comp["calruv_calculado"] - comp["calruv_heredado"]
    comp["dif_relativa"] = comp["dif_absoluta"] / comp["calruv_heredado"].replace(0, pd.NA)
    return comp


def _validar(comp: pd.DataFrame) -> None:
    print(f"Municipios comparados: {len(comp)}")
    sin_match = comp["calruv_heredado"].isna().sum()
    print(f"Sin match en heredado: {sin_match}")

    umbral = 0.001  # 0.1%
    grandes = comp[comp["dif_relativa"].abs() > umbral].sort_values("dif_relativa", key=abs, ascending=False)
    print(f"Municipios con diferencia > {umbral:.1%}: {len(grandes)} / {len(comp)}")
    print(grandes[["CODIGO_MUNICIPIO", "cantpredganruv", "cantpredganencuesta", "calruv_calculado", "calruv_heredado", "dif_relativa"]].head(15).to_string())


def generar_y_guardar() -> None:
    comp = comparar_con_heredado()
    _validar(comp)
    ruta = config.BASES_CALIBRADAS_DIR / "comparacion_calruv_C1_2025.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    comp.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"\nGuardado: {ruta}")


if __name__ == "__main__":
    generar_y_guardar()
