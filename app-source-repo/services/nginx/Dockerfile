# Stage 1: Syntax & Configuration Validation Gate
FROM nginx:1.27-alpine AS validator

WORKDIR /etc/nginx

COPY conf.d/default.conf /etc/nginx/conf.d/default.conf

# Sanity Gate: Test Nginx configuration validity
RUN nginx -t && echo ">> [CI-SANITY] Nginx configuration test passed."

# Stage 2: Production Runtime
FROM nginx:1.27-alpine AS runtime

COPY conf.d/default.conf /etc/nginx/conf.d/default.conf
COPY html/ /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
    CMD wget -qO- http://localhost/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
