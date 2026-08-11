#!/usr/bin/env python3
"""Generador diario de videos estilo Reflexiones (car-drive / golden hour).

Flujo:
  1. Lee channels/reflexiones/estado.json (dia, playlist_index).
  2. Toma la cancion del dia desde playlist/canciones.json.
  3. Usa N frases de esa cancion (una por toma) como overlay reflexivo.
  4. Monta las imagenes de fondo (assets/bg/toma_XX.png) con paneo + corte
     entre tomas, viñeta y grano para imitar el estilo nostalgico.
  5. Genera un MP4 MUDO (el audio se elige en TikTok al publicar).
  6. Incrementa el dia y guarda estado.

Uso:
  python3 generar_video.py [--dia N] [--out salida.mp4] [--segments 3]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CH = BASE / "channels" / "reflexiones"
ESTADO = CH / "estado.json"
PLAYLIST = CH / "playlist" / "canciones.json"
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
BRAND = "REFLEXIONES"

# Paneos diagonales distintos por toma (xf,xt,yf,yt como fraccion de margen)
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


def seg_filter(bg: Path, frames: int, pan, zoom_in, font, titulo, artista,
               frase, y_frase, fade_text):
    sw = int(W * ZOOM)
    sh = int(H * ZOOM)
    xmax, ymax = sw - W, sh - H
    xf, xt, yf, yt = pan
    x0, x1 = int(xf * xmax), int(xt * xmax)
    y0, y1 = int(yf * ymax), int(yt * ymax)
    if zoom_in:
        z = f"'min(zoom+{(ZOOM-1)/frames:.8f},{ZOOM})'"
    else:
        z = f"'max(zoom-{(ZOOM-1)/frames:.8f},1.0)'"
    denom = max(frames - 1, 1)
    x_expr = f"'{x0}+(({x1-x0})*(on/{denom}))'"
    y_expr = f"'{y0}+(({y1-y0})*(on/{denom}))'"

    fade = "if(lt(t,0.6),t/0.6,1)" if fade_text else "1"
    y_title = int(H * 0.80)
    y_artist = y_title + 70
    y_brand = y_artist + 56

    chain = [
        f"scale={sw}:{sh}:force_original_aspect_ratio=increase",
        f"crop={sw}:{sh}",
        f"zoompan=z={z}:d={frames}:x={x_expr}:y={y_expr}:s={W}x{H}:fps={FPS}",
        "eq=contrast=1.08:saturation=0.95:brightness=0.02",
        "vignette=PI/4.2",
        f"drawbox=x=0:y={int(H*0.55)}:w={W}:h={int(H*0.45)}:color=black@0.45:t=fill",
    ]
    # frase reflexiva (blanco, centrada arriba del bloque inferior)
    if frase:
        chain.append(
            f"drawtext=fontfile={font}:text='{esc(frase)}':"
            f"fontcolor=white:fontsize=58:line_spacing=10:"
            f"x=(w-text_w)/2:y={y_frase}:"
            f"shadowcolor=black@0.9:shadowx=3:shadowy=3:alpha='{fade}'"
        )
    # titulo + artista + marca (abajo)
    chain += [
        f"drawtext=fontfile={font}:text='{esc(titulo)}':"
        f"fontcolor=white:fontsize=46:x=60:y={y_title}:"
        f"shadowcolor=black@0.85:shadowx=2:shadowy=2:alpha='{fade}'",
        f"drawtext=fontfile={font}:text='{esc(artista)}':"
        f"fontcolor=white@0.85:fontsize=36:x=60:y={y_artist}:"
        f"shadowcolor=black@0.8:shadowx=2:shadowy=2:alpha='{fade}'",
        f"drawtext=fontfile={font}:text='{esc(BRAND)}':"
        f"fontcolor=0xF0B429:fontsize=28:x=60:y={y_brand}:"
        f"shadowcolor=black@0.8:shadowx=2:shadowy=2:alpha='{fade}'",
    ]
    return ",".join(chain)


def build(total_frames, segs, fon, song):
    n = max(1, segs)
    base = total_frames // n
    rem = total_frames - base * n
    per = [base + (1 if i < rem else 0) for i in range(n)]
    frases = song["frases"]

    splits = "".join(f"[s{i}]" for i in range(n))
    parts = [f"[0:v]split={n}{splits}"]
    outs = []
    for i, fr in enumerate(per):
        bg_files = sorted(BG.glob("toma_*.png"))
        if not bg_files:
            raise GenError("no hay imagenes en assets/bg/")
        bg = bg_files[i % len(bg_files)]
        pan = PANS[i % len(PANS)]
        zoom_in = (i % 2 == 0)
        fade = (i == 0)
        # una frase por toma, rotando
        frase = frases[i % len(frases)] if frases else None
        y_frase = int(H * 0.60)
        # dibujar la frase en la toma actual
        chain = seg_filter(bg, fr, pan, zoom_in, fon, song["titulo"],
                           song["artista"], frase, y_frase, fade)
        # pero el fondo es por toma distinto -> necesitamos split por imagen
        outs.append((bg, chain, fr))
    return parts, outs, n


def render(song, dia, out: Path, segs: int) -> Path:
    if not shutil.which("ffmpeg"):
        raise GenError("ffmpeg no instalado")
    fon = find_font()
    total = int(30 * FPS)  # 30s
    n = max(1, segs)
    base = total // n
    rem = total - base * n
    per = [base + (1 if i < rem else 0) for i in range(n)]
    frases = song.get("frases", [])
    bg_files = sorted(BG.glob("toma_*.png"))
    if not bg_files:
        raise GenError("no hay imagenes en assets/bg/")

    import tempfile
    tmpdir = Path(tempfile.mkdtemp(prefix="refl_"))
    clips = []
    try:
        for i, fr in enumerate(per):
            bg = bg_files[i % len(bg_files)]
            pan = PANS[i % len(PANS)]
            zoom_in = (i % 2 == 0)
            fade = (i == 0)
            frase = frases[i % len(frases)] if frases else None
            clip = tmpdir / f"seg_{i}.mp4"
            # Cada toma: 1 imagen -> zoompan+overlay -> clip corto (sin cuelgue)
            # Pre-escalamos la imagen a 720x1280 para que el zoompan sea rapido
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
            y_title = int(H*0.80); y_artist = y_title+70; y_brand = y_artist+56
            y_frase = int(H*0.60)
            fade_e = "if(lt(t,0.6),t/0.6,1)" if fade else "1"
            chain = [
                "scale=720:1280:force_original_aspect_ratio=increase",
                f"scale={sw}:{sh}:force_original_aspect_ratio=increase,crop={sw}:{sh}",
                f"zoompan=z={z}:d={fr}:x={x_expr}:y={y_expr}:s={W}x{H}:fps={FPS}",
                "eq=contrast=1.08:saturation=0.95:brightness=0.02",
                "vignette=PI/4.2",
                f"drawbox=x=0:y={int(H*0.55)}:w={W}:h={int(H*0.45)}:color=black@0.45:t=fill",
            ]
            if frase:
                # wrap manual: si la frase es larga, la partimos en 2 lineas
                words = frase.split()
                lines = []
                cur = ""
                for w in words:
                    if len(cur + " " + w) <= 22:
                        cur = (cur + " " + w).strip()
                    else:
                        if cur:
                            lines.append(cur)
                        cur = w
                if cur:
                    lines.append(cur)
                wrapped = r"\n".join(lines)
                n_lines = len(lines)
                y_frase_top = y_frase - (n_lines - 1) * 34
                chain.append(
                    f"drawtext=fontfile={fon}:text='{esc(wrapped)}':fontcolor=white:"
                    f"fontsize=46:line_spacing=10:x=(w-text_w)/2:y={y_frase_top}:"
                    f"shadowcolor=black@0.9:shadowx=3:shadowy=3:alpha='{fade_e}'")
            chain += [
                f"drawtext=fontfile={fon}:text='{esc(song['titulo'])}':fontcolor=white:"
                f"fontsize=46:x=60:y={y_title}:shadowcolor=black@0.85:shadowx=2:shadowy=2:alpha='{fade_e}'",
                f"drawtext=fontfile={fon}:text='{esc(song['artista'])}':fontcolor=white@0.85:"
                f"fontsize=36:x=60:y={y_artist}:shadowcolor=black@0.8:shadowx=2:shadowy=2:alpha='{fade_e}'",
                f"drawtext=fontfile={fon}:text='{esc(BRAND)}':fontcolor=0xF0B429:"
                f"fontsize=28:x=60:y={y_brand}:shadowcolor=black@0.8:shadowx=2:shadowy=2:alpha='{fade_e}'",
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

        # Concatenar los clips (sin re-encodear para velocidad)
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
    ap.add_argument("--dia", type=int, default=None, help="fuerza el dia (no incrementa estado)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--segments", type=int, default=3)
    a = ap.parse_args()

    estado = load_estado()
    dia = a.dia if a.dia is not None else estado.get("dia", 0) + 1
    song, idx = pick_cancion(dia)
    out = a.out or (MEDIA / f"dia_{dia:03d}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        render(song, dia, out, a.segments)
    except GenError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # persistir (solo si no forzamos dia)
    if a.dia is None:
        estado["dia"] = dia
        estado["playlist_index"] = idx
        estado["ultima_generacion"] = song["titulo"]
        save_estado(estado)

    print(f"OK  {out}")
    print(f"    dia={dia} cancion='{song['titulo']}' - {song['artista']}")
    print(f"    frases: {song['frases']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
