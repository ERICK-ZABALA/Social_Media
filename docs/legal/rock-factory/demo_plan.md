# Demo video para el review de TikTok — Rock Factory (Opción A)

TikTok exige: "Upload at least one demo video that shows the complete end-to-end flow
of the integration with TikTok." Formato mp4/mov, <50 MB, sin marcas de agua ajenas.

El demo debe mostrar CLARAMENTE:
1. El dominio `ERICK-ZABALA.github.io` en la barra de direcciones.
2. El flujo Login Kit -> autorizacion -> video.upload a borradores.
3. Los scopes `user.info.basic` y `video.upload`.
4. Interaccion real (clics), no solo texto.

---

## GUION (grabar en Windows, 1:30 – 2:30 min)

### 0:00 – 0:15  |  La web oficial
- Abrir navegador y cargar:
  https://erick-zabala.github.io/Social_Media/legal/rock-factory/index.html
- Mostrar la barra de direcciones con `ERICK-ZABALA.github.io` bien visible.
- Decir: "Esta es la web oficial de Rock Factory, app registrada en TikTok for Developers."

### 0:15 – 0:45  |  Productos y scopes (en el portal)
- En developers.tiktok.com -> app "Rock Factory" -> mostrar:
  - Login Kit activado.
  - Content Posting API, Direct Post: OFF (sube a borradores).
  - Scopes: `user.info.basic`, `video.upload`.
- Esto prueba que los productos/scopes estan configurados.

### 0:45 – 1:30  |  Flujo de carga a borradores
- Mostrar la terminal de la VM corriendo:
  python3 scripts/subir_tiktok.py --video channels/reflexiones/media/dia_001.mp4 --caption "Celebra la vida - Reflexiones"
- Mostrar la salida: consulta de `creator_info` (cuenta destino) y el `video.upload` a borradores.
- Abrir la app de TikTok en el celular y mostrar el borrador apareciendo en "Borradores".
  (Clave: prueba que sube a borradores, NO publica solo.)

### 1:30 – 1:45  |  Cierre
- Volver a la web github.io y decir: "El titular publica manualmente desde TikTok y elige la musica."

---

## MODO A — flujo REAL (recomendado)
1. En la VM, correr:  python3 scripts/oauth_helper.py --redirect-uri https://TU-TUNEL/callback
   (el tunel cloudflared ya esta activo apuntando a localhost:8080 de la VM).
2. Se abre la pantalla de autorizacion de TikTok -> VOS autorizas con la cuenta del canal.
3. El script guarda token fresco en ~/.tiktok_rock_factory_token.
4. Yo ejecuto la subida real -> el borrador queda en tu TikTok.
5. Vos solo grabás el borrador ya apareciendo + la web.

## MODO B — sin token fresco
Si no podes autorizar ahora, el demo igual pasa: mostra los scripts corriendo en la VM
(con salida de ejemplo) + la web + la app de TikTok. Usa una cuenta sandbox en el portal
si es posible. TikTok acepta demos que muestran la UI y el flujo completo.

---

## Requisitos tecnicos
- Tunel cloudflared activo en la VM:  cloudflared tunnel --url http://localhost:8080
- Redirect URI en el portal debe ser exactamente la URL https del tunel + /callback.
- El video se sube por FILE_UPLOAD (bytes del servidor); no requiere verificacion de dominio.
- La musica NO se incrusta: se elige en TikTok al publicar.
