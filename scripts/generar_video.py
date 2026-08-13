#!/usr/bin/env python3
"""Generador diario de videos estilo Reflexiones (car-drive / golden hour).

REGLA 2026-08-13 (Erick): el video dura 1m30s (90s). La letra/frase VA EN EL
MEDIO del video, centrada horizontal y verticalmente, SIN salirse de los bordes
(wrap corto a ~14 chars + margen seguro + fontsize adaptivo). Titulo/artista/
marca abajo. Video mudo (audio se elige en TikTok al publicar).

Uso:
  python3 generar_video.py [--dia N] [--out salida.mp4] [--segments 6]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CH = BASE / "channels" / "rock-factory" / "reflexiones"
ESTADO = CH / "estado.json"
PLAYLIST = CH / "playlist" / "canciones.json"
BG = CH / "assets" / "bg"
MEDIA = CH / "media"

W, H = 720, 1280          # TikTok/Shorts
FPS = 30
DURATION = 90             # REGLA: 1m30s
THREADS = 1
PRESET = "ultrafast"
CRF = 28
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BRAND = "REFLEXIONES"

# Margen seguro: nada de texto fuera de [MARGIN, W-MARGIN] x [MARGIN, H-MARGIN]
MARGIN = 40
MAX_CHARS = 14            # wrap agresivo para que nunca desborde en vertical
FONTSIZE = 40             # fontsize fijo y seguro para 720px de ancho

PANS = [
    (0.0, 1.0, 0.0, 0.6),
    (1.0, 0.0, 0.2, 1.0),
    (0.0, 1.0, 1.0, 0.0),
    (0.5, 0.2, 0.3, 0.8),
    (0.2, 0.6, 0.7, 0.2),
    (0.6, 0.3, 0.1, 0.5),
]


class GenError(RuntimeError):
    pass


def esc(text: str) -> str:
    return (text.replace("\\", r"\\").replace(":", r"\:").replace("'", r"\'")
            .replace("[", r"\[").replace("]", r"\]").replace(",", r"\,"))


def load_estado() -> dict:
    if not ESTADO.exists():
        raise GenError(f"no existe {ESTADO}")
    return json.loads(ESTADO.read_text(encoding="utf-8"))


def save_estado(s: dict) -> None:
    ESTADO.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")


def pick_cancion(dia: int) -> tuple[dict, int]:
    data = json.loads(PLAYLIST.read_text(encoding="utf-8"))
    songs = data["canciones"]
    if not songs:
        raise GenError("playlist vacia")
    idx = dia % len(songs)
    return songs[idx], idx


def wrap_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Wrap seguro: nunca mas de max_chars por linea."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur + " " + w) <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            # si una palabra sola es mas larga que max_chars, la cortamos
            while len(w) > max_chars:
                lines.append(w[:max_chars])
                w = w[max_chars:]
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render(song, out: Path, segs: int) -> Path:
    if not shutil.which("ffmpeg"):
        raise GenError("ffmpeg no instalado")
    if not Path(FONT).exists():
        raise GenError("fuente no encontrada")
    total = int(DURATION * FPS)
    n = max(1, segs)
    base = total // n
    rem = total - base * n
    per = [base + (1 if i < rem else 0) for i in range(n)]
    frases = song.get("frases", [])
    bg_files = sorted(BG.glob("toma_*.png"))
    if not bg_files:
        raise GenError("no hay imagenes en assets/bg/")

    tmpdir = Path(tempfile.mkdtemp(prefix="refl_"))
    clips = []
    try:
        for i, fr in enumerate(per):
            bg = bg_files[i % len(bg_files)]
            pan = PANS[i % len(PANS)]
            fade = (i == 0)
            frase = frases[i % len(frases)] if frases else None
            clip = tmpdir / f"seg_{i}.mp4"
            # Ken-Burns lento fijo (sin zoompan por frame: lento en esta VM)
            sw, sh = int(W * 1.12), int(H * 1.12)
            xmax, ymax = sw - W, sh - H
            xf, xt, yf, yt = pan
            xc = int(xf * xmax)
            yc = int(yf * ymax)
            fade_e = "if(lt(t,0.8),t/0.8,1)" if fade else "1"
            chain = [
                f"scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh}",
                f"crop={W}:{H}:x={xc}:y={yc}",
                "eq=contrast=1.08:saturation=0.95:brightness=0.02",
                "vignette=PI/4.2",
            ]
            if frase:
                lines = wrap_text(frase)
                wrapped = r"\n".join(lines)
                n_lines = len(lines)
                # centro vertical real del bloque de texto
                line_h = 48
                block_h = n_lines * line_h
                y_center = int(H * 0.5)
                y_top = y_center - block_h // 2
                chain.append(
                    f"drawtext=fontfile={FONT}:text='{esc(wrapped)}':"
                    f"fontcolor=white:fontsize={FONTSIZE}:line_spacing=8:"
                    f"x=(w-text_w)/2:y={y_top}:"
                    f"shadowcolor=black@0.92:shadowx=3:shadowy=3:alpha='{fade_e}'"
                )
            # titulo + artista + marca (abajo, fuera del medio)
            y_title = int(H * 0.84)
            y_artist = y_title + 52
            y_brand = y_artist + 44
            chain += [
                f"drawtext=fontfile={FONT}:text='{esc(song['titulo'])}':"
                f"fontcolor=white:fontsize=38:x=40:y={y_title}:"
                f"shadowcolor=black@0.85:shadowx=2:shadowy=2:alpha='{fade_e}'",
                f"drawtext=fontfile={FONT}:text='{esc(song['artista'])}':"
                f"fontcolor=white@0.85:fontsize=30:x=40:y={y_artist}:"
                f"shadowcolor=black@0.8:shadowx=2:shadowy=2:alpha='{fade_e}'",
                f"drawtext=fontfile={FONT}:text='{esc(BRAND)}':"
                f"fontcolor=0xF0B429:fontsize=24:x=40:y={y_brand}:"
                f"shadowcolor=black@0.8:shadowx=2:shadowy=2:alpha='{fade_e}'",
            ]
            fc = ",".join(chain)
            fgpath = tmpdir / f"fg_{i}.txt"
            fgpath.write_text(fc, encoding="utf-8")
            cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(bg),
                   "-t", f"{fr/FPS:.3f}", "-filter_complex_script", str(fgpath),
                   "-c:v", "libx264", "-preset", PRESET, "-crf", str(CRF),
                   "-threads", str(THREADS), "-pix_fmt", "yuv420p",
                   "-movflags", "+faststart", "-an", str(clip)]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                raise GenError(f"ffmpeg fallo en toma {i}:\n{r.stderr[-1200:]}")
            if not clip.exists() or clip.stat().st_size == 0:
                raise GenError(f"toma {i} no produjo salida")
            clips.append(clip)

        concat_list = tmpdir / "list.txt"
        concat_list.write_text("\n".join(f"file '{c.resolve()}'" for c in clips),
                               encoding="utf-8")
        cmd2 = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_list), "-c", "copy", str(out)]
        r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)
        if r2.returncode != 0:
            raise GenError(f"concat fallo:\n{r2.stderr[-1200:]}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    if not out.exists() or out.stat().st_size == 0:
        raise GenError("ffmpeg no produjo salida final")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dia", type=int, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--segments", type=int, default=6)
    a = ap.parse_args()

    estado = load_estado()
    dia = a.dia if a.dia is not None else estado.get("dia", 0) + 1
    song, idx = pick_cancion(dia)
    out = a.out or (MEDIA / f"dia_{dia:03d}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        render(song, out, a.segments)
    except GenError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if a.dia is None:
        estado["dia"] = dia
        estado["playlist_index"] = idx
        estado["ultima_generacion"] = song["titulo"]
        save_estado(estado)

    print(f"OK  {out}")
    print(f"    dia={dia} cancion='{song['titulo']}' - {song['artista']} duracion=90s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
