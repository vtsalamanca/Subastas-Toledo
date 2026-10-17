# Subastas-Toledo

Proyecto público de seguimiento de subastas inmobiliarias en Toledo y alrededores, ejecutado en GitHub Actions sin ordenador local.

## Estado verificable
- El adaptador consulta el formulario oficial del Portal de Subastas BOE con un ámbito explícito: inmuebles, estado `Celebrándose` y provincia de Toledo.
- Recorre todas las páginas de resultados y exige que el total declarado por el portal coincida con el número de referencias únicas extraídas.
- Para cada referencia lee información general, autoridad gestora, bienes o lotes, pujas y enlaces a documentos públicos.
- Una ejecución solo se marca como completa cuando no falta ninguna ficha ni ningún lote declarado. La prueba se publica en `data/diagnostics.json`.
- La ejecución validada el 17/10/2026 obtuvo 18 de 18 subastas, 18 fichas legibles, 85 bienes y 0 errores.
- La cobertura es completa dentro de ese ámbito público; no incluye información reservada a usuarios registrados ni subastas presenciales ajenas al Portal BOE.
- La web en `docs/index.html` muestra los bienes estructurados y el resumen de cobertura.

## Activar GitHub Pages
En Settings > Pages elegir Deploy from a branch, rama `main`, carpeta `/docs`. URL esperada: https://vtsalamanca.github.io/Subastas-Toledo/ (no confirmada hasta comprobar el despliegue).

## Siguientes tareas
1. Añadir historial de cambios entre ejecuciones y estados finalizados o suspendidos.
2. Mantener pruebas de contrato para detectar cambios en el HTML del Portal.
3. Incorporar por separado las subastas presenciales de SEGIPSA, sin mezclarlas con la cobertura electrónica del BOE.
4. No registrar una ejecución como completa si el contador, la paginación, una ficha o un lote no cuadran.

No almacenar credenciales ni datos privados en este repositorio público.
