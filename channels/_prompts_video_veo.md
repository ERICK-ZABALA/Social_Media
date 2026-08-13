# Prompts de Video Veo 3.1 — 4 Canales (estilo cinematográfico)
# Config base: veo-3.1-generate-preview, aspect_ratio=9:16, 720p, 8s, person_generation=allow_all
# REGLA: Retro Cartoon SIN letras. InsightStar SIN letras en medio. Factory Rock letra en MEDIO (overlay ffmpeg, no en Veo). IA News subtítulos (overlay ffmpeg).
# Se generan mañana al liberar RPD de Veo (rolling 24h desde ~20:40 UTC del 13 ago).

## 1) RETRO CARTOON (cuentos-caricaturas) — faltan 5 clips: 03, 07, 08, 09, 10
# Estilo Makoto Shinkai, SIN TEXTO, audio ambiente.
CLIP_03 = "Makoto Shinkai anime style, a girl with a red umbrella stands on a stone bridge over a koi pond in a traditional Japanese garden, cherry blossom petals drifting in the wind, soft pink and green palette, dreamy atmosphere, gentle rain. No text, no subtitles."
CLIP_07 = "Makoto Shinkai anime style, a girl in a red coat walks through a snowy town at dusk, lanterns glowing warm orange, snowflakes falling, a frozen river, cozy cinematic winter lighting, bokeh. No text, no subtitles."
CLIP_08 = "Makoto Shinkai anime style, a girl runs through a sunlit field of tall grass and red spider lilies, a torii gate in the distance, mountains and a clear blue sky, dynamic motion, vibrant colors, lens flare. No text, no subtitles."
CLIP_09 = "Makoto Shinkai anime style, a young woman looks out of a train window as it passes a lake at dawn, mist rising from the water, pine forests, a flock of cranes flying, pastel sky, reflective water. No text, no subtitles."
CLIP_10 = "Makoto Shinkai anime style, a young woman with flowing hair stands on a clifftop overlooking a starry night sky with the Milky Way, a distant glowing meteor, silhouette of pine trees, deep blue and purple tones, magical atmosphere. No text, no subtitles."

## 2) FACTORY ROCK / REFLEXIONES — 6 tomas cinematográficas car-drive golden hour
# La frase va en medio por overlay ffmpeg. Veo genera las tomas SIN texto.
TOMA_01 = "Cinematic 9:16 vertical shot, a car driving alone on an empty coastal highway at golden hour, low sun casting long shadows, warm lens flare, shallow depth of field, film grain, slow dolly forward. No text."
TOMA_02 = "Cinematic 9:16, close-up of hands on a steering wheel, golden sunlight through the window, bokeh city lights ahead, warm color grading, slow motion. No text."
TOMA_03 = "Cinematic 9:16, aerial drone shot of a winding mountain road at sunset, car tiny below, vast sky with clouds, epic scale, warm tones. No text."
TOMA_04 = "Cinematic 9:16, roadside diner at dusk, neon sign reflecting on wet asphalt, car parked, nostalgic mood, anamorphic flare. No text."
TOMA_05 = "Cinematic 9:16, rear-view mirror POV of the road stretching to the horizon at magic hour, sun dipping below hills, cinematic vignette. No text."
TOMA_06 = "Cinematic 9:16, the car fading into the horizon as night begins, city skyline glow in distance, peaceful ending, soft fade. No text."

## 3) IA NEWS — 10 + intro + cierre (estilo noticiero futurista, subtítulos por overlay)
# Cada noticia = 1 clip corto. Subtítulos se ponen con ffmpeg drawtext.
N_INTRO = "Cinematic 9:16, futuristic newsroom with holographic data streams floating in dark blue space, a glowing AI globe, sleek sci-fi aesthetic, slow orbit camera. No text."
N1 = "Cinematic 9:16, abstract visualization of an AI neural network expanding across a world map, glowing nodes, deep tech blue, data flowing. No text."
N2 = "Cinematic 9:16, two merging corporate logos dissolving into light particles, sleek acquisition metaphor, dark cinematic background. No text."
N3 = "Cinematic 9:16, enterprise server racks glowing with secure blue shields, data center, cinematic depth, subtle motion. No text."
N4 = "Cinematic 9:16, a stylized national flag dissolving into a grid of AI circuits, upward glowing arrow, patriotic-tech mood. No text."
N5 = "Cinematic 9:16, a rocket made of light ascending through cloud data, billion-dollar scale, epic cinematic. No text."
N6 = "Cinematic 9:16, a samurai-inspired shield with evolving AI patterns, Japan aesthetic fused with tech, calm strength. No text."
N7 = "Cinematic 9:16, a face composed of light scanning lines over a city, surveillance theme, thoughtful mood. No text."
N8 = "Cinematic 9:16, young diverse students seated in a circular assembly, holographic policy document forming, hopeful. No text."
N9 = "Cinematic 9:16, the UN building silhouette with a glowing AI standards constellation above New York skyline, unity. No text."
N10 = "Cinematic 9:16, a security operations center with analysts monitoring glowing threat maps, Pittsburgh skyline hint, vigilant. No text."
N_CIERRE = "Cinematic 9:16, the AI Generativa News logo forming from particles, forward motion into light, outro. No text."

## 4) INSIGHT STAR — corporativo cinematográfico, SIN letras en medio
# Texto en lower-thirds/esquinas por overlay. Voza en off del guion.
IS_01 = "Cinematic 9:16, aerial night view of a glowing smart city, fiber-optic light lines tracing networks between buildings, slow ascent, deep blue and cyan. No text."
IS_02 = "Cinematic 9:16, a server room with cascading data light, SD-WAN visualization, engineers silhouettes monitoring, professional mood. No text."
IS_03 = "Cinematic 9:16, unified communications abstract: voice, video and chat icons merging into one glowing orb, sleek corporate. No text."
IS_04 = "Cinematic 9:16, a 24/7 NOC with multiple screens, a reassuring engineer at desk, warm light contrast, trust. No text."
IS_05 = "Cinematic 9:16, partner logos (Cisco, Cloudflare, Oracle, Google, Avaya, Asterisk) appearing as clean glass panels in sequence, premium. No text."
IS_06 = "Cinematic 9:16, the Insight Star logo forming over a city skyline at dawn, tagline space, calm confident outro. No text."
