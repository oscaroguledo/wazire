# Stage 1: Build static assets
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Copy dist to a shared volume for nginx to serve
FROM alpine:3.19

WORKDIR /dist

COPY --from=builder /app/dist .

# Copy built assets to /output (mounted as the frontend_dist named volume)
CMD ["sh", "-c", "cp -r /dist/. /output/ && echo 'Frontend assets copied successfully'"]
