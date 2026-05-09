FROM node:24-alpine

WORKDIR /app

COPY server.js app.js index.html styles.css README.md ./
COPY assets ./assets

RUN mkdir -p /app/photos

ENV PORT=4173
EXPOSE 4173

CMD ["node", "server.js"]
