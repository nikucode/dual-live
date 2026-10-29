// taller 00: una receta de sonido, un reloj y un dibujo independientes
const $ = id => document.getElementById(id);
const defaults = {tone:52,tail:320,punch:55};
let audio, master, timer, nextTime, step=0, playing=false, lastHit=-1, active=[];
let sequence = [];
const canvas=$('scope'), ctx=canvas.getContext('2d');
const status=message=>{$('status').textContent=message};
function values(){return {tone:+$('tone').value,tail:+$('tail').value,punch:+$('punch').value}}
function setValues(v){for(const id of ['tone','tail','punch']) $(id).value=v[id];displayValues()}
function displayValues(){const v=values();$('tone-value').textContent=v.tone+' Hz';$('tail-value').textContent=v.tail+' ms';$('punch-value').textContent=v.punch+' %';$('detail-tone').textContent=v.tone+' Hz';$('detail-tail').textContent=v.tail+' ms';$('detail-punch').textContent='+'+(v.punch*.24).toFixed(1)+' semitonos al inicio';draw()}
async function ensureAudio(){audio??=new AudioContext();if(!master){master=audio.createGain();master.gain.value=.38;master.connect(audio.destination)}await audio.resume()}
function kick(at){
  const v=values(), duration=v.tail/1000, osc=audio.createOscillator(), gain=audio.createGain();
  osc.type='sine';
  const startHz=v.tone*2**((v.punch*.24)/12);
  osc.frequency.setValueAtTime(startHz,at);
  osc.frequency.exponentialRampToValueAtTime(v.tone,at+Math.min(.12,duration*.7));
  gain.gain.setValueAtTime(.0001,at);
  gain.gain.linearRampToValueAtTime(.8,at+.006);
  gain.gain.exponentialRampToValueAtTime(.0001,at+duration);
  osc.connect(gain).connect(master);osc.start(at);osc.stop(at+duration+.01);
  active.push(osc);osc.onended=()=>{osc.disconnect();gain.disconnect();active=active.filter(n=>n!==osc)};
  lastHit=at;
}
function parsePattern(){const tokens=$('pattern').value.trim().split(/\s+/).filter(Boolean);if(tokens.length!==16||tokens.some(t=>t!=='x'&&t!=='.'))throw Error('Usa 16 pasos separados por espacios; cada uno debe ser x o .');return tokens}
function schedule(){if(!playing)return;const interval=60/160/4;while(nextTime<audio.currentTime+.09){if(sequence[step]==='x')kick(nextTime);nextTime+=interval;step=(step+1)%16}}
async function preview(){try{await ensureAudio();kick(audio.currentTime+.01);status('Escuchaste un bombo. Cambia un control y compara.')}catch(e){status('No pude iniciar el audio: '+e.message)}}
async function play(){try{const newSequence=parsePattern();await ensureAudio();sequence=newSequence;if(playing){status('Patrón actualizado; se aplicará a los próximos pasos.');return}playing=true;step=0;nextTime=audio.currentTime+.06;master.gain.setTargetAtTime(.38,audio.currentTime,.005);schedule();timer=setInterval(schedule,25);status('Tocando patrón de 16 pasos a 160 BPM.')}catch(e){status(e.message)}}
function stop(){playing=false;clearInterval(timer);timer=null;if(audio&&master){master.gain.cancelScheduledValues(audio.currentTime);master.gain.setTargetAtTime(0,audio.currentTime,.003);for(const osc of active){try{osc.stop(audio.currentTime+.015)}catch{}}}status('Detenido. Puedes modificar la receta y volver a escuchar.');lastHit=-1;draw()}
function draw(){const dpr=devicePixelRatio||1,w=canvas.clientWidth,h=canvas.clientHeight;if(!w||!h)return;if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr)}ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#0c0d11';ctx.fillRect(0,0,w,h);const v=values(),elapsed=audio&&lastHit>=0?audio.currentTime-lastHit:1,pulse=elapsed>=0?Math.max(0,1-elapsed/(v.tail/1000)):0;ctx.strokeStyle=pulse>.05?'#d6acbd':'#5e626b';ctx.lineWidth=1+3*pulse;ctx.strokeRect(5,5,w-10,h-10);ctx.strokeStyle='#9bc8ca';ctx.lineWidth=2;ctx.beginPath();for(let px=0;px<w;px++){const t=px/w*v.tail/1000, f0=v.tone*2**(v.punch*.24/12),tau=Math.min(.12,v.tail/1000*.7),phase=2*Math.PI*(v.tone*t+(f0-v.tone)*tau*(1-Math.exp(-t/tau))),env=Math.exp(-t/(v.tail/1000)*5),y=h/2-Math.sin(phase)*env*h*.37;if(px===0)ctx.moveTo(px,y);else ctx.lineTo(px,y)}ctx.stroke()}
function frame(){draw();requestAnimationFrame(frame)}
for(const id of ['tone','tail','punch'])$(id).addEventListener('input',displayValues);
$('audition').addEventListener('click',preview);$('play').addEventListener('click',play);$('stop').addEventListener('click',stop);
$('reset').addEventListener('click',()=>{setValues(defaults);status('Receta original restaurada.')});
$('save').addEventListener('click',()=>{localStorage.setItem('dual-live-kick-v1',JSON.stringify(values()));status('Receta guardada en este navegador.')});
$('guide-toggle').addEventListener('click',()=>{const hidden=$('guide').hidden;$('guide').hidden=!hidden;$('guide-toggle').setAttribute('aria-expanded',String(hidden))});
try{const saved=JSON.parse(localStorage.getItem('dual-live-kick-v1'));if(saved&&['tone','tail','punch'].every(k=>Number.isFinite(saved[k])))setValues(saved);else displayValues()}catch{displayValues()}
requestAnimationFrame(frame);
