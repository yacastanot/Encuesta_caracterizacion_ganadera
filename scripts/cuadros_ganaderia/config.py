"""Rutas y constantes compartidas por todo el pipeline de cuadros.

Traducción a Python de los preámbulos repetidos en los 3 programas SAS de
"Programas Carolina" (4.1, 4.2, 4.3 cuadros *.sas) y de "3. configura base.sas".
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

BASES_CALIBRADAS_DIR = BASE_DIR / "Bases Calibradas"
RUTA_BOVINOS = BASES_CALIBRADAS_DIR / "ruv_bovinos_calibrado_C1_2025.csv"
RUTA_BUFALINOS = BASES_CALIBRADAS_DIR / "ruv_bufalinos_calibrado_C1_2025.csv"

# F_AJUSTA_BOVINOS/BUFALINOS de Ciclo 1 CALCULADOS por nosotros (no el que ya
# trae el CSV) - ver `calibracion_c1.py`. Coincide exacto con el heredado
# (diferencia a nivel de precisión de punto flotante, validado municipio por
# municipio), pero se usa el propio por pedido explícito del usuario: no
# heredar un factor sin haberlo podido calcular y comparar de forma
# independiente primero.
RUTA_FACTOR_C1_INVENTARIO = BASES_CALIBRADAS_DIR / "factor_calibracion_inventario_C1_2025.csv"

RUTA_DIVIPOLA = BASE_DIR / "Scripts calibración R" / "INSUMOS" / "DIVIPOLA_Municipios.xlsx"

# Bases crudas de Ciclo 1 2025 (RUV completo y RUV+encuesta), tal como las exporta
# SAS en "temp.ciclo1ruv" / "temp.ciclo1encuesta" ("3. configura base.sas") - ya
# traen `predioganid` (= CODIGO_SIT || IDENT_GANADERO) precalculado. Se usan para
# recalcular `calruv` de forma independiente en vez de heredarlo de
# calibraencuestac1.xlsx - ver `calibracion_calruv_c1.py`.
RUTA_01ENTRADA_2025_I = BASE_DIR / "01Entrada" / "2025 I"
RUTA_CICLO1_RUV_CRUDO = RUTA_01ENTRADA_2025_I / "ciclo1ruv.sas7bdat"
RUTA_CICLO1_ENCUESTA_CRUDO = RUTA_01ENTRADA_2025_I / "ciclo1encuesta.sas7bdat"

# --- Ciclo 2: insumos crudos reales (exportados directo del RUV/DMC, SIN
# encabezado - el nombre de cada columna viene posicional, del diccionario
# Excel correspondiente, ver `fuente_cruda_c2.py`). A diferencia de Ciclo 1
# (donde "ciclo1encuesta.sas7bdat" ya venía pre-unido con identificación +
# territorio + inventario + respuestas de encuesta), acá son 2 archivos
# separados que hay que unir nosotros (`preparar_ciclo2encuesta.py`):
#  - RUV: universo completo (equivalente a `ciclo1ruv.sas7bdat`).
#  - Encuesta: SOLO respuestas + clave de unión `ruv_id` hacia el RUV (`RUV ID`
#    ahí, NO `CODIGO RUV` pese a lo que sugiere el nombre - ver
#    `preparar_ciclo2encuesta.py`) - equivalente, tras el join, a
#    `ciclo1encuesta.sas7bdat`.
# Copiados localmente con robocopy desde `S:\01Entrada\2025 II\` (solo
# lectura, nunca se escribe ahí - ver `01Entrada/robocopy_2025II.log`).
RUTA_01ENTRADA_2025_II = BASE_DIR / "01Entrada" / "2025 II"
RUTA_CICLO2_RUV_CRUDO = RUTA_01ENTRADA_2025_II / "ExportarArchivoRuv.csv"
RUTA_CICLO2_ENCUESTA_CRUDO = RUTA_01ENTRADA_2025_II / "ExportarArchivoEncuesta2_2025.csv"
RUTA_CICLO2_DICC_RUV = RUTA_01ENTRADA_2025_II / "EncabezadoRuv2-2025.xlsx"
RUTA_CICLO2_DICC_ENCUESTA = RUTA_01ENTRADA_2025_II / "EncabezadoExportarArchivoEncuesta2-2025.xlsx"

# --- Ciclo 2: base YA calibrada por el pipeline legado (R), y su factor de
# calibración propio recalculado en `calibracion_c2.py` (ver ese módulo para
# el porqué: el F_AJUSTA_BOVINOS que trae el CSV original viene corrupto).
# DESDE 2026-09-22 (instrucción explícita del usuario): `RUTA_C2` NO se usa
# como fuente del pipeline - todo se recalcula desde los insumos crudos de
# arriba (`RUTA_CICLO2_*`). Esta base queda reservada solo para comparar al
# final (ver Fase 8 del plan de Ciclo 2), igual que `calibrac12025.xlsx` en
# Ciclo 1 - NUNCA se copia localmente hasta esa fase de validación.
RUTA_C2 = BASES_CALIBRADAS_DIR / "base_ruv_calibrada_C2_2025.csv"
RUTA_FACTOR_C2 = BASES_CALIBRADAS_DIR / "factor_calibracion_C2_2025.csv"

# cal_cobertura / cal_bovinos / cal_bufalinos de Ciclo 1, tomados directo de
# calibrac12025.xlsx (Carolina); calruv y cal_predios ya se recalculan de forma
# independiente (`calibracion_calruv_c1.py` / `calibracion_predios_c1.py`) -
# ver `calibracion_ganadero_c1.py`.
RUTA_FACTOR_GANADERO_C1 = BASES_CALIBRADAS_DIR / "factor_calibracion_ganadero_C1_2025.csv"

# calruv/cal_predios/cal_bovinos/cal_bufalinos/cal_cobertura de Ciclo 2, LOS 5
# recalculados de cero (no hay ningún archivo heredado tipo `calibrac12025.xlsx`
# para Ciclo 2) - ver `calibracion_ganadero_c2.py`.
RUTA_FACTOR_GANADERO_C2 = BASES_CALIBRADAS_DIR / "factor_calibracion_ganadero_C2_2025.csv"

# Cruce municipio_id (interno SAS de Carolina) <-> CODIGO_MUNICIPIO (DIVIPOLA),
# y traducción de las 3 listas de códigos centinela - ver `crosswalk_municipio_id_c1.py`.
RUTA_CROSSWALK_MUNICIPIO_ID_C1 = BASES_CALIBRADAS_DIR / "crosswalk_municipio_id_C1.csv"
RUTA_MUNICIPIOS_CENTINELA_C1 = BASES_CALIBRADAS_DIR / "municipios_centinela_C1.csv"

# OJO: este archivo vive en "01Entrada/2025 I/" (no en una carpeta
# "Calibración/" separada - esa ruta ya no existe, quedó de una reorganización
# de carpetas anterior).
RUTA_FEDEGAN_HISTORICO = RUTA_01ENTRADA_2025_I / "1-Historico-PE-Inventario-Bovino-Bufalino-02132026 - PARA R.xlsx"

# Excepciones de nombre de municipio al cruzar Fedegán x DIVIPOLA (idénticas a
# las de "Scripts calibración R/F_ajusta_bovinos.R" / "F_ajusta_bufalinos.R").
EXCEPCIONES_MUNICIPIO_FEDEGAN = {
    ("BOLÍVAR", "TURBANÁ"): "TURBANA",
    ("CAUCA", "SOTARÁ - PAISPAMBA"): "SOTARÁ PAISPAMBA",
    ("VALLE DEL CAUCA", "SANTIAGO DE CALI"): "CALI",
}

CICLO_C2_DISPONIBLE = "Segundo ciclo nacional de vacunación de 2025"

# --- Histórico 2023/2024: SOLO para el Cuadro 4/5 del libro "ganadero"
# ("nuevos/salieron/se mantienen" ganaderos respecto al ciclo anterior / al
# mismo ciclo del año anterior) - ningún otro cuadro los usa. Copiados
# localmente con robocopy desde `S:\2024\01Entrada` / `S:\2023\01entrada`
# (solo lectura, nunca se escribe ahí), seleccionando de cada carpeta (con
# muchas versiones candidatas) el archivo con fecha de modificación más
# reciente - instrucción explícita del usuario (2026-09-24).
RUTA_01ENTRADA_2024 = BASE_DIR / "01Entrada" / "2024"
# RUV 2024: `ruv.sas7bdat` (10-abr, más reciente que `ruvc1`/`ruvc2` del
# 4-abr por separado) - verificado que es exactamente la unión de esos 2
# (1.510.416 filas = 757.103 + 753.313), con columnas CICLO/ANIO para
# separar cada ciclo, y nombres de columna ya cortos (AFT_BOV_*, no la
# versión truncada AFTOSA_BOVINOS_* de ruvc1/ruvc2).
RUTA_2024_RUV_CRUDO = RUTA_01ENTRADA_2024 / "ruv.sas7bdat"
# Encuesta 2024: separada del RUV (se unen por `RUV_ID`, mismo patrón que
# Ciclo 2 2025 - ver `preparar_ciclo2encuesta.py`). Candidato más reciente
# por ciclo (de 4 y 2 versiones respectivamente, ver docstring de
# `preparar_2024encuesta.py`).
RUTA_2024_ENCUESTA_C1_CRUDO = RUTA_01ENTRADA_2024 / "encuestac1corregida.sas7bdat"
RUTA_2024_ENCUESTA_C2_CRUDO = RUTA_01ENTRADA_2024 / "encuestac2_.sas7bdat"

# 2023: a diferencia de 2024, NO hay un insumo crudo reciente y sin ambigüedad
# (los candidatos crudos son de 2024, con múltiples versiones sin corregir
# claras) - los archivos con fecha de modificación más reciente de toda la
# carpeta (`c12023.sas7bdat`/`c22023.sas7bdat`, 1-sep-2025) ya vienen
# RUV+encuesta unidos Y calibrados por el pipeline legado (traen
# `predioganid`/`gan_cal`/`cal_cobertura` ya calculados). Decisión del
# usuario (2026-09-24): usarlos tal cual para 2023 - a diferencia de 2024/2025,
# 2023 solo sirve de referencia para el "ciclo anterior" de Cuadro 4/5, no se
# publica ningún cuadro de 2023 en este libro, así que no hace falta
# recalibrar desde cero para ese único año.
RUTA_01ENTRADA_2023 = BASE_DIR / "01Entrada" / "2023"
RUTA_2023_C1 = RUTA_01ENTRADA_2023 / "c12023.sas7bdat"
RUTA_2023_C2 = RUTA_01ENTRADA_2023 / "c22023.sas7bdat"

CUADROS_TEMPLATE_DIR = BASE_DIR / "Cuadros para publicación"
TEMPLATE_GANADERO = CUADROS_TEMPLATE_DIR / "Cuadros caracterización del ganadero Ciclos 1 y 2_2025.xlsx"
TEMPLATE_INVENTARIO = CUADROS_TEMPLATE_DIR / "Cuadros caracterización inventario Ciclos 1 y 2_2025.xlsx"
TEMPLATE_PREDIO_GANADERO = CUADROS_TEMPLATE_DIR / "Cuadros Caracterización predio-ganadero Ciclos 1 y 2_2025.xlsx"

OUTPUT_DIR = BASE_DIR / "output"

# Municipios excluidos del universo de Ciclo 1 2025, por 3 motivos distintos
# (confirmados con el usuario, 2026-09-18) - en los 3 casos se excluyen TODOS
# los predios del municipio de todo el pipeline (inventario y, a futuro,
# ganadero/predio-ganadero), vía `preparar_base_c1.cargar_base_cruda`:
#
# 1) <80% de cobertura de encuesta sobre el RUV completo (idéntico y literal
#    en los 3 programas SAS: 4.1, 4.2 y 4.3). El "municipio_id" interno de SAS
#    (43, 185, 822, 826, 829, 833, 843, 848) ya se resolvió a CODIGO_MUNICIPIO
#    vía `crosswalk_municipio_id_c1.py` (fuente: "01Entrada/2025 I/para
#    calibrar formulado fedegan.xlsx"). Verificado (2026-09-16): se recalculó
#    la cobertura real de los 1121 municipios (cantpredganencuesta/
#    cantpredganruv, ver `calibracion_calruv_c1.py`) y estos 8 son
#    EXACTAMENTE los únicos con <80% - no se detectó ningún caso adicional.
#    Confirmado además (2026-09-18) contra el archivo oficial "municipios
#    menores al 80.xlsx" - coincide exacto, fila por fila.
# 2) Zona ZLSV/"o.c." ("Excluidos/Municipios ZLSV_OC_ciclos 2025.xlsx",
#    oficial, 27 municipios - aplica igual a Ciclo 1 y Ciclo 2, según el
#    propio archivo): fuera del programa de vacunación/reporte de Fedegán.
#    23 de los 27 YA no tenían ningún registro RUV (códigos centinela
#    88888/44444 de `crosswalk_municipio_id_c1.py`), pero se agregan acá
#    explícitos de todas formas (2026-09-19, pedido del usuario) para no
#    depender de que "no tenga RUV" siga siendo cierto con datos futuros.
#    Los otros 4 (Acandí/Carmen del Darién/Riosucio/Unguía) sí tenían RUV
#    activo - explica por qué Acandí/Unguía no tenían fila en Fedegán ese
#    ciclo (ver `calibracion_c1.py`) y por qué Riosucio es el único municipio
#    donde Fedegán reportaba menos que el RUV (ver `calibracion_c2.py`).
# 3) Encuestas repetidas ("Excluidos/Municipios Salen Encuestas
#    repetidas_Ciclo 1_2025.xlsx", oficial): municipios con una proporción
#    alta (21%-89%) de encuestas duplicadas - dato de encuesta no confiable.
#    `municipio_id` resuelto vía `crosswalk_municipio_id_c1.py`. Ninguno
#    coincidía con las exclusiones previas - los 32 son nuevos.
_EXCLUIDOS_C1_COBERTURA = {
    "05040": "Anorí, Antioquia",
    "13030": "Altos del Rosario, Bolívar",
    "54206": "Convención, Norte de Santander",
    "54250": "El Tarra, Norte de Santander",
    "54344": "Hacarí, Norte de Santander",
    "54398": "La Playa, Norte de Santander",
    "54670": "San Calixto, Norte de Santander",
    "54800": "Teorama, Norte de Santander",
}
_EXCLUIDOS_C1_ZLSV = {
    "27006": "Acandí, Chocó (ZLSV)",
    "27075": "Bahía Solano, Chocó (ZLSV)",
    "27099": "Bojayá, Chocó (ZLSV)",
    "27150": "Carmen del Darién, Chocó (ZLSV)",
    "27372": "Juradó, Chocó (ZLSV)",
    "27615": "Riosucio, Chocó (ZLSV)",
    "27800": "Unguía, Chocó (ZLSV)",
    "88001": "San Andrés, San Andrés y Providencia (ZLSV)",
    "88564": "Providencia, San Andrés y Providencia (ZLSV)",
    "91001": "Leticia, Amazonas (o.c.)",
    "91263": "El Encanto, Amazonas (o.c.)",
    "91405": "La Chorrera, Amazonas (o.c.)",
    "91407": "La Pedrera, Amazonas (o.c.)",
    "91430": "La Victoria, Amazonas (o.c.)",
    "91460": "Miritý-Paraná, Amazonas (o.c.)",
    "91530": "Puerto Alegría, Amazonas (o.c.)",
    "91536": "Puerto Arica, Amazonas (o.c.)",
    "91540": "Puerto Nariño, Amazonas (o.c.)",
    "91669": "Puerto Santander, Amazonas (o.c.)",
    "91798": "Tarapacá, Amazonas (o.c.)",
    "95200": "Miraflores, Guaviare (o.c.)",
    "97001": "Mitú, Vaupés (o.c.)",
    "97161": "Carurú, Vaupés (o.c.)",
    "97511": "Pacoa, Vaupés (o.c.)",
    "97666": "Taraira, Vaupés (o.c.)",
    "97777": "Papunahua, Vaupés (o.c.)",
    "97889": "Yavaraté, Vaupés (o.c.)",
}
_EXCLUIDOS_C1_ENCUESTAS_REPETIDAS = {
    "05044": "Anzá, Antioquia (30% encuestas duplicadas)",
    "05113": "Buriticá, Antioquia (33% encuestas duplicadas)",
    "05125": "Caicedo, Antioquia (30% encuestas duplicadas)",
    "05197": "Cocorná, Antioquia (32% encuestas duplicadas)",
    "05308": "Girardota, Antioquia (31% encuestas duplicadas)",
    "05318": "Guarne, Antioquia (24% encuestas duplicadas)",
    "05321": "Guatapé, Antioquia (38% encuestas duplicadas)",
    "05364": "Jardín, Antioquia (32% encuestas duplicadas)",
    "05440": "Marinilla, Antioquia (48% encuestas duplicadas)",
    "05467": "Montebello, Antioquia (66% encuestas duplicadas)",
    "05543": "Peque, Antioquia (24% encuestas duplicadas)",
    "05576": "Pueblorrico, Antioquia (34% encuestas duplicadas)",
    "05697": "El Santuario, Antioquia (40% encuestas duplicadas)",
    "05819": "Toledo, Antioquia (21% encuestas duplicadas)",
    "15299": "Garagoa, Boyacá (41% encuestas duplicadas)",
    "15380": "La Capilla, Boyacá (59% encuestas duplicadas)",
    "15491": "Nobsa, Boyacá (89% encuestas duplicadas)",
    "15798": "Tenza, Boyacá (72% encuestas duplicadas)",
    "17495": "Norcasia, Caldas (42% encuestas duplicadas)",
    "17513": "Pácora, Caldas (40% encuestas duplicadas)",
    "25524": "Pandi, Cundinamarca (42% encuestas duplicadas)",
    "25594": "Quetame, Cundinamarca (29% encuestas duplicadas)",
    "25841": "Ubaque, Cundinamarca (48% encuestas duplicadas)",
    "25878": "Viotá, Cundinamarca (31% encuestas duplicadas)",
    "41006": "Acevedo, Huila (41% encuestas duplicadas)",
    "41078": "Baraya, Huila (37% encuestas duplicadas)",
    "41503": "Oporapa, Huila (37% encuestas duplicadas)",
    "52079": "Barbacoas, Nariño (86% encuestas duplicadas)",
    "52323": "Gualmatán, Nariño (24% encuestas duplicadas)",
    "54245": "El Carmen, Norte de Santander (52% encuestas duplicadas)",
    "66318": "Guática, Risaralda (47% encuestas duplicadas)",
    "76318": "Guacarí, Valle del Cauca (78% encuestas duplicadas)",
}

MUNICIPIOS_EXCLUIDOS_C1 = (
    list(_EXCLUIDOS_C1_COBERTURA) + list(_EXCLUIDOS_C1_ZLSV) + list(_EXCLUIDOS_C1_ENCUESTAS_REPETIDAS)
)

# CODIGO_MUNICIPIO -> texto de razón, para cuadros/reportes que necesitan
# explicar CADA exclusión (ej. Cuadro 2 "Municipios sin información
# asociada", `validacion_totales_inventario_c1.py`) - una sola fuente de
# verdad en vez de repetir el motivo en cada consumidor.
RAZON_EXCLUSION_C1 = {
    **{k: "Menos del 80% de cobertura de encuesta sobre el RUV" for k in _EXCLUIDOS_C1_COBERTURA},
    **{k: 'Zona ZLSV/"o.c." - fuera del programa de vacunación/reporte de Fedegán' for k in _EXCLUIDOS_C1_ZLSV},
    **{
        k: "Alta proporción de encuestas duplicadas (municipio con encuestas repetidas)"
        for k in _EXCLUIDOS_C1_ENCUESTAS_REPETIDAS
    },
}

# Municipios excluidos del universo de Ciclo 2 2025, por 3 motivos (mismo
# criterio que MUNICIPIOS_EXCLUIDOS_C1, sección 2026-09-18/19):
#
# 1) Zona ZLSV/"o.c." (27, idéntica a la de C1) - "Excluidos/Municipios
#    ZLSV_OC_ciclos 2025.xlsx" trae columnas separadas para 1er/2do ciclo y
#    confirma que aplica a los dos por igual (2026-09-19, pedido del
#    usuario: los 27 se agregan explícitos, no solo los que ya no tenían RUV).
# 2) Encuestas repetidas (20) - "Excluidos/Municipios Salen Encuestas
#    repetidas_Ciclo 2_2025.xlsx" (oficial, específico de C2 - NO es el mismo
#    archivo/lista que la de Ciclo 1: de 20 municipios, 9 coinciden con la
#    lista de C1 y 11 son exclusivos de C2). `municipio_id` resuelto vía
#    `crosswalk_municipio_id_c1.py` (el crosswalk municipio_id<->CODIGO_MUNICIPIO
#    no depende del ciclo).
#
# 3) <80% de cobertura de encuesta (motivo 1 de C1) - YA calculado con datos
#    propios de Ciclo 2 (`calibracion_calruv_c2.calcular_calruv` +
#    `_validar`, cobertura = cantpredganencuesta/cantpredganruv por
#    municipio), confirmado por el usuario 2026-09-22. 17 municipios, 6 con
#    0% exacto (vacunados sin ninguna encuesta respondida). Notable: 6 de
#    estos 17 coinciden EXACTO con municipios de la lista de C1 (Anorí,
#    Altos del Rosario, Convención, El Tarra, Hacarí, San Calixto) - mismas
#    zonas de baja cobertura en los 2 ciclos, refuerza confianza en el cálculo.
_EXCLUIDOS_C2_COBERTURA = {
    "05055": "Argelia, Antioquia (0% cobertura)",
    "13458": "Montecristo, Bolívar (0% cobertura)",
    "94001": "Inírida, Guainía (0% cobertura)",
    "94343": "Barrancominas, Guainía (0% cobertura)",
    "54250": "El Tarra, Norte de Santander (0% cobertura)",
    "54670": "San Calixto, Norte de Santander (0% cobertura)",
    "54800": "Teorama, Norte de Santander (0% cobertura)",
    "13810": "Tiquisio, Bolívar (0.4% cobertura)",
    "54206": "Convención, Norte de Santander (2.3% cobertura)",
    "54344": "Hacarí, Norte de Santander (4.7% cobertura)",
    "13006": "Achí, Bolívar (9.2% cobertura)",
    "18150": "Cartagena del Chairá, Caquetá (53.1% cobertura)",
    "05040": "Anorí, Antioquia (62.3% cobertura)",
    "05652": "San Francisco, Antioquia (63.4% cobertura)",
    "18753": "San Vicente del Caguán, Caquetá (69.2% cobertura)",
    "13490": "Norosí, Bolívar (71.1% cobertura)",
    "13030": "Altos del Rosario, Bolívar (78.8% cobertura)",
}
_EXCLUIDOS_C2_ZLSV = _EXCLUIDOS_C1_ZLSV  # idéntica a C1 - el archivo oficial aplica a ambos ciclos por igual

_EXCLUIDOS_C2_ENCUESTAS_REPETIDAS = {
    "05197": "Cocorná, Antioquia (22% encuestas duplicadas)",
    "05308": "Girardota, Antioquia (33% encuestas duplicadas)",
    "05321": "Guatapé, Antioquia (22% encuestas duplicadas)",
    "05483": "Nariño, Antioquia (20% encuestas duplicadas)",
    "05628": "Sabanalarga, Antioquia (23% encuestas duplicadas)",
    "05697": "El Santuario, Antioquia (28% encuestas duplicadas)",
    "15215": "Corrales, Boyacá (28% encuestas duplicadas)",
    "15380": "La Capilla, Boyacá (24% encuestas duplicadas)",
    "15491": "Nobsa, Boyacá (44% encuestas duplicadas)",
    "15550": "Pisba, Boyacá (21% encuestas duplicadas)",
    "15759": "Sogamoso, Boyacá (31% encuestas duplicadas)",
    "15798": "Tenza, Boyacá (51% encuestas duplicadas)",
    "15822": "Tota, Boyacá (51% encuestas duplicadas)",
    "19364": "Jambaló, Cauca (29% encuestas duplicadas)",
    "25053": "Arbeláez, Cundinamarca (23% encuestas duplicadas)",
    "25335": "Guayabetal, Cundinamarca (31% encuestas duplicadas)",
    "25594": "Quetame, Cundinamarca (41% encuestas duplicadas)",
    "25841": "Ubaque, Cundinamarca (55% encuestas duplicadas)",
    "44560": "Manaure, La Guajira (40% encuestas duplicadas)",
    "44847": "Uribia, La Guajira (60% encuestas duplicadas)",
}

# Verificado 2026-09-22: los 17 de `_EXCLUIDOS_C2_COBERTURA` NO se solapan
# con ZLSV ni con encuestas repetidas - son 71 municipios excluidos en total.
MUNICIPIOS_EXCLUIDOS_C2 = (
    list(_EXCLUIDOS_C2_COBERTURA) + list(_EXCLUIDOS_C2_ZLSV) + list(_EXCLUIDOS_C2_ENCUESTAS_REPETIDAS)
)

RAZON_EXCLUSION_C2 = {
    **{k: "Menos del 80% de cobertura de encuesta sobre el RUV" for k in _EXCLUIDOS_C2_COBERTURA},
    **{k: 'Zona ZLSV/"o.c." - fuera del programa de vacunación/reporte de Fedegán' for k in _EXCLUIDOS_C2_ZLSV},
    **{
        k: "Alta proporción de encuestas duplicadas (municipio con encuestas repetidas)"
        for k in _EXCLUIDOS_C2_ENCUESTAS_REPETIDAS
    },
}

# Ciclo nacional de vacunación cuya base tenemos disponible en esta iteración.
CICLO_DISPONIBLE = "Primer ciclo nacional de vacunación de 2025"

# --- Recodificación de texto (idéntica en los 3 programas SAS, sección "3. configura base.sas") ---

ORIENTACION_HATO_NORMALIZA = {
    "Ganadería de leche": "Ganadería de Leche",
}

GENERO_NORMALIZA = {
    "HOMBRE": "Hombre",
    "MUJER": "Mujer",
}
GENERO_JURIDICA = "juridi"  # genero='false' o vacío -> persona jurídica

ORIENTACION_HATO_ORDEN = {
    "Ganadería de Leche": 1,
    "Doble propósito": 2,
    "Genética": 3,
    "Cría": 4,
    "Levante": 5,
    "Ceba": 6,
}
ORIENTACION_HATO_ORDEN_DEFAULT = 99

GENERO_ORDEN = {
    "Mujer": 1,
    "Hombre": 2,
    GENERO_JURIDICA: 3,
}
GENERO_ORDEN_DEFAULT = 99

PREDIO_CARGO_ORDEN = {
    "PROPIO": 1,
    "ARRENDADO": 2,
    "POSEEDOR": 3,
    "TENEDOR": 4,
    "TERRITORIO COLECTIVO": 5,
    "OTRO": 6,
}
PREDIO_CARGO_ORDEN_DEFAULT = 99

# --- Peso de calibración pendiente (predios/ganaderos) ---
# Adriana confirmó en la reunión del 2026-08-05 que la ponderación para no duplicar
# conteos de predios/ganaderos con fincas en varios municipios AÚN NO existe (paso
# pendiente de una reunión suya). Ni las bases calibradas ni los scripts R traen ese
# peso. Por decisión explícita del usuario (2026-08-25): se construyen esos cuadros
# con PESO_GANADERO_PREDIO_PENDIENTE = 1.0 (sin ponderar), dejando este único punto
# para conectar el peso real apenas exista.
PESO_GANADERO_PREDIO_PENDIENTE = 1.0

# Preguntas R1-R20 del formulario -> nombres de variable (igual a "3. configura base.sas")
RENOMBRE_PREGUNTAS = {
    # R1/R2 NO están en "3. configura base.sas" (r1=/r2= no existen ahí) - el
    # SAS original nunca las usó en ningún cuadro. A diferencia de R3 en
    # adelante, tampoco vienen pre-renombradas en el .sas7bdat crudo (siguen
    # literalmente "R1"/"R2") - se renombran acá porque Cuadro 10 (R2) y
    # Cuadro 11 (R1) sí las necesitan.
    "R1": "atendioencuesta",
    "R2": "lugarresidencia",
    "R3": "menores18",
    "R4": "edadganadero",
    "R5": "compartelote",
    "R6_1": "abigeato",
    "R6_2": "carneo",
    "R6_3": "extorsion",
    "R6_4": "hurto",
    "R6_5": "invasiontierra",
    "R6_6": "secuestro",
    "R6_7": "otro",
    "R6_8": "ninguno",
    # --- OJO: desfase de 1 confirmado empíricamente ---
    # "3. configura base.sas" hace `rename r8=orientacionhato r12=sistemaproductivo
    # ...` pero esa numeración aplica a la tabla cruda `temp.encuestac1` de
    # Carolina, que sí trae una columna R7 = "cualotrodelito" (texto abierto,
    # pregunta 6.7.1) independiente. En NUESTRA base calibrada esa columna no
    # existe como tal, así que desde R7 en adelante todo queda corrido un
    # puesto. Verificado con las categorías de texto REALES en el CSV (no por
    # posición): R7 trae exactamente {Ganadería de Leche, Doble propósito,
    # Ceba, Cría, Levante, Genética} (=pregunta 8 del papel) y R11 trae
    # exactamente {Pastoreo mejorado, Pastoreo extractivo, Silvopastoril,
    # Estabulado} (=pregunta 11/12 del papel). R12-R18 se confirmaron después
    # contra el diccionario de datos oficial (ver más abajo) - ya no son una
    # inferencia.
    "R7": "orientacionhato",
    "R8": "cantvacasord",
    "R9": "cantlt",
    "R10": "canttrabaj",
    "R11": "sistemaproductivo",
    # R12-R18 confirmados contra `Programas Carolina/Diccionario de datos_Base_Ruv_1_17102025.xlsx`
    # (Hoja2, columna "Etiqueta") - ya no son una inferencia por texto/posición.
    "R12": "consensoresepidem",
    "R13": "conalertatem",
    "R14": "debenotificarica",
    "R15": "signosclinicos",
    "R16": "tienecolmenas",
    # R17 NO es "numcolmenas" (lo que se había supuesto antes de tener el
    # diccionario, a partir de ver que se veía booleano Si/No en vez de
    # numérico): el diccionario confirma que es "conformacion" - coincide con
    # que se viera Si/No.
    "R17": "conformacion",
    "R18": "intcarrera",
    "R_6_1": "cualotrodelito",  # pregunta 6.7.1: texto abierto de "otro" delito
}

# Preguntas R1-R29 de Ciclo 2 (2025-II) -> nombres de variable. NO es la misma
# numeración que `RENOMBRE_PREGUNTAS` (Ciclo 1): el cuestionario cambió por
# completo entre ciclos (más preguntas - 19 vs 20 "de papel", 29 columnas R
# crudas por los sub-ítems de opción múltiple/desglose - y varias preguntas
# nuevas). Confirmado 2026-09-22 de 2 formas independientes que coinciden
# palabra por palabra: (1) el texto literal de cada pregunta viene repetido en
# cada fila de `ExportarArchivoEncuesta2_2025.csv` (columnas `P1`..`P29`,
# `nunique()==1` cada una sobre las 736.149 filas completas, cero ambigüedad);
# (2) el formulario oficial `Formato de sistemas ENCUESTA 2-2025 Vr2.xlsx`
# (hoja "2-2025", columna "PREGUNTA"), que documenta el mismo texto para las
# preguntas 1-19 "de papel". Los otros 2 diccionarios candidatos que existen
# en el servidor (`OE-DG-09 Diccionario de datos.xlsx`, que trae la
# numeración de CICLO 1 por error; `Listado_columnas_ECG_C2_2025.xlsx`, que es
# un archivo derivado del pipeline legado) NO se usaron como fuente - ninguno
# de los 2 es confiable para esto.
#
# IMPORTANTE - preguntas de Ciclo 1 que NO existen en Ciclo 2 (confirmado
# sobre el archivo completo, no aparecen en ningún P1-P29 ni en el RUV crudo):
# `canttrabaj` (Cuadro 5 predio-ganadero), `menores18` (Cuadro 13),
# `tienecolmenas`/`numcolmenas` (Cuadro 14), `conformacion`/`intcarrera`
# (Cuadro 16 del libro ganadero) - el cuestionario de Ciclo 2 las sustituyó
# por las preguntas nuevas de área/cobertura de suelo, razas y área protegida
# (R14-R21, R8-R12, R26) - ver `preparar_ciclo2encuesta.py`.
RENOMBRE_PREGUNTAS_C2 = {
    "R1": "atendioencuesta",
    "R2": "lugarresidencia",
    "R3": "orientacionhato",
    "R4": "cantvacasord",
    "R5": "cantlt",
    "R6": "promliterosdiarios",  # nueva: "En promedio, ¿cuántos litros diarios producen sus vacas?"
    "R7": "preciolitro",  # nueva: "¿En cuánto vendió cada litro de leche ayer?"
    "R8_1": "tienerazapura",  # nueva (Cuadro 18): flag "X"/blanco, pregunta 8 opción múltiple
    "R8_2": "tienerazacruce",  # nueva (Cuadro 18): flag "X"/blanco
    "R9": "razapurapredominante",  # nueva (Cuadro 19), pregunta 8.1
    "R10": "otrarazapuracual",  # pregunta 8.1.1, texto abierto
    "R11": "razacrucepredominante",  # nueva (Cuadro 19), pregunta 8.2
    "R12": "otrarazacrucecual",  # pregunta 8.2.1, texto abierto
    "R13": "compartelote",
    "R14": "unidadmedidaarea",  # nueva, pregunta 10 (Hectáreas/Fanegadas/Plaza o cuadra/m²)
    "R15": "areatotalfinca",  # nueva (Cuadro 15/16), pregunta 11
    "R16": "areaagricola",  # nueva (Cuadro 15), pregunta 11.1.1
    "R17": "areaproducanimales",  # nueva (Cuadro 15), pregunta 11.1.2
    "R18": "areaforestal",  # nueva (Cuadro 15), pregunta 11.1.3
    "R19": "areaconstrucciones",  # nueva (Cuadro 15), pregunta 11.1.4
    "R20": "areaotrosusos",  # nueva (Cuadro 15), pregunta 11.1.5
    "R21": "areaganaderiabovbuf",  # nueva (Cuadro 16), pregunta 12
    "R22": "consensorepidem",  # mismo nombre que usa base_maestra_c1.py/ganadero.py para C1
    "R23": "conalertatem",
    "R24": "debenotificarica",
    "R25": "signosclinicos",
    "R26": "areaprotegida",  # nueva (Cuadro 17), pregunta 17
    # Pregunta 18 (delitos), flags "X"/blanco. Orden R27_1..7 asumido IGUAL al
    # de Ciclo 1 (R6_1..7 en `RENOMBRE_PREGUNTAS`) por continuidad del diseño
    # de la encuesta - NO verificado contra una lista de opciones oficial
    # (no se encontró ninguna en el servidor) - SÍ verificado que R27_8
    # ("ninguno") es la opción "índice 2" (exclusiva) que describe el
    # formulario oficial: 97.3% de las respuestas la marcan, consistente con
    # "no víctima de ningún delito" siendo la respuesta mayoritaria. Revisar
    # esta asunción de orden antes de publicar Cuadro 6 del libro ganadero
    # para Ciclo 2.
    "R27_1": "abigeato",
    "R27_2": "carneo",
    "R27_3": "extorsion",
    "R27_4": "hurto",
    "R27_5": "invasiontierra",
    "R27_6": "secuestro",
    "R27_7": "otro",
    "R27_8": "ninguno",
    "R28": "cualotrodelito",  # pregunta 18.7.1, texto abierto
    # Pregunta 19 (medios de comunicación), nueva - 6 flags "X"/blanco. El
    # formulario oficial señala "Falta la opción NINGUNO" (columna "NOMBRE
    # VARIABLE" de la especificación) - no hay una 7ma opción "ninguno" como
    # en delitos. Etiquetas de cada opción (R29_1..6) NO confirmadas contra
    # una lista oficial - nombres genéricos hasta poder verificarlas.
    "R29_1": "medio_comunicacion_1",
    "R29_2": "medio_comunicacion_2",
    "R29_3": "medio_comunicacion_3",
    "R29_4": "medio_comunicacion_4",
    "R29_5": "medio_comunicacion_5",
    "R29_6": "medio_comunicacion_6",
}
