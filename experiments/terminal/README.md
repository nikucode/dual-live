# dual.live / estudio de ritmos offline

Un instrumento de terminal para aprender síntesis y escribir ritmos con código. Necesita Python 3 y `aplay` para escuchar. No necesita conexión, paquetes Python ni samples descargados. En este equipo, `dual-live` está enlazado en `~/.local/bin`. En otra máquina, ejecuta `./install.sh` una vez desde esta carpeta; también puedes usar `./dual-live` sin instalar el comando global.

## Primera misión, paso a paso

1. Abre una terminal de al menos **60 columnas y 20 filas** y escribe `dual-live`.
2. Lee la pantalla de bienvenida y pulsa **Enter**. Puedes volver a verla con `?`.
3. Pulsa **Espacio** para escuchar el instrumento seleccionado. Pulsa **`p`** para tocar las cuatro pistas juntas; otra vez `p` las detiene.
4. Pulsa **Tab** para pasar de los controles a las pistas. Con `↑` y `↓` elige una pista. Con `←` y `→` mueve el cursor `^` por sus 16 pasos. Escribe `x` para que suene ahí o `.` para dejar silencio. Los cambios entran mientras toca.
5. Pulsa **Tab** para volver a los controles. Elige BPM o volumen con `↑` y `↓`; cambia el valor con `←` y `→`. El volumen va de 0 a 100 y el tempo de 40 a 300 BPM.
6. Pulsa **`e`** para abrir el archivo de código en tu editor (`$EDITOR`, o nano). Edita, guarda y sal del editor: la sesión se recarga y sigue tocando. Si editas el archivo desde otra terminal, pulsa **`l`** para recargarlo.
7. Pulsa **`s`** para guardar en el archivo los cambios hechos con las flechas y teclas. Esto reescribe el archivo, incluidos los comentarios; si escribiste notas propias, guarda una copia antes.
8. Pulsa **`q`** para salir. Detiene el sonido.

La sesión vive en `~/.config/dual-live/session.dual`. La primera ejecución crea una sesión de ejemplo con kick, snare, hat y bass. Puedes abrir otra sesión con `dual-live --session ruta/a/mi-pista.dual`.

## Livecoding sencillo

El archivo contiene instrucciones legibles. Este ejemplo crea un sonido de bombo y decide cuándo tocarlo:

```text
bpm 180
volume 85
sound kick sine 52 320 55
track kick x...x...x...x.x.
```

| Instrucción | Significado |
| --- | --- |
| `bpm 180` | Velocidad en pulsos por minuto |
| `volume 85` | Volumen general, de 0 a 100 |
| `sound kick sine 52 320 55` | Nombre, tipo de onda, frecuencia en Hz, duración en ms y caída inicial de frecuencia |
| `track kick x...x...x...x.x.` | 16 pasos: `x` toca ese sonido, `.` deja silencio |

Puedes crear más sonidos con `sound` y más pistas con `track` (hasta 12). Las ondas disponibles son `sine`, `square`, `saw`, `triangle` y `noise`. Por ejemplo, cambia la caja o inventa un sonido:

```text
sound glitch square 440 90 30
track glitch x...xx..x.x..xx.
```

Cada `track` debe nombrar un `sound` definido en el archivo. Si el código tiene un error, la terminal indica la línea y conserva la última sesión válida. Los cambios de código se aplican en los pasos siguientes; el ritmo no se reinicia al recargar. Esto es un lenguaje pequeño propio, pensado como puente hacia patrones más expresivos al estilo Strudel. Aún no admite notas distintas en cada paso, samples del usuario ni sintaxis de Strudel.

## Exportar y usar el taller visual

```bash
dual-live --render mi-pista.wav --bars 8
dual-live --web
```

El WAV se genera localmente. `--web` abre el taller visual anterior en un navegador mediante `127.0.0.1`. Su receta se guarda por separado. No hay todavía sincronización entre la terminal y el navegador, motor Hydra ni plugin de Omarchy.

## Para desarrollar

```bash
cd /home/minimodecoro/Projects/dual-live-investigacion/prototipo
python3 -B -m unittest -v test_studio.py test_terminal.py
```

`session.example.dual` contiene el ejemplo que acompaña al proyecto. `studio.py` implementa el estudio actual; `terminal.py` conserva el primer taller de bombo para comparar su evolución.
