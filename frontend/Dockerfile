FROM node:24-alpine AS base

WORKDIR /app

ENV PNPM_HOME="/pnpm" \
    PATH="$PNPM_HOME:$PATH"

RUN corepack enable

RUN pnpm config set store-dir /pnpm/store

ENV CI=true

COPY package.json pnpm-lock.yaml ./

RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm install --frozen-lockfile --dangerously-allow-all-builds

COPY . .

FROM base AS dev

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0"]

FROM base AS builder

ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

RUN pnpm build

FROM nginx:1.27-alpine AS prod

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
