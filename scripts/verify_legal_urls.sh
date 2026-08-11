#!/usr/bin/env bash
# Verifica que las URLs legales exigidas por TikTok esten publicas y correctas.
# Uso: bash scripts/verify_legal_urls.sh
set -uo pipefail

BASE="https://erick-zabala.github.io/Social_Media/legal"
URLS=(
  "$BASE/index.html"
  "$BASE/rock-legends-club/index.html"
  "$BASE/rock-legends-club/terms.html"
  "$BASE/rock-legends-club/privacy.html"
  "$BASE/rock-legends-club/icon.png"
)
fail=0

echo "== Verificando URLs legales publicas =="
for u in "${URLS[@]}"; do
  read -r code ctype size < <(curl -sL -o /tmp/_vl.out \
      -w "%{http_code} %{content_type} %{size_download}" "$u")
  if [ "$code" = "200" ]; then
    printf "  OK   %-3s %-9s %6sB  %s\n" "$code" "${ctype%%;*}" "$size" "${u#$BASE/}"
  else
    printf "  FAIL %-3s %s\n" "$code" "${u#$BASE/}"
    fail=1
  fi
done

echo
echo "== Contenido esperado en las paginas =="
check_text() {  # url, texto, etiqueta
  if curl -sL "$1" | grep -qi -- "$2"; then
    echo "  OK   $3"
  else
    echo "  FAIL $3  (no se encontro: $2)"
    fail=1
  fi
}
check_text "$BASE/rock-legends-club/terms.html"   "Términos de Servicio"      "terms: titulo correcto"
check_text "$BASE/rock-legends-club/terms.html"   "video.upload\|borradores"  "terms: menciona borradores"
check_text "$BASE/rock-legends-club/privacy.html" "Política de Privacidad"    "privacy: titulo correcto"
check_text "$BASE/rock-legends-club/privacy.html" "user.info.basic"           "privacy: declara el scope"
check_text "$BASE/rock-legends-club/privacy.html" "rocklegendsclub@gmail.com" "privacy: email de contacto"

echo
if [ "$fail" -eq 0 ]; then
  echo "RESULTADO: todas las URLs responden 200 y el contenido es el esperado."
  echo
  echo "Pegar en el formulario de TikTok:"
  echo "  Terms of Service URL: $BASE/rock-legends-club/terms.html"
  echo "  Privacy Policy URL:   $BASE/rock-legends-club/privacy.html"
else
  echo "RESULTADO: HAY FALLOS. Si todo da 404, Pages todavia no termino de desplegar"
  echo "(tarda 1-2 min) o la carpeta configurada no es /docs."
fi
exit $fail
