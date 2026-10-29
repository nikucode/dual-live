# Strudel, Ableton y dual.live: estudio aplicado

29 de octubre de 2026. Objetivo: hacer que todo el flujo creativo ocurra dentro de la terminal, con sonido, pistas y código editables mientras se reproduce.

## Evidencia de Strudel

REA analizó de forma **estática** dos módulos publicados y previamente capturados del REPL de Strudel: `Repl.DiKk94Ki.js` y `PatternsTab.B07-WynU.js`. Artefacto local SHA-256 `53d5d8dad7036dbe189fac718c4d87227ad2620327e885914f7a103face44c2e`; Evidence principal `ev_bf9cf97c51f28020f4a783898a7f3383b7fd5a10187852b3f558a824e8f443dc`. REA observó referencias y exportación `Repl` en `ev_2ccd1a896eb65c2ea5034d9552331379a21700b67e6110c3d5474e89f7f82471`. La extracción cubrió esos dos archivos; 32 archivos inventariados quedaron sin análisis. No se ejecutó el REPL y no se midió audio.

En el módulo `Repl.DiKk94Ki.js`, la inspección directa del artefacto muestra llamadas separadas a `setCode(...)` y `evaluate(...)`, además de estado `isDirty`, `pending` y `activeCode`. Esto **sugiere** una separación útil entre texto en edición y patrón activo. La documentación oficial confirma que el REPL transpila y evalúa el código para crear un patrón, y que el programador consulta ese patrón periódicamente para generar eventos próximos. [Arquitectura oficial del REPL](https://strudel.cc/technical-manual/repl/).

La mini-notación de Strudel representa secuencias dentro de ciclos, subdivisiones con corchetes, silencios, repetición y otras transformaciones. Nuestro `x...` fijo de 16 pasos es apenas la primera capa; aumentar expresividad requerirá un modelo de eventos temporales y no solo añadir caracteres a la fila. [Mini-notación oficial](https://strudel.cc/learn/mini-notation/). Strudel también documenta síntesis con senoide, diente de sierra, cuadrada, triangular y ruido; estos son buenos bloques para sonidos editables de origen local. [Síntesis oficial](https://strudel.cc/learn/synths/).

REA detectó además referencias estáticas a imports de `mermaid` y `svg-pan-zoom` desde CDN en el módulo del REPL. Son rutas de funciones auxiliares del artefacto inspeccionado; **no prueban** que se pidan al tocar música. Si integramos la interfaz publicada completa, habrá que revisar y empaquetar también esas rutas para conservar el funcionamiento offline. Evidence `ev_2ccd1a896eb65c2ea5034d9552331379a21700b67e6110c3d5474e89f7f82471`. Una búsqueda REA de la cadena `setCode` no encontró una entidad en el grafo parcial (`ev_3f66f559730fcd7c1ca344396d867e5c7d837a42d543a287528864255c7d0939`); no se interpreta como ausencia de esa función.

## Evidencia de Ableton Live

No se encontró una instalación o instalador de Ableton Live en las ubicaciones locales revisadas. Por tanto **no hay análisis REA de su aplicación nativa**. Las conclusiones de esta sección proceden del manual oficial de Live 12.

El manual describe la separación entre pista, dispositivo/instrumento y clip, con edición contextual del elemento seleccionado. Los Drum Racks asignan cadenas a notas distintas, y sus Macro Controls exponen parámetros esenciales sin mostrar siempre toda la estructura. [Instrument, Drum and Effect Racks](https://www.ableton.com/en/live-manual/12/instrument-drum-and-effect-racks/). La vista Session permite lanzar clips en cualquier orden sin interrumpir el tiempo musical global; esto inspira futuras escenas en dual.live, no una copia de su interfaz. [Live Concepts](https://www.ableton.com/en/manual/live-concepts/). El manual de accesibilidad también describe navegación por teclado y ayuda textual al enfocar controles, pertinente a nuestra TUI. [Accessibility and Keyboard Navigation](https://www.ableton.com/en/live-manual/12/accessibility-and-keyboard-navigation/).

## Cambios aplicados en dual.live

1. La bienvenida enseña tres acciones concretas: escuchar, editar pasos y editar sonido.
2. La TUI tiene tres focos: GENERAL, PISTAS y SONIDO. Cada pista muestra los parámetros del sonido que usa: onda, frecuencia, duración, caída y nivel propio. Los cambios entran en las siguientes notas sin cerrar la sesión.
3. `e` abre un editor de `session.dual` **dentro del mismo programa**. Ctrl+R evalúa sin guardar, Ctrl+O evalúa y guarda, Ctrl+X evalúa y vuelve. El código inválido deja activo el último estado válido.
4. Los cambios con flechas sincronizan las líneas del código preservando los comentarios existentes. El archivo sigue siendo texto y puede compartirse sin instalar ningún editor.

## Preguntas abiertas

- Validar de oído la modificación de parámetros y el editor durante una actuación real, fuera del aislamiento de esta sesión.
- Diseñar la próxima capa rítmica: subpasos, variación de vueltas y notas por evento, con pruebas de orden temporal y límites de CPU.
- Si se dispone de un artefacto legítimo de Ableton Live, estudiar con REA el flujo exacto de selección de dispositivo y modificación de macro sin asumir que el manual describe la implementación interna.
