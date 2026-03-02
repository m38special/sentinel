FROM python:3.11-slim

WORKDIR /app

# Install Flask and dependencies
RUN pip install --no-cache-dir flask redis

# Copy source
COPY . .

# Expose port
EXPOSE 5000

# Run the API server
CMD ["python3", "api_server.py"]
