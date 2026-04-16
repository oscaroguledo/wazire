"""TaskScheduler — generic background scheduler for periodic tasks.

Pluggable system for registering and running scheduled tasks:
- Register tasks with intervals
- Automatic execution in background
- Easy to add new task types

Example:
    scheduler = TaskScheduler()
    
    # Register exam status updates (runs every 60s)
    scheduler.register_task("exam_status", update_exam_statuses, interval=60)
    
    # Add more tasks as needed
    scheduler.register_task("cleanup", cleanup_old_data, interval=3600)
"""
from __future__ import annotations

import asyncio
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Callable, Dict, List, Optional, Any, Awaitable
from sqlalchemy import select, func
from core.database import get_session_factory
from models.academic.exam import Exam


@dataclass
class ScheduledTask:
    """A registered scheduled task."""
    name: str
    handler: Callable[[], Awaitable[Any]]
    interval: int  # seconds
    last_run: Optional[datetime] = None
    last_error: Optional[str] = None
    run_count: int = 0


class TaskScheduler:
    """Generic background scheduler for periodic tasks.
    
    Register tasks with intervals, runs them in background loop.
    Each task runs independently on its own schedule.
    
    Args:
        default_interval: Default seconds between task executions
    """
    
    def __init__(self, default_interval: int = 60):
        self.default_interval = default_interval
        self._tasks: Dict[str, ScheduledTask] = {}
        self._task_handles: Dict[str, asyncio.Task] = {}
        self._running = False
        self._main_task: Optional[asyncio.Task] = None
    
    def register_task(
        self,
        name: str,
        handler: Callable[[], Awaitable[Any]],
        interval: Optional[int] = None
    ) -> None:
        """Register a new scheduled task.
        
        Args:
            name: Unique task identifier
            handler: Async function to execute
            interval: Seconds between runs (uses default if not specified)
        """
        self._tasks[name] = ScheduledTask(
            name=name,
            handler=handler,
            interval=interval or self.default_interval
        )
        print(f"[TaskScheduler] Registered '{name}' (interval: {self._tasks[name].interval}s)")
    
    def unregister_task(self, name: str) -> None:
        """Remove a registered task."""
        if name in self._tasks:
            del self._tasks[name]
            print(f"[TaskScheduler] Unregistered '{name}'")
    
    async def start(self) -> None:
        """Start the scheduler and all registered tasks."""
        if self._running:
            return
        self._running = True
        
        # Start each task as its own managed coroutine
        for name, task in self._tasks.items():
            self._task_handles[name] = asyncio.create_task(
                self._run_task_loop(task),
                name=f"scheduler_{name}"
            )
        
        print(f"[TaskScheduler] Started with {len(self._tasks)} task(s)")
    
    async def stop(self) -> None:
        """Stop all tasks and the scheduler."""
        self._running = False
        
        # Cancel all task handles
        for name, handle in self._task_handles.items():
            handle.cancel()
            try:
                await handle
            except asyncio.CancelledError:
                pass
        
        self._task_handles.clear()
        print("[TaskScheduler] Stopped")
    
    async def _run_task_loop(self, task: ScheduledTask) -> None:
        """Run a single task loop."""
        while self._running:
            try:
                await task.handler()
                task.last_run = datetime.now(timezone.utc)
                task.run_count += 1
                task.last_error = None
            except Exception as e:
                task.last_error = f"{type(e).__name__}: {str(e)}"
                print(f"[TaskScheduler] Task '{task.name}' failed: {task.last_error}")
                traceback.print_exc()

            try:
                await asyncio.sleep(task.interval)
            except asyncio.CancelledError:
                break
    
    async def run_task_now(self, name: str) -> Any:
        """Manually trigger a task to run immediately.

        Returns:
            Result from the task handler
        """
        if name not in self._tasks:
            raise ValueError(f"Task '{name}' not found")

        task = self._tasks[name]
        try:
            result = await task.handler()
            task.last_run = datetime.now(timezone.utc)
            task.run_count += 1
            return result
        except Exception as e:
            task.last_error = f"{type(e).__name__}: {str(e)}"
            raise
    
    def get_status(self) -> List[Dict[str, Any]]:
        """Get status of all registered tasks."""
        return [
            {
                "name": t.name,
                "interval": t.interval,
                "last_run": t.last_run.isoformat() if t.last_run else None,
                "run_count": t.run_count,
                "last_error": t.last_error,
                "running": t.name in self._task_handles and not self._task_handles[t.name].done()
            }
            for t in self._tasks.values()
        ]


# Global scheduler instance
_scheduler: Optional[TaskScheduler] = None


def get_scheduler(default_interval: int = 60) -> TaskScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler(default_interval=default_interval)
    return _scheduler


# ============================================================================
# Built-in Task Implementations
# ============================================================================

async def update_exam_statuses() -> Dict[str, int]:
    """Update exam statuses based on start_time and duration.

    For each exam:
    - If status is 'not_started' and start_time <= now → 'in_progress'
    - If status is 'in_progress' and now >= start_time + duration → 'finished'

    Optimized with batch processing by tenant to handle large deployments efficiently.

    Returns:
        Dict with counts of activated and completed exams
    """

    AsyncSessionLocal = get_session_factory()
    async with AsyncSessionLocal() as db:
        # Get current time as timezone-aware UTC
        now = datetime.now(timezone.utc)
        activated = 0
        completed = 0
        skipped_no_duration = 0
        timezone_conversions = 0
        total_tenants_processed = 0

        # Get all unique tenant IDs that have exams with start_time
        tenant_ids_result = await db.execute(
            select(Exam.tenant_id).where(Exam.start_time.is_not(None)).distinct()
        )
        tenant_ids = [row[0] for row in tenant_ids_result.all() if row[0] is not None]

        print(f"[ExamTask] Processing exams for {len(tenant_ids)} tenant(s)")

        # Process exams batch by tenant
        for tenant_id in tenant_ids:
            total_tenants_processed += 1
            tenant_activated = 0
            tenant_completed = 0

            # Get exams for this tenant with start_time set
            tenant_exams_result = await db.execute(
                select(Exam).where(
                    Exam.start_time.is_not(None),
                    Exam.tenant_id == tenant_id
                )
            )

            for exam in tenant_exams_result.scalars():
                # Get exam start_time and ensure it's timezone-aware for comparison
                exam_start = exam.start_time
                if exam_start.tzinfo is None:
                    exam_start = exam_start.replace(tzinfo=timezone.utc)
                    timezone_conversions += 1
                    print(f"[ExamTask] Warning: Exam {exam.id} had naive datetime, converted to UTC")

                current_status = exam.status

                # Skip exams without duration (shouldn't happen per model constraints, but handle gracefully)
                if not exam.duration:
                    skipped_no_duration += 1
                    print(f"[ExamTask] Warning: Exam {exam.id} has no duration, skipping status update")
                    continue

                duration_hours = float(exam.duration)
                end_time = exam_start + timedelta(hours=duration_hours)

                # Case 1: Exam should be activated (not_started → in_progress)
                if current_status == 'not_started':
                    if now >= exam_start and now < end_time:
                        exam.status = 'in_progress'
                        exam.updated_at = now
                        activated += 1
                        tenant_activated += 1
                        print(f"[ExamTask] Activated exam {exam.id}: start={exam_start}, end={end_time}, now={now}")
                    elif now >= end_time:
                        exam.status = 'finished'
                        exam.updated_at = now
                        completed += 1
                        tenant_completed += 1
                        print(f"[ExamTask] Completed exam {exam.id} (missed start): start={exam_start}, end={end_time}, now={now}")

                # Case 2: Exam should be completed (in_progress → finished)
                elif current_status == 'in_progress':
                    if now >= end_time:
                        exam.status = 'finished'
                        exam.updated_at = now
                        completed += 1
                        tenant_completed += 1
                        print(f"[ExamTask] Completed exam {exam.id}: start={exam_start}, end={end_time}, now={now}")

            # Commit after processing each tenant to reduce memory pressure
            await db.commit()

            if tenant_activated > 0 or tenant_completed > 0:
                print(f"[ExamTask] Tenant {tenant_id}: Activated {tenant_activated}, completed {tenant_completed}")

        # Summary log
        if activated > 0 or completed > 0 or skipped_no_duration > 0:
            print(f"[ExamTask] Summary: Tenants processed {total_tenants_processed}, activated {activated}, completed {completed}, skipped (no duration) {skipped_no_duration}, timezone conversions {timezone_conversions}")
        else:
            print(f"[ExamTask] Ran at {now.isoformat()} - processed {total_tenants_processed} tenant(s), no exams to update")

        return {
            "tenants_processed": total_tenants_processed,
            "activated": activated,
            "completed": completed,
            "skipped_no_duration": skipped_no_duration,
            "timezone_conversions": timezone_conversions
        }


# ============================================================================
# Convenience Functions
# ============================================================================

async def start_scheduler(
    default_interval: int = 60,
    with_exam_task: bool = True
) -> TaskScheduler:
    """Start the global scheduler with default tasks.
    
    Args:
        default_interval: Default seconds between task runs
        with_exam_task: Auto-register exam status update task
    
    Example:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            scheduler = await start_scheduler()
            yield
            await scheduler.stop()
    """
    scheduler = get_scheduler(default_interval)
    
    if with_exam_task:
        scheduler.register_task("exam_status", update_exam_statuses, interval=60)
    
    await scheduler.start()
    return scheduler


# ============================================================================
# Manual Task Execution (for testing/ad-hoc runs)
# ============================================================================

async def run_exam_update_now() -> Dict[str, int]:
    """Manually trigger exam status update.
    
    Returns:
        Dict with activated and completed counts
    """
    return await update_exam_statuses()
