FROM node:22-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS build
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
ARG BACKEND_URL=http://app:3000
ENV BACKEND_URL=$BACKEND_URL NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3100 BACKEND_URL=http://app:3000
RUN addgroup -S isms && adduser -S isms -G isms
COPY --from=build --chown=isms:isms /app/.next/standalone ./
COPY --from=build --chown=isms:isms /app/.next/static ./.next/static
COPY --from=build --chown=isms:isms /app/public ./public
USER isms
EXPOSE 3100
CMD ["node", "server.js"]
