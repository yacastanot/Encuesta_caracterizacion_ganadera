# Módulos (`scripts/cuadros_ganaderia/*.py`)

Un bloque por archivo: propósito, cómo se ejecuta (si aplica) y cómo se
relaciona con los demás. Agrupados por función, no alfabéticamente.

## Configuración y catálogos

### `config.py`
Rutas y constantes compartidas por todo el pipeline. Ver
[03_configuracion.md](03_configuracion.md) para el detalle campo por campo.

### `catalogo_territorial.py`
Universo territorial completo DIVIPOLA (~1122 municipios, ~33 departamentos),
leído de `RUTA_DIVIPOLA` y cacheado en memoria (`@lru_cache`). Expone
`cargar_catalogo_municipios()` y `cargar_catalogo_departamentos()`. Es la
fuente que usa `agregador.py` para que todo cuadro muestre el universo
completo aunque un municipio no tenga datos.

### `fuente_cruda.py`
Acceso cacheado a `ciclo1ruv.sas7bdat`/`ciclo1encuesta.sas7bdat`: la primera
vez que se piden, se parsean completos con `pyreadstat` y se cachean en
Parquet (`Bases Calibradas/_cache_*.parquet`); de ahí en adelante se lee del
caché. **`encoding="utf-8"` - CORREGIDO 2026-09-21**: antes usaba
`encoding="latin1"` (por un `UnicodeDecodeError` que ya no se pudo
reproducir), lo que corrompía en silencio CUALQUIER columna de texto con
tildes (cada caracter UTF-8 multibyte se decodificaba mal como 2 caracteres
latin1). Esto rompía comparaciones de texto exacto contra esas columnas sin
lanzar ningún error - se detectó porque Cuadro 4 del libro de inventario
("por orientación de hato") perdía ~84% del inventario bovino: las 4
categorías con tilde de 6 (Leche/Cría/Doble propósito/Genética) quedaban en
cero, solo Ceba/Levante (sin tilde) tenían datos. Si se vuelve a tocar este
módulo, regenerar los cachés (borrar los `.parquet`) y reconstruir
`base_maestra.py`/`base_maestra_inventario.py` después de cualquier cambio
de encoding - nunca se detecta solo, hay que revisar manualmente una columna
con tildes.

## Motor de agregación y escritura

### `agregador.py`
`generar_cuadro(df, value_cols, group_extra=None)`: agrega un DataFrame ya
preparado a nivel Nacional → Departamento → Municipio, haciendo *join
completo* (no inner) contra `catalogo_territorial` para que ningún municipio
se pierda. Traducción directa de la macro SAS `%generar_cuadro_custom3`,
idéntica en los 3 programas originales. Todo cuadro de inventario pasa por
acá al final.

### `redistribucion.py`
`redistribuir_por_categoria(df, columna_categoria, columnas_valor,
categorias)`: reparte proporcionalmente el valor de los registros sin dato en
una variable de cruce (ej. `orientacionhato`) entre las categorías conocidas,
según la mezcla municipal (o nacional si el municipio no tiene ninguna
categoría conocida). Se usa en el Cuadro 4/5 (inventario bovino por
orientación de hato); el mismo patrón se reutilizará en los futuros cuadros
de "ganadero" que necesiten la misma imputación.

### `excel_writer.py`
`escribir_cuadro(origen, destino, hoja, fila_inicio, tabla, value_cols,
columna_inicio=...)`: abre la plantilla Excel real y solo inserta/llena el
bloque de filas de datos, clonando el estilo de celda de la fila de ejemplo.
Nunca reconstruye el archivo desde cero. Es **idempotente**: antes de
escribir borra cualquier fila que una corrida anterior haya dejado en esa
hoja, así que volver a correr un cuadro dos veces no acumula filas
huérfanas - necesario porque cada cuadro corre en su propio proceso Python
(ver `main.py`).

## Calibración - Ciclo 1

Todos siguen el mismo patrón: cargar insumo crudo → calcular factor propio →
(si hay heredado) comparar → guardar. Ver
[01_arquitectura.md](01_arquitectura.md) para la tabla completa de los 5
factores y por qué existe cada uno.

### `crosswalk_municipio_id_c1.py`
Traduce el `municipio_id` interno de los programas SAS de Carolina a
`CODIGO_MUNICIPIO` (DIVIPOLA), usando `01Entrada/2025 I/para calibrar
formulado fedegan.xlsx` como fuente de verdad (trae ambos códigos para los
1121 municipios). También resuelve las 3 listas de códigos centinela
(`ND`/`88888`/`44444`) a nombre y código real. Ejecutar primero, antes que
cualquier otro `calibracion_*.py` que dependa de `_cargar_crosswalk_municipio_id`.
```
python -m scripts.cuadros_ganaderia.crosswalk_municipio_id_c1
```

### `calibracion_calruv_c1.py`
`calruv = cantpredganruv / cantpredganencuesta` (por `predioganid`,
agrupado por municipio), comparando `ciclo1ruv.sas7bdat` (universo completo)
contra `ciclo1encuesta.sas7bdat` (subconjunto que respondió encuesta).

### `calibracion_predios_c1.py`
`cal_predios = Total Predios PM (Fedegán) / predios_encuesta`. La versión
anterior de este módulo usaba `ciclo1ruv.sas7bdat` (universo completo) por
analogía con `calruv` - error de universo detectado al comparar contra
`calibrac12025.xlsx`: coincidía exacto usando `ciclo1encuesta.sas7bdat`, no
`ciclo1ruv.sas7bdat`. Ver el docstring del módulo para el detalle completo
del hallazgo.

### `calibracion_bovinos_bufalinos_c1.py`
`cal_bovinos`/`cal_bufalinos = Total <especie> PM (Fedegán) /
animales_encuesta` (`TOTAL_AFT_<esp> + TOTAL_AFT_<esp>_NV`, sumado por
municipio desde `ciclo1encuesta.sas7bdat`). **No confundir con
`F_AJUSTA_BOVINOS/BUFALINOS`** de `calibracion_c1.py` - ver
[01_arquitectura.md](01_arquitectura.md).

### `calibracion_cobertura_c1.py`
`cal_cobertura = 1 / Total Predios Cobertura` (columna que ya trae Fedegán
directo en `Cuadro 2_Cobertura`) - el único de los 5 factores que no depende
de ningún conteo propio del RUV/encuesta. Corregido 2026-09-23: la fórmula
original (`2 - Total Predios Cobertura`) era solo la aproximación lineal de
`1/C`, descartada tras validar que `1/C` reproduce `Total Predios PM` de
Fedegán con la mitad de error - ver [01_arquitectura.md](01_arquitectura.md).

### `calibracion_ganadero_c1.py`
Junta los 5 factores (`cal_predios`, `cal_bovinos`, `cal_bufalinos`,
`cal_cobertura`, `calruv`) en una sola tabla por municipio
(`calcular_factores_ganadero_c1()`), guardada en `RUTA_FACTOR_GANADERO_C1`.
Consume los 4 módulos anteriores; `_cargar_crosswalk_municipio_id()` (interno)
también sirve de referencia "heredada" para varios de ellos (columnas de
`calibrac12025.xlsx`).
```
python -m scripts.cuadros_ganaderia.calibracion_ganadero_c1
```

### `calibracion_c1.py`
`F_AJUSTA_BOVINOS`/`BUFALINOS = Total <especie> PM (Fedegán) / total_ruv`,
donde `total_ruv` es la suma de los 13 tramos de sexo/edad (+ su propia
`_NV`) de `preparar_base.columnas_inventario(especie)` - **el mismo detalle
que multiplica `preparar_base.aplicar_factor_calibracion`**, no un agregado
aparte (ver docstring del módulo: usar un proxy distinto dejaba un residual
del total calibrado contra Fedegán incluso en municipios con match perfecto).
Municipios sin fila en Fedegán ese ciclo quedan con factor `0` (no `1.0`):
no aportan su inventario crudo sin escalar. También expone
`_fedegan_ciclo1_con_codigo_municipio()`, reutilizada por otros módulos de
calibración C1 y por `validacion_totales_inventario_c1.py`.
```
python -m scripts.cuadros_ganaderia.calibracion_c1
```

## Calibración - Ciclo 2

### `calibracion_c2.py`
`F_AJUSTA_BOVINOS`/`BUFALINOS` de Ciclo 2, recalculado desde `RUTA_C2`
porque el factor que ya traía el CSV original venía corrupto (bug de
notación científica al coaccionar una columna numérica a texto en R, que
infló el valor ~14 órdenes de magnitud en algunos municipios - ver docstring
del módulo para el caso documentado, Convención/Norte de Santander).

## Preparación de la base

### `preparar_base.py`
Carga y limpia `ciclo1encuesta.sas7bdat` (bovinos y bufalinos comparten el
mismo archivo/filas). Funciones clave:

- `cargar_base_cruda(especie, columnas_extra)`: lee con `usecols` acotado
  (incluye automáticamente cualquier `_NV` disponible de lo pedido),
  valida que el archivo sea 100% Ciclo 1 2025, y aplica
  `config.MUNICIPIOS_EXCLUIDOS_C1`.
- `aplicar_factor_calibracion(df, especie, columnas)`: multiplica cada
  columna de inventario (+ `_NV`) por `F_AJUSTA_BOVINOS`/`BUFALINOS`
  (`calibracion_c1.py`).
- `deduplicar_predio_ganadero(df)`: cascada de desempate por `predioganid`
  duplicado (mayor `cantvacasord` → mayor `TOTAL_AFT_BOV` → `FECHA_CREACION`
  más reciente) - solo para cuadros de ganadero/predio-ganadero, el
  inventario (4.1) no deduplica.
- `renombrar_preguntas`/`normalizar_categoricas`: hoy son mayormente
  no-operación (la fuente actual ya trae las preguntas con nombre de
  negocio), se conservan por si se vuelve a una fuente con `R#` crudos.

### `preparar_base_c2.py`
Equivalente a `preparar_base.py` pero para Ciclo 2 (`RUTA_C2`, un solo
archivo con bovinos+bufalinos, columnas nativas del RUV/DMC sin renombrar).

### `base_maestra.py`
Construye la tabla "maestra" de Ciclo 1: una fila por `predioganid`
(deduplicado), con el inventario animal calibrado (bovino + bufalino unidos)
y los 3 pesos de conteo que usan los cuadros de "ganadero" y
"predio-ganadero" - ver [01_arquitectura.md](01_arquitectura.md#calibración-del-ganadero-3-pesos-de-conteo-3-unidades-distintas)
para la tabla completa y por qué son 3 y no 1:

- `peso_ganadero = (1/conteo_predios_ganadero) * cal_cobertura` - cuenta
  GANADEROS (personas), agrupando por `IDENT_GANADERO`.
- `peso_predio_ganadero = calruv * cal_cobertura` - cuenta PARES
  predio-ganadero (fórmula literal del SAS original, `4.2`/`4.3`).
- `peso_predio_fisico = (1/conteo_ganaderos_por_predio) * cal_predios` -
  cuenta PREDIOS FÍSICOS (`CODIGO_SIT`), reconcilia exacto con el "Total
  Predios PM" de Fedegán.

Guarda en `Bases Calibradas/base_maestra_C1_2025.parquet`.
```
python -m scripts.cuadros_ganaderia.base_maestra
```

## Cuadros

### `cuadros/inventario.py`
Genera los Cuadros 3 (bovinos sexo/edad), 4/5 (bovinos por orientación de
hato), 6 (bovinos por sistema productivo), 7 (bufalinos sexo/edad) y 8
(otras especies). Traducción de "4.1. cuadros inventario.sas". Cada
`generar_*()` prepara el detalle vía `preparar_base` y cierra con
`agregador.generar_cuadro`.

### `cuadros/comun.py`
Cuadro 1 ("Total predios/ganaderos/predios ganaderos") y Cuadro 2
("Municipios sin información asociada") - idénticos en los 3 libros de
publicación (inventario, ganadero, predio-ganadero), se calculan una sola
vez acá. `generar_cuadro1()` usa los 3 pesos de `base_maestra.py`
(`peso_predio_fisico` → Total predios, `peso_ganadero` → Total ganaderos,
`peso_predio_ganadero` → Total predios ganaderos).

### `cuadros/ganadero.py`
Cuadros específicos del libro "ganadero" (más allá de Cuadro 1/2). Cuadro 3
("Cantidad de ganaderos por sexo y persona jurídica"): agrupa `peso_ganadero`
por `genero` (`Mujer`/`Hombre`/`config.GENERO_JURIDICA`, ya normalizado en
`base_maestra.py`) - fórmula confirmada contra `4.2. cuadros ganadero.sas`
(`gan_cal` agrupado por `genero`).

### `main.py`
Orquestador de los cuadros de inventario. Cada paso (`cuadro3`, `cuadro4`,
`cuadro6`, `cuadro7`, `cuadro8`, y sus variantes `_c2` para Ciclo 2) corre
como invocación de proceso independiente (`--solo <paso>`) porque encadenar
varios cuadros pesados en un mismo proceso ya causó un `MemoryError` en la
máquina de referencia (poca RAM libre). Todos escriben sobre el mismo
archivo de salida en `output/`, acumulando hoja por hoja.
```
python -m scripts.cuadros_ganaderia.main --solo cuadro3
```

## Validación

### `validacion_totales_inventario_c1.py`
Compara, municipio por municipio, el total REAL que produce el Cuadro 3/7
(los 13 tramos calibrados, exactamente lo que usa `preparar_base`) contra
Fedegán, y clasifica cada diferencia en una de 3 categorías: "excluido del
universo", "RUV sin fila en Fedegán" o "Fedegán sin ningún predio en el
RUV". Guarda `validacion_totales_inventario_{bovinos,bufalinos}_C1_2025.csv`.
Correr después de regenerar cualquier cuadro de inventario, como chequeo de
salud del pipeline completo.
```
python -m scripts.cuadros_ganaderia.validacion_totales_inventario_c1
```

## Ver también

- [05_flujo_datos.md](05_flujo_datos.md) - cómo fluyen los datos entre estos módulos.
