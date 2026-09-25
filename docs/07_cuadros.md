# Detalle de construcción de cada cuadro

Este documento describe, cuadro por cuadro y libro por libro, de dónde sale
cada cifra publicada: la(s) variable(s) cruda(s) de origen (RUV y/o encuesta
de caracterización), la columna de la base maestra que realmente usa el
código, el peso/unidad de conteo aplicado, y el cálculo de agregación
territorial. Es un complemento de referencia rápida a los docstrings de cada
módulo (`cuadros/comun.py`, `cuadros/inventario.py`, `cuadros/ganadero.py`,
`cuadros/predio_ganadero.py`), que siguen siendo la fuente de verdad más
detallada — acá se resume y se cruza la información de los 3 libros en un
solo lugar.

## 0. Conceptos comunes a todos los cuadros

### 0.1. Las 3 unidades de conteo (pesos)

Cada fila de la base maestra es un `predioganid` (predio + documento del
ganadero, ya deduplicado). Tres pesos convierten "cuántas veces cuenta esa
fila" en cada cuadro — ver `base_maestra_c1.py`/`base_maestra_c2.py`:

| Peso | Fórmula | Qué cuenta | Se usa en |
|---|---|---|---|
| `peso_predio_fisico` | `(1 / ganaderos del mismo CODIGO_SIT) * cal_predios` | Predios **físicos** únicos (parcelas) | Cuadro 1 "Total predios" (único que reconcilia exacto con Fedegán) |
| `peso_ganadero` | `(1 / predios del mismo IDENT_GANADERO) * cal_cobertura` | **Ganaderos** (personas/empresas) | Cuadro 1 "Total ganaderos" y todo el libro "ganadero" |
| `peso_predio_ganadero` | `calruv * cal_cobertura` | **Pares** predio-ganadero (relaciones, no parcelas) | Cuadro 1 "Total predios ganaderos" y todo el libro "predio-ganadero" |

`cal_predios`, `cal_cobertura`, `calruv`, `cal_bovinos`, `cal_bufalinos` se
calculan cada uno en su propio módulo `calibracion_*_c1.py`/`_c2.py` (ver
[04_modulos.md](04_modulos.md)), independiente de las columnas de inventario
animal — que usan un factor distinto, `F_AJUSTA_BOVINOS`/`F_AJUSTA_BUFALINOS`
(`calibracion_c1.py`/`calibracion_c2.py`).

### 0.2. Motor de agregación territorial (`agregador.generar_cuadro`)

Todo cuadro pasa por la misma función: agrega a nivel municipio, **redondea
una sola vez ahí** (a entero), y Departamento/Nacional se calculan como suma
de esos enteros ya redondeados — así el "Total Nacional" y cada subtotal
departamental de una hoja siempre coinciden exacto con la suma de sus
municipios. `columnas_totales` (cuando se declara) fuerza además que una
columna "Total" de la MISMA fila sea la suma de sus componentes ya
redondeados (consistencia horizontal); cuando NO se declara, es una decisión
deliberada — casi siempre para que ese total coincida EXACTO con el mismo
total reportado en otro cuadro (p. ej. "Total predios ganaderos" en Cuadro
3-14 del libro predio-ganadero siempre iguala a Cuadro 1, nunca se deriva
como suma de sus categorías propias).

### 0.3. Bases maestras (una fila = qué)

| Base maestra | Módulo | Grano | Usada por |
|---|---|---|---|
| `base_maestra_C1_2025.parquet` | `base_maestra_c1.py` | 1 fila por `predioganid` C1, deduplicado | Cuadro 1/2 (los 3 libros), todo el libro ganadero y predio-ganadero (C1) |
| `base_maestra_C2_2025.parquet` | `base_maestra_c2.py` | 1 fila por `predioganid` C2, deduplicado | Igual, para los bloques "Segundo ciclo" |
| `base_maestra_inventario_C1_2025.parquet` | `base_maestra_inventario_c1.py` | 1 fila por registro RUV+encuesta C1, **sin** deduplicar | Cuadro 3/4/5/6/7/8 del libro inventario (C1) — el inventario animal se suma TODOS los registros, no solo 1 por predio-ganadero |
| (Ciclo 2, libro inventario) | `preparar_base_c2.cargar_inventario_c2`/`cargar_otras_especies_c2` | 1 fila por registro RUV+encuesta C2, sin deduplicar | Cuadro 3/5/7/8 del libro inventario (C2) — no pasa por una tabla "maestra" intermedia, lee directo `preparar_ciclo2encuesta.leer()` |

### 0.4. Origen de las variables crudas

- **Columnas de identificación/RUV** (`CODIGO_SIT`, `IDENT_GANADERO`,
  `GENERO`, `PREDIO_CARGO`, `TOTAL_AFT_BOV`, tramos `AFT_BOV_*`/`AFT_BUF_*`,
  etc.): vienen del archivo de vacunación (RUV), ya con nombre canónico
  (Ciclo 1: `ciclo1encuesta.sas7bdat`, que trae RUV+encuesta pre-unidos;
  Ciclo 2: `ExportarArchivoRuv.csv`, unido a la encuesta en
  `preparar_ciclo2encuesta.py` — ver [04_modulos.md](04_modulos.md)).
- **Preguntas de la encuesta de caracterización** (columnas `R1`, `R2`...):
  se renombran a su nombre de negocio vía `config.RENOMBRE_PREGUNTAS`
  (Ciclo 1) / `config.RENOMBRE_PREGUNTAS_C2` (Ciclo 2) — **la numeración R*
  NO es la misma entre ciclos** (cuestionarios distintos), ver tabla en
  cada sección de cuadro.

---

## 1. Libro "Inventario" (animales)

### Cuadro 1 — Cantidad de predios, ganaderos y predios ganaderos

Idéntico en los 3 libros — ver sección 4 (común a los 3 libros).

### Cuadro 2 — Municipios sin información asociada

Idéntico en los 3 libros — ver sección 4.

### Cuadro 3 — Bovinos por sexo y edad (Primer ciclo) / Cuadro 5 (Segundo ciclo)

- **Fuente cruda**: 26 columnas de tramo `AFT_BOV_{MAC,HEM}_*` (13 tramos ×
  macho/hembra, cada una con su variante `_NV` = "no vacunados") — RUV
  directo, sin pasar por ninguna pregunta de encuesta.
- **Base/peso**: `base_maestra_inventario_c1.py` (C1) / `preparar_base_c2.cargar_inventario_c2("bovinos")`
  (C2). **No** usa ningún `peso_*` de predio-ganadero — cada fila (registro
  RUV+encuesta) aporta directo sus 26 columnas de tramo, ya multiplicadas por
  `F_AJUSTA_BOVINOS` (factor Fedegán/RUV por municipio, `calibracion_c1.py`/
  `calibracion_c2.py`).
- **Cálculo**: suma `columna + columna_NV` por tramo, agrupa 13 tramos en 6
  franjas etarias de publicación (`men_3_mes`...`may_3_ani`, con el tramo
  "mayor de 3 años" absorbiendo hembras 3-5 años + mayores de 5 años),
  separado en Macho/Hembra/Total.
- **`columnas_totales`**: sí — `macho_total`/`hembra_total` = suma de sus 6
  tramos; `total_X` = `macho_X + hembra_X` por franja; `total_total` =
  `macho_total + hembra_total`.
- **Ciclos**: C1 en columnas E-Z de "Cuadro 3"; C2 en columnas AA-AV de la
  MISMA hoja "Cuadro 3" (bloque "Segundo ciclo").

### Cuadro 7 — Bufalinos por sexo y edad (Primer ciclo) / Cuadro 3 bufalinos C2

Misma lógica exacta que Cuadro 3, sustituyendo `AFT_BOV_*` por `AFT_BUF_*`
(26 columnas equivalentes) y `F_AJUSTA_BOVINOS` por `F_AJUSTA_BUFALINOS`.
Ciclos: C1 en "Cuadro 7" E-Z, C2 en "Cuadro 7" AA-AV.

### Cuadro 4 (Primer ciclo) / Cuadro 5 (Segundo ciclo) — Bovinos por edad, sexo y orientación del hato

- **Fuente cruda**: las mismas 26 columnas `AFT_BOV_*` de Cuadro 3, más
  `orientacionhato` (pregunta "¿Cuál es la principal orientación de su hato
  ganadero?" — R7 en C1 / R3 en C2, `config.RENOMBRE_PREGUNTAS`/`_C2`).
- **Cálculo**: el bloque "Total inventario bovino" se **reutiliza directo**
  de Cuadro 3 (no se recalcula, para garantizar coincidencia exacta). Los
  predios se reparten en 6 bloques de orientación (Ganadería de Leche, Cría,
  Ceba, Levante, Doble propósito, Genética); los predios SIN orientación
  reportada se redistribuyen proporcionalmente entre las 6 categorías
  (`redistribucion.py`), igual que el SAS original.
- **Nota de redondeo**: el bloque "Total" nunca se deriva de la suma de los 6
  bloques de orientación (para seguir coincidiendo exacto con Cuadro 3); el
  residuo de redondeo que eso deja (~0.006% nacional) se absorbe en el bloque
  "Doble propósito" (el más grande), decisión confirmada por el usuario.
- Hoja separada por ciclo: Cuadro 4 = C1, Cuadro 5 = C2 (no comparten hoja,
  a diferencia del resto del libro).

### Cuadro 6 — Bovinos por sistema productivo (solo Ciclo 1)

- **Fuente cruda**: `sistemaproductivo` (pregunta "11. ¿Cuál es el sistema
  productivo implementado en el predio?" — R11 en C1; **no existe en C2**).
  Las mismas 26 columnas `AFT_BOV_*` de Cuadro 3 para el total de animales.
- **Cálculo**: total de bovinos (con `_NV`) agrupado en 4 sistemas
  (Pastoreo mejorado / Pastoreo extractivo / Estabulado / Silvopastoril).
- **`columnas_totales`**: `sist_total` = suma de los 4 sistemas (exhaustivos,
  sin nulos).

### Cuadro 8 — Otras especies pecuarias

- **Fuente cruda**: `TOTAL_<especie>`/`<especie>_MACHO`/`<especie>_HEMBRA`
  para Equinos, Porcinos, Ovinos, Caprinos, Otros — columnas RUV nativas, sin
  ninguna pregunta de encuesta de por medio.
- **Cálculo**: suma directa, **sin calibrar** (ni `F_AJUSTA_*` ni ningún
  `peso_*` — igual que el SAS original, que tampoco calibra estas especies).
- **`columnas_totales`**: `TOTAL_<especie>` = `MACHO + HEMBRA` (verificado
  exacto en los datos reales).
- Bloque C1 ("Cuadro 8" E-S) y C2 ("Cuadro 8" T-AH, misma hoja).

---

## 2. Libro "Ganadero"

Cuadro 1/2: ver sección 4. Todos los cuadros de este libro cuentan
**ganaderos** (personas/empresas) con `peso_ganadero`, sobre
`base_maestra_c1`/`base_maestra_c2` (deduplicada por `predioganid`).

### Cuadro 4 — Ganaderos nuevos/salieron/se mantienen vs. ciclo anterior

### Cuadro 5 — Ganaderos nuevos/salieron/se mantienen vs. mismo ciclo, año anterior

Único par de cuadros del proyecto que necesita datos de **años anteriores a
2025** (`cuadros/ganadero_historico.py`) - a diferencia del resto del libro,
que solo compara C1/C2 del mismo año 2025.

- **Fuente**: 6 "fotos" de identidad de ganaderos por ciclo (`IDENT_GANADERO`
  + `CODIGO_MUNICIPIO` + `peso_ganadero`, sin ninguna pregunta de encuesta -
  estos cuadros no desagregan por sexo/tenencia/orientación):
  - **2025-C1/2025-C2**: ya existentes (`base_maestra_c1`/`_c2`).
  - **2024-C1/2024-C2**: reconstruidos desde cero (`base_maestra_ganadero_historico.construir_2024`)
    - RUV: `ruv.sas7bdat` (un solo archivo para los 2 ciclos de 2024, columna
      `CICLO` - **ojo**: no usa 1/2 literal, es un contador interno sin
      reiniciar por año; verificado que CICLO=2 es Ciclo 1 2024 y CICLO=3 es
      Ciclo 2 2024, por conteo exacto de filas contra los archivos
      `ruvc1.sas7bdat`/`ruvc2.sas7bdat` por separado).
    - Encuesta: `encuestac1corregida.sas7bdat` (Ciclo 1) / `encuestac2_.sas7bdat`
      (Ciclo 2) - separada del RUV, se une por `RUV_ID` (mismo patrón que
      Ciclo 2 2025). ~0.6-0.8% de huérfanos (no cero, a diferencia de Ciclo 2
      2025) - documentado y descartado, no bloquea el join.
    - `cal_cobertura = 1/C` (misma fórmula ya corregida, `calibracion_cobertura_historico.py`),
      sin `cal_predios`/`cal_bovinos`/`cal_bufalinos`/`calruv` (Cuadro 4/5 no
      los necesita - no cuentan predios físicos ni pares predio-ganadero).
  - **2023-C1/2023-C2**: decisión del usuario (2026-09-24) - se usan
    `c12023.sas7bdat`/`c22023.sas7bdat` TAL CUAL (ya vienen con RUV+encuesta
    unidos y `cal_cobertura`/`gan_cal` ya calibrados por el pipeline legado;
    los candidatos genuinamente crudos de 2023 eran mucho más antiguos y
    ambiguos) - 2023 solo sirve de referencia para el "ciclo anterior", no se
    publica ningún cuadro de 2023 en este libro.
- **Cálculo** (por bloque, ciclo "actual" vs. ciclo "referencia"): "Total" =
  `SUM(peso_ganadero)` del actual; "nuevos" = ídem, solo `IDENT_GANADERO` que
  no estaban en la referencia; "salieron" = `SUM(peso_ganadero)` de la
  REFERENCIA (no del actual), solo los que no siguen en el actual, agrupado
  por el municipio que tenían en la referencia; "se mantienen" = ídem actual,
  los que sí estaban antes.
- **Cuadro 4** (ciclo cronológico anterior): 2024-C1 vs 2023-C2, 2024-C2 vs
  2024-C1, 2025-C1 vs 2024-C2, 2025-C2 vs 2025-C1.
- **Cuadro 5** (mismo ciclo, año anterior): 2024-C1 vs 2023-C1, 2025-C1 vs
  2024-C1, 2024-C2 vs 2023-C2, 2025-C2 vs 2024-C2.
- **`columnas_totales`**: ninguna - "Total de ganaderos en el ciclo" de los
  bloques 2025 debe coincidir EXACTO con "Total ganaderos" de Cuadro 1/3 (ya
  verificado en el validador estructural), y derivarlo de nuevos+mantienen
  rompería esa coincidencia.
- **Los bloques 2024 (2024-C1 y 2024-C2) NO usan el cálculo propio descrito
  arriba** - decisión del usuario (2026-09-25), tras validar municipio por
  municipio: el cálculo independiente daba diferencias reales en 1.036 de
  1.121 municipios frente a `anex-CAG-CaractGanadero-2024.xlsx` (el libro ya
  publicado), con diferencias nacionales de hasta 4% en "Total" y 30% en
  "salieron" - la causa más probable es que el candidato de encuesta 2024 más
  reciente por fecha de archivo (`encuestac1corregida.sas7bdat`) no es
  necesariamente el mismo snapshot que usó el equipo que publicó el libro
  2024 (ver Cuadro 4/5 más arriba para la lista de ~10 versiones candidatas).
  Ante esa inconsistencia real, se **copian los valores exactos del libro
  publicado 2024** en vez del cálculo propio: los 4 valores (total/nuevos/
  salieron/mantienen) se extraen a nivel MUNICIPIO de las columnas
  correspondientes de Cuadro 4 (M-P="1er Ciclo 2024", Q-T="2do Ciclo 2024")
  y Cuadro 5 (I-L="1er Ciclo 2024", Q-T="2do Ciclo 2024") del libro 2024,
  redondeados a entero, y departamento/nacional se recalculan como suma de
  esos municipios YA redondeados (vía `agregador.generar_cuadro`, mismo
  motor que usa el resto del proyecto) - así se garantiza consistencia
  exacta en los 3 niveles territoriales aunque el libro 2024 publicado no
  fuera perfectamente consistente internamente (sus propias filas
  Nacional/Departamento guardan el valor decimal SIN redondear, no
  necesariamente la suma exacta de sus municipios). Municipios con "n.d."/
  "o.c."/"ZLSV" en el libro 2024 (sin dato para ese municipio/ciclo) se
  tratan como 0. Los bloques 2025 (2025-C1/2025-C2) siguen siendo el cálculo
  propio, sin tocar - solo 2024 se reemplazó. Ver
  `scripts/cuadros_ganaderia/main.py`/pendientes `cuadro4_ganadero.parquet`/
  `cuadro5_ganadero.parquet` (las columnas `c2024c1_*`/`c2024c2_*` quedaron
  sobrescritas con los valores copiados, `c2025c1_*`/`c2025c2_*` intactas).
- **Bug encontrado y corregido** (2026-09-24): `IDENT_GANADERO` viene en
  tipos incompatibles entre fuentes (`float` en todo lo que sale de un
  `.sas7bdat` - 2023/2024/2025-C1 - vs texto en `base_maestra_c2`/2025-C2,
  construida desde CSV) - sin normalizar, el bloque "2025-C2 vs 2025-C1" daba
  100% "nuevos" (0 coincidencias reales), mismo bug ya documentado para
  Cuadro 1. Al normalizar con `pd.to_numeric` se encontró además el ÚNICO
  valor sucio de las 712.846 filas de `IDENT_GANADERO` en C2 (`"686805_"`,
  con un guion bajo pegado, error de captura evidente) - se limpia quitando
  cualquier caracter no numérico ANTES de convertir (`686805_` → `686805`),
  en vez de dejarlo como texto sucio que nunca haría match con el valor real
  en otro ciclo - decisión del usuario (2026-09-24).

### Cuadro 3 — Ganaderos por sexo y persona jurídica

- **Fuente cruda**: `GENERO` (RUV) → normalizado a columna `genero`
  ("Mujer"/"Hombre"/persona jurídica, `preparar_base_c1.normalizar_categoricas`).
- **Cálculo**: `SUM(peso_ganadero)` agrupado por `genero`.
- **`columnas_totales`**: `natural_total = mujeres + hombres`;
  `total_ganaderos = natural_total + juridica`.
- Ciclos: E-I "Primer ciclo" / J-N "Segundo ciclo", misma hoja "Cuadro 3".

### Cuadro 6 — Ganaderos víctimas de algún delito

- **Fuente cruda**: 8 banderas 'X'/blanco — `abigeato`/`carneo`/`extorsion`/
  `hurto`/`invasiontierra`/`secuestro`/`otro`/`ninguno` (pregunta 18 de la
  encuesta; C1: R6_1..8; C2: R27_1..8, orden asumido igual a C1 — no
  verificado contra una lista oficial para C2, ver `config.py`). Filtra
  además `orientacionhato` no vacío (réplica del `WHERE` del SAS original).
- **Cálculo**: `SUM(peso_ganadero)` por cada bandera. **No mutuamente
  excluyentes** (un ganadero puede marcar varios delitos) — sin
  `columnas_totales`.
- Ciclos: E-M "Primer ciclo" / N-V "Segundo ciclo", misma hoja "Cuadro 6".

### Cuadro 8 — Ganaderos por sexo, tenencia del predio y persona jurídica

- **Fuente cruda**: `PREDIO_CARGO` (RUV, pregunta "El predio a su cargo es:
  1.Propio 2.Arrendado 3.Poseedor 4.Tenedor 5.Territorio colectivo 6.Otro")
  cruzado con `genero`.
- **Cálculo**: `SUM(peso_ganadero)` por tenencia × género (28 columnas:
  Total + 6 tenencias general + 3 bloques de 7 columnas cada uno —
  Hombre/Mujer/Jurídica).
- **`columnas_totales`**: en las 2 direcciones — cada bloque de género suma
  sus 6 tenencias (`h_total = Σ h_*`), y cada tenencia "general" suma sus 3
  bloques de género (`propio = h_propio + m_propio + j_propio`).
- Ciclos: E-AF "Primer ciclo" / AH-BH "Segundo ciclo" (columna AG queda como
  separador sin datos, verificado contra la plantilla real), misma hoja
  "Cuadro 8".

### Cuadro 9 — Ganaderos que comparten lote con otros ganaderos

- **Fuente cruda**: `compartelote` (pregunta "¿En este predio su ganado
  comparte los mismos lotes con los de otros ganaderos?" Sí/No — C1: R5;
  C2: R13), cruzada con `genero`.
- **Cálculo**: `SUM(peso_ganadero)` por Sí/No × género (sin columna "Total"
  por bloque — Sí+No ya es el total).
- **`columnas_totales`**: `general_si`/`general_no` = suma de sus 3 bloques
  de género; `total_ganaderos = general_si + general_no`.
- Respuesta afirmativa: se acepta "Si" y "Sí" indistintamente (`_filtro_valor`,
  ver nota de calidad de datos abajo).

### Cuadro 10 — Ganaderos por lugar de residencia

- **Fuente cruda**: `lugarresidencia` (pregunta "¿En dónde vive el
  ganadero? 1. En el predio visitado 2. En otro lugar diferente al predio" —
  C1: R2; C2: R2), cruzada con `genero`.
- **Cálculo**: igual patrón que Cuadro 9, pero los 3 bloques de género SÍ
  traen su propio "Total" (a diferencia de Cuadro 9/11).
- **Nota de datos**: en Ciclo 2 el valor " En otro lugar diferente al
  predio" trae un espacio inicial pegado — se aplica `.str.strip()`.

### Cuadro 11 — Ganaderos que responden directamente la encuesta

- **Fuente cruda**: `atendioencuesta` (pregunta "¿La encuesta fue atendida
  por el ganadero?" Sí/No — C1: R1; C2: R1).
- **Cálculo**: idéntico patrón a Cuadro 9 (sin "Total" por bloque de género).

### Cuadro 12 — Ganaderos que conocen qué es un sensor epidemiológico

- **Fuente cruda**: `consensorepidem` (C1: R12; C2: R22) — "¿Sabe qué es un
  sensor epidemiológico? 1.Sí 2.No 3.No sabe/no responde".
- **Cálculo**: `SUM(peso_ganadero)` por Sí/No/No sabe, **sin** desagregar por
  sexo/persona jurídica. Las respuestas en blanco (cadena vacía en C1) se
  suman a "No sabe/no responde" (decisión del usuario).
- **`columnas_totales`**: `total_ganaderos = si + no + no_sabe`.

### Cuadro 13 — Ganaderos que conocen el sistema de alerta temprana

`conalertatem` (C1: R13; C2: R23) — misma estructura que Cuadro 12.

### Cuadro 14 — Ganaderos que conocen la obligación de notificar al ICA

`debenotificarica` (C1: R14; C2: R24) — misma estructura que Cuadro 12.

### Cuadro 15 — Ganaderos cuyo ganado presentó signos clínicos reproductivos

`signosclinicos` (C1: R15; C2: R25) — misma estructura que Cuadro 12.

### Cuadro 16 — Conocimiento de programas Universidad del Área Andina (solo Ciclo 1)

- **Fuente cruda**: `conformacion` ("¿Conoce los programas...?") e
  `intcarrera` ("¿Le interesaría cursar esta carrera?") — R17/R18 en C1;
  **no existen en C2**.
- **Cálculo**: 2 preguntas independientes lado a lado, cada una con su
  propio "Total de ganaderos" (E y H = el mismo valor repetido) + Sí/No (sin
  "No sabe/no responde", a diferencia de Cuadro 12-15).
- **Nota de datos**: "Sí" llega truncada a 1 byte en la fuente (queda como
  `"S"` suelta) en ~3.300 filas de ~730.000 — se trata como respuesta
  afirmativa igual que "Si" (`.isin(["Si", "S"])`).

---

## 3. Libro "Predio-ganadero"

Cuadro 1/2: ver sección 4. Todos los cuadros de este libro cuentan **pares
predio-ganadero** con `peso_predio_ganadero`, sobre `base_maestra_c1`/
`base_maestra_c2`. Fedegán no tiene cifra de referencia para esta unidad — la
validación de este libro es solo de consistencia interna (vertical/horizontal
y cruzada entre cuadros), no contra Fedegán.

### Cuadro 3 — Predios ganaderos por inventario bovino/bufalino

- **Fuente cruda**: `TOTAL_AFT_BOV`/`TOTAL_AFT_BOV_NV` y
  `TOTAL_AFT_BUF`/`TOTAL_AFT_BUF_NV` (agregados RUV, sin desglose por tramo).
- **Cálculo**: `SUM(peso_predio_ganadero)` según el predio tenga inventario
  bovino y/o bufalino > 0 — 3 categorías mutuamente excluyentes y
  exhaustivas (con bovinos / con bufalinos / con ambos).
- **`columnas_totales`**: sí, para las 3 categorías entre sí — pero
  `total_predios_ganaderos` (columna E) queda independiente (coincide con
  Cuadro 1).
- Ciclos: E-H "Primer ciclo" / I-L "Segundo ciclo", misma hoja "Cuadro 3".

### Cuadro 4 — Predios ganaderos por orientación del hato

- **Fuente cruda**: `orientacionhato` (misma pregunta que Cuadro 4/5 del
  libro inventario — C1: R7; C2: R3), ya normalizada.
- **Cálculo**: `SUM(peso_predio_ganadero)` por las 6 orientaciones. Sin
  redistribución proporcional (a diferencia del libro inventario):
  `orientacionhato` no tiene blancos en la base maestra.
- Ciclos: E-K "Primer ciclo" / L-R "Segundo ciclo", misma hoja "Cuadro 4".

### Cuadro 5 — Predios ganaderos por cantidad de trabajadores (solo Ciclo 1)

- **Fuente cruda**: `canttrabaj` (C1: R10; **no existe en C2**).
- **Cálculo**: 8 clases definidas por quiebres naturales de la frecuencia
  acumulada real (0 / 1 / 2 / 3 / 4-5 / 6-10 / 11-20 / 21+, ver docstring del
  módulo para la justificación completa — la plantilla no traía rangos
  predefinidos).

### Cuadro 6 — Predios ganaderos por sistema productivo, sexo y persona jurídica

- **Fuente cruda**: `sistemaproductivo` (C1: R11; no existe en C2) cruzado
  con `genero`.
- **Cálculo**: 4 bloques de sistema productivo, cada uno con Total = Natural
  (Hombre+Mujer) + Jurídica.
- **`columnas_totales`**: sí para los subtotales internos de cada bloque;
  `total_predios_ganaderos` general queda independiente (coincide con
  Cuadro 1).

### Cuadro 7 — Predios ganaderos por sistema productivo × orientación del hato

Cruce de `sistemaproductivo` (Cuadro 6) con `orientacionhato` (Cuadro 4).
1 bloque "Total" + 6 bloques de orientación, cada uno desglosado en 4
sistemas productivos. Todas las columnas "Total" son independientes (no
derivadas de sus 4 columnas de sistema productivo). Solo Ciclo 1.

### Cuadro 8 — Predios ganaderos por sexo/persona jurídica × sistema productivo

Cruce de `genero` con `sistemaproductivo`. 1 bloque "Total" + 3 bloques de
género, cada uno desglosado en 4 sistemas productivos. Solo Ciclo 1.

### Cuadro 9 — Predios ganaderos por sexo, condición jurídica y orientación del hato

Cruce de `genero` con `orientacionhato`. 1 columna "Total" general + 3
bloques de género (Mujeres/Hombres/Jurídica), cada uno desglosado en las 6
orientaciones — el "Total" de cada bloque coincide exacto con la columna
`{género}_total` de Cuadro 8. Ciclos: E-Z "Primer ciclo" / AA en adelante
"Segundo ciclo", misma hoja.

### Cuadro 10 — Predios ganaderos por tenencia × sistema productivo

Cruce de `PREDIO_CARGO` (tenencia, mismo catálogo que Cuadro 8 del libro
ganadero) con `sistemaproductivo`. 1 columna "Total" general + 6 bloques de
tenencia, cada uno desglosado en 4 sistemas productivos — el "Total" de cada
bloque de tenencia coincide exacto con `{tenencia}_total` de Cuadro 11. Solo
Ciclo 1.

### Cuadro 11 — Predios ganaderos por tenencia del predio

Columna "Total" (E) + 6 columnas de tenencia (F-K), sin cruce. Cada columna
de tenencia coincide exacto con `{tenencia}_total` de Cuadro 10. Ciclos: E-K
"Primer ciclo" / L-R "Segundo ciclo", misma hoja.

### Cuadro 12 — Predios ganaderos por tenencia × orientación del hato

Cruce de `PREDIO_CARGO` con `orientacionhato`. 1 columna "Total" general + 6
bloques de tenencia, cada uno desglosado en las 6 orientaciones — el "Total"
de cada bloque de tenencia coincide exacto con `{tenencia}_total` de Cuadro
11. Ciclos: E-AU "Primer ciclo" / AV en adelante "Segundo ciclo", misma hoja.

### Cuadro 13 — Predios ganaderos por número de niños residentes (solo Ciclo 1)

- **Fuente cruda**: `menores18` (numérica, "¿Cuántos menores de 18 años
  viven permanentemente en el predio ganadero?" — agregada a la base maestra
  específicamente para este cuadro; no existe en C2).
- **Cálculo**: 8 rangos de la plantilla real (0 / 1-5 / 6-10 / 11-15 / 16-20
  / 21-50 / >50 / No sabe-no responde). Los blancos (26.3% de las filas) se
  fusionan con "No sabe/no responde".

### Cuadro 14 — Predios ganaderos con colmenas (solo Ciclo 1)

- **Fuente cruda**: `tienecolmenas` (Sí/No, sin blancos) + `numcolmenas`
  (numérica, solo diligenciada si `tienecolmenas`=Sí) — ninguna existe en C2.
- **Cálculo**: E=total general, F=con colmenas, G-L=6 rangos de cantidad de
  colmenas sobre un valor "efectivo" (0 si `tienecolmenas`=No, `numcolmenas`
  si =Sí) — partición exhaustiva de TODOS los predios, no solo los que
  tienen colmenas.

### Cuadro 15 — Predios ganaderos por cobertura de tierra y área (solo Ciclo 2)

- **Fuente cruda**: `areaagricola`/`areaproducanimales`/`areaforestal`/
  `areaconstrucciones`/`areaotrosusos` (R16-R20, pregunta 11.1) +
  `unidadmedidaarea` (R14) para la conversión de unidad.
- **Cálculo**: E=total general + 5 bloques (uno por tipo de cobertura), cada
  uno con "Total predios" (con esa cobertura > 0, en cualquier unidad) y
  "Hectáreas" (`_area_en_hectareas`: Hectáreas tal cual, Metros cuadrados /
  10.000, "Fanegadas o Plaza o Cuadra" **excluida de la suma** — 3 unidades
  tradicionales distintas sin factor único, decisión del usuario; también se
  excluyen valores > 100.000 ha, ~78 registros con errores de captura).

### Cuadro 16 — Predios ganaderos por área de ganadería bovina/bufalina (solo Ciclo 2)

- **Fuente cruda**: `areaproducanimales` (R17, subconjunto de Cuadro 15) y
  `areaganaderiabovbuf` (R21, pregunta 12).
- **Cálculo**: E=total + F=con producción animal + G=hectáreas de producción
  animal + H=hectáreas de ganadería bovina/bufalina (subconjunto de G).

### Cuadro 17 — Predios ganaderos en área protegida (solo Ciclo 2)

- **Fuente cruda**: `areaprotegida` (R26, "¿Sabe si su predio se encuentra
  dentro de un área protegida? 1.Sí 2.No 3.No sabe/no responde").
- **Cálculo**: E=total + F/G/H=Sí/No/No sabe. **Sin** `columnas_totales`
  (corregido 2026-09-24 — ver docstring del módulo: la versión original
  derivaba el total como suma de sí/no/no_sabe, rompiendo la coincidencia
  exacta con Cuadro 1/15/16/18/19).

### Cuadro 18 — Predios ganaderos por razas puras o cruces (solo Ciclo 2)

- **Fuente cruda**: `tienerazapura`/`tienerazacruce` (R8_1/R8_2, flags de
  opción múltiple, "X" o vacío — pregunta 8).
- **Cálculo**: E=total + F=con razas puras + G=con razas de cruce, **no**
  mutuamente excluyentes (un predio puede tener ambas).

### Cuadro 19 — Predios ganaderos por raza predominante (solo Ciclo 2)

- **Fuente cruda**: `razapurapredominante`/`razacrucepredominante` (R9/R11,
  texto libre) contra una lista oficial de 52 razas puras + 28 cruces (80
  categorías de la plantilla real, columnas `pura_*`/`cruce_*`).
- **Cálculo**: cada valor real se mapea a su etiqueta de plantilla
  normalizando mayúsculas/tildes/apóstrofes (`_normalizar_raza`), con
  excepciones explícitas para 4 valores que no calzan ni normalizados
  (p. ej. "Brahaman" dato → "Brahman" plantilla) — **falla fuerte**
  (`KeyError`) ante cualquier valor sin mapear, nunca se descarta en
  silencio.

---

## 4. Cuadros comunes a los 3 libros (`cuadros/comun.py`)

### Cuadro 1 — Cantidad de predios, ganaderos y predios ganaderos

- **Base/peso**: `base_maestra_c1`/`base_maestra_c2` completa — las 3
  columnas de peso a la vez (`peso_predio_fisico`, `peso_ganadero`,
  `peso_predio_ganadero`).
- **Cálculo**: `SUM` de cada peso por `CODIGO_MUNICIPIO`. Columnas E-G =
  Ciclo 1, H-J = Ciclo 2 (misma fórmula, otra base maestra).
- **Columnas K-N ("... nuevos")**: predios/ganaderos/pares que aparecen en
  C2 pero NO en C1 (comparando `CODIGO_SIT`/`IDENT_GANADERO`/`predioganid`
  normalizados por separado contra su universo de C1) + total de animales
  (bovino+bufalino, sin calibrar) en esos predios físicos nuevos.
- **Nota histórica**: "Total predios" y "Total predios ganaderos" NO son la
  misma cantidad (a diferencia del SAS original, que las trataba igual) —
  decisión del usuario para no sobreestimar "Total predios" ~+25%.

### Cuadro 2 — Municipios sin información asociada

- **Fuente**: `config.MUNICIPIOS_EXCLUIDOS_C1`/`_C2` (unión de los 2 ciclos)
  — listado plano de municipios excluidos del pipeline, con su motivo real
  por columna separada (Observación C1 / Observación C2): <80% de cobertura
  de vacunación, ZLSV ("zonas libres sin vacunación") o encuestas repetidas.
  No pasa por `agregador.generar_cuadro` (es un listado plano, sin jerarquía
  territorial ni relaciones numéricas que validar).

---

## Ver también

- [01_arquitectura.md](01_arquitectura.md) — los 5 factores de calibración y
  los 3 pesos de conteo, en detalle.
- [04_modulos.md](04_modulos.md) — qué hace cada módulo `.py`.
- [05_flujo_datos.md](05_flujo_datos.md) — diagrama del flujo completo.
- Docstrings de `cuadros/comun.py`, `cuadros/inventario.py`,
  `cuadros/ganadero.py`, `cuadros/predio_ganadero.py` — el detalle más fino
  de cada decisión metodológica y cada hallazgo de calidad de datos.
