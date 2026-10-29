# Hallazgos para construir dual.live sin internet

Investigación del 29 de octubre de 2026. Este documento añade evidencia concreta a la propuesta; no certifica todavía una aplicación offline.

## Resultado principal

La integración es viable como diseño, pero copiar la interfaz o usar las funciones de inicio por defecto puede mantener dependencias de internet. Encontramos dos puntos concretos en los módulos publicados de Strudel: el inicio de bancos de sonidos y la descarga dinámica de Hydra.

## Qué se obtuvo

La clonación de Git falló con `Could not resolve host: github.com`. Por tanto, **no hay repositorios completos clonados**. Se consultó código público de Hydra mediante navegación y se utilizó REA para capturar los cuerpos de los scripts servidos por Strudel, exportándolos localmente con un manifiesto de procedencia y hashes.

- Captura: `rea-strudel-fuentes.json`.
- Scripts exportados: `upstream/strudel-publicado/files/`.
- Procedencia, URL y SHA-256 de cada archivo: `upstream/strudel-publicado/manifest.json`.
- Evidencia de captura: `ev_28f64d9db04da708aa6396f0f4dafc226e7d05c46149773679ea71bf2f20033a`.

La captura utilizó Chromium temporal en modo headless, almacenamiento vacío y service workers bloqueados. REA abrió el sitio y esperó seis segundos tras navegar. Algunos límites de retención se alcanzaron: no representa todos los módulos ni toda actividad posible. Los archivos exportados permiten inspección estática; haberlos descargado no demuestra que todas sus funciones se ejecutaran. No se pulsó reproducir ni se probó audio.

## 1. `initHydra()` tiene una descarga remota por defecto

Archivo exportado: `hydra.DIhEaGsV.js`.

El módulo exporta `initHydra`, `clearHydra` y `H`. En su inicialización toma una opción `src` cuyo valor por defecto es `https://unpkg.com/hydra-synth`, realiza un `import` dinámico de esa ruta y luego construye Hydra.

**Implicación:** incluir el módulo de integración de Strudel no incluye automáticamente el motor visual. Hay que empaquetar también hydra-synth y configurar esa ruta, o crear una integración propia que lo importe desde la compilación local.

**Decisión propuesta:** cargar Hydra una vez desde archivos locales al iniciar la aplicación. El sketch del usuario no debe tener que resolver la instalación de su motor. La posibilidad de sustituir `src` está observada en este módulo; sigue pendiente validar la ruta y el formato exactos de nuestra distribución.

El mismo módulo inicia con `detectAudio: false` y permite `feedStrudel`. La función `H` consulta un patrón en el tiempo actual. Esto sirve como candidato para conectar imagen y patrón sin depender de un micrófono. No demuestra sincronización audiovisual medida.

## 2. El arranque del sitio carga bancos externos

Archivo exportado: `prebake.DWT_uGxT.js`.

La inicialización contiene una base `https://strudel.b-cdn.net` y solicitudes a piano, VCSL, cajas de ritmos, uzu-drumkit, uzu-wavetables y mridangam, además de registros de sintetizadores y soundfonts.

Los catálogos observados en la captura de arranque coinciden con rutas presentes en ese módulo. Esa coincidencia respalda el punto de integración, pero las capturas no contienen pilas de iniciadores para atribuir cada petición a una línea concreta.

**Decisión propuesta:** usar una inicialización propia que registre solamente los sonidos necesarios. Primera biblioteca: bombo, caja, hi-hat y un break original o con licencia comprobada. Incluir tanto el mapa de nombres como los archivos de audio. No copiar toda la biblioteca remota por defecto.

También debe auditarse la carga de AudioWorklets, soundfonts y cualquier importación diferida de la versión elegida. Esa revisión aún no está completa.

## 3. El sitio Hydra y el motor Hydra son componentes distintos

El [HTML del sitio Hydra](https://github.com/hydra-synth/hydra/blob/main/index.html) referencia hydra-synth y p5.js desde CDN, fuentes de Google y un favicon remoto. Estas referencias explican parte de las solicitudes observadas previamente.

En el [constructor del motor](https://github.com/hydra-synth/hydra-synth/blob/main/src/hydra-synth.js), `pb` empieza en `null`, el canvas se puede proporcionar y la detección de audio es configurable. Su `hush()` limpia fuentes y salidas; no detiene por sí mismo el bucle de animación.

**Decisión propuesta:** usar hydra-synth dentro de nuestra interfaz. No incorporar automáticamente galerías, traducciones remotas ni conexiones de la plataforma online. El botón detener de dual.live debe coordinar audio y visuales explícitamente, distinguiendo silenciar/limpiar de congelar el dibujo.

Las [fuentes de Hydra](https://github.com/hydra-synth/hydra-synth/blob/main/src/hydra-source.js) admiten imágenes, videos y canvas. Un canvas con dibujos ASCII propios puede ser entrada visual; las imágenes y videos deben tener rutas locales. Estas posibilidades proceden de lectura de código, no de una prueba visual local realizada aquí.

## 4. Corrección de la propuesta anterior

El ejemplo que contenía `await initHydra()` sin opciones no debe presentarse como offline. Tampoco se puede dar por hecho que `s("bd sd")` encontrará sonidos locales: esos nombres necesitan un banco registrado por nuestra aplicación.

La interfaz pequeña sigue siendo adecuada, pero hay que separar sus responsabilidades:

| Instalación y arranque | Sketch de Javi |
|---|---|
| Cargar motores locales y banco de sonidos | Escribir patrones y transformaciones |
| Inicializar el reloj y el canvas | Elegir cómo cambia la escena |
| Gestionar ejecutar/detener/guardar | Experimentar con valores y capas |
| Mostrar errores y recursos faltantes | Consultar ejemplos y conceptos |

## Siguiente prueba concreta

Construir un banco de integración local mínimo: un patrón, cuatro sonidos locales y un visual generado. Permitir solo solicitudes a loopback durante la prueba. Abrir con perfil vacío, ejecutar, modificar, detener y volver a abrir. Registrar tanto solicitudes permitidas como intentos externos bloqueados, errores, audio generado y cambios del canvas.

La captura de red por sí sola no prueba que haya sonido ni que el shader produzca una imagen correcta. Esas verificaciones se deben registrar por separado. El contenido actual son insumos de investigación, no una distribución instalable.
