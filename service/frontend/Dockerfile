FROM node:20-alpine

WORKDIR /app/frontend

# Set environment to development
ENV NODE_ENV=development

# Copy frontend package files
COPY src/package*.json ./

# Install all dependencies (including devDependencies)
RUN npm install

# Copy all frontend source files
COPY src/ ./

# Copy dev entrypoint script
COPY docker-entrypoint-dev.sh /docker-entrypoint-dev.sh
RUN chmod +x /docker-entrypoint-dev.sh

# Expose Vite dev server port
EXPOSE 5173

# Use entrypoint that auto-reinstalls deps when package-lock.json changes
ENTRYPOINT ["/docker-entrypoint-dev.sh"]
