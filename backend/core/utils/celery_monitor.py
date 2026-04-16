from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from celery.result import AsyncResult
from celery import Celery
import json

from core.utils.logger import logger


class CeleryMonitor:
    """Monitor and track Celery background job status and metrics."""
    
    def __init__(self, celery_app: Celery):
        self.celery_app = celery_app
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status and metadata of a Celery task.
        
        Args:
            task_id: The Celery task ID
            
        Returns:
            Dictionary containing task status, result, error, and metadata
        """
        result = AsyncResult(task_id, app=self.celery_app)
        
        status_info = {
            "task_id": task_id,
            "status": result.status,
            "state": result.state,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "failed": result.failed() if result.ready() else None,
        }
        
        if result.ready():
            if result.successful():
                status_info["result"] = result.result
            elif result.failed():
                status_info["error"] = str(result.result)
                status_info["traceback"] = result.traceback
        else:
            status_info["info"] = result.info
        
        return status_info
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get extended task information from Celery backend."""
        try:
            return self.celery_app.backend.get_task_meta(task_id)
        except Exception as e:
            logger.error(f"Failed to get task info for {task_id}: {e}")
            return None
    
    def revoke_task(self, task_id: str, terminate: bool = False) -> bool:
        """Revoke (cancel) a running or pending task.
        
        Args:
            task_id: The Celery task ID
            terminate: Whether to forcefully terminate the task
            
        Returns:
            True if task was successfully revoked
        """
        try:
            self.celery_app.control.revoke(task_id, terminate=terminate)
            logger.info(f"Task {task_id} revoked (terminate={terminate})")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke task {task_id}: {e}")
            return False
    
    def get_active_tasks(self) -> Dict[str, Any]:
        """Get information about currently active tasks."""
        try:
            inspect = self.celery_app.control.inspect()
            active = inspect.active()
            
            if not active:
                return {"active": [], "total": 0}
            
            # Flatten the worker-based structure
            all_active = []
            for worker, tasks in active.items():
                for task in tasks:
                    all_active.append({
                        "worker": worker,
                        "task_id": task["id"],
                        "task_name": task["name"],
                        "args": task["args"],
                        "kwargs": task["kwargs"],
                        "time_start": task.get("time_start"),
                    })
            
            return {"active": all_active, "total": len(all_active)}
        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}")
            return {"active": [], "total": 0}
    
    def get_scheduled_tasks(self) -> Dict[str, Any]:
        """Get information about scheduled tasks."""
        try:
            inspect = self.celery_app.control.inspect()
            scheduled = inspect.scheduled()
            
            if not scheduled:
                return {"scheduled": [], "total": 0}
            
            all_scheduled = []
            for worker, tasks in scheduled.items():
                for task in tasks:
                    all_scheduled.append({
                        "worker": worker,
                        "task_id": task["id"],
                        "task_name": task["name"],
                        "args": task["args"],
                        "kwargs": task["kwargs"],
                        "eta": task.get("eta"),
                    })
            
            return {"scheduled": all_scheduled, "total": len(all_scheduled)}
        except Exception as e:
            logger.error(f"Failed to get scheduled tasks: {e}")
            return {"scheduled": [], "total": 0}
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get statistics about Celery workers."""
        try:
            inspect = self.celery_app.control.inspect()
            stats = inspect.stats()
            
            if not stats:
                return {"workers": [], "total": 0}
            
            worker_stats = []
            for worker, stat in stats.items():
                worker_stats.append({
                    "worker": worker,
                    "total_tasks": stat.get("total", {}).values(),
                    "pool": stat.get("pool", {}),
                    "rusage": stat.get("rusage", {}),
                })
            
            return {"workers": worker_stats, "total": len(worker_stats)}
        except Exception as e:
            logger.error(f"Failed to get worker stats: {e}")
            return {"workers": [], "total": 0}
    
    def get_queue_length(self, queue_name: str = "default") -> int:
        """Get the number of tasks in a specific queue."""
        try:
            with self.celery_app.pool.acquire(block=True) as conn:
                return conn.default_channel.queue_declare(
                    queue=queue_name, passive=True
                ).message_count
        except Exception as e:
            logger.error(f"Failed to get queue length for {queue_name}: {e}")
            return 0


def log_task_result(task_id: str, result: Any, status: str) -> None:
    """Log the result of a Celery task for monitoring purposes.
    
    Args:
        task_id: The Celery task ID
        result: The task result or error
        status: The task status (SUCCESS, FAILURE, etc.)
    """
    log_data = {
        "task_id": task_id,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    if status == "SUCCESS":
        log_data["result"] = str(result)[:500]  # Limit result length
        logger.info(f"Task completed: {json.dumps(log_data)}")
    else:
        log_data["error"] = str(result)[:500]  # Limit error length
        logger.error(f"Task failed: {json.dumps(log_data)}")
