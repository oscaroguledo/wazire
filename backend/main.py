

# Import all models first to prevent circular dependency errors
# This ensures all model classes are available before SQLAlchemy configures mappers
import models

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import get_settings
from core.database import close_db
from core.utils.logger import logger
from core.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from core.middleware.error_handler import setup_error_handlers
from slowapi.errors import RateLimitExceeded
from core.utils.kafka import producer_service
from core.kafka_manager import kafka_manager

settings = get_settings()

# Apply LOG_LEVEL from settings to the root logger and our app logger
import logging as _logging
_logging.basicConfig(level=getattr(_logging, settings.LOG_LEVEL, _logging.INFO))
logger.setLevel(getattr(_logging, settings.LOG_LEVEL, _logging.INFO))

@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Application lifespan: perform startup and graceful shutdown tasks.

	This is an async context manager. It MUST `yield` to allow FastAPI to
	enter the application runtime; failing to yield causes the
	`'coroutine' object is not an async iterator` error.
	"""

	# Startup actions
	logger.info("Wazire backend starting up...")

	# Start pooled Kafka producer (used by tasks/dispatcher)
	try:
		await producer_service.start()
		# Bind kafka_manager to the now-started producer
		kafka_manager._producer = producer_service
	except Exception:
		logger.exception("Failed to start Kafka producer")

	# Yield to enter the application runtime — FastAPI serves requests from here
	yield

	# Shutdown actions (run only when the application is stopping)
	logger.info("Stopping Kafka producer...")
	
	try:
		await producer_service.stop()
	except Exception:
		logger.exception("Error stopping Kafka producer")

	logger.info("Closing database connections...")
	await close_db()
	logger.info("Wazire backend has been shut down.")


app = FastAPI(
	title="Wazire Backend",
	description="Academic assessment and examination management system API",
	version="1.0.0",
	lifespan=lifespan,
	docs_url="/api/v1/docs",
	redoc_url="/api/v1/redoc",
	openapi_url="/api/v1/openapi.json"
)

# Setup error handlers
setup_error_handlers(app)

# Add rate limit exception handler
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# Configure CORS based on environment
if settings.FRONTEND_ORIGIN:
	# Explicit FRONTEND_ORIGIN env var takes precedence (production-safe)
	allowed_origins = [settings.FRONTEND_ORIGIN]
elif settings.DEBUG:
	# Development: Allow all origins
	allowed_origins = ["*"]
else:
	# Production fallback: use CORS_ORIGINS list from settings
	allowed_origins = settings.cors_origins_list() or [
		"https://wazire.com",
		"https://www.wazire.com",
	]

app.add_middleware(
	CORSMiddleware,
	allow_origins=allowed_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Request ID middleware moved to core.middleware for reuse and clarity
from core.middleware.request_id import RequestIDMiddleware
from core.middleware.tenant import TenantMiddleware
from core.middleware.timing import TimingMiddleware

app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TenantMiddleware)

# Register routers
from routes import health
from routes.account import users, tenants
from routes.academic import submissions, courses, exams, questions, answers, enrollments
from routes.analytics import dashboard
from routes.billings import invoice as billings_invoice
import uvicorn

# API Version 1
app.include_router(health, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(tenants.router, prefix="/api/v1")
app.include_router(submissions.router, prefix="/api/v1/academic")
app.include_router(courses.router, prefix="/api/v1/academic")
app.include_router(exams.router, prefix="/api/v1/academic")
app.include_router(questions.router, prefix="/api/v1/academic")
app.include_router(answers.router, prefix="/api/v1/academic")
app.include_router(enrollments.router, prefix="/api/v1/academic")
app.include_router(dashboard.router, prefix="/api/v1/analytics")

# Billings routes
app.include_router(billings_invoice.router, prefix="/api/v1")



if __name__ == "__main__":
	logger.info("Running via uvicorn entrypoint")
	uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
