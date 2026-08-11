# Social Media Factory

Orquestador de contenido para 5 canales. Hermes actúa como cerebro: investiga,
genera, pide aprobación y publica. Nada se publica sin aprobación explícita.

## Estructura

```
social-media/
├── smf/                          # NÚCLEO COMPARTIDO (los 5 canales)
│   ├── schema.sql                #   esquema SQLite
│   └── db.py                     #   estados, idempotencia, backoff
├── tests/                        # suite (pytest)
│
├── channels/                     # UN DIRECTORIO POR CANAL
│   └── rock-legends-club/
│       ├── docs/                 #   guías y trámites del canal
│       ├── assets/               #   icono, logos
│       └── media/                #   videos (ignorado por git)
│
├── docs/legal/                   # PUBLICADO EN GITHUB PAGES
│   ├── index.html                #   índice de canales
│   └── rock-legends-club/        #   ToS + Privacy exigidos por TikTok
│
└── shared/                       # recursos comunes entre canales
```

**Por qué esta separación:** `smf/` es infraestructura común — la máquina de
estados y la lógica de publicación son idénticas para los 5 canales. Solo cambia
la configuración, los assets y los trámites, que viven en `channels/<slug>/`.

**Nombres en minúscula con guiones:** las rutas bajo `docs/legal/` se sirven como
URLs públicas y TikTok las valida de forma estricta. Un espacio se convierte en
`%20` y provoca rechazos.

## Canales

| Canal | Slug | Plataforma inicial | Estado |
|---|---|---|---|
| Rock Legends Club | `rock-legends-club` | TikTok | En registro de app |
| Insight Star | `insight-star` | LinkedIn/X | Pendiente |
| IA Generativa News | `ia-generativa-news` | Multi | Pendiente |
| Reflexciones | `reflexciones` | TikTok/Shorts | Pendiente |
| Cuentos Caricaturas | `cuentos-caricaturas` | TikTok/Shorts | Pendiente |

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
- [ ] Etapa 2 — publisher de TikTok (`video.upload`)
- [ ] Etapa 3 — UI de aprobación (necesaria para el demo de la revisión)
- [ ] Etapa 4 — bot de Telegram

## Seguridad

Las credenciales **nunca** van al repositorio. `.gitignore` excluye `*client_secret*`,
`*token*.json`, `.env` y `media/`. Los secretos viven en archivos con `chmod 600`
fuera del repo (`~/.tiktok_rock_secret`).
