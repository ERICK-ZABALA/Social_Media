# Registro de la app en developers.tiktok.com — Music Rock

Fuente: docs oficiales de TikTok for Developers + guías 2026 (verificado 2026-08-11).
Toda la información de la API fue contrastada; los límites de TikTok cambian, así que
la fuente de verdad final siempre es https://developers.tiktok.com

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

---

## PASO 0 — Requisitos previos

1. Cuenta de TikTok **real** para el canal (`Rock Legends`), creada desde la app del
   celular y con algunos videos ya publicados. Las cuentas vacías levantan sospecha
   en la auditoría.
2. Email de contacto: `rock.legends.club@gmail.com` con 2FA activo.
3. Nombre y logo del canal listos.

---

## PASO 1 — Crear la cuenta de developer

1. Ir a https://developers.tiktok.com
2. **Log in** con la cuenta de TikTok de Rock Legends (no con Gmail).
3. Aceptar los Developer Terms.
4. Verificar el email.

---

## PASO 2 — Registrar la app

1. https://developers.tiktok.com/apps → **Connect an app** / **Create an app**
2. Completar:

   | Campo | Valor sugerido |
   |---|---|
   | App name | `Rock Legends Publisher` |
   | Description | Herramienta interna de programación y publicación de contenido original sobre historia y cultura del rock para el canal Rock Legends. |
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

---

## PASO 4 — Configurar scopes

En **Manage apps → Scopes**, agregar:

    user.info.basic        (obligatorio siempre)
    video.upload           (Opción A)
    video.publish          (Opción B — solo si vas por auditoría completa)

Pedir solo lo que se usa. Scopes de más = más motivos de rechazo.

---

## PASO 5 — Redirect URI de OAuth

En **Login Kit** configurar el redirect URI. Para desarrollo local:

    http://localhost:8080/callback

Debe coincidir **carácter por carácter** con el que use el código, o el OAuth falla
con `redirect_uri_mismatch`.

---

## PASO 6 — Verificación de dominio (solo si usás PULL_FROM_URL)

Necesaria únicamente si TikTok descarga el video desde una URL tuya.
Si subimos los bytes con `FILE_UPLOAD`, **este paso no aplica**.

1. **Manage apps → URL properties → Verify**
2. Descargar el archivo `tiktok-developers-site-verification.txt`
3. Publicarlo en la raíz del dominio
4. Confirmar

Como no tenemos dominio propio todavía, el plan es **FILE_UPLOAD** y saltear esto.

---

## PASO 7 — Sandbox

1. **Add a sandbox** (hasta 5 por app)
2. Autorizar la cuenta de TikTok de Rock Legends como cuenta de prueba

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
printf '%s' 'TU_CLIENT_SECRET' > ~/.tiktok_rock_secret
chmod 600 ~/.tiktok_rock_secret
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

## Datos técnicos verificados de la API

Host: `https://open.tiktokapis.com`

| Endpoint | Para qué |
|---|---|
| `POST /v2/post/publish/creator_info/query/` | Privacidad y ajustes del creador. **Obligatorio antes de cada post** |
| `POST /v2/post/publish/video/init/` | Inicia la publicación; devuelve `publish_id` |
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

## Cronograma realista

| Opción | Tiempo hasta publicar en público |
|---|---|
| A (`video.upload`) | 1-3 días (solo registro) |
| B (`video.publish`) | 3-6 semanas (registro + UI + auditoría con rechazos) |
