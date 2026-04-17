# Docker Setup & Migration Guide

This guide covers how to use Docker with the Wazire application, including container management and database migrations.

## Prerequisites

- Docker and Docker Compose installed
- Backend `.env` file configured (copy from `.env.example`)

## Quick Start

```bash
# Start the application in development mode
./start_app.sh start

# Start with database seeding
./start_app.sh start -s

# Start in production mode
./start_app.sh start -m prod
```

## Application Management Script (`start_app.sh`)

The `start_app.sh` script provides a convenient interface for managing the entire application stack.

### Available Commands

#### `start`
Start the application containers.

```bash
./start_app.sh start                    # Start in dev mode
./start_app.sh start -m prod            # Start in prod mode
./start_app.sh start -s                 # Start with database seeding
./start_app.sh start -m prod -s         # Start in prod mode with seeding
```

#### `stop`
Stop all application containers.

```bash
./start_app.sh stop
```

#### `restart`
Restart all application containers.

```bash
./start_app.sh restart
```

#### `clear`
Remove all containers, volumes, and data. **Warning: This deletes all data!**

```bash
./start_app.sh clear
```

#### `logs`
View application logs in real-time (press Ctrl+C to exit).

```bash
./start_app.sh logs
```

#### `status`
Show the status of all containers.

```bash
./start_app.sh status
```

#### `seed`
Seed the database with initial data.

```bash
./start_app.sh seed
```

#### `migrate`
Run pending database migrations.

```bash
./start_app.sh migrate
```

#### `migrate-create`
Create a new migration file.

```bash
./start_app.sh migrate-create "your migration message"
```

#### `migrate-rollback`
Rollback the last migration.

```bash
./start_app.sh migrate-rollback
```

### Options

- `-m, --mode`: Set mode to `dev` (default) or `prod`
- `-s, --seed`: Seed the database when starting
- `-h, --help`: Show help message

## Database Migrations

### Migration Workflow

1. **Make code changes** to your models in `backend/models/`
2. **Generate migration** (requires containers to be running):

```bash
# Start containers if not running
./start_app.sh start

# Create migration
./start_app.sh migrate-create "add user phone number field"
```

3. **Review the generated migration file** in `backend/alembic/versions/`
4. **Apply the migration**:

```bash
./start_app.sh migrate
```

### Migration Commands

#### Run Migrations
Apply all pending migrations to bring the database up to date.

```bash
./start_app.sh migrate
```

Or manually using Docker Compose:

```bash
docker-compose exec backend alembic upgrade head
```

#### Create Migration
Generate a new migration based on model changes.

```bash
./start_app.sh migrate-create "description of changes"
```

Or manually:

```bash
docker-compose exec backend alembic revision --autogenerate -m "description"
```

#### Rollback Migration
Undo the last migration.

```bash
./start_app.sh migrate-rollback
```

Or manually:

```bash
docker-compose exec backend alembic downgrade -1
```

#### View Migration History
See all migrations and their order.

```bash
docker-compose exec backend alembic history
```

#### View Current Migration
Check which migration is currently applied.

```bash
docker-compose exec backend alembic current
```

## Development Workflow

### Typical Development Session

```bash
# 1. Start the application
./start_app.sh start

# 2. Make code changes to models or business logic

# 3. If model changes, create migration
./start_app.sh migrate-create "init db"

# 4. Review and apply migration
./start_app.sh migrate

# 5. Test changes

# 6. View logs if needed
./start_app.sh logs

# 7. Stop when done
./start_app.sh stop
```

### Without Automatic Migrations

The Dockerfile is configured to **only run the application**, not migrations. This gives you control over when migrations are applied. You must manually run migrations after model changes.

## Container Architecture

The application consists of the following containers:

- **postgres**: PostgreSQL database (port 5432)
- **redis**: Redis cache (port 6379)
- **backend**: FastAPI backend (port 8000)
- **celery-worker**: Background task processor
- **celery-beat**: Scheduled task scheduler
- **frontend**: React frontend (port 5173)

## Environment Variables

Configure the following in `backend/.env`:

```bash
# Database
POSTGRES_DB=wazire
POSTGRES_USER=wazire
POSTGRES_PASSWORD=your_password
POSTGRES_PORT=5432

# Redis
REDIS_PASSWORD=
REDIS_PORT=6379

# Application
BACKEND_PORT=8000
FRONTEND_PORT=5173

# API Keys
GROQ_API_KEY=your_api_key
```

## Access Points

After starting the application:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **Health Check**: http://localhost:8000/health

## Troubleshooting

### Containers won't start
```bash
# Check container status
./start_app.sh status

# View logs
./start_app.sh logs

# Restart containers
./start_app.sh restart
```

### Database connection issues
```bash
# Check if postgres is healthy
docker-compose ps postgres

# View postgres logs
docker-compose logs postgres

# Clear and restart (WARNING: deletes data)
./start_app.sh clear
./start_app.sh start
```

### Migration errors
```bash
# Check current migration version
docker-compose exec backend alembic current

# View migration history
docker-compose exec backend alembic history

# Force specific migration (use with caution)
docker-compose exec backend alembic upgrade <revision_id>
```

### Permission issues with .env file
```bash
# Ensure .env file exists
ls -la backend/.env

# Copy from example if missing
cp backend/.env.example backend/.env
```

## Production Deployment

For production deployment:

1. Create a production docker-compose file (`docker-compose.prod.yml`)
2. Use production environment variables
3. Start with production mode:

```bash
./start_app.sh start -m prod
```

The script will automatically use `docker-compose.prod.yml` if it exists.

## Health Checks

The backend includes a health check endpoint:

```bash
curl http://localhost:8000/health
```

Docker Compose includes health checks for postgres and redis to ensure services are ready before dependent services start.

## Data Persistence

PostgreSQL and Redis data are persisted in Docker volumes:
- `postgres_data`: PostgreSQL database files
- `redis_data`: Redis data

Use `./start_app.sh clear` to remove volumes (WARNING: deletes all data).

## Security Notes

- The application runs as a non-root user in containers
- Database passwords should be set in environment variables
- API keys should not be committed to version control
- Use `.gitignore` to exclude `.env` files
