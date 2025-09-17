# Build frontend
FROM node:20-alpine AS build
WORKDIR /app
# Prefer pnpm if lockfile exists, fall back to npm
COPY frontend/package.json ./package.json
# Copy whichever lockfile exists (pnpm or npm)
# Using npm ci by default; if you later switch to pnpm, update this stage accordingly
COPY frontend/package-lock.json ./package-lock.json
RUN npm ci
COPY frontend/ ./
# Allow overriding API base at build time; default to /api
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

# Runtime
FROM nginx:1.27-alpine
COPY --from=build /app/dist/ /usr/share/nginx/html/
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
