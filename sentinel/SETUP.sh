# SENTINEL Docker Setup (v2.1)
# Run this on your production server

cd sentinel

# Build and start all services
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f sentinel
docker-compose logs -f celery-worker

# With monitoring (Flower UI)
docker-compose --profile monitoring up -d

# Stop all
docker-compose down
