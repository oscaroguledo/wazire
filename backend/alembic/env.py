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

# Import models - we need to patch DATABASE_URL before importing core.database
# to avoid async engine creation during migration
original_db_url = os.environ.get('DATABASE_URL')
if original_db_url:
    # Temporarily use sync URL for migrations
    os.environ['DATABASE_URL'] = original_db_url.replace('postgresql+asyncpg://', 'postgresql+psycopg2://', 1)

from core.database import Base

# Restore original async URL
if original_db_url:
    os.environ['DATABASE_URL'] = original_db_url

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
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
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
    
    # Convert async URL to sync URL for migrations
    db_url = config.get_main_option("sqlalchemy.url")
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    
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
