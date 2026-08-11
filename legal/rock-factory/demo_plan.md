# Demo video para el review de TikTok — Rock Factory (Opción A)

TikTok exige: "Upload at least one demo video that shows the complete end-to-end flow
of the integration with TikTok." Formato mp4/mov, <50 MB, sin marcas de agua ajenas.

Requisito clave de TikTok para apps NO aprobadas:
"If your app has not been approved before, you are required to use a sandbox environment
on the Developer Portal to demonstrate the integration."

=> El demo se graba en MODO SANDBOX y debe mostrar CLARAMENTE:
1. El dominio de la web `ERICK-ZABALA.github.io` en la barra de direcciones.
2. Los productos Login Kit + Content Posting API y los scopes `user.info.basic` + `video.upload`.
3. El flujo OAuth real: login -> pantalla de consentimiento con `video.upload` visible -> Allow.
4. La app de TikTok con la cuenta de sandbox (`rock.factory0`, privada).
5. Interaccion real (clics), no solo texto.

NOTA TECNICA (verificada 2026-08-11): el sandbox de TikTok NO concede el scope
`video.upload` a cuentas de prueba hasta que la app pasa review, por lo que la
subida real a borradores devuelve 401 scope_not_authorized. Eso NO impide el review:
TikTok pide mostrar el flujo en sandbox, y el flujo OAuth + consentimiento YA es la
evidencia end-to-end. No hace falta una subida exitosa para enviar a review.

---

## GUION (grabar en Windows, 1:30 – 2:30 min)

### 0:00 – 0:15  |  La web oficial
- Abrir navegador y cargar:
  https://erick-zabala.github.io/Social_Media/legal/rock-factory/index.html
- Mostrar la barra de direcciones con `ERICK-ZABALA.github.io` bien visible.
- Decir: "Esta es la web oficial de Rock Factory, app registrada en TikTok for Developers."

### 0:15 – 0:45  |  Productos y scopes (portal de TikTok)
- En developers.tiktok.com -> app "Rock Factory" -> mostrar:
  - Login Kit activado, Redirect URI apuntando al tunel https del server.
  - Content Posting API, Direct Post: OFF (sube a borradores, el titular publica despues).
  - Scopes: `user.info.basic`, `video.upload`.
  - Sandbox -> Target User: `rock.factory0` agregado.
- Esto prueba que los productos/scopes estan configurados en sandbox.

### 0:45 – 1:30  |  Flujo OAuth real (lo que logramos)
- Mostrar en la VM (o grabar la pantalla de la sesion) el script:
  python3 scripts/oauth_helper.py --redirect-uri https://TU-TUNEL/callback
- Mostrar la pantalla de autorizacion de TikTok y la pantalla de consentimiento donde
  aparecen los dos scopes:
    - "Access your profile info (avatar and display name)"  (= user.info.basic)
    - "Upload draft content to TikTok for further editing"  (= video.upload)
- Mostrar que diste Allow y la pagina "Autorizacion capturada".
- Mostrar el token guardado (sin revelar el secreto) en ~/.tiktok_rock_factory_token.
- Esto ES el flujo end-to-end: Login Kit -> consentimiento -> token con video.upload.

### 1:30 – 1:45  |  La app de TikTok (cuenta sandbox)
- Abrir la app de TikTok en el celular con la cuenta `rock.factory0` (debe estar PRIVADA).
- Mostrar que es la cuenta de sandbox autorizada para Rock Factory.
- Decir: "El titular publica manualmente desde TikTok y elige la musica; la app solo
  prepara el borrador."

### 1:45 – 2:00  |  Cierre
- Volver a la web github.io y recalcar: dominio verificado, flujo de sandbox completo.

---

## Requisitos tecnicos (para reproducir el flujo)
- Tunel cloudflared en la VM:  cloudflared tunnel --url http://localhost:8080
  (la URL cambia al reiniciar; debe coincidir con el Redirect URI del portal).
- Credenciales en la VM: ~/.tiktok_rock_factory_key y ~/.tiktok_rock_factory_secret (chmod 600).
- Cuenta de sandbox: agregada por su @handle (rock.factory0), NO por email.
- La cuenta de TikTok debe estar en PRIVADO para que el sandbox acepte subidas.
- El consentimiento de video.upload se ve en la pantalla "Rock Factory (Sandbox) would like to".
- Bugs conocidos del script (no bloquean el demo):
  * oauth_helper.py no escribe el token si TikTok lo devuelve en la raiz (no en "data");
    se escribe manualmente desde /tmp/tiktok_exchange_raw.json.
  * subir_tiktok.py hace creator_info/query como paso previo, que en sandbox da 401;
    el flujo de borradores real usa video/init + video/upload.
