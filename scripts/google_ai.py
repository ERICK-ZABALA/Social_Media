# Reusable Python module: scripts/google_ai.py (Social_Media repo)
# Pattern for calling Google AI Studio from Python with a file-stored key.
# Verified 2026-08-13: TTS works on free tier; Imagen/Veo 429 (quota 0).
import base64, json, os, struct, time, urllib.request, urllib.error
from pathlib import Path

KEY_FILE = Path(os.path.expanduser("~/.google_gemini_key"))
KEY_FILE_ALT = Path(os.path.expanduser("~/.google_gemini_key2"))
KEY_FILE_ALT3 = Path(os.path.expanduser("~/.google_gemini_key3"))
KEY_FILE_ALT4 = Path(os.path.expanduser("~/.google_gemini_key4"))
KEY_FILE_ALT5 = Path(os.path.expanduser("~/.google_gemini_key5"))
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
TTS_MODEL = "gemini-2.5-flash-preview-tts"
IMAGE_MODEL = "gemini-3-pro-image"   # needs paid tier (free = 429)

# Orden de preferencia para repartir la cuota de TTS (todas gratuitas).
# KEY5 (2026-08-13) es la única con cuota viva; va PRIMERO.
_KEY_FILES = [KEY_FILE_ALT5, KEY_FILE_ALT, KEY_FILE_ALT4, KEY_FILE_ALT3, KEY_FILE]

def api_key():
    for kf in _KEY_FILES:
        if kf.exists() and kf.read_text().strip():
            return kf.read_text().strip()
    raise RuntimeError(f"Falta alguna key en ~/.google_gemini_key* (chmod 600)")

def _post_json(model, action, payload, timeout=300):
    url = f"{BASE_URL}/models/{model}:{action}?key={api_key()}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except TimeoutError as e:
            # la conexion SSL se colgo leyendo la respuesta (key lenta)
            if attempt < 3:
                time.sleep(10*(attempt+1)); continue
            raise RuntimeError(f"HTTP timeout: {e}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 3:
                time.sleep(8*(attempt+1)); continue
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:600]}")

def generate_speech(text, out_wav, voice="Kore"):
    resp = _post_json(TTS_MODEL, "generateContent",
        {"contents":[{"parts":[{"text":text}]}],
         "generationConfig":{"responseModalities":["AUDIO"],
           "speechConfig":{"voiceConfig":{"prebuiltVoiceConfig":{"voiceName":voice}}}}})
    b64 = None; rate = 24000
    for p in (resp["candidates"][0]["content"]["parts"]):
        if "inlineData" in p:
            b64 = p["inlineData"]["data"]; mt = p["inlineData"]["mimeType"]
            if "rate=" in mt: rate = int(mt.split("rate=")[1].split(";")[0])
            break
    pcm = base64.b64decode(b64)
    with open(out_wav,"wb") as f:
        f.write(b"RIFF"); f.write(struct.pack("<I",36+len(pcm))); f.write(b"WAVE")
        f.write(b"fmt "); f.write(struct.pack("<IHHIIHH",16,1,1,rate,rate*2,2,16))
        f.write(b"data"); f.write(struct.pack("<I",len(pcm))); f.write(pcm)
    return Path(out_wav)
