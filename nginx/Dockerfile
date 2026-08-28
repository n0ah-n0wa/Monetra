# Monetra edge reverse proxy (TLS termination, non-root).
FROM nginxinc/nginx-unprivileged:1.27-alpine AS production

USER root

COPY nginx.prod.conf /etc/nginx/nginx.conf
COPY includes /etc/nginx/includes
COPY templates/default.conf.template /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.sh /usr/local/bin/monetra-nginx-entrypoint.sh

RUN apk add --no-cache su-exec \
    && chmod +x /usr/local/bin/monetra-nginx-entrypoint.sh \
    && mkdir -p /etc/nginx/certs /etc/nginx/certs-ro /etc/nginx/conf.d \
    && chown -R nginx:nginx /var/cache/nginx /var/log/nginx

ENTRYPOINT ["/usr/local/bin/monetra-nginx-entrypoint.sh"]

EXPOSE 8080 8443

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/nginx-health >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
