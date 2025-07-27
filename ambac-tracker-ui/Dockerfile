FROM node:20-alpine

WORKDIR /app

# Copy and install dependencies
COPY ./package*.json ./
RUN npm install

# Copy rest of the frontend source
COPY . .

# Declare a build argument
ARG VITE_API_TARGET

# Expose it to the build process as an environment variable
ENV VITE_API_TARGET=$VITE_API_TARGET

# Serve with Vite's preview server (handles SPA routing automatically)
EXPOSE 5173
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]