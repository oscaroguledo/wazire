# Wazire Backend Setup

## Docker Compose (Recommended)

From the repository root, run:
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)

docker compose down --rmi all --volumes
docker builder prune -a

docker compose build postgres redis
docker compose up -d postgres redis
docker compose ps
docker logs postgres
docker logs redis

docker compose build backend
docker compose up -d backend
docker compose ps
docker logs backend

docker compose build celery-worker
docker compose up celery-worker
docker compose ps
docker logs celery-worker


docker compose build celery-beat
docker compose up celery-beat
docker compose ps
docker logs celery-beat

docker compose build frontend
docker compose up frontend
docker compose ps
docker logs frontend




# exit
Ctrl + D
<!-- docker exec -it postgres sh  -->
<!-- docker compose exec backend sh -->

alembic revision --autogenerate -m "init db"
alembic upgrade head

docker compose up -d backend celery-worker celery-beat frontend
