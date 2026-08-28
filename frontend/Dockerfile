# syntax=docker/dockerfile:1
# Production frontend image. Development uses the Compose node service.

FROM node:22-bookworm-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-fund --no-audit

COPY . .
RUN npm run build

# Official unprivileged nginx image (runs as uid 101, listens on 8080).
FROM nginxinc/nginx-unprivileged:1.27-alpine AS production

COPY --chown=nginx:nginx --from=build /app/dist /usr/share/nginx/html
COPY nginx.frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
