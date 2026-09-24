# Configuración (`config.py`)

Este proyecto no usa `.env` ni variables de entorno: no maneja credenciales
ni servicios externos con secretos, así que la "única fuente de verdad" que
recomienda el estándar de DANE la cumple directamente
`scripts/cuadros_ganaderia/config.py`, con rutas (`pathlib.Path`) y
constantes de negocio. **Ningún módulo debe construir una ruta o repetir una
constante de negocio por su cuenta - siempre se importa desde `config`.**

## Rutas base

| Constante | Valor | Uso |
|---|---|---|
| `BASE_DIR` | Raíz del repo (2 niveles arriba de `config.py`) | Base de todas las demás rutas |
| `BASES_CALIBRADAS_DIR` | `BASE_DIR / "Bases Calibradas"` | Carpeta de salida de todos los `calibracion_*.py` y de `base_maestra.py` |
| `RUTA_01ENTRADA_2025_I` | `BASE_DIR / "01Entrada" / "2025 I"` | Insumos crudos de Ciclo 1 2025 |
| `RUTA_DIVIPOLA` | `Scripts calibración R/INSUMOS/DIVIPOLA_Municipios.xlsx` | Catálogo territorial completo (`catalogo_territorial.py`) |
| `CUADROS_TEMPLATE_DIR` | `BASE_DIR / "Cuadros para publicación"` | Plantillas Excel oficiales |
| `OUTPUT_DIR` | `BASE_DIR / "output"` | Cuadros ya generados |

## Insumos crudos (Ciclo 1)

| Constante | Archivo | Qué es |
|---|---|---|
| `RUTA_CICLO1_RUV_CRUDO` | `ciclo1ruv.sas7bdat` | Universo RUV completo Ciclo 1 2025 - solo se usa como referencia para `calruv` |
| `RUTA_CICLO1_ENCUESTA_CRUDO` | `ciclo1encuesta.sas7bdat` | Predios del RUV que además respondieron la encuesta - **fuente real de todo el pipeline C1** (ver `01_arquitectura.md`) |
| `RUTA_FEDEGAN_HISTORICO` | `01Entrada/2025 I/1-Historico-PE-Inventario-Bovino-Bufalino...xlsx` | Marco Fedegán, hoja `Cuadro 2_Cobertura` |

## Insumos crudos (Ciclo 2)

| Constante | Archivo | Qué es |
|---|---|---|
| `RUTA_C2` | `base_ruv_calibrada_C2_2025.csv` | Base RUV consolidada cruda C2 (bovinos+bufalinos en un archivo, columnas sin renombrar) |
| `RUTA_FACTOR_C2` | `factor_calibracion_C2_2025.csv` | Factor `F_AJUSTA_BOVINOS/BUFALINOS` de C2, recalculado (`calibracion_c2.py`) |

## Salidas de calibración (todas bajo `BASES_CALIBRADAS_DIR`)

| Constante | Archivo | Generado por |
|---|---|---|
| `RUTA_FACTOR_C1_INVENTARIO` | `factor_calibracion_inventario_C1_2025.csv` | `calibracion_c1.py` - `F_AJUSTA_BOVINOS/BUFALINOS` |
| `RUTA_FACTOR_GANADERO_C1` | `factor_calibracion_ganadero_C1_2025.csv` | `calibracion_ganadero_c1.py` - tabla de 5 factores (`cal_predios`, `cal_bovinos`, `cal_bufalinos`, `cal_cobertura`, `calruv`) |
| `RUTA_CROSSWALK_MUNICIPIO_ID_C1` | `crosswalk_municipio_id_C1.csv` | `crosswalk_municipio_id_c1.py` - `municipio_id` ↔ `CODIGO_MUNICIPIO` para los 1121 municipios |
| `RUTA_MUNICIPIOS_CENTINELA_C1` | `municipios_centinela_C1.csv` | `crosswalk_municipio_id_c1.py` - traducción de las 3 listas de códigos centinela (ND/88888/44444) |

> **`RUTA_BOVINOS`/`RUTA_BUFALINOS`** (`ruv_bovinos/bufalinos_calibrado_C1_2025.csv`)
> quedaron **sin uso** después de migrar `preparar_base.py`/`calibracion_c1.py`
> a leer `ciclo1encuesta.sas7bdat` directamente - eran el insumo original del
> pipeline en R, que no está disponible en este entorno. Se dejaron
> declaradas por si se retoma esa fuente; si no, son candidatas a limpieza.

## Plantillas de publicación

| Constante | Archivo |
|---|---|
| `TEMPLATE_INVENTARIO` | `Cuadros caracterización inventario Ciclos 1 y 2_2025.xlsx` |
| `TEMPLATE_GANADERO` | `Cuadros caracterización del ganadero Ciclos 1 y 2_2025.xlsx` |
| `TEMPLATE_PREDIO_GANADERO` | `Cuadros Caracterización predio-ganadero Ciclos 1 y 2_2025.xlsx` |

## `MUNICIPIOS_EXCLUIDOS_C1`

Lista de 44 códigos `CODIGO_MUNICIPIO` (DIVIPOLA, 5 dígitos) excluidos de
**todo** el pipeline de Ciclo 1, aplicada en
`preparar_base.cargar_base_cruda`. Documentado a fondo en el comentario de la
propia constante (`config.py:73-100`) y en
[01_arquitectura.md](01_arquitectura.md#municipios-excluidos-del-universo).
No editar esta lista sin volver a correr
`validacion_totales_inventario_c1.py` para confirmar el impacto.

## Excepciones de nombre de municipio

`EXCEPCIONES_MUNICIPIO_FEDEGAN`: diccionario `(Departamento, Municipio) ->
Municipio normalizado`, para los 3 casos donde el nombre en Fedegán no
coincide letra por letra con DIVIPOLA (Turbaná/Turbana, Sotará - Paispamba,
Santiago de Cali/Cali). Se usa en **todo** cruce Fedegán↔DIVIPOLA
(`calibracion_c1.py`, `calibracion_c2.py`, `calibracion_predios_c1.py`,
`calibracion_bovinos_bufalinos_c1.py`, `calibracion_cobertura_c1.py`).

## Recodificación de texto y órdenes de fila

Traducción directa de la sección "3. configura base.sas" (idéntica en los 3
programas SAS originales) - normaliza texto y define el orden en que las
categorías deben aparecer como filas en los cuadros:

- `ORIENTACION_HATO_NORMALIZA`, `ORIENTACION_HATO_ORDEN` (+ `_DEFAULT`)
- `GENERO_NORMALIZA`, `GENERO_JURIDICA`, `GENERO_ORDEN` (+ `_DEFAULT`)
- `PREDIO_CARGO_ORDEN` (+ `_DEFAULT`)

## `RENOMBRE_PREGUNTAS`

Mapeo `R3`..`R18`/`R_6_1` (código crudo de pregunta del formulario) →
nombre de variable de negocio (`menores18`, `orientacionhato`,
`cantvacasord`, etc.), idéntico a "3. configura base.sas". **Ya no aplica a
la fuente actual** (`ciclo1encuesta.sas7bdat` trae las preguntas con su
nombre de negocio directo, ver `04_modulos.md` → `preparar_base.py`) -
`preparar_base.renombrar_preguntas()` queda como no-operación segura por si
se vuelve a una fuente con `R#` crudos.

## `PESO_GANADERO_PREDIO_PENDIENTE`

`1.0` - placeholder explícito. El peso real para no duplicar conteos de
predios/ganaderos con fincas en varios municipios todavía no existe
(pendiente del equipo de diseño). Es el único punto del código que hay que
tocar cuando ese peso esté disponible.

## Ver también

- [04_modulos.md](04_modulos.md) - qué módulo usa cada constante.
