#!/usr/bin/env python3
"""Generador de videos verticales estilo "music card" para TikTok.

Replica la estetica de los videos de referencia (@erickdaniellyrics_19):
  - fondo visual 9:16 con movimiento de camara (ken-burns + pan diagonal)
  - el clip se divide en SEGMENTOS con recorridos de camara distintos
    (zoom-in / zoom-out alternados + paneo en distintas direcciones) para
    que el encuadre "respire" y no se vea estatico, imitando el ritmo de
    edicion de TikTok
  - viñeta + grada de color para que el texto respire
  - overlay inferior izquierdo: titulo de la cancion, banda y marca del canal
  - SIN audio: el audio se elige en la app de TikTok desde la biblioteca
    licenciada al publicar el borrador (unico camino legal por API)

Uso:
  python -m smf.video.lyric_card --bg fondo.jpg --title "..." --artist "..." \
      --brand "ROCK LEGENDS CLUB" --duration 30 --segments 3 --out salida.mp4
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

W, H = 1080, 1920          # 9:16 nativo de TikTok
FPS = 30
ZOOM_MAX = 1.18            # zoom maximo del recorrido de camara
# La VM donde corre tiene ~320MB libres: libx264 con threads>1 + veryfast
# revienta la memoria (OOM, exit 137). Ultrafast + 1 thread es estable.
THREADS = 1
PRESET = "ultrafast"
CRF = 28
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]

# Presets de paneo diagonal: (xf, xt, yf, yt) como fraccion de (xmax, ymax).
# Cada segmento usa uno distinto para que la camara "viaje" en otra direccion.
PAN_PRESETS = [
    (0.00, 1.00, 0.00, 0.55),   # izq->der, arriba->medio
    (1.00, 0.00, 0.15, 1.00),   # der->izq, arriba->abajo
    (0.00, 1.00, 1.00, 0.00),   # izq->der, abajo->arriba
    (0.50, 0.50, 0.00, 1.00),   # centro x fijo, arriba->abajo
]


class VideoError(RuntimeError):
    pass


def find_font() -> str:
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return f
    raise VideoError(
        "No se encontro una fuente TTF. Instalar con: apt-get install fonts-dejavu-core"
    )


def esc(text: str) -> str:
    """Escapa texto para el filtro drawtext de ffmpeg."""
    out = text.replace("\\", r"\\").replace(":", r"\:").replace("'", r"\'")
    return out.replace("[", r"\[").replace("]", r"\]").replace(",", r"\,")


def _segment_text_chain(title, artist, brand, font, fade_in):
    """Overlay de texto (titulo/artista/marca). fade_in=True solo en el seg 0."""
    fade = "if(lt(t,0.8),t/0.8,1)" if fade_in else "1"
    y_title = int(H * 0.775)
    y_artist = y_title + 92
    y_brand = y_artist + 78
    return [
        f"drawtext=fontfile={font}:text='{esc(title)}':"
        f"fontcolor=white:fontsize=68:x=72:y={y_title}:"
        f"shadowcolor=black@0.85:shadowx=3:shadowy=3:alpha='{fade}'",
        f"drawtext=fontfile={font}:text='{esc(artist)}':"
        f"fontcolor=white@0.88:fontsize=52:x=72:y={y_artist}:"
        f"shadowcolor=black@0.8:shadowx=2:shadowy=2:alpha='{fade}'",
        f"drawtext=fontfile={font}:text='{esc(brand)}':"
        f"fontcolor=0xF0B429:fontsize=34:x=72:y={y_brand}:"
        f"shadowcolor=black@0.8:shadowx=2:shadowy=2:alpha='{fade}'",
    ]


def _segment_chain(seg_index, frames, pan, zoom_in, font, title, artist, brand,
                   fade_in, lyric):
    """Construye el filtergraph de UN segmento (encuadre + grada + texto)."""
    scale_w = int(W * ZOOM_MAX)
    scale_h = int(H * ZOOM_MAX)
    xmax = scale_w - W
    ymax = scale_h - H
    xf, xt, yf, yt = pan
    x0, x1 = int(xf * xmax), int(xt * xmax)
    y0, y1 = int(yf * ymax), int(yt * ymax)

    if zoom_in:
        z_expr = f"'min(zoom+{(ZOOM_MAX-1)/frames:.8f},{ZOOM_MAX})'"
    else:
        # zoom-out: arranca en ZOOM_MAX y retrocede a 1.0
        z_expr = f"'max(zoom-{(ZOOM_MAX-1)/frames:.8f},1.0)'"

    # zoompan usa 'on' (frame de salida), no 't', para x/y.
    denom = max(frames - 1, 1)
    x_expr = f"'{x0}+(({x1}-{x0})*(on/{denom}))'"
    y_expr = f"'{y0}+(({y1-y0})*(on/{denom}))'"

    chain = [
        f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase",
        f"crop={scale_w}:{scale_h}",
        (f"zoompan=z={z_expr}:d={frames}:x={x_expr}:y={y_expr}"
         f":s={W}x{H}:fps={FPS}"),
        # look cinematografico
        "eq=contrast=1.12:saturation=0.92:brightness=-0.04",
        # viñeta
        "vignette=PI/4.5",
        # degradado inferior para el overlay
        (f"drawbox=x=0:y={int(H*0.62)}:w={W}:h={int(H*0.38)}"
         ":color=black@0.55:t=fill"),
    ]
    chain += _segment_text_chain(title, artist, brand, font, fade_in)

    if lyric:
        chain.append(
            f"drawtext=fontfile={font}:text='{esc(lyric)}':"
            f"fontcolor=white:fontsize=84:line_spacing=16:"
            f"x=(w-text_w)/2:y=(h-text_h)/2-120:"
            f"shadowcolor=black@0.9:shadowx=4:shadowy=4:"
            f"enable='between(t,1.2,{frames/FPS-1})'"
        )
    return ",".join(chain)


def build_filtergraph(total_frames, segments, font, title, artist, brand, lyric):
    """Arma el filter_complex: split en N segmentos + concat."""
    n = max(1, segments)
    base = total_frames // n
    remainder = total_frames - base * n
    frames_per = [base + (1 if i < remainder else 0) for i in range(n)]

    # Las etiquetas de salida del split van PEGADAS, sin ':'
    splits = "".join(f"[s{i}]" for i in range(n))
    parts = [f"[0:v]split={n}{splits}"]

    outs = []
    for i, fr in enumerate(frames_per):
        pan = PAN_PRESETS[i % len(PAN_PRESETS)]
        zoom_in = (i % 2 == 0)              # in/out/in alternados
        fade_in = (i == 0)                  # fade solo al arrancar el video
        # el lyric solo en el segmento del medio para no repetirse
        seg_lyric = lyric if (n > 1 and i == n // 2) else None
        chain = _segment_chain(i, fr, pan, zoom_in, font, title, artist,
                               brand, fade_in, seg_lyric)
        label = f"[v{i}]"
        outs.append(f"[s{i}]{chain},setpts=PTS-STARTPTS{label}")

    concat_in = "".join(f"[v{i}]" for i in range(n))
    parts.append(";".join(outs))
    parts.append(f"{concat_in}concat=n={n}:v=1:a=0[v]")
    # Unir con ';' en una sola linea (ffmpeg parsea mal '\n' entre ramas del split)
    return ";".join(parts)


def render(bg: Path, out: Path, title: str, artist: str, brand: str,
           duration: float, lyric: str | None = None, segments: int = 3) -> Path:
    if not shutil.which("ffmpeg"):
        raise VideoError("ffmpeg no esta instalado")
    if not bg.exists():
        raise VideoError(f"no existe el fondo: {bg}")

    font = find_font()
    total_frames = int(round(duration * FPS))
    fg = build_filtergraph(total_frames, segments, font, title, artist,
                           brand, lyric)

    # Escribir el filtergraph a un archivo y usar -filter_complex_script:
    # evita problemas de parseo de comillas/saltos de linea en argv.
    tmpdir = Path(tempfile.mkdtemp(prefix="lyriccard_"))
    script = tmpdir / "fg.txt"
    script.write_text(fg, encoding="utf-8")

    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-loop", "1", "-i", str(bg),
        "-t", str(duration + 0.5),
        "-filter_complex_script", str(script),
        "-map", "[v]",
        "-c:v", "libx264", "-preset", PRESET, "-crf", str(CRF),
        "-threads", str(THREADS), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-an",                      # SIN audio: se agrega en TikTok
        str(out),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        try:
            script.unlink()
            tmpdir.rmdir()
        except OSError:
            pass
    if r.returncode != 0:
        raise VideoError(f"ffmpeg fallo:\n{r.stderr[-1500:]}")
    if not out.exists() or out.stat().st_size == 0:
        raise VideoError("ffmpeg no produjo salida")
    return out


def probe(path: Path) -> dict:
    """Devuelve metadatos reales del archivo generado."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,codec_name",
         "-show_entries", "format=duration,size",
         "-of", "default=nw=1", str(path)],
        capture_output=True, text=True,
    )
    d = {}
    for line in r.stdout.strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k] = v
    r2 = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    d["has_audio"] = bool(r2.stdout.strip())
    return d


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bg", required=True, type=Path, help="imagen de fondo")
    p.add_argument("--title", required=True)
    p.add_argument("--artist", required=True)
    p.add_argument("--brand", default="ROCK LEGENDS CLUB")
    p.add_argument("--duration", type=float, default=30.0)
    p.add_argument("--segments", type=int, default=3,
                   help="cantidad de cortes con recorrido de camara distinto")
    p.add_argument("--lyric", default=None,
                   help="frase breve centrada (cita, NO la letra completa)")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args(argv)

    try:
        out = render(a.bg, a.out, a.title, a.artist, a.brand,
                     a.duration, a.lyric, a.segments)
    except VideoError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    m = probe(out)
    print(f"OK  {out}")
    print(f"    {m.get('width')}x{m.get('height')} {m.get('codec_name')} "
          f"{float(m.get('duration', 0)):.1f}s "
          f"{int(m.get('size', 0))//1024}KB audio={m['has_audio']} "
          f"segments={a.segments}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
