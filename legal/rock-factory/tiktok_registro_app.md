# Registro de la app en developers.tiktok.com — ROCK FACTORY (APP OFICIAL)

Fuente: docs oficiales de TikTok for Developers + guías 2026 (verificado 2026-08-11).
Toda la información de la API fue contrastada; los límites de TikTok cambian, así que
la fuente de verdad final siempre es https://developers.tiktok.com

**App oficial del proyecto:** `Rock Factory` — email del owner: `rock.factory@outlook.com`
Sustituye a la app de prueba anteriore (`Rock Legends Publisher`). Esta es la que se
envía a review y la que usa `scripts/subir_tiktok.py`.

---

## DECISIÓN PREVIA: qué scope pedir

Esto define el resto del trámite. No se puede cambiar sin rehacer la solicitud.

| | `video.upload` (Opción A) | `video.publish` (Opción B) |
|---|---|---|
| Qué hace | Sube a **borradores**; vos publicás desde el celular | Publica **directo**, sin intervención |
| UI obligatoria | No | Sí: avatar, usuario, selector de privacidad, duet/stitch/comentarios, disclosure comercial |
| Auditoría | Liviana o innecesaria | 2-4 semanas, varias rondas de rechazo habituales |
| Visibilidad antes de aprobar | **Pública** (la publicás vos) | `SELF_ONLY` forzado |
| Encaja con bot de Telegram | Sí | No sin construir web UI |

**Recomendado: Opción A.** Publicás en público desde el día uno a cambio de un toque
en el celular por video. Migrar a B más adelante, con el canal ya andando.

> **Estado de la app (2026-08-11):** ya creada en el portal con nombre `Rock Factory`,
> plataforma Web marcada, owner `rock.factory@outlook.com`. **Faltan** antes de enviar a
> review: Description, Terms of Service URL, Privacy Policy URL, agregar producto
> Content Posting API + scopes, y el demo video. Ver sección "CHECKLIST PARA ENVIAR".

---

## MONETIZACIÓN Y PAÍS DE LA CUENTA (notas del 2026-08-11)

La app `Rock Factory` está asociada a una cuenta de TikTok **registrada en Francia**,
para acceder al TikTok Creator Rewards Program (países elegibles: EE.UU., Reino Unido,
Alemania, Japón, Corea del Sur, Francia, México, Brasil). Bolivia NO está en la lista.

- El país de la cuenta de TikTok NO se elige en un formulario: se fija en el alta por la
  **SIM (+33 Francia)** con la que se crea la cuenta. Una VPN sola no lo cambia.
- Señales que TikTok usa (en orden de peso): (1) código del teléfono/SIM, (2) región de
  la App Store/Google Play, (3) idioma y zona horaria del celular, (4) IP.
- La región de Google Play se cambia desde la cuenta de Google, pero SOLO afecta la
  señal #2 (descarga de la app); no fija el país de TikTok. Google limita el cambio a
  una vez por año y exige método de pago del país.
- **Cobro:** Payoneer opera en Bolivia y TikTok paga vía Payoneer en 120+ países, así
  que se puede tener la cuenta "en Francia" y cobrar a La Paz.
- **Advertencia clave:** el Creator Rewards paga por las VISTAS de audiencias de países
  elegibles. Si el contenido atrae a LATAM (no elegible), el RPM es bajo. Para ganar en
  serio la audiencia debe ser de Francia/regiones elegibles (subtítulos, horarios y
  hashtags orientados a Francia).

---

## PASO 0 — Requisitos previos

1. Cuenta de TikTok **real** para el canal, creada con SIM de Francia (+33), con algunos
   videos ya publicados. Las cuentas vacías levantan sospecha en la auditoría.
2. Email de contacto: `rock.factory@outlook.com` con 2FA activo.
3. Nombre y logo del canal listos (`docs/legal/rock-factory/icon.png`, 1024x1024).
4. Sitio web público con ToS y Privacy Policy. Se usa GitHub Pages de este repo
   (ver sección "URLs legales"). El PAT fine-grained NO tiene Pages:write → **la
   activación de GitHub Pages la hace el usuario** en el portal de GitHub.

---

## PASO 1 — Crear la cuenta de developer

1. Ir a https://developers.tiktok.com
2. **Log in** con la cuenta de TikTok del canal (la de Francia).
3. Aceptar los Developer Terms.
4. Verificar el email.

---

## PASO 2 — Registrar la app (HECHO parcialmente)

1. https://developers.tiktok.com/apps → **Connect an app** / **Create an app**
2. Completar:

   | Campo | Valor |
   |---|---|
   | App name | `Rock Factory` |
   | Description | *Ver texto sugerido en scripts/legal_description.txt* (mín. 120 chars) |
   | Category | Content Management / Productivity |
   | Platform | Web |

**Sobre la descripción:** TikTok rechaza apps con propósito difuso. Decir "publica
contenido original propio en mi propio canal" es un caso de uso claro y legítimo.
No prometer funciones que la app no tenga.

---

## PASO 3 — Agregar el producto Content Posting API

1. Dentro de la app → **Add products** → **Content Posting API**
2. Elegir el modo:
   - Opción A → activar **Direct Post: OFF** (queda como upload a inbox/borradores)
   - Opción B → activar **Direct Post: ON** (dispara todos los requisitos de UI)

> **Pendiente:** aún no se ve el producto agregado en el portal. Agregar Content
> Posting API con Direct Post OFF antes de continuar.

---

## PASO 4 — Configurar scopes

En **Manage apps → Scopes**, agregar:

    user.info.basic        (obligatorio siempre)
    video.upload           (Opción A)

Pedir solo lo que se usa. Scopes de más = más motivos de rechazo.

> **Pendiente:** en el portal figura "No scopes yet". Agregar los dos de arriba.

---

## PASO 5 — Redirect URI de OAuth (HTTPS obligatorio)

TikTok exige que el Redirect URI empiece con `https://`. No acepta `http://localhost`.
Se resuelve con un **túnel HTTPS independiente** (ngrok o cloudflared) que apunte a
`http://localhost:8080` en la máquina donde corre `scripts/oauth_helper.py`.

Flujo:
1. En esa máquina, levantar el túnel:
   - ngrok:   `ngrok http 8080`  → da `https://xxxx.ngrok.io`
   - cloudflared: `cloudflared tunnel --url http://localhost:8080` → da `https://xxxx.trycloudflare.com`
2. El redirect URI a poner en el portal (Login Kit → Redirect URI) es:
   `https://<host-del-tunel>/callback`
3. Configurar el script con ese mismo valor:
   `python3 scripts/oauth_helper.py --redirect-uri https://<host-del-tunel>/callback`
   o exportando `TIKTOK_REDIRECT_URI`.

El túnel es independiente de insightstar.net (no se usa el dominio de la empresa).
Apagar el túnel cuando no se esté haciendo OAuth.

> Nota: el Redirect URI NO tiene que coincidir con el Web/Desktop URL (github.io).
> TikTok solo pide que el dominio mostrado en el DEMO VIDEO coincida con el
> Web/Desktop URL. El callback por túnel no aparece en la página web del demo.

---

## PASO 6 — Verificación de dominio (solo si usás PULL_FROM_URL)

Necesaria únicamente si TikTok descarga el video desde una URL tuya.
Si subimos los bytes con `FILE_UPLOAD`, **este paso no aplica**.

Como no tenemos dominio propio todavía, el plan es **FILE_UPLOAD** y saltear esto.

---

## PASO 7 — Sandbox

1. **Add a sandbox** (hasta 5 por app)
2. Autorizar la cuenta de TikTok del canal como cuenta de prueba

Límites del sandbox, confirmados:
- Todo lo publicado queda en `SELF_ONLY`
- Máximo **5 cuentas** autorizadas cada 24 horas
- El sandbox **no** habilita publicación pública

---

## PASO 8 — Guardar credenciales (IMPORTANTE)

La app entrega dos valores:

    client_key      -> público, puede ir en el código
    client_secret   -> SECRETO

Guardar el secret en archivo, **nunca** pegarlo en un chat:

```bash
printf '%s' 'TU_CLIENT_SECRET' > ~/.tiktok_rock_factory_secret
chmod 600 ~/.tiktok_rock_factory_secret
```

---

## PASO 9 — Enviar a auditoría (solo Opción B)

Antes de enviar hay que tener construido y funcionando:
- [ ] Avatar y nombre del creador visibles antes de publicar
- [ ] Selector de privacidad con los valores de `privacy_level_options`
- [ ] Controles de duet / stitch / comentarios
- [ ] Toggle de divulgación de contenido comercial con el texto legal
- [ ] Sin marcas de agua, logos ni texto promocional añadido al video
- [ ] Video demo mostrando el flujo completo

La auditoría evalúa una app terminada, no un prototipo.

---

## URLS LEGALES (GitHub Pages)

Los documentos están en `docs/legal/rock-factory/`:
- `index.html`  → página de inicio de la app
- `terms.html`  → Términos de Servicio
- `privacy.html`→ Política de Privacidad
- `icon.png`    → icono 1024x1024

Una vez que el usuario active GitHub Pages en el repo (source: branch `main`, carpeta
`/docs` o `/root`), las URLs quedarán así (reemplazar `USUARIO` por el login de GitHub):

    https://USUARIO.github.io/Social_Media/legal/rock-factory/index.html
    https://USUARIO.github.io/Social_Media/legal/rock-factory/terms.html
    https://USUARIO.github.io/Social_Media/legal/rock-factory/privacy.html

> NOTA: el PAT fine-grained actual NO tiene permiso `pages:write` (403). La activación
> de GitHub Pages la hace el usuario en https://github.com/USUARIO/Social_Media/settings/pages
> O bien se rota el PAT para incluir el permiso. Mientras tanto, estas URLs NO resuelven.

---

## DATOS TÉCNICOS VERIFICADOS DE LA API

Host: `https://open.tiktokapis.com`

| Endpoint | Para qué |
|---|---|
| `POST /v2/post/publish/creator_info/query/` | Privacidad y ajustes del creador. **Obligatorio antes de cada post** |
| `POST /v2/video/upload/` | Sube video a borradores (Opción A, FILE_UPLOAD) |
| `POST /v2/post/publish/video/init/` | Inicia la publicación; devuelve `publish_id` (Opción B) |
| `POST /v2/post/publish/status/fetch/` | Poll hasta `PUBLISH_COMPLETE` |

- Publicación **asíncrona**: `init` devuelve un id, no un post publicado
- Caption: máximo 2.200 caracteres
- Rate limit: 6 requests/minuto por usuario
- Los access token caducan: hay que implementar refresh desde el inicio
- Tope diario de publicaciones por cuenta

### Errores frecuentes a evitar
1. Publicar sin consultar `creator_info` primero → request rechazado
2. Asumir visibilidad pública antes de la auditoría
3. Dejar el refresh de tokens para el final
4. Superar límites de tamaño/formato (el error se confunde con fallo de auth)

---

---

## ESQUEMA MULTI-CUENTA (1 app, 4 cuentas) — actualizado 2026-08-12

La app **"Rock Factory" es UNA sola** y su revisión de scopes
(`user.info.basic` + `video.upload`) autoriza a TODAS las cuentas del proyecto.
No se genera una app por canal. Cuentas ya creadas en TikTok (región Francia, SIM
+33) y listas para dar el consentimiento OAuth cuando la app esté aprobada:

| Canal (slug)         | Email de la cuenta TikTok        | Archivo de token (chmod 600)              |
|---|---|---|
| rock-factory         | rock.factory@outlook.com         | `~/.tiktok_rock_factory_token`           |
| cuentos-caricaturas  | retro.cartoon@outlook.com        | `~/.tiktok_retro_cartoon_token`          |
| insight-star         | insight.star@outlook.com         | `~/.tiktok_insight_star_token`           |
| ia-generativa-news   | generative.ai.news@outlook.com   | `~/.tiktok_generative_ai_news_token`     |

Flujo por cuenta (cuando la app esté aprobada):
1. Consentimiento OAuth de ESA cuenta con la app Rock Factory (mismo `client_key`).
2. El token resultante se guarda en su propio archivo (ruta arriba), chmod 600.
3. En sandbox se agregan las 4 como cuentas de prueba (el sandbox permite hasta 5;
   todo queda `SELF_ONLY` hasta que la app esté en producción).

Inicializar la estructura de tokens (crea los archivos vacíos con permisos
correctos; no sobrescribe los existentes):

    python3 scripts/token_setup.py            # crea los 4 archivos
    python3 scripts/token_setup.py --check    # lista cuáles ya existen

> PENDIENTE (no bloquea la espera de aprobación): `scripts/subir_tiktok.py` y
> `scripts/oauth_helper.py` hoy asumen UNA sola cuenta (hardcodean
> `~/.tiktok_rock_factory_token`). Al aprobarse la app hay que parametrizarlos
> con `--account <slug>` para leer el token de la cuenta correcta. VER tarea C.

---

## CHECKLIST PARA ENVIAR A REVIEW (faltantes al 2026-08-11)

- [ ] Description rellenado (mín. 120 chars) — texto en `scripts/legal_description.txt`
- [ ] Terms of Service URL — requiere GitHub Pages activo
- [ ] Privacy Policy URL — requiere GitHub Pages activo
- [ ] Producto Content Posting API agregado (Direct Post: OFF)
- [ ] Scopes `user.info.basic` + `video.upload` agregados
- [ ] Demo video subido mostrando flujo video.upload en sandbox

## Cronograma realista

| Opción | Tiempo hasta publicar en público |
|---|---|
| A (`video.upload`) | 1-3 días (solo registro) |
| B (`video.publish`) | 3-6 semanas (registro + UI + auditoría con rechazos) |
