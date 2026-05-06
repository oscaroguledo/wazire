

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

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Application lifespan: perform startup and graceful shutdown tasks.

	This is an async context manager. It MUST `yield` to allow FastAPI to
	enter the application runtime; failing to yield causes the
	`'coroutine' object is not an async iterator` error.
	"""

	# Startup actions
	logger.info("Wazire backend starting up...")

	# Yield control to the application runtime
	yield

	# Shutdown actions
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
if settings.DEBUG:
	# Development: Allow all origins
	allowed_origins = ["*"]
else:
	# Production: Restrict to specific domains
	allowed_origins = [
		"https://wazire.com",
		"https://www.wazire.com",
		"http://localhost:5173",
		"http://localhost:5174",
		# Add your production frontend domains here
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
from routes.account import user, tenant
from routes.academic import submission, course, exam, question, answer, enrollments
from routes.analytics import dashboard
from routes import websocket
import uvicorn

# API Version 1
app.include_router(health, prefix="/api/v1")
app.include_router(websocket, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")
app.include_router(tenant.router, prefix="/api/v1")
app.include_router(submission.router, prefix="/api/v1/academic")
app.include_router(course.router, prefix="/api/v1/academic")
app.include_router(exam.router, prefix="/api/v1/academic")
app.include_router(question.router, prefix="/api/v1/academic")
app.include_router(answer.router, prefix="/api/v1/academic")
app.include_router(enrollments.router, prefix="/api/v1/academic")
app.include_router(dashboard.router, prefix="/api/v1/analytics")



if __name__ == "__main__":
	logger.info("Running via uvicorn entrypoint")
	uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
