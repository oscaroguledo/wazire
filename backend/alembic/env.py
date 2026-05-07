from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

# Import models - we need to use sync URL for migrations
from core.config import get_settings
settings = get_settings()

# Get DATABASE_URL from config and convert to sync URL for Alembic
db_url = settings.DATABASE_URL
if db_url:
    # Convert async URL to sync URL for migrations
    if db_url.startswith('postgresql+asyncpg://'):
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql+psycopg2://', 1)
    elif db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    # sqlite support removed - migrations expect a PostgreSQL URL

from core.database import Base

# Import all models to register with Base
from models.account.users import User
from models.account.tenant import Tenant
from models.account.oauth import OAuth
from models.academic.course import Course
from models.academic.enrollment import Enrollment
from models.academic.exam import Exam
from models.academic.question import Question, QuestionExams, Answer
from models.academic.submission import Submission, SubmissionAttempt
from models.academic.student_answer import StudentAnswer
from models.analytics.dashboard import LecturerDashboard, AdminDashboard, StudentDashboard
# Skip billings as requested
# from models.billings.invoice import Invoice
# from models.billings.paymentmethod import PaymentMethod
# from models.billings.usage import Usage

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Use the db_url from config (already converted to sync)
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # For async PostgreSQL, we need to use create_async_engine
    # However, Alembic doesn't support async migrations by default
    # So we use the synchronous driver for migrations
    from sqlalchemy.engine import Engine
    from sqlalchemy import create_engine

    # Use the db_url from config (already converted to sync)
    connectable = create_engine(db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
