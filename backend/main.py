

# Import all models first to prevent circular dependency errors
# This ensures all model classes are available before SQLAlchemy configures mappers
import models

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import Settings
from core.database import close_db
from core.utils.logger import logger
from core.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from core.middleware.error_handler import setup_error_handlers
from slowapi.errors import RateLimitExceeded
from services.engine import start_scheduler

settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
	scheduler = None
	try:
		# Start scheduler background task for exam and other periodic tasks
		logger.info("Starting scheduler for exam etc...")
		scheduler = await start_scheduler(default_interval=60)
		logger.info("Scheduler started.")
	except Exception as e:
		logger.error(f"Startup failed: {e}")
		raise

	yield

	# Shutdown
	if scheduler:
		logger.info("Stopping scheduler...")
		await scheduler.stop()

	# Close database connections
	logger.info("Closing database connections...")
	await close_db()
	logger.info("Wazire backend has been shut down.")


app = FastAPI(
	title="Wazire Backend (MVP)",
	version="0.1.0",
	lifespan=lifespan,
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


app.include_router(health)
app.include_router(websocket)
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
	import uvicorn

	logger.info("Running via uvicorn entrypoint")
	uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
