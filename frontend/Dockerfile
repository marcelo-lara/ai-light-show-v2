FROM denoland/deno:2.2.5

WORKDIR /app

COPY . .

RUN deno cache dev.ts

EXPOSE 5173

CMD ["deno", "task", "dev"]