# Plan de Implementación — Hermes Media Factory
### Instancia en Google Cloud + Aprobación vía Telegram

---

## 0. Punto de partida y supuestos

- Hermes Agent ya corre como servicio/proceso en una **instancia de Google Compute Engine (GCE)**.
- Ya existe un **bot de Telegram conectado a Hermes** (probablemente vía la skill de Telegram o un webhook custom).
- Vamos a usar Telegram no solo como canal de chat, sino como **la bandeja de aprobación** (botones inline: Aprobar / Editar / Rechazar).
- 5 marcas: Insight Star, Music Rock, Reflexciones, Cuentos Caricaturas, IA Generativa News.
- Nada se publica sin tu aprobación explícita.

---

## 1. Arquitectura general sobre la instancia GCE

```
GCE INSTANCE (VM)
│
├── hermes-core/            → Proceso principal del agente (systemd service)
│   ├── llm client
│   ├── memory store
│   ├── skills/
│   └── orchestrator
│
├── telegram-bridge/         → Bot de Telegram (webhook o long polling)
│   ├── /aprobar /rechazar /editar (comandos + botones inline)
│   └── notificaciones push cuando hay contenido pendiente
│
├── content-db/               → Base de datos (Postgres o SQLite al inicio)
│   ├── tabla: content_items
│   ├── tabla: approvals
│   ├── tabla: schedule
│   └── tabla: metrics
│
├── scheduler/                 → Cron jobs / cola de tareas (cron + systemd timers, o Celery/Redis si crece)
│   ├── job diario de investigación por canal
│   └── job de publicación (solo items "aprobado" y con fecha cumplida)
│
├── publishers/                 → Módulos de publicación por red
│   ├── meta_publisher.py (FB/IG)
│   ├── x_publisher.py (usa xurl / X API)
│   ├── linkedin_publisher.py
│   ├── tiktok_publisher.py
│   └── youtube_publisher.py
│
└── skills/
    ├── insight_star/
    ├── music_rock/
    ├── reflexiones/
    ├── cuentos_caricaturas/
    └── ia_news/
```

**Por qué esta separación:** cada pieza puede fallar o reiniciarse sola sin tumbar el agente principal. El `content-db` es la fuente de verdad — todo pasa por ahí antes de publicarse.

---

## 2. Fase 1 — Infraestructura base (semana 1)

1. **Base de datos.** Empezar con SQLite si el volumen es bajo (más simple en una sola VM); migrar a Postgres cuando haya varios canales publicando a diario. Definir el esquema mínimo:
   - `content_items(id, marca, tipo, texto, media_url, plataformas[], estado, fecha_creacion, fecha_programada)`
   - `approvals(id, content_id, decision, comentario, fecha)`
   - `metrics(id, content_id, plataforma, views, likes, comments, shares, followers_gained, fecha)`
2. **Servicio systemd** para Hermes core, con reinicio automático (`Restart=on-failure`).
3. **Logs centralizados** (journald o un archivo rotado) — vas a necesitarlos para depurar generación fallida.
4. **Backups automáticos** de la base de datos (cron diario a un bucket de Cloud Storage).

Entregable de esta fase: Hermes corriendo de forma estable, con una DB vacía lista para recibir contenido.

---

## 3. Fase 2 — Telegram como bandeja de aprobación (semana 1-2)

Esta es la pieza más importante para tu flujo, así que la detallo:

**Formato de notificación que Hermes te envía por Telegram:**

```
📋 NUEVO CONTENIDO — Insight Star
"Los Voice Agents están cambiando los Contact Centers..."
[imagen/preview adjunto]

Redes: LinkedIn, Facebook, Instagram, X, TikTok
Fecha propuesta: 11/08/2026 10:00

[🟢 Aprobar]  [🟡 Editar]  [🔴 Rechazar]
```

**Comportamiento de los botones:**
- 🟢 Aprobar → cambia `estado` a `aprobado` en la DB, el scheduler lo toma en la próxima corrida.
- 🟡 Editar → el bot responde "¿qué querés cambiar?", tu respuesta en texto libre se pasa como instrucción al mismo skill que generó el contenido, se regenera y te vuelve a mandar la preview.
- 🔴 Rechazar → se marca `rechazado`, se guarda igual en la DB para no repetir el mismo tema (memoria de "ya lo intentamos").

**Detalle técnico:** esto se implementa con Telegram Bot API usando `InlineKeyboardMarkup` y `callback_query` handlers. Si tu bridge actual solo hace mensajes de texto, hay que añadir soporte de botones inline — es la única pieza nueva de código que realmente hace falta escribir en esta fase.

**Para evitar saturarte:** agrupar notificaciones — un resumen diario a una hora fija (ej. 8:00 AM) con todo lo pendiente de las 5 marcas, en vez de mensajes sueltos todo el día.

---

## 4. Fase 3 — Arrancar con 2 canales piloto (semana 2-4)

Como ya se planteó en la conversación previa, no conviene lanzar los 5 canales a la vez. Empezar con:

- **Insight Star** (solo texto/imagen, sin video — el flujo más simple)
- **IA Generativa News** (investigación + guion, valida el pipeline de research)

**Flujo a validar en esta fase:**
```
Cron diario → skill investiga (web search) → LLM redacta →
control de calidad básico (longitud, tono, sin datos inventados) →
guarda en content_db como "pendiente" → notifica por Telegram →
esperás tu decisión → si apruebas, scheduler publica en la fecha marcada
```

**Qué medir antes de avanzar a fase 4:**
- ¿La investigación trae fuentes reales y verificables?
- ¿El contenido generado necesita edición tuya en más del 30% de los casos? (si sí, hay que ajustar los prompts de los skills antes de escalar)
- ¿El scheduler publica en el horario correcto sin fallos?

---

## 5. Fase 4 — Publishers por plataforma (semana 3-5, en paralelo con fase 3)

Cada red social necesita su propio módulo porque las APIs son distintas:

| Plataforma | Vía de publicación | Nota |
|---|---|---|
| X | `xurl` (ya mencionado en tu setup) | Más simple, ya tenés la skill |
| LinkedIn | LinkedIn API (requiere app registrada) | Aprobación de app puede tardar días — iniciar trámite ya |
| Facebook / Instagram | Meta Graph API (Business) | Requiere cuenta de negocio + revisión de app de Meta |
| TikTok | TikTok Content Posting API | Acceso restringido, solicitar cuanto antes — es el trámite más lento típicamente |
| YouTube Shorts | YouTube Data API v3 | Cuotas diarias limitadas, hay que planificar volumen |

**Recomendación:** iniciar los registros de app/developer de Meta, TikTok y LinkedIn **ahora mismo**, en paralelo a todo lo demás, porque las aprobaciones de esas plataformas suelen ser el cuello de botella real del proyecto, no el desarrollo de Hermes.

---

## 6. Fase 5 — Canales audiovisuales (semana 5-9)

Una vez validado el pipeline de texto/aprobación, se suma la pata de producción audiovisual para Music Rock, Reflexciones y Cuentos Caricaturas:

```
Guion → Storyboard/imágenes → Narración (TTS) →
Música (licenciada/original) → Subtítulos → Edición 9:16 → Preview
```

Puntos de atención que ya identificaste correctamente en tu mensaje original:

- **Music Rock:** priorizar interpretaciones propias, música original o covers con licencia real. Subir covers comerciales sin autorización es un riesgo de copyright y de takedown en todas las plataformas, no solo legal.
- **Reflexciones:** usar guion original + imágenes/video generados en vez de reutilizar escenas de películas con copyright.
- **Cuentos Caricaturas:** personajes originales (como el ejemplo del zorro) en vez de personajes con marca registrada — además construye identidad propia de marca, que es mejor para monetización a largo plazo.

Esta fase es la que más herramientas nuevas requiere (generación de imagen, TTS, edición de video), así que conviene definir presupuesto y elegir proveedores antes de integrarlos como skills nuevas de Hermes.

---

## 7. Fase 6 — Analytics y loop de aprendizaje (semana 8+)

Job diario/semanal que:
1. Trae métricas de cada plataforma (views, likes, shares, followers ganados) vía sus APIs.
2. Las guarda en la tabla `metrics` ligadas a cada `content_id`.
3. Un skill de análisis resume qué hooks, duraciones y temas funcionaron mejor por canal.
4. Ese resumen se inyecta como contexto en los prompts de generación siguientes (ajuste de estrategia, no solo reporte).

Este loop es lo que convierte el sistema en algo que mejora solo, en vez de repetir la misma fórmula indefinidamente.

---

## 8. Cronograma resumen

| Semana | Foco |
|---|---|
| 1 | Infraestructura base + DB en la VM |
| 1-2 | Bot de Telegram con botones de aprobación |
| 2-4 | Pilotos: Insight Star + IA Generativa News (solo texto/imagen) |
| 3-5 | Publishers de X, LinkedIn, Meta (en paralelo, iniciar trámites de apps ya) |
| 5-9 | Suma de Music Rock, Reflexciones, Cuentos Caricaturas (pipeline audiovisual) |
| 6-10 | Trámites TikTok/YouTube (suelen tardar más — iniciarlos temprano) |
| 8+ | Analytics y loop de optimización activo |

---

## 9. Riesgos a vigilar

- **Copyright** en Music Rock/Reflexciones/Cuentos, como ya se señaló — define desde ya una política de fuentes (qué material es propio/licenciado) antes de generar el primer video.
- **Aprobación de apps de las plataformas** (Meta, TikTok) puede ser el cuello de botella real del cronograma, no el desarrollo técnico.
- **Cuotas de API** (YouTube especialmente) — planificar volumen de publicación según los límites, no al revés.
- **Costo de generación audiovisual** (imagen/video/TTS) escala rápido con 4 canales de video diario — conviene estimar costo por pieza antes de fase 5.

---

## 10. Repositorios de GitHub que le sirven a Hermes (por componente)

No hace falta programar todo desde cero. Estos repos cubren buena parte de las piezas del plan — la idea es usarlos como base o referencia dentro de los skills de Hermes, no como reemplazo del agente.

### A. Bot de Telegram con botones de aprobación (Fase 2)
- **python-telegram-bot** — https://github.com/python-telegram-bot/python-telegram-bot
  La librería estándar en Python para bots de Telegram. Trae el ejemplo exacto que necesitás: `InlineKeyboardMarkup` + `CallbackQueryHandler` para los botones 🟢/🟡/🔴 (ver `examples/inlinekeyboard.py` y `inlinekeyboard2.py` del propio repo, este último ya maneja flujos tipo conversación con estados, que es justo el patrón "aprobar → editar → publicar").

### B. Orquestador de scheduling y publicación multi-plataforma (Fases 4-5)
- **Postiz** — https://github.com/gitroomhq/postiz-app
  El más maduro de la categoría (33k+ estrellas). Autopublica en X, Instagram, TikTok, LinkedIn, YouTube, Facebook, Telegram y más desde un solo calendario, con agente de IA embebido y workflows tipo n8n. Se puede self-hostear en tu misma instancia de GCE. Es la opción más sólida para reemplazar tus módulos `publishers/` custom si no querés mantenerlos vos mismo.
- **trypost** — https://github.com/trypostit/trypost
  Alternativa open source más liviana, con servidor MCP nativo — esto es relevante porque significa que Hermes (como agente) podría llamarlo directamente como herramienta en vez de que vos programes cada integración de API a mano. Incluye workspaces con flujos de aprobación pensados para agencias que manejan varias marcas, que calza con tu caso de 5 canales.
- **socialmediascheduler** (Masterjx9) — https://github.com/Masterjx9/socialmediascheduler
  Más simple, buen ejemplo de referencia si preferís algo minimalista en vez de las plataformas completas de arriba (usa SQLite, fácil de leer y adaptar).

### C. Investigación / noticias de IA (canal "IA Generativa News", Fase 3)
- **rss-news-ai** — https://github.com/ai4altruism/rss-news-ai
  Monitorea feeds RSS, usa un LLM para filtrar qué es realmente relevante, agrupa cobertura duplicada de un mismo tema y entrega resúmenes — es casi exactamente el job que describiste como "buscar 50-100 noticias → eliminar duplicadas → top 10". Entrega a Slack/email/dashboard, fácil de adaptar para que entregue a tu `content_db` en vez de eso.
- **My-AI-News-Aggregator** — https://github.com/mehdi1514/My-AI-News-Aggregator
  Pipeline más completo con agentes separados (digest agent, curator agent, email agent) y Postgres — buena referencia de arquitectura para tu propio pipeline de investigación diaria.
- **awesome-ai-news** — https://github.com/taielab/awesome-ai-news
  No es una herramienta sino un directorio curado de decenas de estas herramientas — útil para comparar antes de elegir una base.

### D. Generación de video "faceless" para Music Rock / Reflexciones / Cuentos Caricaturas (Fase 5)
- **openshorts** — https://github.com/mutonby/openshorts
  El más completo de los que encontré: guion con IA (hook-problema-solución-CTA), voz con ElevenLabs, subtítulos automáticos con faster-whisper, overlays de texto, y **publicación directa a TikTok/Instagram Reels/YouTube Shorts**. MIT license para el núcleo. Es probablemente la base más sólida para tu pipeline audiovisual completo.
- **Viral-Faceless-Shorts-Generator** — https://github.com/Dark2C/Viral-Faceless-Shorts-Generator
  Especialmente relevante porque su flujo ya incluye un paso de **"Approve Script" manual** antes de generar el video final — es el mismo principio de tu bandeja de aprobación, aplicado a nivel de guion. Usa Piper TTS (gratis, corre local) y FFmpeg.
- **AI-Youtube-Shorts-Generator** — https://github.com/SaarD00/AI-Youtube-Shorts-Generator
  Buen ejemplo del patrón "guion con estructura narrativa fija" (Hook → Contexto → Mecanismo → Giro), aplicable directamente a Reflexciones y Cuentos Caricaturas.
- **awesome-faceless** — https://github.com/sasharun/awesome-faceless
  Directorio curado de 80+ herramientas (TTS, texto-a-video, edición) — útil para elegir componentes sueltos si preferís armar tu propio pipeline en vez de adoptar uno completo.

### E. Nota sobre copyright en Music Rock
Ningún repo de "cover generator" resuelve el problema legal que ya identificaste (covers de canciones comerciales sin licencia). Para ese canal específico, lo que estos repos sí aportan es la parte de **producción** (TTS, voz, edición) — la fuente del audio/interpretación debe seguir siendo propia o licenciada, como ya definiste en el plan original.

### F. Cómo encajan en tu arquitectura de la Fase 1
No reemplazan a Hermes como orquestador — se integran como:
1. **Skills** que Hermes invoca (research, guion, TTS, video, publicación), o
2. **Servicios independientes en la misma VM** (ej. Postiz u openshorts corriendo en su propio contenedor Docker) a los que Hermes les manda trabajo vía API/cola, y de los que recibe el resultado para pasar por tu bandeja de aprobación en Telegram antes de publicar.

La segunda opción es la más recomendable para no reinventar el pipeline de video/audio desde cero — Hermes queda como el "cerebro" que decide qué, cuándo y con qué contenido, y estos servicios hacen el trabajo pesado de producción.

---

## 11. Primer paso concreto

Si querés arrancar ya, el primer entregable accionable es: el bot de Telegram con botones inline funcionando sobre un `content_item` de prueba (uno solo, manual, sin cron todavía). Eso valida toda la cadena aprobación→estado→publicación antes de conectar la generación automática. ¿Querés que armemos ese código base para el bridge de Telegram con botones inline como siguiente paso?
