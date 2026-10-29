# dual.live — taller de sonidos

Propuesta actualizada a partir de la idea de Alex: crear sonidos mediante síntesis, aprender modificándolos y utilizarlos en livecoding. Este documento describe el diseño; aún no hay implementación del panel.

## El centro del instrumento

Los presets son recetas editables de síntesis: forma de onda, frecuencia, evolución temporal, filtros y mezclas. Se guardan como parámetros y se generan localmente cada vez que suenan. La biblioteca inicial puede funcionar sin descargar ni incluir grabaciones.

Tres fuentes de sonido, con síntesis como opción inicial:

1. **Crear:** osciladores y ruido generados por la aplicación.
2. **Abrir archivo:** sonidos del equipo, importados a la biblioteca local.
3. **Importar desde una URL:** acción explícita que necesita conexión y guarda una copia local reutilizable. Indicar procedencia y licencia cuando estén disponibles. No prometer compatibilidad con cualquier URL: existen restricciones de acceso, formato y CORS.

Después de importar, el proyecto referencia su copia local. Una URL guardada por sí sola no es un sonido disponible offline. Para compartir proyectos con archivos, exportar los recursos junto con la escena.

## Una interfaz que permite profundizar

```text
+---------------------------------------------------+
| sonido: [bombo suave v]                  [escuchar] |
|                                                   |
| tono        grave -------o-------- agudo          |
| cola        corta ----o----------- larga          |
| golpe       redondo --------o----- marcado        |
|                                                   |
| [comparar original] [guardar como...]              |
| > ver como funciona                               |
+---------------------------------------------------+
```

El panel ampliado muestra valores numéricos, unidades y curvas correspondientes a esos mismos controles. No son dos sintetizadores independientes ni dos niveles de capacidad de la persona. Se puede abrir o cerrar la explicación cuando resulte útil.

| Control inicial del bombo | Qué modifica | Detalle ampliado |
|---|---|---|
| Tono: grave/agudo | Frecuencia final del cuerpo | Hz y nota aproximada |
| Cola: corta/larga | Tiempo que tarda en apagarse | Decaimiento de amplitud en ms |
| Golpe: redondo/marcado | Cantidad de subida inicial respecto al tono final | Envolvente de frecuencia: desplazamiento en semitonos |

El tiempo de caída de frecuencia comienza fijo y aparece como control adicional al desplegar detalles. Así los tres primeros sliders tienen una relación clara con el motor. Los nombres se adaptan al instrumento: un control útil para un bombo no tiene por qué significar lo mismo para un pad.

Cada slider también admite teclado y entrada numérica. Los cambios se pueden deshacer y el preset original queda recuperable. El volumen maestro es independiente del carácter del sonido. La aplicación abre silenciosa; escuchar un golpe requiere pulsar el botón, y repetirlo es una acción explícita.

## Qué hace que una onda se convierta en un instrumento

Elegir seno, triángulo, cuadrada o sierra cambia el contenido armónico. Para obtener un instrumento también hay que decidir cómo cambia su altura y su amplitud durante el tiempo. Una onda constante produce un tono sostenido; el gesto temporal del sonido es una parte importante de su identidad.

Ejemplos de recetas propuestas, no imitaciones exactas de instrumentos acústicos:

| Preset | Receta inicial |
|---|---|
| Bombo | Seno con frecuencia descendente y amplitud que se apaga |
| Caja | Ruido filtrado mezclado con un cuerpo tonal breve |
| Hi-hat | Ruido con filtro pasaaltos y duración corta |
| Bajo | Sierra o cuadrada filtrada con envolvente de amplitud |

Para el primer prototipo basta el **bombo**. Una vez claros los controles y su vínculo con código/patrón, añadir caja y hi-hat permite crear ritmos con un pequeño kit enteramente sintetizado.

## Una receta matemática que se puede explorar

Modelo de un bombo sencillo:

```text
f(t) = f_final + (f_inicial - f_final) · exp(-t / tau_f)
fase(t) = 2π · integral de f(u), desde u=0 hasta u=t
x(t) = A(t) · sin(fase(t))
```

`f(t)` desciende rápidamente: por ejemplo, de 150 a 50 Hz. `A(t)` sube con un ataque muy corto y luego decae. Los valores son puntos de partida para experimentar, no un preset afinado y probado. Con frecuencia variable, la fase se obtiene integrando la frecuencia: usar simplemente `sin(2π · f(t) · t)` no representa en general esa misma frecuencia instantánea.

En la implementación no hace falta calcular manualmente cada muestra. Web Audio proporciona un oscilador con frecuencia y tipo de onda controlables y permite programar su inicio y final. [OscillatorNode](https://developer.mozilla.org/en-US/docs/Web/API/OscillatorNode). La automatización puede dibujar cambios graduales de frecuencia y ganancia; las rampas exponenciales requieren valores positivos. Para silenciar, terminar con una pequeña rampa apropiada y detener la voz. [Automatización exponencial](https://developer.mozilla.org/en-US/docs/Web/API/AudioParam/exponentialRampToValueAtTime).

La visualización educativa debe distinguir **forma de onda**, **envolvente temporal** y **espectro**. Mostrar inicialmente la señal y, al desplegar detalles, las curvas de frecuencia y amplitud. Etiquetar qué gráficos son mediciones y cuáles representan parámetros del preset.

## Cómo encaja con Strudel

Strudel ya incluye síntesis: ondas básicas, ruido y controles adicionales. Podemos investigar sus voces y envolventes antes de crear adaptadores nuevos. [Síntesis de Strudel](https://strudel.cc/learn/synths/). La captura anterior también encontró registros de sintetizadores en el arranque publicado, junto a los bancos remotos; esos bancos no son necesariamente un requisito para las voces sintetizadas.

El motor musical conserva un solo reloj. El preset define **cómo** suena una voz; el patrón define **cuándo** se dispara. La preescucha y el patrón deben utilizar la misma receta. Si una voz requiere Web Audio propio, registrar su disparo en el planificador musical; no crear un segundo `setInterval` para el panel.

## Controles y código sin pisarse

Propuesta inicial: los parámetros del instrumento viven en un objeto de datos compartido. Los sliders y los campos numéricos editan ese objeto. El panel ofrece una vista de su receta y exportación; el código del patrón se mantiene separado y referencia el instrumento.

No intentar deducir posiciones de sliders a partir de cualquier código JavaScript. Una receta libre puede tener funciones que no admiten una traducción reversible a tres controles. Al pasar una receta a código libre, conservar una copia y mostrar qué controles siguen vinculados. Un slider nunca debe reescribir silenciosamente un sketch personalizado.

Para percusión, los nuevos parámetros se aplican al próximo golpe; esto debe indicarse. Más adelante se puede añadir modulación de voces sostenidas con cambios suavizados. Guardar nombre, tipo de voz, parámetros y versión del esquema permite recrear el sonido sin una grabación.

## Primera entrega que valida esta idea

Un panel de bombo con tres sliders, detalles numéricos, botón de preescucha, comparar/restaurar, guardar receta y un patrón repetitivo editable que usa ese sonido. Verificar que funciona sin red, que lo guardado reproduce la misma receta y que detener cancela la sesión sin reinicios automáticos.

La identidad visual sigue siendo ASCII y cyberpunk suave, con ayuda contextual en español. Esta dirección sustituye la propuesta de empezar obligatoriamente con un banco de samples. Los samples, cortes de breaks e importación online siguen siendo ampliaciones útiles, especialmente para explorar breakcore.
