FROM node:22-alpine AS build

WORKDIR /app
COPY apps/dashboard/package.json ./
RUN npm install
COPY apps/dashboard ./
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
