// ---------------------------------------
// obtengo canvas
// ---------------------------------------
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

// ---------------------------------------
// sistema de capas (layers)
// ---------------------------------------
let layers = [];

// agregar una capa
function addLayer(fn) {
  layers.push(fn);
}

// limpiar capas (esto pasa cada frame)
function clearLayers() {
  layers = [];
}

// ---------------------------------------
// tamaño del canvas
// ---------------------------------------
function resizeCanvas() {
  canvas.width = canvas.clientWidth;
  canvas.height = canvas.clientHeight;
}

resizeCanvas();
window.addEventListener("resize", resizeCanvas);

// ---------------------------------------
// tiempo base (para animaciones)
// ---------------------------------------
let startTime = Date.now();
let time = 0;

// sliders globales (valores vivos)
let slider1 = 30;
let slider2 = 10;

// beat global para sincronizar visuales
let beat = 0;

// tiempo en segundos
function getTime() {
  return (Date.now() - startTime) / 1000;
}

// ---------------------------------------
// funciones base (mini lenguaje)
// ---------------------------------------

// fondo
function background(color = "black") {
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}

// circulo con color
function circle(x, y, r, color = "white") {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
}

// ---------------------------------------
// sistema de imagenes
// ---------------------------------------
const images = {};

// dibujar imagen
function drawImage(name, x, y, w, h) {

  // si no existe la imagen, la cargo
  if (!images[name]) {
    const img = new Image();
    img.src = "assets/" + name;
    images[name] = img;
  }

  const img = images[name];

  // si aun no carga, no dibujo
  if (!img.complete) return;

  // glow suave
  ctx.shadowBlur = 20;
  ctx.shadowColor = "white";

  ctx.drawImage(img, x, y, w, h);

  ctx.shadowBlur = 0;
}

// ---------------------------------------
// glitch (cortes horizontales)
// ---------------------------------------
function glitchImage(name, x, y, w, h, intensity = 10) {

  if (!images[name]) {
    const img = new Image();
    img.src = "assets/" + name;
    images[name] = img;
  }

  const img = images[name];

  if (!img.complete) return;

  let slices = 20;

  for (let i = 0; i < slices; i++) {

    let sliceY = (h / slices) * i;
    let sliceH = h / slices;

    let offset = (Math.random() - 0.5) * intensity;

    ctx.drawImage(
      img,
      0, sliceY, img.width, sliceH,
      x + offset, y + sliceY, w, sliceH
    );
  }
}

// ---------------------------------------
// onda (imagen liquida)
// ---------------------------------------
function waveImage(name, x, y, w, h, amplitude = 20, frequency = 0.05) {

  if (!images[name]) {
    const img = new Image();
    img.src = "assets/" + name;
    images[name] = img;
  }

  const img = images[name];

  if (!img.complete) return;

  let slices = 40;

  for (let i = 0; i < slices; i++) {

    let sliceY = (h / slices) * i;
    let sliceH = h / slices;

    // movimiento ondulado
    let offset = Math.sin(time * 2 + i * frequency) * amplitude;

    ctx.drawImage(
      img,
      0, sliceY, img.width, sliceH,
      x + offset, y + sliceY, w, sliceH
    );
  }
}


// ---------------------------------------
// sistema de audio (mini live coding)
// ---------------------------------------

let audioCtx = null;

// iniciar audio (necesario por seguridad del navegador)
function initAudio() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
}

// sonido kick (grave)
function kick(time) {
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();

  osc.type = "sine";
  osc.frequency.setValueAtTime(150, time);
  osc.frequency.exponentialRampToValueAtTime(50, time + 0.1);

  gain.gain.setValueAtTime(slider2 / 100, time);
  gain.gain.exponentialRampToValueAtTime(0.001, time + 0.1);

  osc.connect(gain);
  gain.connect(audioCtx.destination);

  osc.start(time);
  osc.stop(time + 0.1);
}

// snare (ruido)
function snare(time) {
  const noise = audioCtx.createBufferSource();
  const buffer = audioCtx.createBuffer(1, 44100, 44100);
  const data = buffer.getChannelData(0);

  for (let i = 0; i < 44100; i++) {
    data[i] = Math.random() * 2 - 1;
  }

  noise.buffer = buffer;

  const gain = audioCtx.createGain();
  gain.gain.setValueAtTime(1, time);
  gain.gain.exponentialRampToValueAtTime(0.01, time + 0.2);

  noise.connect(gain);
  gain.connect(audioCtx.destination);

  noise.start(time);
  noise.stop(time + 0.2);
}

// interpretar patron tipo "kick snare kick"
// ---------------------------------------
//  secuenciador (tipo strudel)
// ---------------------------------------

let currentPattern = [];
let currentStep = 0;
let bpm = 120;
let isPlaying = false;
let intervalId = null;

// interpretar patrones tipo "kick*2 snare"
function parsePattern(pattern) {

  let result = [];

  let parts = pattern.split(" ");

  for (let part of parts) {

    // si tiene *
    if (part.includes("*")) {

      let [sound, times] = part.split("*");
      times = parseInt(times);

      for (let i = 0; i < times; i++) {
        result.push(sound);
      }

    } else {
      result.push(part);
    }
  }

  return result;
}

// iniciar secuencia
function play(pattern, newBpm = 120) {

  if (!audioCtx) return;

  bpm = newBpm;
  currentPattern = parsePattern(pattern);
  currentStep = 0;

  if (intervalId) clearInterval(intervalId);

  const stepTime = (60 / bpm) * 1000;

  isPlaying = true;

  intervalId = setInterval(() => {

    const step = currentPattern[currentStep];

    const now = audioCtx.currentTime;

    if (step === "kick") kick(now);
    if (step === "snare") snare(now);

    currentStep = (currentStep + 1) % currentPattern.length;
    // guardamos el paso actual para usarlo en visuales
    window.beat = currentStep;
  }, stepTime);
}

// detener (muy importante)
function stop() {
  if (intervalId) {
    clearInterval(intervalId);
    intervalId = null;
  }
  isPlaying = false;
}

// ---------------------------------------
// codigo del editor
// ---------------------------------------
let currentCode = "";

// ejecutar codigo
function runCode() {
  currentCode = document.getElementById("editor").value;
}

// ---------------------------------------
// ejemplos interactivos
// ---------------------------------------

// ejemplo circulo
function exampleCircle() {

  const code = `
addLayer(() => {
  background("black")
})

addLayer(() => {
  circle(300, 200, 50, "#00ffff")
})
`;

  document.getElementById("editor").value = code;
  currentCode = code;

  closeManual();
}

// ejemplo onda
function exampleWave() {

  const code = `
addLayer(() => {
  background("rgba(0,0,0,0.1)")
})

addLayer(() => {
  waveImage("fondoonwn.jpg", 200, 100, 300, 300, 30, 0.1)
})
`;

  document.getElementById("editor").value = code;
  currentCode = code;

  closeManual();
}

// ---------------------------------------
// manual
// ---------------------------------------
function openManual() {
  document.getElementById("manual").style.display = "flex";
}

function closeManual() {
  document.getElementById("manual").style.display = "none";
}

// ---------------------------------------
// modo historia 💌
// ---------------------------------------
function startMemory() {

  currentCode = `
addLayer(() => {
  background("black")
})

addLayer(() => {
  let x = 300 + Math.sin(time) * 80
  let y = 200 + Math.cos(time * 0.5) * 40

  waveImage("fondoonwn.jpg", x - 100, y - 100, 200, 200, 20, 0.1)
})

addLayer(() => {
  let x = 300 + Math.sin(time) * 80
  let y = 200 + Math.cos(time * 0.5) * 40

  for (let i = 0; i < 5; i++) {
    let angle = time + i
    let ox = x + Math.cos(angle) * 60
    let oy = y + Math.sin(angle) * 60

    circle(ox, oy, 5, "#ff77ff")
  }
})

// pequeños glitches como recuerdos rotos
addLayer(() => {
  if (Math.random() > 0.7) {
    glitchImage("fondoonwn.jpg", 200, 100, 200, 200, 20)
  }
})
`;
}

// ---------------------------------------
// sandbox 🧪
// ---------------------------------------
function openSandbox() {

  currentCode = `
addLayer(() => {
  background("black")
})

addLayer(() => {
  let x = 200 + Math.sin(time * 2) * 100
  circle(x, 200, 50, "#00ffff")
})
`;
}

// ---------------------------------------
// modo automatico (visual + audio integrado)
// ---------------------------------------

let autoStarted = false;

function defaultVisuals() {

  // aseguramos que audio existe
  initAudio();

  // iniciar musica automaticamente
  if (!isPlaying && audioCtx) {
    play("kick*2 snare kick snare", slider1 + 60);
  }

  // fondo
  addLayer(() => {
    background("rgba(0,0,0,0.2)")
  });

  // visual sincronizado
  addLayer(() => {

    // fallback si beat no existe aún
    let safeBeat = beat || 0;

    let pulse = 60 + Math.sin(time * 6) * 30;

    // sliders afectan visual
    pulse += slider2;

    circle(300, 200, pulse, "#ff77ff");

  });

}
// ---------------------------------------
// loop principal
// ---------------------------------------
function loop() {

  // actualizar sliders cada frame
  slider1 = Number(document.getElementById("slider1").value);
  slider2 = Number(document.getElementById("slider2").value);
  time = getTime();

  // fondo con trail
  ctx.fillStyle = "rgba(0, 0, 0, 0.1)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  clearLayers();

  // si no hay codigo, usamos modo default
  if (!currentCode || currentCode.trim() === "") {

    defaultVisuals();

  } else {
    try {
      eval(currentCode);
    } catch (e) {
      console.error(e);
    }
  }

  for (let layer of layers) {
    layer();
  }

  requestAnimationFrame(loop);
}

loop();

/*
---------------------------------------

holii

si estas leyendo esto,
es porque llegaste aca

esto no esta terminado
y eso esta bien

la idea es que podamos construirlo juntos

puedes:
- romper cosas
- cambiar todo
- crear tus propias funciones
- hacerlo tuyo tambien

cosas que podriamos hacer:

- audio reactivo
- visuales mas complejas
- modo live entre dos personas
- glitch mas roto
- sistema tipo instrumento

(me gustaria mucho hacerlo contigo)

---------------------------------------
*/