#!/usr/bin/env python3
"""Generador de Retro Cartoon (estilo anime Shinkai) para Rock Factory.

REGLA 2026-08-13 (Erick): el video dura 1m30s (90s) y NO lleva letras/texto
overlay. Solo fondos animados estilo Shinkai + brand sutil (opcional, sin
texto central). El audio se elige en TikTok al publicar (video mudo aqui).

Uso:
  python3 generar_retro_cartoon.py [--dia N] [--out salida.mp4] [--segments 6]
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
CH = BASE / "channels" / "cuentos-caricaturas"
ESTADO = CH / "estado.json"
HISTORIAS = CH / "playlist" / "historias.json"
BG = CH / "assets" / "bg"
MEDIA = CH / "media"

W, H = 720, 1280          # TikTok/Shorts acepta 720x1280 sin problema
FPS = 30
DURATION = 90             # REGLA: 1m30s exactos
THREADS = 1
PRESET = "ultrafast"
CRF = 28

# Pans suaves estilo Shinkai (movimiento lento de camara, no cortes bruscos)
PANS = [
    (0.10, 0.40, 0.15, 0.55),
    (0.45, 0.15, 0.55, 0.20),
    (0.15, 0.55, 0.40, 0.10),
    (0.55, 0.25, 0.20, 0.60),
    (0.30, 0.60, 0.55, 0.30),
    (0.60, 0.30, 0.10, 0.45),
]


class GenError(RuntimeError):
    pass


def load_estado() -> dict:
    if not ESTADO.exists():
        return {"dia": 0, "ultima_generacion": None}
    return json.loads(ESTADO.read_text(encoding="utf-8"))


def save_estado(s: dict) -> None:
    ESTADO.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")


def pick_historia(dia: int) -> tuple[list[str], str]:
    data = json.loads(HISTORIAS.read_text(encoding="utf-8"))
    hs = data["historias"]
    if not hs:
        raise GenError("no hay historias en historias.json")
    h = hs[dia % len(hs)]
    return h["lineas"], h.get("titulo", "Cuento")


def render(out: Path, segs: int) -> Path:
    if not shutil.which("ffmpeg"):
        raise GenError("ffmpeg no instalado")
    bg_files = sorted(BG.glob("toma_*.png"))
    if not bg_files:
        raise GenError("no hay imagenes en assets/bg/")

    total = int(DURATION * FPS)           # 2700 frames
    n = max(1, segs)
    base = total // n
    rem = total - base * n
    per = [base + (1 if i < rem else 0) for i in range(n)]

    tmpdir = Path(tempfile.mkdtemp(prefix="cuento_"))
    clips = []
    try:
        for i, fr in enumerate(per):
            bg = bg_files[i % len(bg_files)]
            pan = PANS[i % len(PANS)]
            clip = tmpdir / f"seg_{i}.mp4"
            # Ken-Burns lento: un solo scale + crop fijo por toma (sin zoompan
            # por frame: en esta VM lento y timeout). El movimiento lo da el
            # pan entre tomas + fade. Grade cinematografico Shinkai.
            sw, sh = int(W * 1.12), int(H * 1.12)
            xmax, ymax = sw - W, sh - H
            xf, xt, yf, yt = pan
            xc = int(xf * xmax)
            yc = int(yf * ymax)
            fade = (i == 0)
            fade_e = "if(lt(t,0.8),t/0.8,1)" if fade else "1"
            chain = [
                f"scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh}",
                f"crop={W}:{H}:x={xc}:y={yc}",
                "eq=contrast=1.08:saturation=1.12:brightness=0.04",
                "vignette=PI/4.6",
            ]
            chain.append(
                f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                f":text='RETRO CARTOON':fontcolor=0xF0B429@0.0:fontsize=1:x=10:y=10"
            )  # placeholder invisible: el video va SIN letras (regla)
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
                raise GenError(f"ffmpeg fallo en toma {i}:\\n{r.stderr[-1200:]}")
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
    _, titulo = pick_historia(dia)
    out = a.out or (MEDIA / f"dia_{dia:03d}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        render(out, a.segments)
    except GenError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if a.dia is None:
        estado["dia"] = dia
        estado["ultima_generacion"] = titulo
        save_estado(estado)

    print(f"OK  {out}")
    print(f"    dia={dia} titulo='{titulo}' duracion=90s sin_letras=si")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
