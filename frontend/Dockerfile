# Build stage
FROM node:20-alpine as build

WORKDIR /app

ARG VITE_WS_URL
ARG VITE_BACKEND_URL
ENV VITE_WS_URL=${VITE_WS_URL}
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]