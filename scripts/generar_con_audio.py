#!/usr/bin/env python3
"""Genera video prototipo CON AUDIO usando Google AI (Gemini TTS) + ffmpeg.

Pipeline:
  1. Toma el titulo + lineas de la playlist del canal (una linea por toma).
  2. Genera la narracion en espanol con Gemini TTS (una pista por frase) y
     las concatena en un unico WAV alineado a la duracion del video.
  3. Anima los fondos assets/bg/toma_*.png con pan/crop (mismo estilo que
     Reflexiones / Cuentos) + overlay de texto + mux del audio.

Requiere: ~/.google_gemini_key (chmod 600) para el TTS, y ffmpeg.
Imagen/Veo de Google NO se usan aqui (cuota 0 en la key actual); los fondos
son los PNG ya generados en assets/bg/.

NOTA RAM: el contenedor tiene ~182MB libres; decodificar PNG de 3MB a 1080p+
con zoompan mata por OOM. Por eso pre-convertimos cada fondo a JPG 720x1280 y
procesamos a esa resolucion (TikTok/Shorts la acepta). El nivel visual
(fondo cinematografico + texto + audio) se conserva.

Uso:
  python3 generar_con_audio.py --canal insight-star --dia 1 --segments 3
  python3 generar_con_audio.py --canal ia-generativa-news --dia 1
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_ai import generate_speech  # noqa: E402

BASE = Path(__file__).resolve().parent.parent

W, H = 720, 1280
FPS = 30
THREADS = 1
PRESET = "ultrafast"
CRF = 28

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

CFG = {
    "insight-star": {
        "playlist": "insights.json",
        "key": "insights",
        "brand": "INSIGHT STAR",
        "brand_color": "0xF0B429",
        "voice": "Kore",           # female_warm
        "grade": "eq=contrast=1.06:saturation=1.02:brightness=0.04",
    },
    "ia-generativa-news": {
        "playlist": "noticias.json",
        "key": "noticias",
        "brand": "IA GENERATIVA NEWS",
        "brand_color": "0x00E5FF",
        "voice": "Puck",           # male_clear
        "grade": "eq=contrast=1.10:saturation=1.15:brightness=0.03",
    },
}

PANS = [
    (0.0, 1.0, 0.0, 0.6),
    (1.0, 0.0, 0.2, 1.0),
    (0.0, 1.0, 1.0, 0.0),
]


class GenError(RuntimeError):
    pass


def esc(text: str) -> str:
    return (text.replace("\\", r"\\").replace(":", r"\:").replace("'", r"\'")
            .replace("[", r"\[").replace("]", r"\]").replace(",", r"\,"))


def render_video(lineas, titulo, bg_files, out: Path, segs: int, grade: str,
                 brand: str, brand_color: str, audio_wav: Path | None = None) -> Path:
    """Renderiza el video con fondos animados (pan) + overlay; audio se muxea."""
    if not shutil.which("ffmpeg"):
        raise GenError("ffmpeg no instalado")
    if not Path(FONT).exists():
        raise GenError("fuente no encontrada")
    if not bg_files:
        raise GenError("no hay fondos en assets/bg/")

    total = int(30 * FPS)
    n = max(1, segs)
    base = total // n
    rem = total - base * n
    per = [base + (1 if i < rem else 0) for i in range(n)]

    tmpdir = Path(tempfile.mkdtemp(prefix="conaudio_"))
    clips = []
    conv = []
    try:
        # pre-convertir fondos a JPG 720x1280 (decodificacion ligera en RAM)
        for i, bg in enumerate(bg_files):
            jp = tmpdir / f"bg_{i}.jpg"
            r0 = subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", str(bg),
                 "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                        f"crop={W}:{H}", "-q:v", "7", str(jp)],
                capture_output=True, text=True, timeout=60)
            if r0.returncode != 0:
                raise GenError(f"pre-convert fondo {i} fallo:\n{r0.stderr[-400:]}")
            conv.append(jp)

        for i, fr in enumerate(per):
            bg = conv[i % len(conv)]
            pan = PANS[i % len(PANS)]
            # Fondo ya viene a 720x1280 (pre-convert). Se OMITE el
            # scale+crop: en este contenedor lento cada filtro extra suma
            # ~30-60s por toma y provocaba timeout a 120s. El zoom fijo no
            # aporta movimiento real, asi que no se pierde nada visual.
            clip = tmpdir / f"seg_{i}.mp4"
            fade = (i == 0)
            fade_e = "if(lt(t,0.6),t/0.6,1)" if fade else "1"
            chain = [
                grade,
                "vignette=PI/4.4",
            ]
            if lineas:
                linea = lineas[i % len(lineas)]
                words = linea.split()
                wraps = []; cur = ""
                for w in words:
                    if len(cur + " " + w) <= 18:
                        cur = (cur + " " + w).strip()
                    else:
                        if cur:
                            wraps.append(cur)
                        cur = w
                if cur:
                    wraps.append(cur)
                wrapped = r"\n".join(wraps)
                n_lines = len(wraps)
                y_linea = int(H*0.60) - (n_lines-1)*22
                chain.append(
                    f"drawtext=fontfile={FONT}:text='{esc(wrapped)}':fontcolor=white:"
                    f"fontsize=32:line_spacing=8:x=(w-text_w)/2:y={y_linea}:"
                    f"shadowcolor=black@0.92:shadowx=2:shadowy=2:alpha='{fade_e}'")
            chain += [
                f"drawtext=fontfile={FONT}:text='{esc(titulo)}':fontcolor=white:"
                f"fontsize=32:x=40:y={int(H*0.80)}:shadowcolor=black@0.85:shadowx=2:shadowy=2:alpha='{fade_e}'",
                f"drawtext=fontfile={FONT}:text='{esc(brand)}':fontcolor={brand_color}:"
                f"fontsize=18:x=40:y={int(H*0.80)+46}:shadowcolor=black@0.8:shadowx=2:shadowy=2:alpha='{fade_e}'",
            ]
            fc = ",".join(chain)
            fgpath = tmpdir / f"fg_{i}.txt"
            fgpath.write_text(fc, encoding="utf-8")
            cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(bg),
                   "-t", f"{fr/FPS:.3f}", "-filter_complex_script", str(fgpath),
                   "-c:v", "libx264", "-preset", PRESET, "-crf", str(CRF),
                   "-threads", str(THREADS), "-pix_fmt", "yuv420p",
                   "-movflags", "+faststart", "-an", str(clip)]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if r.returncode != 0:
                raise GenError(f"ffmpeg fallo en toma {i}:\n{r.stderr[-1200:]}")
            if not clip.exists() or clip.stat().st_size == 0:
                raise GenError(f"toma {i} no produjo salida")
            clips.append(clip)

        concat = tmpdir / "list.txt"
        concat.write_text("\n".join(f"file '{c.resolve()}'" for c in clips),
                           encoding="utf-8")
        tmpvid = tmpdir / "video_noa.mp4"
        r2 = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat",
                             "-safe", "0", "-i", str(concat), "-c", "copy",
                             str(tmpvid)], capture_output=True, text=True, timeout=120)
        if r2.returncode != 0:
            raise GenError(f"concat video fallo:\n{r2.stderr[-800:]}")
        wav_in = audio_wav if audio_wav is not None else (tmpdir / "narracion.wav")
        if not wav_in.exists():
            raise GenError(f"narracion.wav no encontrado en {wav_in}")
        cmd3 = ["ffmpeg", "-v", "error", "-y", "-i", str(tmpvid),
                "-i", str(wav_in), "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags",
                "+faststart", str(out)]
        r3 = subprocess.run(cmd3, capture_output=True, text=True, timeout=120)
        if r3.returncode != 0:
            raise GenError(f"mux audio fallo:\n{r3.stderr[-800:]}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    if not out.exists() or out.stat().st_size == 0:
        raise GenError("salida final vacia")
    return out


def build_narration(texts, voice, out_wav: Path) -> float:
    """Genera un WAV con TODA la narracion en UNA sola llamada TTS.

    El tier gratuito de Gemini TTS limita ~10 req/min, asi que enviamos el
    guion completo (titulo + lineas) en un solo generate_speech para no
    agotar la cuota. Reintenta con backoff largo ante 429.
    """
    guion = ". ".join(t.strip().rstrip(".") for t in texts if t.strip()) + "."
    last_err = None
    for attempt in range(8):
        try:
            generate_speech(guion, out_wav, voice=voice)
            break
        except RuntimeError as e:
            last_err = e
            if "429" in str(e) or "503" in str(e):
                time.sleep(15 * (attempt + 1))
                continue
            raise
    else:
        raise RuntimeError(f"TTS fallo tras reintentos: {last_err}")
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                         "format=duration", "-of",
                         "default=noprint_wrappers=1:nokey=1", str(out_wav)],
                        capture_output=True, text=True)
    try:
        return float(dur.stdout.strip())
    except Exception:
        return 30.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canal", required=True, choices=list(CFG.keys()))
    ap.add_argument("--dia", type=int, default=1)
    ap.add_argument("--segments", type=int, default=3)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    cfg = dict(CFG[a.canal])
    playlist = json.loads(
        (BASE / "channels" / a.canal / "playlist" / cfg["playlist"]).read_text(
            encoding="utf-8"))
    items = playlist[cfg["key"]]
    it = items[a.dia % len(items)]
    titulo = it["titulo"]
    lineas = it["lineas"]
    narrate = [titulo] + lineas

    CH = BASE / "channels" / a.canal
    BG = sorted((CH / "assets" / "bg").glob("toma_*.png"))
    MEDIA = CH / "media"
    MEDIA.mkdir(parents=True, exist_ok=True)
    out = a.out or (MEDIA / f"dia_{a.dia:03d}_audio.mp4")

    tmp = Path(tempfile.mkdtemp(prefix="nar_"))
    try:
        wav = tmp / "narracion.wav"
        print(f"Generando narracion TTS ({len(narrate)} frases, voz "
              f"{cfg['voice']})...", flush=True)
        dur = build_narration(narrate, cfg["voice"], wav)
        print(f"  audio: {dur:.1f}s -> {wav.stat().st_size} bytes", flush=True)
        out = render_video(lineas, titulo, BG, out, a.segments, cfg["grade"],
                           cfg["brand"], cfg["brand_color"], audio_wav=wav)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"OK  {out}  ({out.stat().st_size} bytes)")
    print(f"    canal={a.canal} dia={a.dia} titulo='{titulo}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
