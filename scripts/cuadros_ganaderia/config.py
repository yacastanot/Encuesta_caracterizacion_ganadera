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

# --- Ciclo 2: base consolidada cruda (bovinos+bufalinos en un solo archivo,
# nombres de columna del RUV/DMC sin renombrar) + factor de calibración propio,
# recalculado en `calibracion_c2.py` (ver ese módulo para el porqué: el
# F_AJUSTA_BOVINOS que trae el CSV original viene corrupto). ---
RUTA_C2 = BASES_CALIBRADAS_DIR / "base_ruv_calibrada_C2_2025.csv"
RUTA_FACTOR_C2 = BASES_CALIBRADAS_DIR / "factor_calibracion_C2_2025.csv"

# cal_cobertura / calruv / cal_predios / cal_bovinos / cal_bufalinos de Ciclo 1,
# tomados directo de los Excel originales de Carolina - ver `calibracion_ganadero_c1.py`.
RUTA_FACTOR_GANADERO_C1 = BASES_CALIBRADAS_DIR / "factor_calibracion_ganadero_C1_2025.csv"

# Cruce municipio_id (interno SAS de Carolina) <-> CODIGO_MUNICIPIO (DIVIPOLA),
# y traducción de las 3 listas de códigos centinela - ver `crosswalk_municipio_id_c1.py`.
RUTA_CROSSWALK_MUNICIPIO_ID_C1 = BASES_CALIBRADAS_DIR / "crosswalk_municipio_id_C1.csv"
RUTA_MUNICIPIOS_CENTINELA_C1 = BASES_CALIBRADAS_DIR / "municipios_centinela_C1.csv"

CALIBRACION_DIR = BASE_DIR / "Calibración"
RUTA_FEDEGAN_HISTORICO = CALIBRACION_DIR / "1-Historico-PE-Inventario-Bovino-Bufalino-02132026 - PARA R.xlsx"

# Excepciones de nombre de municipio al cruzar Fedegán x DIVIPOLA (idénticas a
# las de "Scripts calibración R/F_ajusta_bovinos.R" / "F_ajusta_bufalinos.R").
EXCEPCIONES_MUNICIPIO_FEDEGAN = {
    ("BOLÍVAR", "TURBANÁ"): "TURBANA",
    ("CAUCA", "SOTARÁ - PAISPAMBA"): "SOTARÁ PAISPAMBA",
    ("VALLE DEL CAUCA", "SANTIAGO DE CALI"): "CALI",
}

CICLO_C2_DISPONIBLE = "Segundo ciclo nacional de vacunación de 2025"

CUADROS_TEMPLATE_DIR = BASE_DIR / "Cuadros de ssalida publicaciones ciclo I y II de 2025"
TEMPLATE_GANADERO = CUADROS_TEMPLATE_DIR / "Cuadros caracterización del ganadero Ciclos 1 y 2_2025.xlsx"
TEMPLATE_INVENTARIO = CUADROS_TEMPLATE_DIR / "Cuadros caracterización inventario Ciclos 1 y 2_2025.xlsx"
TEMPLATE_PREDIO_GANADERO = CUADROS_TEMPLATE_DIR / "Cuadros Caracterización predio-ganadero Ciclos 1 y 2_2025.xlsx"

OUTPUT_DIR = BASE_DIR / "output"

# Municipios excluidos del universo por tener menos del 80% de encuestas
# (idéntico y literal en los 3 programas SAS: 4.1, 4.2 y 4.3).
# OJO: esta lista usa el "municipio_id" INTERNO de SAS (tabla RUV propia), no el
# código DIVIPOLA de 5 dígitos. No tenemos ese id interno en nuestras bases
# calibradas (solo tenemos CODIGO_MUNICIPIO = código DIVIPOLA real), así que esta
# exclusión NO se puede aplicar todavía tal cual - queda documentada aquí como
# pendiente de mapear id_interno -> codigo DIVIPOLA antes de replicarla.
MUNICIPIOS_ND_ID_INTERNO_SAS = [43, 185, 822, 826, 829, 833, 843, 848]

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
