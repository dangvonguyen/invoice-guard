FROM node:24-alpine

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

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0"]
