FROM node:20-slim AS build
WORKDIR /srv
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# NEXT_PUBLIC_* values are inlined at build time, so the API URL must be a build argument
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-slim
WORKDIR /srv
ENV NODE_ENV=production
COPY --from=build /srv ./
EXPOSE 3000
CMD ["npm", "start"]
