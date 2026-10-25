# syntax=docker/dockerfile:1
ARG NODE_IMAGE
ARG NGINX_IMAGE
FROM ${NODE_IMAGE} AS build
WORKDIR /workspace
COPY apps/admin/package.json apps/admin/package-lock.json ./
RUN npm ci --ignore-scripts
COPY apps/admin/ ./
# Catalog photographs and SuperSports branding are shared static assets.
COPY apps/storefront/public/ ./public/
RUN npm run build

FROM ${NGINX_IMAGE}
COPY devops/docker/storefront-entrypoint.sh /usr/local/bin/storefront-entrypoint
RUN chmod 0555 /usr/local/bin/storefront-entrypoint
COPY devops/nginx/admin.conf /etc/nginx/nginx.conf
COPY --from=build /workspace/dist /usr/share/nginx/html
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/healthz"]
ENTRYPOINT ["/usr/local/bin/storefront-entrypoint"]
