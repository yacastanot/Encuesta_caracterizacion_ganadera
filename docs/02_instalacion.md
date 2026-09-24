# Instalación

## Requisitos del sistema

| Requisito | Versión / detalle |
|---|---|
| Python | 3.13 |
| Sistema operativo | Windows (rutas de red `S:\...`, algunos módulos leen archivos con `PowerShell`/UNC paths) |
| RAM libre | Poca disponible en la máquina de referencia - por eso `main.py` corre cada cuadro en su propio proceso (`--solo <paso>`), ver `04_modulos.md` |

## Paquetes de Python

No hay `requirements.txt` fijado con versiones exactas todavía (pendiente,
ver `06_git.md`). Los paquetes que usa el código:

```
pandas
pyreadstat      # lectura de .sas7bdat
openpyxl        # lectura/escritura de plantillas Excel
pyarrow         # requerido por pandas para escribir/leer .parquet (base_maestra)
```

Instalar con:

```bash
pip install pandas pyreadstat openpyxl pyarrow
```

## Estructura de carpetas (insumos vs. código)

Este repositorio versiona **solo el código** (`scripts/`). Todo lo demás -
bases de datos, insumos pesados (CSV de 1GB+, Excel, `.sas7bdat`) - queda
fuera de git (`.gitignore`) porque mezclar código con datos de encuesta no es
seguro ni práctico. Eso significa que, al clonar el repo en una máquina
nueva, **las siguientes carpetas están vacías y hay que poblarlas** copiando
desde la unidad de red `S:\` (`\\systema20\MUESTRAS\Agropecuarias\RUV_ECG`):

| Carpeta local | Contenido esperado | Origen en `S:\` |
|---|---|---|
| `01Entrada/2025 I/` | `ciclo1ruv.sas7bdat`, `ciclo1encuesta.sas7bdat`, marco Fedegán (`1-Historico-PE-Inventario-Bovino-Bufalino...xlsx`), `para calibrar formulado fedegan.xlsx` | `S:\01Entrada\2025 I\` |
| `Programas Carolina/` | `calibrac12025.xlsx`, `calibraencuestac1.xlsx` (archivos SAS heredados de Carolina, usados solo para *comparar* contra los factores recalculados) | `S:\02Programas\Programas Carolina\` (los `.xlsx` de datos, no los `.sas`) |
| `Excluidos/` | `Municipios ZLSV_OC_ciclos 2025.xlsx`, `Municipios Salen Encuestas repetidas_Ciclo 1_2025.xlsx` | Compartidos directamente por el equipo |
| `Cuadros para publicación/` | Las 3 plantillas Excel oficiales (inventario, ganadero, predio-ganadero) | Compartidas directamente por el equipo |
| `Scripts calibración R/INSUMOS/` | `DIVIPOLA_Municipios.xlsx` (catálogo territorial) | Compartido directamente |
| `Bases Calibradas/` | Se genera sola al correr los módulos `calibracion_*.py`/`base_maestra.py` - no hace falta copiar nada acá | N/A |
| `output/` | Se genera sola al correr `main.py` | N/A |

`config.py` (ver `03_configuracion.md`) asume que estas carpetas existen con
esos nombres exactos, relativas a la raíz del repo (`config.BASE_DIR`).

## Verificar que todo está en su sitio

```bash
python -c "from scripts.cuadros_ganaderia import config; print(config.RUTA_CICLO1_ENCUESTA_CRUDO.exists())"
```

Si da `False`, revisar que `01Entrada/2025 I/ciclo1encuesta.sas7bdat` exista
en la ruta esperada.

## Primer corrida completa (Ciclo 1)

```bash
# 1. Crosswalk municipio_id -> CODIGO_MUNICIPIO (necesario para varios módulos de calibración)
python -m scripts.cuadros_ganaderia.crosswalk_municipio_id_c1

# 2. Factores de calibración
python -m scripts.cuadros_ganaderia.calibracion_ganadero_c1
python -m scripts.cuadros_ganaderia.calibracion_c1

# 3. Base maestra
python -m scripts.cuadros_ganaderia.base_maestra

# 4. Cuadros de inventario (uno por uno)
python -m scripts.cuadros_ganaderia.main --solo cuadro3
python -m scripts.cuadros_ganaderia.main --solo cuadro4
python -m scripts.cuadros_ganaderia.main --solo cuadro6
python -m scripts.cuadros_ganaderia.main --solo cuadro7
python -m scripts.cuadros_ganaderia.main --solo cuadro8

# 5. (Opcional) Validar el resultado contra Fedegán
python -m scripts.cuadros_ganaderia.validacion_totales_inventario_c1
```

El resultado final queda en
`output/Cuadros caracterización inventario Ciclos 1 y 2_2025_generado.xlsx`.

## Ver también

- [03_configuracion.md](03_configuracion.md) - cada ruta/constante de `config.py`.
- [04_modulos.md](04_modulos.md) - qué hace cada script.
