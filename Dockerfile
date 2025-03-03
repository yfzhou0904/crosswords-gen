# Use Python 3.12 as base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install Node.js and npm for Svelte frontend build
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend files
COPY frontend/package.json frontend/package-lock.json ./frontend/
WORKDIR /app/frontend
RUN npm ci

# Copy the rest of the frontend code and build it
COPY frontend ./
RUN npm run build

# Go back to app directory and copy the rest of the application
WORKDIR /app
COPY generator.py pdf.py web.py templates ./
COPY config.example.toml ./

# Create output directory with proper permissions
RUN mkdir -p output && chmod 777 output

# Expose the port the app runs on
EXPOSE 80

# Create a volume mount point for config
VOLUME ["/app/config"]

# Command to run the application
CMD ["python", "web.py"]
