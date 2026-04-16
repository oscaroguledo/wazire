#!/bin/bash

# Wazire Application Management Script
# Usage: ./start_app.sh [command] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
MODE="dev"
SEED=false
COMMAND=""
COMPOSE_FILE="docker-compose.yml"

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show usage
show_usage() {
    cat << EOF
Wazire Application Management Script

Usage: ./start_app.sh [COMMAND] [OPTIONS]

Commands:
  start           Start the application
  stop            Stop the application
  restart         Restart the application
  clear           Clear all containers and volumes
  logs            Show application logs
  status          Show container status
  seed            Seed the database
  migrate         Run database migrations
  migrate-create  Create a new migration
  migrate-rollback Rollback last migration

Options:
  -m, --mode      Set mode: dev (default) or prod
  -s, --seed      Seed the database when starting
  -h, --help      Show this help message

Examples:
  ./start_app.sh start                    # Start in dev mode without seeding
  ./start_app.sh start -m prod            # Start in prod mode
  ./start_app.sh start -s                 # Start in dev mode with seeding
  ./start_app.sh start -m prod -s         # Start in prod mode with seeding
  ./start_app.sh stop                     # Stop the application
  ./start_app.sh clear                    # Clear all containers and volumes
  ./start_app.sh seed                     # Seed the database only
  ./start_app.sh logs                     # Show logs
  ./start_app.sh status                   # Show container status
  ./start_app.sh migrate                  # Run database migrations
  ./start_app.sh migrate-create "msg"     # Create new migration with message
  ./start_app.sh migrate-rollback         # Rollback last migration

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        start|stop|restart|clear|logs|status|seed|migrate|migrate-create|migrate-rollback)
            COMMAND="$1"
            shift
            ;;
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -s|--seed)
            SEED=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# If no command specified, show usage
if [ -z "$COMMAND" ]; then
    print_info "No command specified. Showing usage..."
    show_usage
    exit 0
fi

# Validate mode
if [ "$MODE" != "dev" ] && [ "$MODE" != "prod" ]; then
    print_error "Invalid mode: $MODE. Must be 'dev' or 'prod'"
    exit 1
fi

# Set compose file based on mode
if [ "$MODE" = "prod" ]; then
    if [ -f "docker-compose.prod.yml" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
        print_info "Using production compose file: $COMPOSE_FILE"
    else
        print_warning "Production compose file not found, using default: $COMPOSE_FILE"
    fi
fi

# Check if docker-compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "Docker compose file not found: $COMPOSE_FILE"
    exit 1
fi

# Check if .env file exists for backend
if [ ! -f "backend/.env" ]; then
    print_warning "Backend .env file not found. Creating from .env.example..."
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        print_warning "Please update backend/.env with your configuration"
    else
        print_error "backend/.env.example not found"
        exit 1
    fi
fi

# Function to seed the database
seed_database() {
    print_info "Seeding database..."
    
    # Check if seed_db.py exists
    if [ ! -f "backend/seed_db.py" ]; then
        print_error "Seed script not found: backend/seed_db.py"
        return 1
    fi
    
    # Run seed script in backend container
    docker-compose -f $COMPOSE_FILE exec -T backend python seed_db.py
    
    if [ $? -eq 0 ]; then
        print_success "Database seeded successfully"
    else
        print_error "Database seeding failed"
        return 1
    fi
}

# Function to run migrations
run_migrations() {
    print_info "Running database migrations..."
    docker-compose -f $COMPOSE_FILE exec -T backend alembic upgrade head
    
    if [ $? -eq 0 ]; then
        print_success "Migrations completed successfully"
    else
        print_error "Migration failed"
        return 1
    fi
}

# Function to create migration
create_migration() {
    local message="$1"
    print_info "Creating migration: $message"
    docker-compose -f $COMPOSE_FILE exec -T backend alembic revision --autogenerate -m "$message"
    
    if [ $? -eq 0 ]; then
        print_success "Migration created successfully"
        print_info "Review the migration file, then run: ./start_app.sh migrate"
    else
        print_error "Migration creation failed"
        return 1
    fi
}

# Function to rollback migration
rollback_migration() {
    print_warning "Rolling back last migration..."
    docker-compose -f $COMPOSE_FILE exec -T backend alembic downgrade -1
    
    if [ $? -eq 0 ]; then
        print_success "Rollback completed successfully"
    else
        print_error "Rollback failed"
        return 1
    fi
}

# Execute commands based on command
case $COMMAND in
    start)
        print_info "Starting Wazire application in $MODE mode..."
        
        # Build and start containers
        docker-compose -f $COMPOSE_FILE up -d --build
        
        # Wait for services to be healthy
        print_info "Waiting for services to be healthy..."
        sleep 10
        
        # Show container status
        docker-compose -f $COMPOSE_FILE ps
        
        # Seed database if requested
        if [ "$SEED" = true ]; then
            print_info "Seeding database..."
            sleep 5
            seed_database
        fi
        
        print_success "Application started successfully!"
        print_info "Frontend: http://localhost:5173"
        print_info "Backend API: http://localhost:8000"
        print_info "API Docs: http://localhost:8000/docs"
        ;;
        
    stop)
        print_info "Stopping Wazire application..."
        docker-compose -f $COMPOSE_FILE down
        print_success "Application stopped successfully"
        ;;
        
    restart)
        print_info "Restarting Wazire application..."
        docker-compose -f $COMPOSE_FILE restart
        print_success "Application restarted successfully"
        ;;
        
    clear)
        print_warning "This will remove all containers, volumes, and data!"
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Clearing all containers and volumes..."
            docker-compose -f $COMPOSE_FILE down -v
            docker system prune -f
            print_success "All containers and volumes cleared"
        else
            print_info "Operation cancelled"
        fi
        ;;
        
    logs)
        print_info "Showing application logs (Ctrl+C to exit)..."
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
        
    status)
        print_info "Container status:"
        docker-compose -f $COMPOSE_FILE ps
        ;;
        
    seed)
        print_info "Seeding database..."
        seed_database
        ;;
        
    migrate)
        print_info "Running migrations..."
        run_migrations
        ;;
        
    migrate-create)
        if [ -z "$2" ]; then
            print_error "Please provide a migration message"
            print_info "Usage: ./start_app.sh migrate-create "your message""
            exit 1
        fi
        create_migration "$2"
        ;;
        
    migrate-rollback)
        rollback_migration
        ;;
        
    *)
        print_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac

exit 0
