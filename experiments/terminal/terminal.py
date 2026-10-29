#!/usr/bin/env python3
"""dual.live: taller de bombo que se toca y edita dentro de la terminal."""

from __future__ import annotations

import argparse
from array import array
import curses
from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import wave

RATE = 44100
BPM = 160
DEFAULT_PATTERN = "x...x...x...x.x."
CONFIG = Path.home() / ".config" / "dual-live" / "kick.json"


def parse_pattern(value: str) -> str:
    pattern = "".join(value.split()).lower()
    if len(pattern) != 16 or any(char not in "x." for char in pattern):
        raise ValueError("El patrón debe tener 16 pasos: x = bombo, . = silencio")
    return pattern


@dataclass(frozen=True)
class Recipe:
    tone: int = 52
    tail: int = 320
    punch: int = 55
    pattern: str = DEFAULT_PATTERN

    def validated(self) -> Recipe:
        if not 35 <= self.tone <= 90:
            raise ValueError("El tono debe estar entre 35 y 90 Hz")
        if not 80 <= self.tail <= 800:
            raise ValueError("La cola debe estar entre 80 y 800 ms")
        if not 0 <= self.punch <= 100:
            raise ValueError("El golpe debe estar entre 0 y 100")
        parse_pattern(self.pattern)
        return self


def synthesize_kick(recipe: Recipe, rate: int = RATE) -> array:
    """Genera PCM flotante a partir de una senoide y dos envolventes."""
    recipe.validated()
    count = round(recipe.tail * rate / 1000)
    duration = count / rate
    glide = min(0.12, duration * 0.7)
    start_hz = recipe.tone * 2 ** ((recipe.punch * 0.24) / 12)
    phase = 0.0
    out = array("f")
    for i in range(count):
        t = i / rate
        hz = start_hz * (recipe.tone / start_hz) ** min(1.0, t / glide)
        phase += 2 * math.pi * hz / rate
        attack = min(1.0, t / 0.006)
        decay = math.exp(math.log(0.0001) * t / duration)
        out.append(math.sin(phase) * attack * decay * 0.38)
    return out


def pcm16(samples: array) -> bytes:
    out = array("h", (round(max(-1.0, min(1.0, sample)) * 32767) for sample in samples))
    if sys.byteorder != "little":
        out.byteswap()
    return out.tobytes()


def render_pattern(recipe: Recipe, bars: int = 2) -> bytes:
    """Render determinista, útil para exportar y verificar sin audio activo."""
    recipe.validated()
    if bars < 1:
        raise ValueError("La cantidad de vueltas debe ser positiva")
    step_frames = RATE * 60 / BPM / 4
    total = math.ceil(16 * bars * step_frames)
    samples = array("f", [0.0]) * total
    voice = synthesize_kick(recipe)
    for step in range(16 * bars):
        if recipe.pattern[step % 16] == "x":
            start = round(step * step_frames)
            for i in range(min(len(voice), total - start)):
                samples[start + i] += voice[i]
    return pcm16(samples)


def load_recipe() -> Recipe:
    try:
        raw = json.loads(CONFIG.read_text(encoding="utf-8"))
        return Recipe(
            tone=int(raw["tone"]), tail=int(raw["tail"]),
            punch=int(raw["punch"]), pattern=parse_pattern(raw["pattern"]),
        ).validated()
    except (OSError, ValueError, TypeError, KeyError):
        return Recipe()


def save_recipe(recipe: Recipe) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(recipe.__dict__, indent=2) + "\n", encoding="utf-8")


class AudioEngine:
    def __init__(self, get_recipe):
        self.get_recipe = get_recipe
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.process: subprocess.Popen | None = None
        self.preview_event = threading.Event()
        self.playing = False
        self.step = 0
        self.error = ""

    def start(self, playing: bool) -> None:
        self.stop()
        self.playing = playing
        self.step = 0
        self.error = ""
        self.stop_event = threading.Event()
        self.preview_event = threading.Event()
        if not playing:
            self.preview_event.set()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        process = self.process
        if process and process.poll() is None:
            process.terminate()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
        self.thread = None
        self.process = None
        self.playing = False

    def _run(self) -> None:
        try:
            self.process = subprocess.Popen(
                ["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-c", "1", "-r", str(RATE), "-"],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            process = self.process
            voices: list[tuple[array, int]] = []
            frame = 0
            next_step = 0
            next_step_frame = 0
            step_frames = RATE * 60 / BPM / 4
            chunk = 512
            preview_frames = 0
            while not self.stop_event.is_set():
                recipe = self.get_recipe()
                if self.preview_event.is_set():
                    self.preview_event.clear()
                    voices.append((synthesize_kick(recipe), frame))
                    preview_frames = max(preview_frames, frame + round(recipe.tail * RATE / 1000) + 512)
                if not self.playing and frame >= preview_frames:
                    break
                end = frame + chunk
                if self.playing:
                    while next_step_frame < end:
                        recipe = self.get_recipe()
                        self.step = next_step % 16
                        if recipe.pattern[self.step] == "x":
                            voices.append((synthesize_kick(recipe), next_step_frame))
                        next_step += 1
                        next_step_frame = round(next_step * step_frames)
                mixed = array("f", [0.0]) * chunk
                remaining = []
                for voice, start in voices:
                    low = max(frame, start)
                    high = min(end, start + len(voice))
                    for pos in range(low, high):
                        mixed[pos - frame] += voice[pos - start]
                    if end < start + len(voice):
                        remaining.append((voice, start))
                voices = remaining
                if process.stdin is None:
                    raise OSError("No se pudo abrir la salida de audio")
                process.stdin.write(pcm16(mixed))
                frame = end
            if process.stdin:
                process.stdin.close()
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
            self.playing = False


def run_tui(screen) -> None:
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    screen.keypad(True)
    screen.timeout(80)
    lock = threading.Lock()
    recipe = load_recipe()

    def current() -> Recipe:
        with lock:
            return recipe

    engine = AudioEngine(current)
    selected = 0
    step_cursor = 0
    guide = False
    message = "Espacio: escuchar bombo | p: tocar patrón | g: guía"

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
            if height < 16 or width < 48:
                line(0, "Agranda la terminal a 48 x 16 o más. Pulsa q para salir.")
            else:
                line(0, "dual.live / taller 00 / (=^･ω･^=)", curses.A_BOLD)
                line(1, "Un bombo hecho de una onda / 160 BPM")
                line(3, "CONTROLES  ↑↓ elegir  ←→ cambiar")
                controls = [
                    ("Tono ", f"{recipe.tone:3} Hz", recipe.tone, 35, 90),
                    ("Cola ", f"{recipe.tail:3} ms", recipe.tail, 80, 800),
                    ("Golpe", f"{recipe.punch:3} %", recipe.punch, 0, 100),
                ]
                for i, (name, value, amount, minimum, maximum) in enumerate(controls):
                    fill = round((amount - minimum) / (maximum - minimum) * 18)
                    bar = "#" * fill + "." * (18 - fill)
                    line(4 + i, f"{'>' if i == selected else ' '} {name:6} [{bar}] {value}", curses.A_REVERSE if i == selected else 0)
                line(8, "PATRÓN  ←→ mover paso  x = bombo  . = silencio")
                cells = " ".join(recipe.pattern)
                line(9, "  " + cells)
                marker = " " * (2 + 2 * step_cursor) + "^"
                line(10, marker)
                line(12, "[espacio] escuchar  [p] tocar/detener  [s] guardar  [r] restaurar")
                line(13, "[tab] patrón/controles  [g] guía  [q] salir")
                if engine.error:
                    message = "Audio: " + engine.error
                line(15, ("TOCANDO / paso " + str(engine.step + 1) + "  |  " if engine.playing else "DETENIDO  |  ") + message)
                if guide and height > 20:
                    line(17, "GUÍA / cambia un control y escucha qué ocurre", curses.A_BOLD)
                    line(18, "Onda: vibración que se repite. Hz: repeticiones por segundo.")
                    line(19, "Cola: tiempo hasta apagarse. Golpe: caída inicial de frecuencia.")
                    line(20, "Tu receta se guarda en ~/.config/dual-live/kick.json")
            screen.refresh()
            key = screen.getch()
            if key == -1:
                continue
            if key in (ord("q"), 27):
                break
            if key == ord("g"):
                guide = not guide
            elif key == ord("\t"):
                selected = 3 if selected < 3 else 0
            elif key == curses.KEY_UP:
                selected = (selected - 1) % 4
            elif key == curses.KEY_DOWN:
                selected = (selected + 1) % 4
            elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                delta = -1 if key == curses.KEY_LEFT else 1
                if selected == 3:
                    step_cursor = (step_cursor + delta) % 16
                else:
                    field = ("tone", "tail", "punch")[selected]
                    increment = (1, 10, 5)[selected]
                    minimum, maximum = ((35, 90), (80, 800), (0, 100))[selected]
                    with lock:
                        recipe = replace(recipe, **{field: max(minimum, min(maximum, getattr(recipe, field) + delta * increment))})
            elif key in (ord("x"), ord(".")):
                with lock:
                    pattern = list(recipe.pattern)
                    pattern[step_cursor] = chr(key)
                    recipe = replace(recipe, pattern="".join(pattern))
                step_cursor = (step_cursor + 1) % 16
                selected = 3
            elif key == ord(" "):
                engine.start(False)
                message = "Escucha el bombo y mueve un control para comparar."
            elif key == ord("p"):
                if engine.playing:
                    engine.stop()
                    message = "Patrón detenido."
                else:
                    engine.start(True)
                    message = "Edita el patrón mientras suena."
            elif key == ord("s"):
                try:
                    save_recipe(recipe)
                    message = "Receta guardada."
                except OSError as exc:
                    message = "No se pudo guardar: " + str(exc)
            elif key == ord("r"):
                with lock:
                    recipe = Recipe()
                message = "Receta original restaurada."
    finally:
        engine.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="dual.live: bombo sintetizado en la terminal, sin internet")
    parser.add_argument("--render", metavar="ARCHIVO.wav", help="exporta el patrón a un WAV sin abrir la interfaz")
    parser.add_argument("--bars", type=int, default=2, help="vueltas al exportar (por defecto: 2)")
    args = parser.parse_args()
    if args.render:
        try:
            pcm = render_pattern(load_recipe(), args.bars)
            with wave.open(args.render, "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(RATE)
                output.writeframes(pcm)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print("WAV creado:", args.render)
        return 0
    if not shutil.which("aplay"):
        parser.error("Se necesita aplay para escuchar audio en la terminal")
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("La interfaz necesita una terminal interactiva")
    try:
        curses.wrapper(run_tui)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
