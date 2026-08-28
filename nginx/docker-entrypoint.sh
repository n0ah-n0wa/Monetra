#!/bin/sh
set -eu

if [ -d /etc/nginx/certs-ro ]; then
  mkdir -p /etc/nginx/certs
  copied=0
  for cert in /etc/nginx/certs-ro/*.pem; do
    [ -e "$cert" ] || continue
    cp "$cert" /etc/nginx/certs/
    copied=1
  done
  if [ "$copied" -eq 0 ]; then
    echo "ERROR: No TLS certificates found in /etc/nginx/certs-ro" >&2
    exit 1
  fi
  chown -R nginx:nginx /etc/nginx/certs
  chmod 644 /etc/nginx/certs/fullchain.pem
  chmod 640 /etc/nginx/certs/privkey.pem
fi

if [ ! -f /etc/nginx/certs/fullchain.pem ] || [ ! -f /etc/nginx/certs/privkey.pem ]; then
  echo "ERROR: TLS certificate or private key missing after startup copy" >&2
  exit 1
fi

export NGINX_SERVER_NAME="${NGINX_SERVER_NAME:-_}"
export NGINX_CLIENT_MAX_BODY_SIZE="${NGINX_CLIENT_MAX_BODY_SIZE:-10m}"
export NGINX_HSTS_MAX_AGE="${NGINX_HSTS_MAX_AGE:-31536000}"
if [ -z "${NGINX_CSP:-}" ]; then
  NGINX_CSP="default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'"
fi
export NGINX_CSP

if [ -n "$NGINX_HSTS_MAX_AGE" ] && [ "$NGINX_HSTS_MAX_AGE" != "0" ]; then
  export NGINX_HSTS_DIRECTIVE="add_header Strict-Transport-Security \"max-age=${NGINX_HSTS_MAX_AGE}; includeSubDomains\" always;"
else
  export NGINX_HSTS_DIRECTIVE=""
fi

if [ -f /etc/nginx/templates/default.conf.template ]; then
  envsubst '${NGINX_SERVER_NAME} ${NGINX_CLIENT_MAX_BODY_SIZE} ${NGINX_HSTS_DIRECTIVE} ${NGINX_CSP}' \
    < /etc/nginx/templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf
fi

chown -R nginx:nginx /var/cache/nginx /var/log/nginx /var/run 2>/dev/null || true

exec su-exec nginx /docker-entrypoint.sh "$@"
