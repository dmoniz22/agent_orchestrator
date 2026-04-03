FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY frontend/package.json ./

# Install dependencies
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Copy env file - use localhost for development outside Docker network
# For production/Docker networking, override with http://backend:8000
COPY frontend/.env.local ./.env.local

# Expose port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev"]