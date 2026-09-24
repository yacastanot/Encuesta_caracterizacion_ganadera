"""Carga y limpieza de la base RUV+encuesta cruda (bovinos / bufalinos).

Traducción a Python de "3. configura base.sas" (renombrado de preguntas,
normalización de texto, variables *Orden) y de la deduplicación por
predio-ganadero que aplican "4.2. cuadros ganadero.sas" / "4.3. cuadros predio
ganadero.sas".

Fuente: `ciclo1encuesta.sas7bdat` (no `ciclo1ruv.sas7bdat`, el universo RUV
completo) - antes se usaban `ruv_bovinos_calibrado_C1_2025.csv` /
`ruv_bufalinos_calibrado_C1_2025.csv` (insumo del pipeline R, nunca
disponibles en este entorno), pero se confirmó que esos 2 CSV ya no existen
localmente y que su universo de predios coincide EXACTO con
`ciclo1encuesta.sas7bdat`: `nunique(predioganid)` da 745.993 en ambos casos
(el mismo número que ya documentaba este módulo de antes, cuando sí existían
los CSV) - confirma que son la misma fuente, solo que acá se lee el
`.sas7bdat` crudo directo en vez de un CSV intermedio ya exportado por R.
`ciclo1ruv.sas7bdat` (universo completo, sin filtrar a quienes respondieron la
encuesta) NO es la fuente correcta acá: sus predios sin encuesta no traen
R4/R7/R10/R11 etc., que sí hacen falta para los cuadros de ganadero/predio-
ganadero que se construyen con esta base.

Ya NO hace falta `renombrar_preguntas`: a diferencia de la tabla cruda
`temp.encuestac1` que usaba el SAS original (con columnas R3..R20 en crudo),
`ciclo1encuesta.sas7bdat`/`ciclo1ruv.sas7bdat` ya traen las preguntas bajo su
nombre de negocio directo (`cantvacasord`, `orientacionhato`, etc. -
verificado columna por columna contra `config.RENOMBRE_PREGUNTAS.values()`).
`renombrar_preguntas` se deja como no-operación segura (por si algún día se
vuelve a una fuente con R3..R20 crudos) en vez de borrarla.
"""
from __future__ import annotations

import pandas as pd

from . import config, fuente_cruda_c1

# Columnas base de identificación / territorio necesarias en (casi) todos los usos.
_COLS_ID = [
    "CODIGO_SIT",
    "IDENT_GANADERO",
    "GANADERO_ID",
    "PREDIO_ID",
    "RUV_ID",
    "DEPARTAMENTO",
    "MUNICIPIO",
    "CODIGO_MUNICIPIO",
    "CICLO",
    "PERIODOCICLO",
    "FECHA_CREACION",
    "GENERO",
    "TIPO_PROPIEDAD",
    "PREDIO_CARGO",
    "F_AJUSTA_BOVINOS",
    "F_AJUSTA_BUFALINOS",
    "TOTAL_AFT_BOV",
    "TOTAL_AFTOSA_BOVINOS",
    "TOTAL_AFTOSA_BUFALINOS",
]

_TRAMOS_HEMBRA = ["MEN_3_MES", "MEN_DE_3_8_MES", None, "1_2_ANI", "2_3_ANI", "3_5_ANI", "MAY_5_ANI"]
# NOTA: el tramo "9-12 meses" hembra no lleva prefijo HEM en el esquema original
# del RUV (columna compartida `AFT_<ESP>_DE_8_12_MES`) - ver `columnas_inventario`.

_COLS_INVENTARIO_BOV = (
    [f"AFT_BOV_HEM_{t}" for t in ["MEN_3_MES", "MEN_DE_3_8_MES", "1_2_ANI", "2_3_ANI", "3_5_ANI", "MAY_5_ANI"]]
    + ["AFT_BOV_DE_8_12_MES"]
    + [f"AFT_BOV_MAC_{t}" for t in ["MEN_3_MES", "3_8_MES", "8_12_MES", "1_2_ANI", "2_3_ANI", "MAY_3_ANI"]]
)
_COLS_INVENTARIO_BUF = (
    [f"AFT_BUF_HEM_{t}" for t in ["MEN_3_MES", "MEN_DE_3_8_MES", "1_2_ANI", "2_3_ANI", "3_5_ANI", "MAY_5_ANI"]]
    + ["AFT_BUF_DE_8_12_MES"]
    + [f"AFT_BUF_MAC_{t}" for t in ["MEN_3_MES", "3_8_MES", "8_12_MES", "1_2_ANI", "2_3_ANI", "MAY_3_ANI"]]
)

_COLS_OTRAS_ESPECIES = [
    f"{esp}_{sexo}" for esp in ["EQUINOS", "PORCINOS", "OVINOS", "CAPRINOS", "OTROS"] for sexo in ["MACHO", "HEMBRA"]
] + [f"TOTAL_{esp}" for esp in ["EQUINOS", "PORCINOS", "OVINOS", "CAPRINOS", "OTROS"]]

_COLS_ENCUESTA = [f"R{i}" for i in range(1, 6)] + [f"R6_{i}" for i in range(1, 9)] + [f"R{i}" for i in range(7, 21)]


def columnas_inventario(especie: str) -> list[str]:
    return _COLS_INVENTARIO_BOV if especie.lower() == "bovinos" else _COLS_INVENTARIO_BUF


def cargar_base_cruda(especie: str, columnas_extra: list[str] | None = None) -> pd.DataFrame:
    """Carga `ciclo1encuesta.sas7bdat` con las columnas de identificación + las
    pedidas (bovinos y bufalinos comparten el mismo archivo/filas - solo
    cambian las columnas AFT_BOV_*/AFT_BUF_* que se piden en `columnas_extra`).

    `columnas_extra`: columnas adicionales específicas del cuadro que se va a
    construir (ej. columnas AFT_BOV_* para inventario, o cantvacasord/genero
    para cuadros de ganadero). Si es None, se cargan TODAS las columnas del
    archivo (útil para explorar, pero pesado en memoria).
    """
    especie = especie.lower()
    if especie not in ("bovinos", "bufalinos"):
        raise ValueError(f"especie desconocida: {especie!r} (use 'bovinos' o 'bufalinos')")

    ruta = config.RUTA_CICLO1_ENCUESTA_CRUDO
    if columnas_extra is None:
        columns = None
    else:
        disponibles = fuente_cruda_c1.columnas_disponibles(ruta)
        # CICLO/ANIO siempre se piden para poder validar el archivo abajo,
        # aunque no vengan en `columnas_extra`.
        pedidas = set(_COLS_ID) | set(columnas_extra) | {"CICLO", "ANIO"}
        # Cualquier columna pedida que tenga variante "_NV" (no vacunados) en
        # el archivo se incluye automáticamente - `aplicar_factor_calibracion`
        # y los cuadros de inventario siempre suman la base + su "_NV" junto.
        # Sin esto, "_NV" queda fuera de la selección en silencio (no truena,
        # solo falta del DataFrame) y esas cantidades se pierden sin aviso.
        pedidas |= {f"{c}_NV" for c in pedidas if f"{c}_NV" in disponibles}
        columns = [c for c in disponibles if c in pedidas]

    # `fuente_cruda_c1.leer`: primera vez parsea el .sas7bdat completo y lo
    # cachea en Parquet; de ahí en adelante lee del caché (mucho más rápido -
    # ver docstring de `fuente_cruda_c1.py`).
    df = fuente_cruda_c1.leer(ruta, columns=columns)

    # `ciclo1encuesta.sas7bdat` viene (según su nombre) ya filtrado a Ciclo 1
    # 2025, pero eso no está garantizado por el código - se verifica en vez de
    # asumirlo (mismo criterio que el resto del pipeline de calibración). Trae
    # ~10 filas con CICLO/ANIO en blanco (sin metadata, no son otro ciclo) -
    # se dejan pasar, el `dropna` de abajo ya las descarta si tampoco traen
    # CODIGO_MUNICIPIO.
    if "CICLO" in df.columns and "ANIO" in df.columns:
        mal_ciclo = df[df["CICLO"].notna() & (df["CICLO"] != 1)]
        mal_anio = df[df["ANIO"].notna() & (df["ANIO"] != 2025)]
        if len(mal_ciclo) or len(mal_anio):
            raise ValueError(
                f"ciclo1encuesta.sas7bdat trae {len(mal_ciclo)} filas con CICLO != 1 y {len(mal_anio)} "
                "con ANIO != 2025 - ya no se puede asumir que el archivo viene puro Ciclo 1 2025."
            )

    df = df.dropna(subset=["CODIGO_MUNICIPIO"]).copy()
    df["CODIGO_MUNICIPIO"] = df["CODIGO_MUNICIPIO"].astype(int).astype(str).str.zfill(5)

    # Municipios excluidos del universo por <80% de cobertura de encuesta -
    # idéntico y literal en los 3 programas SAS (4.1/4.2/4.3), ver
    # `config.MUNICIPIOS_EXCLUIDOS_C1`. Se excluyen acá, en la carga
    # compartida, para que aplique igual a inventario y a la base maestra.
    df = df[~df["CODIGO_MUNICIPIO"].isin(config.MUNICIPIOS_EXCLUIDOS_C1)]

    df["ESPECIE_BASE"] = especie
    return df


def renombrar_preguntas(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica el rename R1..R20 -> nombres de negocio (igual a `3. configura base.sas`)."""
    renombres = {k: v for k, v in config.RENOMBRE_PREGUNTAS.items() if k in df.columns}
    return df.rename(columns=renombres)


def normalizar_categoricas(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza texto de genero/orientacionhato/predio_cargo y agrega columnas *Orden.

    Réplica de la sección 8 del preámbulo SAS (idéntica en los 3 programas).
    """
    df = df.copy()

    if "orientacionhato" in df.columns:
        df["orientacionhato"] = df["orientacionhato"].replace(config.ORIENTACION_HATO_NORMALIZA)
        df["ohOrden"] = (
            df["orientacionhato"].map(config.ORIENTACION_HATO_ORDEN).fillna(config.ORIENTACION_HATO_ORDEN_DEFAULT)
        )

    if "GENERO" in df.columns:
        genero = df["GENERO"].replace(config.GENERO_NORMALIZA)
        es_juridica = genero.isna() | (genero.astype(str).str.lower() == "false") | (genero.astype(str).str.strip() == "")
        genero = genero.where(~es_juridica, config.GENERO_JURIDICA)
        df["genero"] = genero
        df["generoOrden"] = df["genero"].map(config.GENERO_ORDEN).fillna(config.GENERO_ORDEN_DEFAULT)

    if "PREDIO_CARGO" in df.columns:
        df["predioCargoOrden"] = (
            df["PREDIO_CARGO"].map(config.PREDIO_CARGO_ORDEN).fillna(config.PREDIO_CARGO_ORDEN_DEFAULT)
        )

    return df


def calcular_predioganid(df: pd.DataFrame) -> pd.DataFrame:
    """predioganid = CODIGO_SIT || ident_ganadero (idéntico a los 3 programas SAS)."""
    df = df.copy()
    df["predioganid"] = df["CODIGO_SIT"].astype(str) + df["IDENT_GANADERO"].astype(str)
    return df


def deduplicar_predio_ganadero(df: pd.DataFrame) -> pd.DataFrame:
    """Cascada de desempate por `predioganid` duplicado (4.2 / 4.3 cuadros *.sas):

    1) mayor `cantvacasord`; 2) entre empatados, mayor `total_aft_bov`;
    3) entre empatados, `fecha_creacion` más reciente.

    Solo debe usarse para cuadros de GANADERO / PREDIO-GANADERO. Los cuadros
    de INVENTARIO (4.1) no aplican esta deduplicación en el SAS original.
    """
    df = calcular_predioganid(df)
    total_col = "TOTAL_AFT_BOV" if "TOTAL_AFT_BOV" in df.columns else "TOTAL_AFTOSA_BOVINOS"
    orden_cols = []
    if "cantvacasord" in df.columns:
        orden_cols.append("cantvacasord")
    if total_col in df.columns:
        orden_cols.append(total_col)
    if "FECHA_CREACION" in df.columns:
        orden_cols.append("FECHA_CREACION")

    if not orden_cols:
        return df.drop_duplicates(subset="predioganid", keep="first")

    df_ordenado = df.sort_values(orden_cols, ascending=False, na_position="last")
    return df_ordenado.drop_duplicates(subset="predioganid", keep="first")


_FACTOR_C1_INVENTARIO_CACHE: dict[str, pd.DataFrame] = {}


def _cargar_factor_c1_calculado(especie: str) -> pd.DataFrame:
    """F_AJUSTA_BOVINOS/BUFALINOS de Ciclo 1 - ver `calibracion_c1.py` para la
    fórmula exacta (replica los programas R oficiales: `TOTAL_AFT_<esp> +
    TOTAL_BRU_<esp>_NV`, factor=0 en vez de 1.0 para municipios sin match en
    Fedegán). NO es lo mismo que `cal_bovinos`/`cal_bufalinos`
    (`calibracion_bovinos_bufalinos_c1.py`) - esa es una fórmula distinta
    (`AFT_<esp>_NV`), para un propósito distinto (comparada contra
    `calibrac12025.xlsx`, no contra el R).

    Se lee de `config.RUTA_FACTOR_C1_INVENTARIO` si ya existe (generado por
    `python -m scripts.cuadros_ganaderia.calibracion_c1`) en vez de
    recalcularlo: recalcular implica releer `ciclo1encuesta.sas7bdat`
    completo dos veces (bovinos + bufalinos) más el Excel de Fedegán - caro
    de repetir en CADA uno de los ~12 procesos que arma un libro completo
    (ver `main.py`). Si el CSV no existe, se calcula igual (con aviso) para
    no bloquear una corrida nueva - pero conviene generarlo una vez antes de
    correr el libro completo. Regenerar manualmente cuando cambie el insumo
    de Fedegán o la fórmula (no hay invalidación automática por fecha)."""
    especie = especie.lower()
    if especie not in _FACTOR_C1_INVENTARIO_CACHE:
        factor_col = "F_AJUSTA_BOVINOS" if especie == "bovinos" else "F_AJUSTA_BUFALINOS"
        if config.RUTA_FACTOR_C1_INVENTARIO.exists():
            factor_todas = pd.read_csv(
                config.RUTA_FACTOR_C1_INVENTARIO, sep=";", decimal=",", encoding="utf-8-sig",
                dtype={"CODIGO_MUNICIPIO": str},
            )
            factor_todas["CODIGO_MUNICIPIO"] = factor_todas["CODIGO_MUNICIPIO"].str.zfill(5)
            factor = factor_todas[["CODIGO_MUNICIPIO", factor_col]]
        else:
            from . import calibracion_c1

            print(
                f"AVISO: {config.RUTA_FACTOR_C1_INVENTARIO.name} no existe - calculando F_AJUSTA_{especie.upper()} "
                "desde cero (más lento). Para acelerar corridas futuras: "
                "`python -m scripts.cuadros_ganaderia.calibracion_c1` una vez."
            )
            factor = calibracion_c1.comparar_especie(especie)[["CODIGO_MUNICIPIO", "factor_calculado"]].rename(
                columns={"factor_calculado": factor_col}
            )
        _FACTOR_C1_INVENTARIO_CACHE[especie] = factor
    return _FACTOR_C1_INVENTARIO_CACHE[especie]


def aplicar_factor_calibracion(df: pd.DataFrame, especie: str, columnas: list[str]) -> pd.DataFrame:
    """Multiplica cada columna de inventario (y su variante _NV) por el factor
    municipal F_AJUSTA_BOVINOS / F_AJUSTA_BUFALINOS, calculado por nosotros
    (ver `_cargar_factor_c1_calculado` / `calibracion_c1.py`)."""
    df = df.copy()
    factor_col = "F_AJUSTA_BOVINOS" if especie.lower() == "bovinos" else "F_AJUSTA_BUFALINOS"
    factor_tabla = _cargar_factor_c1_calculado(especie)
    df = df.drop(columns=[factor_col], errors="ignore").merge(factor_tabla, on="CODIGO_MUNICIPIO", how="left")
    factor = df[factor_col].fillna(1.0)
    for base_col in columnas:
        for col in (base_col, f"{base_col}_NV"):
            if col in df.columns:
                df[col] = df[col].fillna(0) * factor
    return df
