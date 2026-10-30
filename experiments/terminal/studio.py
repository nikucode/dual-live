"""Estudio de ritmos offline: pistas sintetizadas y código recargable."""

from __future__ import annotations

import argparse
from array import array
import curses
from dataclasses import dataclass, replace
from functools import lru_cache
import math
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import threading
import wave

RATE = 44100
SESSION_PATH = Path.home() / ".config" / "dual-live" / "session.dual"
WAVES = {"sine", "square", "saw", "triangle", "noise"}
MAX_HITS_PER_BAR = 64
EXAMPLE = """# dual.live / sesión inicial (puedes editarla mientras suena)
# bpm: pulsos por minuto. volume: volumen general de 0 a 100.
bpm 180
volume 85

# sound nombre onda frecuencia_hz duracion_ms caida_0_a_100 [nivel_0_a_100]
# ondas: sine square saw triangle noise
sound kick sine 52 320 55
sound snare noise 1800 160 0
sound hat noise 7000 55 0
sound bass saw 65 260 0

# track nombre 16_pasos (x toca, . calla)
track kick x...x...x...x.x.
track snare ....x.......x...
track hat x.x.x.x.x.x.x.x.
track bass x.......x.......
"""


@dataclass(frozen=True)
class Sound:
    name: str
    wave: str
    hz: float
    tail: int
    sweep: int
    level: int = 100


@dataclass(frozen=True)
class Track:
    sound: Sound
    pattern: str


@dataclass(frozen=True)
class Session:
    bpm: int
    volume: int
    tracks: tuple[Track, ...]


@dataclass(frozen=True)
class Hit:
    offset: float
    velocity: float
    transpose: int


@dataclass(frozen=True)
class Step:
    token: str
    hits: tuple[Hit, ...]


def _read_atom(pattern: str, position: int) -> tuple[str, float, int, int]:
    if position >= len(pattern) or pattern[position] not in "xX.":
        raise ValueError("usa x, X, . o grupos [xx]")
    char = pattern[position]
    end = position + 1
    transpose = 0
    if end < len(pattern) and pattern[end] == "{":
        if char == ".":
            raise ValueError("un silencio no puede tener tono")
        closing = pattern.find("}", end + 1)
        if closing < 0:
            raise ValueError("falta cerrar {tono}")
        value = pattern[end + 1:closing]
        if not re.fullmatch(r"[+-]?\d{1,2}", value):
            raise ValueError("el tono usa semitonos, por ejemplo x{+7}")
        transpose = int(value)
        if not -24 <= transpose <= 24:
            raise ValueError("el tono debe estar entre -24 y +24 semitonos")
        end = closing + 1
    return pattern[position:end], 1.25 if char == "X" else (1.0 if char == "x" else 0.0), transpose, end


@lru_cache(maxsize=256)
def parse_pattern(pattern: str) -> tuple[Step, ...]:
    """Dieciséis pasos; [..] subdivide un paso sin alargar la vuelta."""
    steps = []
    position = 0
    while position < len(pattern):
        if pattern[position] == "[":
            start = position
            position += 1
            atoms = []
            while position < len(pattern) and pattern[position] != "]":
                token, velocity, transpose, position = _read_atom(pattern, position)
                atoms.append((token, velocity, transpose))
                if len(atoms) > 8:
                    raise ValueError("un grupo admite máximo 8 subpasos")
            if position >= len(pattern) or len(atoms) < 2:
                raise ValueError("un grupo [..] necesita cierre y 2 a 8 subpasos")
            position += 1
            hits = tuple(Hit(i / len(atoms), velocity, transpose) for i, (_, velocity, transpose) in enumerate(atoms) if velocity)
            steps.append(Step(pattern[start:position], hits))
        else:
            token, velocity, transpose, position = _read_atom(pattern, position)
            steps.append(Step(token, (Hit(0.0, velocity, transpose),) if velocity else ()))
        if len(steps) > 16:
            raise ValueError("el patrón tiene más de 16 pasos")
    if len(steps) != 16:
        raise ValueError(f"el patrón necesita 16 pasos; encontré {len(steps)}")
    return tuple(steps)


def step_symbol(step: Step) -> str:
    if not step.hits:
        return "."
    if step.token.startswith("["):
        return str(len(step.hits)) if len(step.hits) < 10 else "*"
    if step.hits[0].transpose:
        return "^"
    return "X" if step.hits[0].velocity > 1 else "x"


def parse_session(source: str) -> Session:
    bpm, volume = 180, 85
    sounds: dict[str, Sound] = {}
    pending: list[tuple[str, str]] = []
    for number, raw in enumerate(source.splitlines(), 1):
        parts = raw.split("#", 1)[0].split()
        if not parts:
            continue
        try:
            if parts[0] == "bpm" and len(parts) == 2:
                bpm = int(parts[1])
                if not 40 <= bpm <= 300:
                    raise ValueError("bpm debe estar entre 40 y 300")
            elif parts[0] == "volume" and len(parts) == 2:
                volume = int(parts[1])
                if not 0 <= volume <= 100:
                    raise ValueError("volume debe estar entre 0 y 100")
            elif parts[0] == "sound" and len(parts) in (6, 7):
                _, name, wave_name, hz_text, tail_text, sweep_text, *level_text = parts
                if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
                    raise ValueError("nombre inválido; usa letras minúsculas, números y _")
                if name in sounds:
                    raise ValueError(f"el sonido {name} está repetido")
                hz, tail, sweep = float(hz_text), int(tail_text), int(sweep_text)
                level = int(level_text[0]) if level_text else 100
                if wave_name not in WAVES:
                    raise ValueError("onda desconocida: " + wave_name)
                if not math.isfinite(hz) or not 20 <= hz <= 12000:
                    raise ValueError("frecuencia debe estar entre 20 y 12000 Hz")
                if not 20 <= tail <= 2000 or not 0 <= sweep <= 100 or not 0 <= level <= 100:
                    raise ValueError("duración 20–2000 ms; caída y nivel 0–100")
                sounds[name] = Sound(name, wave_name, hz, tail, sweep, level)
            elif parts[0] == "track" and len(parts) == 3:
                _, name, pattern = parts
                parse_pattern(pattern)
                pending.append((name, pattern))
            else:
                raise ValueError("instrucción desconocida o cantidad incorrecta de valores")
        except ValueError as exc:
            raise ValueError(f"Línea {number}: {exc}") from exc
    if not pending:
        raise ValueError("Agrega al menos una línea track")
    if len(pending) > 12:
        raise ValueError("Máximo 12 pistas por ahora")
    tracks = []
    for name, pattern in pending:
        if name not in sounds:
            raise ValueError(f"La pista {name} no tiene una definición sound")
        tracks.append(Track(sounds[name], pattern))
    total_hits = sum(len(step.hits) for track in tracks for step in parse_pattern(track.pattern))
    if total_hits > MAX_HITS_PER_BAR:
        raise ValueError(f"Máximo {MAX_HITS_PER_BAR} golpes por vuelta; encontré {total_hits}")
    return Session(bpm, volume, tuple(tracks))


def format_session(session: Session) -> str:
    sounds = {track.sound.name: track.sound for track in session.tracks}
    lines = ["# dual.live / edita y pulsa l para recargar", f"bpm {session.bpm}", f"volume {session.volume}", ""]
    for sound in sounds.values():
        lines.append(f"sound {sound.name} {sound.wave} {sound.hz:g} {sound.tail} {sound.sweep} {sound.level}")
    lines.append("")
    lines += [f"track {track.sound.name} {track.pattern}" for track in session.tracks]
    return "\n".join(lines) + "\n"


def sync_source(source: str, session: Session) -> str:
    """Refleja controles de la TUI en código, conservando comentarios y orden."""
    sounds = {track.sound.name: track.sound for track in session.tracks}
    track_number = 0
    result = []
    for line in source.splitlines():
        body, marker, comment = line.partition("#")
        parts = body.split()
        if parts:
            if parts[0] == "bpm":
                body = f"bpm {session.bpm}"
            elif parts[0] == "volume":
                body = f"volume {session.volume}"
            elif parts[0] == "sound" and len(parts) >= 2 and parts[1] in sounds:
                sound = sounds[parts[1]]
                body = f"sound {sound.name} {sound.wave} {sound.hz:g} {sound.tail} {sound.sweep} {sound.level}"
            elif parts[0] == "track" and track_number < len(session.tracks):
                track = session.tracks[track_number]
                body = f"track {track.sound.name} {track.pattern}"
                track_number += 1
        suffix = (" #" + comment) if marker else ""
        result.append(body.rstrip() + suffix)
    return "\n".join(result) + "\n"


def ensure_session_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(EXAMPLE, encoding="utf-8")


def synthesize(sound: Sound, transpose: int = 0) -> array:
    count = round(sound.tail * RATE / 1000)
    base_hz = min(RATE * 0.45, sound.hz * 2 ** (transpose / 12))
    start_hz = min(RATE * 0.45, base_hz * 2 ** (sound.sweep * 0.24 / 12))
    glide = min(0.12, sound.tail / 1000 * 0.7)
    phase = 0.0
    lowpass = 0.0
    rng = random.Random(f"{sound.name}:{base_hz}:{sound.tail}:{sound.sweep}")
    out = array("f")
    for i in range(count):
        t = i / RATE
        hz = start_hz * (base_hz / start_hz) ** min(1.0, t / glide)
        phase = (phase + hz / RATE) % 1.0
        if sound.wave == "sine":
            signal = math.sin(2 * math.pi * phase)
        elif sound.wave == "square":
            signal = 1.0 if phase < 0.5 else -1.0
        elif sound.wave == "saw":
            signal = 2 * phase - 1
        elif sound.wave == "triangle":
            signal = 1 - 4 * abs(phase - 0.5)
        else:
            white = rng.uniform(-1, 1)
            lowpass += min(1.0, 2 * math.pi * sound.hz / RATE) * (white - lowpass)
            signal = white - lowpass * 0.7
        attack = min(1.0, t / 0.004)
        decay = math.exp(math.log(0.0001) * t / (sound.tail / 1000))
        out.append(signal * attack * decay * 0.72 * sound.level / 100)
    return out


def pcm16(samples: array, volume: int) -> bytes:
    gain = volume / 100
    out = array("h", (round(max(-1.0, min(1.0, value * gain)) * 32767) for value in samples))
    if sys.byteorder != "little":
        out.byteswap()
    return out.tobytes()


def render(session: Session, bars: int = 2) -> bytes:
    if bars < 1 or bars > 128:
        raise ValueError("--bars debe estar entre 1 y 128")
    step_frames = RATE * 60 / session.bpm / 4
    total = math.ceil(16 * bars * step_frames)
    mixed = array("f", [0.0]) * total
    cache: dict[tuple[Sound, int], array] = {}
    for step in range(16 * bars):
        start = round(step * step_frames)
        for track in session.tracks:
            for hit in parse_pattern(track.pattern)[step % 16].hits:
                hit_start = start + round(hit.offset * step_frames)
                key = (track.sound, hit.transpose)
                if key not in cache:
                    cache[key] = synthesize(track.sound, hit.transpose)
                voice = cache[key]
                for i in range(min(len(voice), total - hit_start)):
                    mixed[hit_start + i] += voice[i] * hit.velocity
    return pcm16(mixed, session.volume)


class Engine:
    def __init__(self, current):
        self.current = current
        self.thread = None
        self.process = None
        self.stop_event = threading.Event()
        self.playing = False
        self.step = 0
        self.error = ""
        self.preview_track = None

    def start(self, preview_track: int | None = None):
        self.stop()
        self.preview_track = preview_track
        self.playing = preview_track is None
        self.step = 0
        self.error = ""
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
        self.thread = None
        self.process = None
        self.playing = False

    def _run(self):
        process = None
        try:
            process = subprocess.Popen(
                ["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-c", "1", "-r", str(RATE), "-"],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            self.process = process
            voices: list[tuple[array, int, float]] = []
            voice_cache: dict[tuple[Sound, int], array] = {}
            cache_session = None
            frame = 0
            next_step = 0
            next_frame = 0
            next_frame_exact = 0.0
            preview_end = 0
            if self.preview_track is not None:
                session = self.current()
                index = min(self.preview_track, len(session.tracks) - 1)
                voice = synthesize(session.tracks[index].sound)
                voices.append((voice, 0, 1.0))
                preview_end = len(voice) + 512
            while not self.stop_event.is_set():
                if not self.playing and frame >= preview_end:
                    break
                end = frame + 512
                if self.playing:
                    while next_frame < end:
                        session = self.current()
                        if session is not cache_session:
                            voice_cache.clear()
                            cache_session = session
                        self.step = next_step % 16
                        step_frames = RATE * 60 / session.bpm / 4
                        for track in session.tracks:
                            for hit in parse_pattern(track.pattern)[self.step].hits:
                                key = (track.sound, hit.transpose)
                                if key not in voice_cache:
                                    voice_cache[key] = synthesize(track.sound, hit.transpose)
                                voices.append((voice_cache[key], next_frame + round(hit.offset * step_frames), hit.velocity))
                        next_step += 1
                        next_frame_exact += step_frames
                        next_frame = round(next_frame_exact)
                mixed = array("f", [0.0]) * 512
                remaining = []
                for voice, start, velocity in voices:
                    low, high = max(frame, start), min(end, start + len(voice))
                    for pos in range(low, high):
                        mixed[pos - frame] += voice[pos - start] * velocity
                    if end < start + len(voice):
                        remaining.append((voice, start, velocity))
                voices = remaining
                if process.stdin is None:
                    raise OSError("Salida de audio no disponible")
                process.stdin.write(pcm16(mixed, self.current().volume))
                frame = end
            if process.stdin:
                try:
                    process.stdin.close()
                except BrokenPipeError:
                    pass
            if self.stop_event.is_set() and process.poll() is None:
                process.terminate()
            code = process.wait(timeout=1)
            if code and not self.stop_event.is_set():
                detail = process.stderr.read().decode(errors="replace").strip() if process.stderr else ""
                self.error = detail or "aplay no pudo reproducir el audio"
        except (OSError, subprocess.TimeoutExpired) as exc:
            if not self.stop_event.is_set():
                self.error = str(exc)
        finally:
            if process is not None:
                if process.stdin and not process.stdin.closed:
                    try:
                        process.stdin.close()
                    except OSError:
                        pass
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                if process.stderr:
                    process.stderr.close()
            self.playing = False


def run_tui(screen, path: Path):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.keypad(True)
    screen.timeout(80)
    lock = threading.Lock()
    source = path.read_text(encoding="utf-8")
    session = parse_session(source)
    focus = "global"
    selected = 0
    track_index = 0
    cursor = 0
    help_page = True
    editing = False
    editor_lines: list[str] = []
    editor_row = editor_col = editor_top = 0
    editor_left = 0
    message = "Bienvenido. Enter para comenzar."

    def current():
        with lock:
            return session

    engine = Engine(current)

    def line(y, text, attr=0):
        height, width = screen.getmaxyx()
        if 0 <= y < height and width > 0:
            try:
                screen.addnstr(y, 0, text.ljust(width - 1), width - 1, attr)
            except curses.error:
                pass

    try:
        while True:
            screen.erase()
            height, width = screen.getmaxyx()
            if height < 24 or width < 60:
                line(0, "Amplía la terminal a 60 x 24. q: salir")
            elif help_page:
                line(0, "dual.live / tres pasos para empezar / (=^･ω･^=)", curses.A_BOLD)
                line(3, "1 / ESCUCHA", curses.A_BOLD)
                line(4, "Pulsa Enter y luego p. Sonarán todas las pistas.")
                line(7, "2 / CAMBIA UNA PISTA", curses.A_BOLD)
                line(8, "Pulsa Tab: selecciona PISTAS. ↑↓ elige kick, snare...")
                line(9, "←→ mueve ^; x toca, X acentúa, r repite, . calla.")
                line(12, "3 / CAMBIA SU SONIDO", curses.A_BOLD)
                line(13, "Pulsa Tab: selecciona SONIDO. ↑↓ elige onda, tono,")
                line(14, "duración, caída o nivel; ←→ cambia el valor.")
                line(17, "Tab: GENERAL → PISTAS → SONIDO. j/k y +/- también sirven.")
                line(18, "e abre código aquí. Ctrl+R aplica; Ctrl+O guarda.")
                line(20, "Enter: comenzar  |  ?: volver a esta guía  |  q: salir")
            elif editing:
                line(0, "dual.live / código de la sesión", curses.A_BOLD)
                line(1, "Ctrl+R: aplicar  Ctrl+O: guardar  Ctrl+X: volver")
                line(2, "Error de código: se conserva lo que ya sonaba.")
                visible = height - 8
                editor_top = max(0, min(editor_top, editor_row))
                if editor_row >= editor_top + visible:
                    editor_top = editor_row - visible + 1
                content_width = max(1, width - 6)
                if editor_col < editor_left:
                    editor_left = editor_col
                elif editor_col >= editor_left + content_width:
                    editor_left = editor_col - content_width + 1
                for y in range(visible):
                    index = editor_top + y
                    if index < len(editor_lines):
                        visible_text = editor_lines[index][editor_left:editor_left + content_width]
                        line(4 + y, f"{index + 1:3} {visible_text}", curses.A_REVERSE if index == editor_row else 0)
                line(height - 3, message)
                line(height - 2, f"{path}  |  línea {editor_row + 1}, columna {editor_col + 1}")
            else:
                line(0, "dual.live / estudio de ritmos / (=^･ω･^=)", curses.A_BOLD)
                line(1, f"{session.bpm} BPM  |  volumen {session.volume}%  |  {len(session.tracks)} pistas  |  sin internet")
                line(3, "GENERAL  Tab cambia sección; ↑↓ elige; ←→ ajusta")
                for i, (name, value) in enumerate((("BPM", session.bpm), ("Volumen", session.volume))):
                    chosen = focus == "global" and selected == i
                    line(4 + i, f"{'>' if chosen else ' '} {name:8} {value}", curses.A_REVERSE if chosen else 0)
                line(7, "PISTAS  ↑↓ elige ←→ paso x golpe X acento r repite . calla")
                max_visible = min(len(session.tracks), 4)
                start_index = max(0, min(track_index - max_visible + 1, len(session.tracks) - max_visible))
                for row, index in enumerate(range(start_index, start_index + max_visible)):
                    track = session.tracks[index]
                    is_active = focus == "tracks" and track_index == index
                    symbols = " ".join(step_symbol(step) for step in parse_pattern(track.pattern))
                    line(8 + row, f"{'>' if is_active else ' '} {track.sound.name:10} {symbols}", curses.A_REVERSE if is_active else 0)
                if focus == "tracks":
                    token = parse_pattern(session.tracks[track_index].pattern)[cursor].token
                    line(12, " " * (13 + 2 * cursor) + "^ " + str(cursor + 1) + ": " + token)
                sound = session.tracks[track_index].sound
                line(14, f"SONIDO / {sound.name}  Tab para editar sus parámetros")
                parameters = (("Onda", sound.wave), ("Frecuencia", f"{sound.hz:g} Hz"), ("Duración", f"{sound.tail} ms"), ("Caída", f"{sound.sweep}%"), ("Nivel", f"{sound.level}%"))
                for i, (name, value) in enumerate(parameters):
                    chosen = focus == "sound" and selected == i
                    line(15 + i, f"{'>' if chosen else ' '} {name:11} {value}", curses.A_REVERSE if chosen else 0)
                line(20, "p tocar/parar | Espacio escuchar | e código | s guardar")
                line(21, "Tab sección | ? guía | l recargar archivo | q salir")
                if engine.error:
                    message = "Audio: " + engine.error
                state = f"TOCANDO paso {engine.step + 1}" if engine.playing else "DETENIDO"
                line(23, state + " | " + message)
                if height > 24:
                    line(24, f"Código: {path}")
            if editing and not help_page and height >= 24 and width >= 60:
                try:
                    screen.move(4 + editor_row - editor_top, min(width - 2, 4 + editor_col - editor_left))
                except curses.error:
                    pass
            screen.refresh()
            try:
                pressed = screen.get_wch()
            except curses.error:
                pressed = -1
            key = ord(pressed) if isinstance(pressed, str) else pressed
            if key == -1:
                continue
            if height < 24 or width < 60:
                if key == ord("q"):
                    break
                continue
            if editing:
                if key in (curses.KEY_F5, curses.KEY_F2, 27, 18, 15, 24):
                    candidate = "\n".join(editor_lines) + "\n"
                    try:
                        updated = parse_session(candidate)
                        with lock:
                            session = updated
                        source = candidate
                        track_index = min(track_index, len(session.tracks) - 1)
                        message = "Código aplicado. El ritmo continúa."
                        if key in (curses.KEY_F2, 15):
                            path.write_text(source, encoding="utf-8")
                            message = "Código aplicado y guardado."
                        if key in (27, 24):
                            editing = False
                            try:
                                curses.curs_set(0)
                            except curses.error:
                                pass
                    except (OSError, ValueError) as exc:
                        message = str(exc) + " | sigue sonando la versión anterior"
                    continue
                if key in (curses.KEY_UP, curses.KEY_DOWN):
                    editor_row = max(0, min(len(editor_lines) - 1, editor_row + (-1 if key == curses.KEY_UP else 1)))
                    editor_col = min(editor_col, len(editor_lines[editor_row]))
                elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                    editor_col = max(0, min(len(editor_lines[editor_row]), editor_col + (-1 if key == curses.KEY_LEFT else 1)))
                elif key == curses.KEY_HOME:
                    editor_col = 0
                elif key == curses.KEY_END:
                    editor_col = len(editor_lines[editor_row])
                elif key in (10, 13, curses.KEY_ENTER):
                    rest = editor_lines[editor_row][editor_col:]
                    editor_lines[editor_row] = editor_lines[editor_row][:editor_col]
                    editor_lines.insert(editor_row + 1, rest)
                    editor_row += 1
                    editor_col = 0
                elif key in (8, 127, curses.KEY_BACKSPACE):
                    if editor_col:
                        text = editor_lines[editor_row]
                        editor_lines[editor_row] = text[:editor_col - 1] + text[editor_col:]
                        editor_col -= 1
                    elif editor_row:
                        editor_col = len(editor_lines[editor_row - 1])
                        editor_lines[editor_row - 1] += editor_lines.pop(editor_row)
                        editor_row -= 1
                elif key == curses.KEY_DC:
                    text = editor_lines[editor_row]
                    if editor_col < len(text):
                        editor_lines[editor_row] = text[:editor_col] + text[editor_col + 1:]
                    elif editor_row + 1 < len(editor_lines):
                        editor_lines[editor_row] += editor_lines.pop(editor_row + 1)
                elif key == 9:
                    text = editor_lines[editor_row]
                    editor_lines[editor_row] = text[:editor_col] + "  " + text[editor_col:]
                    editor_col += 2
                elif 32 <= key <= 0x10FFFF:
                    text = editor_lines[editor_row]
                    editor_lines[editor_row] = text[:editor_col] + chr(key) + text[editor_col:]
                    editor_col += 1
                continue
            if key == ord("q"):
                break
            if help_page:
                if key in (10, 13, curses.KEY_ENTER, ord("?")):
                    help_page = False
                continue
            if key == ord("?"):
                help_page = True
            elif key == 9:
                focus = {"global": "tracks", "tracks": "sound", "sound": "global"}[focus]
                selected = 0
            elif key in (curses.KEY_UP, curses.KEY_DOWN, ord("k"), ord("j")):
                delta = -1 if key in (curses.KEY_UP, ord("k")) else 1
                if focus == "tracks":
                    track_index = (track_index + delta) % len(session.tracks)
                else:
                    selected = (selected + delta) % (2 if focus == "global" else 5)
            elif key in (curses.KEY_LEFT, curses.KEY_RIGHT, ord("-"), ord("+")):
                delta = -1 if key in (curses.KEY_LEFT, ord("-")) else 1
                if focus == "tracks":
                    cursor = (cursor + delta) % 16
                elif focus == "global":
                    with lock:
                        if selected == 0:
                            session = replace(session, bpm=max(40, min(300, session.bpm + delta * 5)))
                        else:
                            session = replace(session, volume=max(0, min(100, session.volume + delta * 5)))
                    source = sync_source(source, session)
                else:
                    sound = session.tracks[track_index].sound
                    if selected == 0:
                        waves = ("sine", "triangle", "square", "saw", "noise")
                        new_sound = replace(sound, wave=waves[(waves.index(sound.wave) + delta) % len(waves)])
                    else:
                        field, step_size, bounds = (("hz", 5, (20, 12000)), ("tail", 10, (20, 2000)), ("sweep", 5, (0, 100)), ("level", 5, (0, 100)))[selected - 1]
                        new_sound = replace(sound, **{field: max(bounds[0], min(bounds[1], getattr(sound, field) + delta * step_size))})
                    with lock:
                        session = replace(session, tracks=tuple(replace(track, sound=new_sound) if track.sound.name == sound.name else track for track in session.tracks))
                    source = sync_source(source, session)
            elif key in (ord("x"), ord("X"), ord("."), ord("r")) and focus == "tracks":
                tracks = list(session.tracks)
                cells = [step.token for step in parse_pattern(tracks[track_index].pattern)]
                old = cells[cursor]
                if key == ord("r"):
                    cells[cursor] = "[xxxx]" if old == "[xx]" else "[xx]"
                else:
                    cells[cursor] = chr(key)
                tracks[track_index] = replace(tracks[track_index], pattern="".join(cells))
                updated = replace(session, tracks=tuple(tracks))
                candidate = sync_source(source, updated)
                try:
                    parse_session(candidate)
                    with lock:
                        session = updated
                    source = candidate
                    message = f"Paso {cursor + 1}: {cells[cursor]}"
                    if key != ord("r"):
                        cursor = (cursor + 1) % 16
                except ValueError as exc:
                    message = str(exc)
            elif key == ord(" "):
                engine.start(preview_track=track_index)
                message = f"Escuchando {session.tracks[track_index].sound.name}."
            elif key == ord("p"):
                if engine.playing:
                    engine.stop()
                    message = "Patrón detenido."
                else:
                    engine.start()
                    message = "Pistas sonando; puedes editarlas ahora."
            elif key == ord("l"):
                try:
                    loaded_source = path.read_text(encoding="utf-8")
                    loaded = parse_session(loaded_source)
                    with lock:
                        session = loaded
                    source = loaded_source
                    track_index = min(track_index, len(session.tracks) - 1)
                    message = "Código aplicado desde el siguiente paso."
                except (OSError, ValueError) as exc:
                    message = str(exc) + " | se conserva la sesión anterior"
            elif key == ord("s"):
                try:
                    path.write_text(source, encoding="utf-8")
                    message = "Sesión guardada en el archivo de código."
                except OSError as exc:
                    message = str(exc)
            elif key == ord("e"):
                editor_lines = source.splitlines() or [""]
                editor_row = editor_col = editor_top = 0
                editor_left = 0
                editing = True
                try:
                    curses.curs_set(1)
                except curses.error:
                    pass
                message = "Edita; Ctrl+R aplica, Ctrl+O guarda, Ctrl+X vuelve."
    finally:
        engine.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="dual.live: pistas sintetizadas y livecoding offline en terminal")
    parser.add_argument("--session", type=Path, default=SESSION_PATH, help="archivo de código .dual")
    parser.add_argument("--render", metavar="ARCHIVO.wav", help="exporta la sesión a WAV")
    parser.add_argument("--bars", type=int, default=4, help="vueltas para exportar")
    args = parser.parse_args()
    try:
        ensure_session_file(args.session)
        session = parse_session(args.session.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.render:
        try:
            data = render(session, args.bars)
            with wave.open(args.render, "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(RATE)
                output.writeframes(data)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print("WAV creado:", args.render)
        return 0
    if not shutil.which("aplay"):
        parser.error("Se necesita aplay para escuchar audio en la terminal")
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("La interfaz necesita una terminal interactiva")
    try:
        curses.wrapper(run_tui, args.session)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
