# dual.live / estudio de ritmos offline

Un instrumento de terminal para aprender síntesis y escribir ritmos con código. Necesita Python 3 y `aplay` para escuchar. No necesita conexión, paquetes Python ni samples descargados. En este equipo, `dual-live` está enlazado en `~/.local/bin`. En otra máquina, ejecuta `./install.sh` una vez desde esta carpeta; también puedes usar `./dual-live` sin instalar el comando global.

## Primera misión, paso a paso

1. Abre una terminal de al menos **60 columnas y 24 filas** y escribe `dual-live`.
2. Lee la pantalla de bienvenida y pulsa **Enter**. Puedes volver a verla con `?`.
3. Pulsa **`p`** para tocar las pistas juntas; otra vez `p` las detiene. **Espacio** escucha el instrumento seleccionado.
4. Pulsa **Tab** hasta **PISTAS**. Con `↑` y `↓` elige una. Con `←` y `→` mueve el cursor `^` por sus 16 pasos. Escribe `x` para tocar o `.` para callar.
5. Pulsa **Tab** una vez más hasta **SONIDO**. Verás los parámetros de esa pista: onda, frecuencia, duración, caída y nivel propio. Elige uno con `↑` y `↓`; ajústalo con `←` y `→`. Puedes seguir tocando mientras cambias el sonido.
6. Otro **Tab** vuelve a **GENERAL**, donde ajustas BPM (40–300) y volumen general (0–100).
7. Pulsa **`e`** para escribir código **dentro de dual.live**. Usa **Ctrl+R** para aplicar sin parar el ritmo, **Ctrl+O** para aplicar y guardar, o **Ctrl+X** para aplicar y volver. Si hay un error, el sonido anterior sigue y puedes corregir la línea. También funcionan F5, F2 y Esc en terminales que envían esas teclas.
8. Pulsa **`s`** en la vista principal para guardar cambios hechos con las flechas. El archivo conserva comentarios existentes cuando sincroniza las líneas de controles, sonidos y pistas. **`l`** recarga el archivo si lo modificaste desde fuera.
9. Pulsa **`q`** para salir. Detiene el sonido.

Si tu terminal no envía las flechas, **`j`/`k`** bajan/suben y **`-`/`+`** retroceden/avanzan o ajustan el valor.

La sesión vive en `~/.config/dual-live/session.dual`. La primera ejecución crea una sesión de ejemplo con kick, snare, hat y bass. Puedes abrir otra sesión con `dual-live --session ruta/a/mi-pista.dual`.

## Livecoding sencillo

El archivo contiene instrucciones legibles. Este ejemplo crea un sonido de bombo y decide cuándo tocarlo:

```text
bpm 180
volume 85
sound kick sine 52 320 55 100
track kick x...x...x...x.x.
```

| Instrucción | Significado |
| --- | --- |
| `bpm 180` | Velocidad en pulsos por minuto |
| `volume 85` | Volumen general, de 0 a 100 |
| `sound kick sine 52 320 55 100` | Nombre, onda, frecuencia en Hz, duración en ms, caída inicial y nivel propio (0–100) |
| `track kick x...x...x...x.x.` | 16 pasos: `x` toca ese sonido, `.` deja silencio |

Puedes crear más sonidos con `sound` y más pistas con `track` (hasta 12). Las ondas disponibles son `sine`, `square`, `saw`, `triangle` y `noise`. Por ejemplo, cambia la caja o inventa un sonido:

```text
sound glitch square 440 90 30 75
track glitch x...xx..x.x..xx.
```

Cada `track` debe nombrar un `sound` definido en el archivo. El nivel propio es opcional en archivos anteriores: si falta, vale 100. Si varias pistas usan el mismo nombre de sonido, editarlo cambia todas esas pistas. Si el código tiene un error, la terminal indica la línea y conserva la última sesión válida. Los cambios válidos se aplican en los pasos siguientes; el ritmo no se reinicia. Esto es un lenguaje pequeño propio, pensado como puente hacia patrones más expresivos al estilo Strudel. Aún no admite notas distintas en cada paso, samples del usuario ni sintaxis de Strudel.

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
