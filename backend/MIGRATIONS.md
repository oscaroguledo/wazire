# Database Migrations with Alembic

This project uses Alembic for database schema migrations. Migrations are used to manage changes to the database structure over time.

## Database Configuration

### PostgreSQL Connection
- **Host**: aws-1-us-west-2.pooler.supabase.com
- **Port**: 5432
- **Database**: postgres
- **User**: postgres.uhwhwwxfqhybuaqqmktm
- **Password**: ism&!PtU8mNZ8pj
- **Connection String**: `postgresql://postgres.uhwhwwxfqhybuaqqmktm:ism%26%21PtU8mNZ8pj@aws-1-us-west-2.pooler.supabase.com:5432/postgres`

**Note:** The password in the connection string is URL-encoded (`&` → `%26`, `!` → `%21`)

For async operations with SQLAlchemy, use the asyncpg driver:
```
DATABASE_URL=postgresql+asyncpg://postgres.uhwhwwxfqhybuaqqmktm:ism%26%21PtU8mNZ8pj@aws-1-us-west-2.pooler.supabase.com:5432/postgres
```

## Alternative: Direct Table Creation

If you prefer to create tables directly without using migrations (e.g., for development or initial setup), you can use the `init_db()` function:

```bash
python -c "from core.database import init_db; import asyncio; asyncio.run(init_db())"
```

This will create all required tables including:
- `account.users` and `account.tenants`
- `academic.courses`, `academic.exams`, `academic.questions`
- `academic.enrollments`, `academic.submissions`
- `analytics.dashboards`

**Note:** This method is recommended for initial setup or development. For production deployments, use Alembic migrations for better version control and rollback capabilities.

## Setup

Alembic is already configured in the `alembic/` directory. The configuration is in `alembic.ini` and the migration environment is in `alembic/env.py`.

## Database Connection

The database URL is read from the `.env` file via the `DATABASE_URL` environment variable. For PostgreSQL, use:

```
DATABASE_URL=postgresql://user:password@host:port/database
```

## Creating a New Migration

When you make changes to the database models (in `models/`), create a migration to reflect those changes:

```bash
# Using the virtual environment
python -m alembic revision --autogenerate -m "description of changes"

# Or if using a specific Python path
.venv/bin/python -m alembic revision --autogenerate -m "description of changes"
```

This will:
1. Compare the current database schema with the models
2. Generate a new migration file in `alembic/versions/`
3. Name the file with a timestamp and your description

**Example:**
```bash
python -m alembic revision --autogenerate -m "add scan_pages to submission_attempts"
```

## Reviewing Generated Migrations

Always review the generated migration file before applying it:

```bash
# Check the generated file in alembic/versions/
cat alembic/versions/20250415_103000_add_scan_pages_to_submission_attempts.py
```

Make sure the changes match what you expect. If the autogenerate doesn't detect your changes correctly, you may need to manually edit the migration file.

## Applying Migrations

To apply pending migrations to the database:

```bash
# Apply all pending migrations
python -m alembic upgrade head

# Apply a specific migration
python -m alembic upgrade <revision_id>

# Or using the virtual environment
.venv/bin/python -m alembic upgrade head
```

## Rolling Back Migrations

To revert the last migration:

```bash
# Revert the last migration
python -m alembic downgrade -1

# Revert to a specific revision
python -m alembic downgrade <revision_id>

# Revert to the base (no migrations)
python -m alembic downgrade base
```

## Viewing Migration History

To see the migration history:

```bash
# Show all migrations
python -m alembic history

# Show current version
python -m alembic current

# Show SQL that would be executed (without running it)
python -m alembic upgrade head --sql
```

## Manual Migrations

Sometimes autogenerate doesn't detect complex changes. You can create a manual migration:

```bash
python -m alembic revision -m "manual migration description"
```

Then edit the generated file in `alembic/versions/` to add your custom upgrade/downgrade logic:

```python
def upgrade() -> None:
    # Your custom upgrade logic
    op.execute("ALTER TABLE users ADD COLUMN new_column VARCHAR(50)")

def downgrade() -> None:
    # Your custom downgrade logic
    op.execute("ALTER TABLE users DROP COLUMN new_column")
```

## Common Issues

### "Target database is not up to date"

This means you have pending migrations. Run:
```bash
python -m alembic upgrade head
```

### "No changes detected"

If autogenerate doesn't detect your changes:
1. Make sure your models are imported in `alembic/env.py`
2. Check that the database connection is correct
3. Try manually creating the migration

### Migration conflicts

If multiple developers create migrations with the same revision ID, you'll need to resolve conflicts by renaming one of the migration files and updating its revision ID.

## Best Practices

1. **Always review generated migrations** before applying them
2. **Write descriptive migration messages** to explain what changed
3. **Test migrations on a development database** before production
4. **Never modify applied migrations** - create a new one instead
5. **Keep migrations in order** - don't skip revisions
6. **Backup your database** before major migrations

## Production Deployment

When deploying to production:

1. Ensure all migrations are applied to the production database
2. Run migrations as part of your deployment script:
   ```bash
   python -m alembic upgrade head
   ```
3. Verify the migration was successful:
   ```bash
   python -m alembic current
   ```

## PostgreSQL Specific Notes

- PostgreSQL supports timezone-aware datetimes (TIMESTAMPTZ)
- The migration environment automatically converts async URLs to sync URLs for migration execution
- Schema creation is handled automatically by Alembic

## Troubleshooting

### Connection Issues

If you get connection errors:
1. Check your `.env` file has the correct `DATABASE_URL`
2. Verify the database server is running
3. Check network/firewall settings

### Permission Issues

If you get permission errors:
1. Ensure the database user has CREATE TABLE permissions
2. For PostgreSQL, the user should be a superuser or have proper schema permissions

### Migration Lock

If migrations get stuck:
```bash
# Check for a lock
python -m alembic check

# Clear the lock if needed (use with caution)
# Delete the alembic_version table row or update the version_num
```

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
