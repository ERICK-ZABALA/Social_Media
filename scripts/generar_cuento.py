#!/usr/bin/env python3
"""Generador diario de cuentos caricatura (estilo anime Shinkai) para Rock Factory.

Igual que generar_video.py pero usa lineas de un CUENTO (no frases reflexivas)
como overlay por toma. El video queda MUDO (audio se elige en TikTok).

Uso:
  python3 generar_cuento.py [--dia N] [--out salida.mp4] [--segments 3] \
      [--historia "linea1|linea2|linea3"]
  Si no pasas --historia, la lee de playlist/historias.json segun el dia.
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

W, H = 1080, 1920
FPS = 30
ZOOM = 1.16
THREADS = 1
PRESET = "ultrafast"
CRF = 28
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
BRAND = "CUENTOS CARICATURAS"

PANS = [
    (0.0, 1.0, 0.0, 0.6),
    (1.0, 0.0, 0.2, 1.0),
    (0.0, 1.0, 1.0, 0.0),
]


class GenError(RuntimeError):
    pass


def find_font() -> str:
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return f
    raise GenError("Fuente TTF no encontrada")


def esc(text: str) -> str:
    return (text.replace("\\", r"\\").replace(":", r"\:").replace("'", r"\'")
            .replace("[", r"\[").replace("]", r"\]").replace(",", r"\,"))


def load_estado() -> dict:
    if not ESTADO.exists():
        return {"dia": 0, "ultima_generacion": None}
    return json.loads(ESTADO.read_text(encoding="utf-8"))


def save_estado(s: dict) -> None:
    ESTADO.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")


def pick_historia(dia: int, explicit=None) -> tuple[list[str], str]:
    if explicit:
        return [l.strip() for l in explicit.split("|") if l.strip()], "custom"
    data = json.loads(HISTORIAS.read_text(encoding="utf-8"))
    hs = data["historias"]
    if not hs:
        raise GenError("no hay historias en historias.json")
    h = hs[dia % len(hs)]
    return h["lineas"], h.get("titulo", "Cuento")


def render(lineas, titulo, out: Path, segs: int) -> Path:
    if not shutil.which("ffmpeg"):
        raise GenError("ffmpeg no instalado")
    fon = find_font()
    total = int(30 * FPS)
    n = max(1, segs)
    base = total // n
    rem = total - base * n
    per = [base + (1 if i < rem else 0) for i in range(n)]
    bg_files = sorted(BG.glob("toma_*.png"))
    if not bg_files:
        raise GenError("no hay imagenes en assets/bg/")

    tmpdir = Path(tempfile.mkdtemp(prefix="cuento_"))
    clips = []
    try:
        for i, fr in enumerate(per):
            bg = bg_files[i % len(bg_files)]
            pan = PANS[i % len(PANS)]
            zoom_in = (i % 2 == 0)
            fade = (i == 0)
            linea = lineas[i % len(lineas)] if lineas else None
            clip = tmpdir / f"seg_{i}.mp4"
            sw = int(W * ZOOM); sh = int(H * ZOOM)
            xmax, ymax = sw - W, sh - H
            xf, xt, yf, yt = pan
            x0, x1 = int(xf*xmax), int(xt*xmax)
            y0, y1 = int(yf*ymax), int(yt*ymax)
            z = (f"'min(zoom+{(ZOOM-1)/fr:.8f},{ZOOM})'" if zoom_in
                 else f"'max(zoom-{(ZOOM-1)/fr:.8f},1.0)'")
            denom = max(fr-1, 1)
            x_expr = f"'{x0}+(({x1-x0})*(on/{denom}))'"
            y_expr = f"'{y0}+(({y1-y0})*(on/{denom}))'"
            y_title = int(H*0.80); y_brand = y_title+66
            y_linea = int(H*0.62)
            fade_e = "if(lt(t,0.6),t/0.6,1)" if fade else "1"
            chain = [
                "scale=720:1280:force_original_aspect_ratio=increase",
                f"scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh}",
                f"zoompan=z={z}:d={fr}:x={x_expr}:y={y_expr}:s={W}x{H}:fps={FPS}",
                "eq=contrast=1.06:saturation=1.08:brightness=0.03",
                "vignette=PI/4.4",
            ]
            if linea:
                # wrap manual a ~24 chars
                words = linea.split()
                lines = []; cur = ""
                for w in words:
                    if len(cur + " " + w) <= 24:
                        cur = (cur + " " + w).strip()
                    else:
                        if cur:
                            lines.append(cur)
                        cur = w
                if cur:
                    lines.append(cur)
                wrapped = r"\n".join(lines)
                n_lines = len(lines)
                y_top = y_linea - (n_lines - 1) * 34
                chain.append(
                    f"drawtext=fontfile={fon}:text='{esc(wrapped)}':fontcolor=white:"
                    f"fontsize=44:line_spacing=8:x=(w-text_w)/2:y={y_top}:"
                    f"shadowcolor=black@0.9:shadowx=3:shadowy=3:alpha='{fade_e}'")
            chain += [
                f"drawtext=fontfile={fon}:text='{esc(titulo)}':fontcolor=white:"
                f"fontsize=42:x=60:y={y_title}:shadowcolor=black@0.85:shadowx=2:shadowy=2:alpha='{fade_e}'",
                f"drawtext=fontfile={fon}:text='{esc(BRAND)}':fontcolor=0xF0B429:"
                f"fontsize=26:x=60:y={y_brand}:shadowcolor=black@0.8:shadowx=2:shadowy=2:alpha='{fade_e}'",
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
        try:
            for f in tmpdir.glob("*"):
                f.unlink()
            tmpdir.rmdir()
        except OSError:
            pass
    if not out.exists() or out.stat().st_size == 0:
        raise GenError("ffmpeg no produjo salida final")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dia", type=int, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--segments", type=int, default=3)
    ap.add_argument("--historia", type=str, default=None,
                    help="lineas separadas por |")
    a = ap.parse_args()

    estado = load_estado()
    dia = a.dia if a.dia is not None else estado.get("dia", 0) + 1
    lineas, titulo = pick_historia(dia, a.historia)
    out = a.out or (MEDIA / f"dia_{dia:03d}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        render(lineas, titulo, out, a.segments)
    except GenError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if a.dia is None:
        estado["dia"] = dia
        estado["ultima_generacion"] = titulo
        save_estado(estado)

    print(f"OK  {out}")
    print(f"    dia={dia} titulo='{titulo}'")
    print(f"    lineas: {lineas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
