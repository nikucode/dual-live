# dual.live / estudio de ritmos en terminal

Actualización del 29 de octubre de 2026.

## Qué funciona hoy

- Interfaz de terminal con una bienvenida paso a paso y guía reabrible con `?`.
- Síntesis local de bombo, caja, hi-hat y bajo mediante senoide, diente de sierra y ruido. También se pueden definir ondas cuadradas y triangulares.
- BPM de 40 a 300, volumen general de 0 a 100 y hasta 12 pistas de 16 pasos.
- Edición por teclado durante la reproducción: pasos de las pistas, forma de onda, frecuencia, duración, caída y nivel de cada sonido. El código de `session.dual` se edita dentro de la misma interfaz y se aplica sin reiniciar el ritmo.
- Exportación WAV local y taller visual anterior con `--web`.
- Instalación de un comando en `~/.local/bin` con `install.sh`; no se descargan paquetes al tocar.

## Lenguaje actual

```text
bpm 180
volume 85
sound kick sine 52 320 55
track kick x...x...x...x.x.
```

`sound` define nombre, onda, frecuencia en Hz, duración en ms, caída inicial de frecuencia y, opcionalmente, nivel propio de 0 a 100. `track` asocia un sonido a 16 pasos. Una `x` toca y un `.` calla. Un archivo inválido conserva la sesión anterior y muestra un error con línea cuando es posible.

## Próximos pasos útiles

1. Notas o parámetros distintos por paso para líneas de bajo y melodías.
2. Acentos, subdivisiones y variación por vuelta para ritmos breakcore.
3. Importar sonidos propios desde archivos locales de forma opcional.
4. Unificar la sesión entre terminal y taller visual; después explorar integración con Strudel/Hydra sin descargas al tocar.
5. Pruebas de audio en máquinas distintas; el motor actual usa `aplay` y PipeWire/ALSA.

El código actual es un lenguaje pequeño propio. La compatibilidad con sintaxis Strudel todavía no está implementada.
