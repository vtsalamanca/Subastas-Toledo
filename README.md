# Subastas-Toledo

Proyecto público de seguimiento de subastas inmobiliarias en Toledo y alrededores, ejecutado en GitHub Actions sin ordenador local.

## Estado verificable
- La página inicial del Portal de Subastas BOE y su formulario de búsqueda avanzada son accesibles públicamente (comprobado manualmente el 17/10/2026).
- **La extracción automatizada de anuncios no está implementada ni validada.** Las fuentes del catálogo son candidatas, no fuentes ya comprobadas automáticamente.
- El workflow programado ejecuta un diagnóstico diario y publica `not_checked`, no anuncios ficticios.
- La web en `docs/index.html` muestra `docs/data/results.json` y `docs/data/status.json`.

## Activar GitHub Pages
En Settings > Pages elegir Deploy from a branch, rama `main`, carpeta `/docs`. URL esperada: https://vtsalamanca.github.io/Subastas-Toledo/ (no confirmada hasta comprobar el despliegue).

## Siguientes tareas
1. Desarrollar un adaptador de consulta del BOE y probar respuesta, paginación, provincias, localidades y enlaces originales.
2. No registrar una fuente como verificada salvo que se haya consultado y validado la respuesta de esa ejecución.
3. Añadir controles de duplicados, historial, errores y tests de integración.
4. Añadir otras fuentes con la misma validación.

No almacenar credenciales ni datos privados en este repositorio público.
