# MAKROskop — static SvelteKit site served by nginx.
# Build context is the repo root; only app/ is needed (data JSON is committed in app/static/data).
# Dokploy: build type Dockerfile, container port 80, health check path /.

FROM oven/bun:1 AS build
WORKDIR /app
COPY app/package.json app/bun.lock ./
RUN bun install --frozen-lockfile
COPY app/ ./
# Optional: Dokploy build arg APP_COMMIT=<sha> stamps the footer; omitted → date only.
ARG APP_COMMIT=""
ENV APP_COMMIT=$APP_COMMIT
RUN bun run build

FROM nginx:alpine
COPY app/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
CMD ["nginx", "-g", "daemon off;"]
