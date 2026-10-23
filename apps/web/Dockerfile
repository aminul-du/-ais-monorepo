FROM node:20-alpine AS builder
WORKDIR /repo
RUN apk add --no-cache libc6-compat

# Copy the whole monorepo structure the build needs
# (turbopack.root = /repo, so all packages/ must be visible)
COPY apps/web/package*.json ./apps/web/
COPY packages/design-system/package.json ./packages/design-system/
COPY packages/design-system/src ./packages/design-system/src

WORKDIR /repo/apps/web
RUN npm install --no-audit --no-fund

WORKDIR /repo
COPY apps/web ./apps/web

WORKDIR /repo/apps/web
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -S app && adduser -S app -G app
COPY --from=builder --chown=app:app /repo/apps/web/.next/standalone ./
COPY --from=builder --chown=app:app /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=app:app /repo/apps/web/public ./apps/web/public
USER app
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
