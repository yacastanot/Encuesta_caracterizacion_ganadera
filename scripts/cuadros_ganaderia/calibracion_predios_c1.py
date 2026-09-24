"""Recalcula `cal_predios` de Ciclo 1 2025 de forma independiente, con la
misma política del proyecto que ya se aplicó a F_AJUSTA_BOVINOS/BUFALINOS
(`calibracion_c1.py`) y a `calruv` (`calibracion_calruv_c1.py`): no heredar un
factor de `calibrac12025.xlsx` sin haberlo podido calcular y comparar primero
de forma independiente.

Regla:

    cal_predios = Total Predios PM / predios encuesta

 - `Total Predios PM`: Fedegán, `1-Historico-PE-Inventario-Bovino-Bufalino...xlsx`,
   hoja "Cuadro 2_Cobertura", filtrado a AÑO=2025 / CICLO 1 - misma fuente y
   mismo filtro que ya usa `calibracion_c1.py` para Total Bovinos/Bufalinos PM.
 - `predios encuesta`: count(distinct CODIGO_SIT) en `ciclo1encuesta.sas7bdat`
   (NO en `ciclo1ruv.sas7bdat`), agrupado por CODIGO_MUNICIPIO.

Por qué `ciclo1encuesta` y no `ciclo1ruv` (universo completo)
------------------------------------------------------------------------------
La primera versión de este módulo usaba `ciclo1ruv.sas7bdat` (universo RUV
completo), asumiendo que la columna heredada `predios ruv` de
`calibrac12025.xlsx` contaba eso - por el nombre. Esa versión reproducía el
heredado en la mayoría de municipios (diferencias de +1 a +3, atribuibles a
que el RUV sigue creciendo), pero fallaba por completo en 6 municipios de baja
cobertura (Convención, El Tarra, Hacarí, La Playa, Teorama, Anorí), donde el
heredado daba `cal_predios` de hasta 58x y el calculado apenas ~1x - se
documentó (equivocadamente) como un dato corrupto en el heredado.

Prueba que corrigió el diagnóstico: contar `predios ruv` desde
`ciclo1encuesta.sas7bdat` en vez de `ciclo1ruv.sas7bdat` reproduce el heredado
EXACTO en 1055/1055 municipios (incluidos los 6 "outliers"). O sea, pese al
nombre de la columna ("predios ruv"), Carolina la calculó sobre los predios
que ADEMÁS respondieron la encuesta de caracterización, no sobre el universo
RUV completo. Esto además es coherente con el resto del pipeline: en
`base_maestra_c1.py`, `peso_predio_ganadero = calruv * cal_cobertura` ya hace
exactamente la cadena encuesta → RUV → Fedegán en dos pasos; `cal_predios`
es la versión de un solo paso (encuesta → Fedegán directo). Y explica los 6
"outliers" sin apelar a datos corruptos: en esas zonas (Catatumbo, Anorí) el
RUV sí vacuna, pero casi nadie responde la encuesta de caracterización -
`calruv` (RUV/encuesta) es precisamente altísimo ahí por la misma razón (ver
`calibracion_calruv_c1.py` / `calibracion_ganadero_c1._validar`).

Validado contra el heredado (`calibrac12025.xlsx`, columnas `Total Predios PM`
/ `predios ruv` / `cal_predios`): numerador Y denominador coinciden EXACTO en
1055/1055 municipios. Se calcula igual el propio (no se hereda directo) por
la misma política del proyecto - la independencia del cálculo es lo que
permitió detectar el error de universo, no algo que se pueda dar por sentado
de antemano.
"""
from __future__ import annotations

import pandas as pd

from . import calibracion_ganadero_c1, catalogo_territorial, config, fuente_cruda_c1


def _contar_predios_encuesta() -> pd.Series:
    df = fuente_cruda_c1.leer(
        config.RUTA_CICLO1_ENCUESTA_CRUDO, columns=["CODIGO_MUNICIPIO", "CODIGO_SIT", "CICLO", "ANIO"]
    )

    # `ciclo1encuesta.sas7bdat` viene (según su nombre) ya filtrado a Ciclo 1
    # 2025, pero eso no está garantizado por el código - se verifica en vez de
    # asumirlo (mismo criterio que el cruce con Fedegán). Trae ~10 filas con
    # CICLO/ANIO en blanco (sin metadata, no son otro ciclo) - se dejan pasar;
    # si CODIGO_MUNICIPIO también viene vacío ahí, el dropna de abajo las descarta.
    mal_ciclo = df[df["CICLO"].notna() & (df["CICLO"] != 1)]
    mal_anio = df[df["ANIO"].notna() & (df["ANIO"] != 2025)]
    if len(mal_ciclo) or len(mal_anio):
        raise ValueError(
            f"ciclo1encuesta.sas7bdat trae {len(mal_ciclo)} filas con CICLO != 1 y {len(mal_anio)} con ANIO != 2025 - "
            "ya no se puede asumir que el archivo viene puro Ciclo 1 2025, hay que filtrar explícito."
        )

    df = df.dropna(subset=["CODIGO_MUNICIPIO"]).copy()
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)
    return df.groupby("CODIGO_MUNICIPIO")["CODIGO_SIT"].nunique().rename("predios_encuesta")


def _cargar_total_predios_pm_fedegan() -> pd.DataFrame:
    fedegan = pd.read_excel(config.RUTA_FEDEGAN_HISTORICO, sheet_name="Cuadro 2_Cobertura")
    fedegan = fedegan[(fedegan["AÑO"] == 2025) & (fedegan["CICLO"] == "CICLO 1")].copy()

    fedegan["Municipio"] = fedegan.apply(
        lambda r: config.EXCEPCIONES_MUNICIPIO_FEDEGAN.get((r["Departamento"], r["Municipio"]), r["Municipio"]),
        axis=1,
    )
    fedegan["Total Predios PM"] = pd.to_numeric(
        fedegan["Total Predios PM"].astype(str).replace("-", "0"), errors="coerce"
    ).fillna(0)

    divipola = catalogo_territorial.cargar_catalogo_municipios().rename(
        columns={"CODIGO_MUNICIPIO": "COD_MPIO", "DEPARTAMENTO": "Departamento", "MUNICIPIO": "Municipio"}
    )
    fedegan_join = fedegan.merge(
        divipola[["COD_MPIO", "Departamento", "Municipio"]], on=["Departamento", "Municipio"], how="left"
    )

    # El Fedegán histórico NO trae código DIVIPOLA propio - solo Departamento/
    # Municipio en texto, así que TODO el cruce depende de que esos nombres
    # coincidan exacto contra el catálogo DIVIPOLA. Si algún nombre deja de
    # cruzar (typo, tilde, municipio renombrado) esa fila quedaría con
    # CODIGO_MUNICIPIO=NaN y su Total Predios PM se perdería en silencio más
    # adelante (nunca se uniría a ningún `predios_encuesta`) - se falla fuerte
    # acá en vez de dejar que eso pase inadvertido.
    huerfanas = fedegan_join[fedegan_join["COD_MPIO"].isna()]
    if len(huerfanas):
        raise ValueError(
            f"{len(huerfanas)} filas de Fedegán (Cuadro 2_Cobertura, Ciclo 1 2025) no cruzaron contra "
            f"DIVIPOLA: {list(huerfanas[['Departamento', 'Municipio']].itertuples(index=False, name=None))} - "
            "revisar `config.EXCEPCIONES_MUNICIPIO_FEDEGAN` antes de confiar en este factor."
        )
    assert len(fedegan_join) == len(fedegan), "el cruce contra DIVIPOLA duplicó filas de Fedegán (fan-out inesperado)"

    # Dirección contraria: municipios DIVIPOLA que NO aparecen en Fedegán Ciclo 1
    # 2025 - esperado (no es un error): son los municipios sin ningún registro
    # RUV (códigos centinela 88888/44444, 35+31=66 ya documentados en
    # `calibracion_ganadero_c1.py`), no un problema de cruce de nombres.
    sin_fedegan = set(divipola["COD_MPIO"]) - set(fedegan_join["COD_MPIO"].dropna())
    print(
        f"Municipios DIVIPOLA sin fila en Fedegán Ciclo 1 2025: {len(sin_fedegan)} "
        "(esperado: municipios sin ningún registro RUV, no un fallo de cruce de nombres)"
    )

    return fedegan_join[["COD_MPIO", "Total Predios PM"]].rename(columns={"COD_MPIO": "CODIGO_MUNICIPIO"})


def _factor_seguro(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    return (numerador / denominador).where(denominador > 0).fillna(1.0)


def calcular_cal_predios() -> pd.DataFrame:
    fedegan = _cargar_total_predios_pm_fedegan()
    predios_encuesta = _contar_predios_encuesta()

    comp = fedegan.merge(predios_encuesta, on="CODIGO_MUNICIPIO", how="left")
    comp["cal_predios_calculado"] = _factor_seguro(comp["Total Predios PM"], comp["predios_encuesta"])
    return comp


def _cargar_heredado() -> pd.DataFrame:
    """`cal_predios` tal como venía en calibrac12025.xlsx (heredado de
    Carolina), cruzado a CODIGO_MUNICIPIO vía el crosswalk de municipio_id.
    Solo para comparar - el pipeline ya no usa este valor."""
    cruce = calibracion_ganadero_c1._cargar_crosswalk_municipio_id()
    return cruce[["CODIGO_MUNICIPIO", "Total Predios PM", "predios ruv", "cal_predios"]].rename(
        columns={
            "Total Predios PM": "total_predios_pm_heredado",
            "predios ruv": "predios_encuesta_heredado",
            "cal_predios": "cal_predios_heredado",
        }
    )


def comparar_con_heredado() -> pd.DataFrame:
    calculado = calcular_cal_predios()
    heredado = _cargar_heredado()
    comp = calculado.merge(heredado, on="CODIGO_MUNICIPIO", how="outer")
    comp["dif_predios_encuesta"] = comp["predios_encuesta"] - comp["predios_encuesta_heredado"]
    comp["dif_relativa_cal"] = (comp["cal_predios_calculado"] - comp["cal_predios_heredado"]) / comp[
        "cal_predios_heredado"
    ].replace(0, pd.NA)

    divipola = catalogo_territorial.cargar_catalogo_municipios().rename(
        columns={"CODIGO_MUNICIPIO": "COD_MPIO"}
    )
    comp = comp.merge(
        divipola[["COD_MPIO", "DEPARTAMENTO", "MUNICIPIO"]], left_on="CODIGO_MUNICIPIO", right_on="COD_MPIO", how="left"
    ).drop(columns="COD_MPIO")

    cols_nombre = ["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO"]
    comp = comp[cols_nombre + [c for c in comp.columns if c not in cols_nombre]]
    return comp


def _validar(comp: pd.DataFrame) -> None:
    print(f"Municipios comparados: {len(comp)}")
    print(f"Sin match en heredado: {comp['cal_predios_heredado'].isna().sum()}")

    dif_num = (comp["Total Predios PM"] - comp["total_predios_pm_heredado"]).fillna(-999)
    print(f"Numerador (Total Predios PM) con diferencia != 0: {(dif_num != 0).sum()} / {len(comp)}")

    dif_den = comp["dif_predios_encuesta"].fillna(-999)
    print(f"Denominador (predios encuesta) con diferencia != 0: {(dif_den != 0).sum()} / {len(comp)}")

    umbral = 0.01  # 1%
    grandes = comp[comp["dif_relativa_cal"].abs() > umbral].sort_values("dif_relativa_cal", key=abs, ascending=False)
    print(f"\nMunicipios con diferencia en cal_predios > {umbral:.0%}: {len(grandes)} / {len(comp)}")
    print(grandes[
        ["CODIGO_MUNICIPIO", "DEPARTAMENTO", "MUNICIPIO", "predios_encuesta", "predios_encuesta_heredado",
         "cal_predios_calculado", "cal_predios_heredado", "dif_relativa_cal"]
    ].head(15).to_string())


def generar_y_guardar() -> None:
    comp = comparar_con_heredado()
    _validar(comp)
    ruta = config.BASES_CALIBRADAS_DIR / "comparacion_cal_predios_C1_2025.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    comp.to_csv(ruta, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"\nGuardado: {ruta}")


if __name__ == "__main__":
    generar_y_guardar()
