# Convenciones de Git

## Estado actual (honesto, no aspiracional)

Este repositorio hoy es un solo desarrollador trabajando directo sobre
`master`, en GitHub (`origin/master`), sin ramas de feature ni Pull Requests
todavía. Lo que sigue en este documento es la convención objetivo, adaptada
de "Recomendaciones uso de Python y codeversion" (DANE, mayo 2026), para
adoptar a medida que el equipo crezca o el proyecto pase a Codeversion
(GitLab institucional).

## Qué se versiona

Solo `scripts/` (el código) y `.gitignore`. Todo lo demás queda fuera del
repo a propósito (`.gitignore`):

```gitignore
/*
!/scripts/
!/.gitignore
!/README.md
!/docs/

**/__pycache__/
*.pyc
```

**Por qué**: esta carpeta de trabajo mezcla código con bases de datos e
insumos pesados (CSV de 1GB+, `.sas7bdat`, Excel, `.docx`) que no deben vivir
en un repositorio de control de versiones - ni por tamaño, ni porque son
datos de encuesta. Cualquier archivo nuevo bajo `Bases Calibradas/`,
`output/`, `01Entrada/`, etc. NO se sube aunque `git add -A` lo sugiera -
verificar con `git status` antes de cualquier commit.

## Flujo objetivo (GitFlow simplificado)

```
main                    ← núcleo estable, protegido
  ↑ PR + CI
develop                 ← integración del equipo
  ↑ PR + CI
feature/nombre-corto    ← una rama por cambio, aislada
```

1. **Sincronizar**: `git pull` sobre `develop` antes de empezar.
2. **Aislar**: `git checkout -b feature/nombre-corto`.
3. **Desarrollar**: commits atómicos y trazables (ver mensajes, abajo).
4. **Proponer**: `git push` + Pull Request hacia `develop`.
5. **Aprobar**: revisión por pares antes de `merge`.

`main` nunca recibe commits directos - solo llega ahí vía `develop`, tras
validación.

## Mensajes de commit

Convención a seguir (no aplicada retroactivamente al historial actual):

```
<tipo>: <resumen corto en imperativo>

<cuerpo opcional: por qué, no qué - el diff ya dice qué cambió>
```

Tipos sugeridos: `feat` (funcionalidad nueva), `fix` (corrección de bug),
`docs` (documentación), `refactor` (sin cambio de comportamiento), `data`
(cambios en factores/listas de calibración, ej. `MUNICIPIOS_EXCLUIDOS_C1`).

## Regla de oro: documentación en el mismo commit/PR que el código

Si un cambio agrega o modifica un módulo, agrega/actualiza también:

- El docstring del módulo/función.
- `docs/04_modulos.md` si es un módulo nuevo o cambia su propósito.
- `docs/03_configuracion.md` si agrega/quita una constante de `config.py`.
- `docs/01_arquitectura.md` si cambia una decisión de diseño (ej. una nueva
  fuente de datos, un nuevo factor de calibración).

Un cambio de código sin la documentación correspondiente actualizada no está
completo.

## Pendientes para llegar al estándar completo

- [ ] `requirements.txt` con versiones exactas (`pip freeze > requirements.txt`).
- [ ] Migrar a Codeversion (GitLab institucional) si el proyecto pasa a
      producción DANE.
- [ ] Ramas `develop`/`main` con protección y CI (linters, al menos).
- [ ] Definir dueño(s) de revisión de PR.

## Ver también

- [README.md](../README.md) - estado general del proyecto.
