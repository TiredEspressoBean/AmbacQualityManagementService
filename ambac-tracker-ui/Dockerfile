FROM node:20-alpine

WORKDIR /app

# Copy and install dependencies
COPY ./package*.json ./
RUN npm install

# Copy rest of the frontend source
COPY . .

# Declare a build argument for Vite
ARG VITE_API_TARGET
ENV VITE_API_TARGET=$VITE_API_TARGET

# 👉 Build the app for production
RUN npm run build

# Expose Vite preview server
EXPOSE 5173

# Start the preview server for the built output
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
