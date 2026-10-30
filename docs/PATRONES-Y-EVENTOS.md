# Patrones expresivos en dual.live

30 de octubre de 2026. Continuación del [estudio de Strudel y Ableton](ESTUDIO-STRUDEL-ABLETON-REA.md).

## Qué aprendimos al contrastarlos

**Strudel.** Su mini-notación divide un ciclo: un grupo entre corchetes ocupa el tiempo de un elemento del nivel superior. Añadir eventos dentro del grupo aumenta la densidad, no la duración del ciclo. También permite pausas, transformaciones y patrones de parámetros. La documentación del REPL explica que el código evaluado produce un patrón y que el programador consulta eventos de intervalos próximos mientras suena. [Mini-notación](https://strudel.cc/learn/mini-notation/), [arquitectura del REPL](https://strudel.cc/technical-manual/repl/). El análisis REA previo de dos módulos publicados respalda la separación entre texto editado y código activo, pero fue estático y parcial; no se midió su programador en ejecución. Evidence `ev_bf9cf97c51f28020f4a783898a7f3383b7fd5a10187852b3f558a824e8f443dc`.

**Ableton Live.** El editor MIDI expone propiedades por nota como velocidad y probabilidad; los clips tienen envolventes que afectan parámetros de instrumentos y mezclador. Esto muestra una separación útil entre la receta del instrumento y los eventos que la activan. No se analizó un binario de Live con REA porque no hay uno local; estas afirmaciones proceden del manual oficial. [Editing MIDI](https://www.ableton.com/en/live-manual/12/editing-midi/), [Clip Envelopes](https://www.ableton.com/en/live-manual/12/clip-envelopes/).

**Decisión para dual.live.** Mantener una vuelta de 16 pasos facilita el primer contacto con la terminal. Cada paso puede ahora contener subeventos. No copiamos el lenguaje de Strudel: definimos un subconjunto propio, documentado y limitado, que podemos tocar offline sin JavaScript ni servicio externo.

## Modelo implementado

El analizador convierte la cadena de una pista en 16 `Step`; cada uno contiene cero o más `Hit` con posición relativa dentro del paso, intensidad y transposición en semitonos. La interfaz simple sigue escribiendo `x` y `.`. La interfaz avanzada usa `X`, `[xx]`, `[x.X.]` y `x{+7}`. El sonido final toma la frecuencia y envolvente del `sound` de la pista; el evento puede variar su intensidad y tono. El render WAV y el motor en vivo usan el mismo analizador de pasos.

Ejemplo: en `track kick x...x...[xx]...x.x.`, `[xx]` ocupa **un** paso base y dispara dos golpes a mitad de ese paso. En la vista de terminal, ese paso aparece como `2`; al seleccionarlo se ve la expresión completa.

El límite actual es de 64 golpes por vuelta, ocho subpasos por grupo y transposición de −24 a +24 semitonos. Es una protección del motor Python en tiempo real, no un límite musical de Strudel o Ableton. El tono de osciladores se limita antes de Nyquist; las ondas cuadrada y diente de sierra siguen siendo síntesis simple y pueden presentar aliasing en frecuencias altas. Los golpes acentuados se mezclan y la salida PCM se limita a rango seguro; si muchas capas coinciden, puede haber distorsión por recorte. El siguiente paso de audio es medir y mejorar esa mezcla, no subir el nivel sin control.

## Cómo evolucionar sin perder claridad

1. **Ahora:** un paso seleccionado muestra su expresión completa; `r` crea repeticiones, `X` acentúa, y `e` permite transposición con código en la propia terminal.
2. **Después:** nombres de notas y escalas para bajo/melodía, y variación por vuelta con una semilla reproducible. Esa variación debe renderizarse igual en vivo y en WAV.
3. **Más adelante:** automatización de parámetros, clips/escenas y archivos de audio propios como opción local. Mantener síntesis matemática como punto de partida y verificar que la importación no introduzca una dependencia de red.

Las pruebas automatizadas comprueban la duración de la vuelta, el instante de cada subgolpe, el cambio de frecuencia, la intensidad y el límite de densidad. La escucha real en el equipo de Javi sigue siendo una validación distinta.
