# Social Media Factory

Orquestador de contenido para 4 canales. Hermes actúa como cerebro: investiga,
genera, pide aprobación y publica. Nada se publica sin aprobación explícita.

## Arquitectura

Una SOLA app de TikTok **"Rock Factory"** (mismos `client_key`/`client_secret`)
autoriza a las 4 cuentas del proyecto vía OAuth. Cada cuenta guarda su propio
token en un archivo `chmod 600` fuera del repo. El mapa de cuentas vive en
`scripts/accounts.py` y los scripts de OAuth/subida lo resuelven con `--account <slug>`.

## Estructura

```
social-media/
├── smf/                          # NÚCLEO COMPARTIDO (los 4 canales)
│   ├── schema.sql                #   esquema SQLite
│   ├── db.py                     #   estados, idempotencia, backoff
│   └── video/
│       └── lyric_card.py         #   overlay de tarjetas de letra
├── tests/                        # suite (pytest)
│
├── channels/                     # UN DIRECTORIO POR CANAL
│   ├── rock-factory/             #   marca de la app + canal principal
│   │   └── reflexiones/          #   sub-canal "Reflexiones" (vive DENTRO)
│   │       ├── docs/             #     guías del canal
│   │       ├── assets/bg/        #     fondos de video (toma_XX.png)
│   │       ├── playlist/         #     canciones.json
│   │       ├── media/            #     videos (IGNORADO por git)
│   │       └── estado.json       #     día actual, última generación
│   ├── cuentos-caricaturas/      #   (antes retro-cartoon)
│   ├── insight-star/             #   videos Insight Star (muestras generadas)
│   └── ia-generativa-news/       #   videos IA Generativa News (muestras generadas)
│
├── scripts/                      # generadores + OAuth + subida (multi-cuenta)
│   ├── accounts.py               #   mapa slug -> email -> token (1 app, 4 cuentas)
│   ├── generar_video.py          #   Reflexiones (rock-factory)
│   ├── generar_retro_cartoon.py  #   Cuentos Caricaturas
│   ├── generar_insight_star.py   #   Insight Star
│   ├── generar_ia_news.py        #   IA Generativa News
│   ├── oauth_helper.py           #   flujo OAuth --account <slug>
│   ├── subir_tiktok.py           #   publisher video.upload --account <slug>
│   ├── token_setup.py            #   init de los 4 archivos de token (chmod 600)
│   └── legal_description.txt
│
├── legal/                        # PUBLICADO EN GITHUB PAGES
│   ├── index.html                #   índice de canales
│   └── rock-factory/             #   ToS + Privacy + icono exigidos por TikTok
│       ├── terms.html
│       ├── privacy.html
│       ├── icon.png
│       └── tiktok_registro_app.md
│
└── shared/                       # recursos comunes entre canales
```

**Por qué esta separación:** `smf/` es infraestructura común — la máquina de
estados y la lógica de publicación son idénticas para los 4 canales. Solo cambia
la configuración, los assets y los trámites, que viven en `channels/<slug>/`.

**Nombres en minúscula con guiones:** las rutas bajo `legal/` se sirven como
URLs públicas y TikTok las valida de forma estricta. Un espacio se convierte en
`%20` y provoca rechazos.

## Canales

| Canal | Slug | Plataforma inicial | Estado |
|---|---|---|---|
| Rock Factory | `rock-factory` | TikTok | App en revisión (sandbox) |
| Insight Star | `insight-star` | LinkedIn/X | Muestras generadas |
| IA Generativa News | `ia-generativa-news` | Multi | Muestras generadas |
| Reflexiones *(dentro de Rock Factory)* | `rock-factory/reflexiones` | TikTok/Shorts | Diario (cron 9am) |
| Cuentos Caricaturas | `cuentos-caricaturas` | TikTok/Shorts | Prototipo Shinkai |

## Desarrollo

```bash
uv venv .venv && . .venv/bin/activate
uv pip install -e ".[dev]"
pytest
```

## Estado actual

- [x] Etapa 1 — esquema SQLite, máquina de estados, idempotencia, backoff (14 tests)
- [x] Bloqueo anti-copyright: no se aprueba nada con `rights_status` sin resolver
- [x] Páginas legales e icono para la revisión de TikTok
- [x] Reordenamiento de carpetas (reflexiones dentro de rock-factory; cuentos-caricaturas)
- [x] Esquema multi-cuenta (1 app, 4 tokens) + scripts parametrizados con --account
- [x] Generadores de muestra para insight-star e ia-generativa-news
- [ ] Etapa 2 — publisher de TikTok (`video.upload`) en producción (app en revisión)
- [ ] Etapa 3 — UI de aprobación (necesaria para el demo de la revisión)
- [ ] Etapa 4 — bot de Telegram

## Seguridad

Las credenciales **nunca** van al repositorio. `.gitignore` excluye `*client_secret*`,
`*token*.json`, `.env` y `media/`. Los secretos viven en archivos con `chmod 600`
fuera del repo (`~/.tiktok_rock_factory_token`, etc.). El mapa de cuentas está en
`scripts/accounts.py` (solo slugs/emails/rutas, sin secretos).
