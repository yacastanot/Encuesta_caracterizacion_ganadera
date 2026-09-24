# Encuesta de Caracterización Ganadera (ECG)

Pipeline en Python que reconstruye los cuadros de caracterización ganadera
(inventario, ganadero, predio-ganadero) de los 3 programas SAS originales de
Carolina, calibrados contra el marco de Fedegán, para los Ciclos 1 y 2 de
vacunación 2025.

## Inicio rápido

```bash
pip install -r requirements.txt

# 1. Factores de calibración de Ciclo 1 (calruv, cal_predios, cal_bovinos, cal_bufalinos, cal_cobertura)
python -m scripts.cuadros_ganaderia.calibracion_ganadero_c1

# 2. Factor F_AJUSTA_BOVINOS/BUFALINOS (inventario) de Ciclo 1
python -m scripts.cuadros_ganaderia.calibracion_c1

# 3. Base maestra de Ciclo 1 (una fila por predio-ganadero, ya calibrada)
python -m scripts.cuadros_ganaderia.base_maestra

# 4. Un cuadro de inventario (cada uno corre como proceso propio, ver docs/04_modulos.md)
python -m scripts.cuadros_ganaderia.main --solo cuadro3
```

## Requisitos

| Requisito | Detalle |
|---|---|
| Python | 3.13 |
| Paquetes | `pandas`, `pyreadstat`, `openpyxl`, `pyarrow` (ver `docs/02_instalacion.md`) |
| Insumos externos | RUV crudo (`.sas7bdat`), marco Fedegán (`.xlsx`), plantillas Excel de publicación - ninguno se versiona, ver `docs/02_instalacion.md` |
| Acceso | Unidad de red `S:\` (`\\systema20\MUESTRAS\Agropecuarias\RUV_ECG`) para insumos que no viven en este repo (programas SAS/R originales, marcos oficiales) |

## Documentación completa

- Arquitectura y decisiones de diseño → [docs/01_arquitectura.md](docs/01_arquitectura.md)
- Instalación e insumos → [docs/02_instalacion.md](docs/02_instalacion.md)
- Configuración (`config.py`) → [docs/03_configuracion.md](docs/03_configuracion.md)
- Módulos (`scripts/cuadros_ganaderia/*.py`) → [docs/04_modulos.md](docs/04_modulos.md)
- Flujo de datos end-to-end → [docs/05_flujo_datos.md](docs/05_flujo_datos.md)
- Convenciones de Git → [docs/06_git.md](docs/06_git.md)

## Estado del proyecto

**En desarrollo.**

- **Inventario Ciclo 1** (Cuadros 3, 4, 6, 7, 8): completo, calibrado y
  validado contra Fedegán.
- **Inventario Ciclo 2**: completo (bloque "Segundo ciclo" de las mismas
  hojas).
- **Base maestra Ciclo 1** (predio-ganadero deduplicado, pesos de
  calibración): completa.
- **Ganadero / predio-ganadero** (`4.2`/`4.3` del SAS original): factores de
  calibración listos; los cuadros en sí todavía no están escritos.
