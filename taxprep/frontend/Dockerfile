FROM node:20-slim AS build
WORKDIR /srv
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build
FROM node:20-slim
WORKDIR /srv
COPY --from=build /srv ./
EXPOSE 3000
CMD ["npm", "start"]
