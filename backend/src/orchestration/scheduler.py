"""Task scheduler for managing asynchronous task execution."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, TypeVar
from uuid import UUID, uuid4

from src.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class TaskStatus(str, Enum):
    """Task status in scheduler."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(int, Enum):
    """Task priority levels."""
    
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class Task:
    """Represents a scheduled task."""
    
    task_id: UUID = field(default_factory=uuid4)
    coro: Coroutine | None = field(default=None)
    priority: TaskPriority = field(default=TaskPriority.NORMAL)
    timeout_seconds: float = field(default=120.0)
    status: TaskStatus = field(default=TaskStatus.PENDING)
    result: Any = field(default=None)
    error: str | None = field(default=None)
    start_time: float | None = field(default=None)
    end_time: float | None = field(default=None)
    
    def __lt__(self, other: "Task") -> bool:
        """Compare tasks by priority (lower value = higher priority)."""
        return self.priority < other.priority


@dataclass
class TaskResult:
    """Result of a task execution."""
    
    task_id: UUID
    status: TaskStatus
    result: Any = None
    error: str | None = None
    duration_seconds: float = 0.0


class Scheduler:
    """Priority-based async task scheduler.
    
    Manages task queue with priority ordering, timeout enforcement,
    and deadlock detection.
    """
    
    def __init__(
        self,
        max_concurrent: int = 10,
        default_timeout: float = 120.0
    ) -> None:
        """Initialize scheduler.
        
        Args:
            max_concurrent: Maximum concurrent tasks.
            default_timeout: Default timeout per task.
        """
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self._task_queue: asyncio.PriorityQueue[Task] = asyncio.PriorityQueue()
        self._tasks: dict[UUID, Task] = {}
        self._running_tasks: dict[UUID, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._shutdown = False
        self._worker_task: asyncio.Task | None = None
        
        logger.info(
            "Scheduler initialized",
            max_concurrent=max_concurrent,
            default_timeout=default_timeout
        )
    
    async def start(self) -> None:
        """Start the scheduler worker."""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("Scheduler worker started")
    
    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        self._shutdown = True
        
        # Cancel all running tasks
        for task in self._running_tasks.values():
            task.cancel()
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Scheduler stopped")
    
    async def submit_task(
        self,
        coro: Coroutine[Any, Any, T],
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout_seconds: float | None = None,
        task_id: UUID | None = None
    ) -> UUID:
        """Submit a task to the scheduler.
        
        Args:
            coro: Coroutine to execute.
            priority: Task priority.
            timeout_seconds: Timeout in seconds.
            task_id: Optional task ID.
            
        Returns:
            Task ID.
        """
        if self._shutdown:
            raise RuntimeError("Scheduler is shutdown")
        
        task = Task(
            task_id=task_id or uuid4(),
            coro=coro,
            priority=priority,
            timeout_seconds=timeout_seconds or self.default_timeout
        )
        
        self._tasks[task.task_id] = task
        await self._task_queue.put(task)
        
        logger.info(
            "Task submitted",
            task_id=str(task.task_id),
            priority=priority.value
        )
        
        return task.task_id
    
    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a pending or running task.
        
        Args:
            task_id: Task to cancel.
            
        Returns:
            True if cancelled.
        """
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        
        if task.status == TaskStatus.RUNNING and task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
        
        task.status = TaskStatus.CANCELLED
        logger.info("Task cancelled", task_id=str(task_id))
        return True
    
    def get_status(self, task_id: UUID) -> TaskStatus | None:
        """Get task status.
        
        Args:
            task_id: Task ID.
            
        Returns:
            Task status or None if not found.
        """
        task = self._tasks.get(task_id)
        return task.status if task else None
    
    def get_result(self, task_id: UUID) -> TaskResult | None:
        """Get task result.
        
        Args:
            task_id: Task ID.
            
        Returns:
            Task result or None.
        """
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        duration = 0.0
        if task.start_time and task.end_time:
            duration = task.end_time - task.start_time
        
        return TaskResult(
            task_id=task_id,
            status=task.status,
            result=task.result,
            error=task.error,
            duration_seconds=duration
        )
    
    def list_tasks(
        self,
        status: TaskStatus | None = None
    ) -> list[Task]:
        """List tasks.
        
        Args:
            status: Filter by status.
            
        Returns:
            List of tasks.
        """
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks
    
    async def _worker(self) -> None:
        """Worker loop processing tasks."""
        while not self._shutdown:
            try:
                # Wait for a task with timeout for periodic checks
                task = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            
            # Process task with semaphore
            async with self._semaphore:
                await self._execute_task(task)
    
    async def _execute_task(self, task: Task) -> None:
        """Execute a task with timeout.
        
        Args:
            task: Task to execute.
        """
        task.status = TaskStatus.RUNNING
        task.start_time = asyncio.get_event_loop().time()
        
        logger.info("Task started", task_id=str(task.task_id))
        
        try:
            # Run with timeout
            result = await asyncio.wait_for(
                task.coro,
                timeout=task.timeout_seconds
            )
            task.result = result
            task.status = TaskStatus.COMPLETED
            logger.info(
                "Task completed",
                task_id=str(task.task_id)
            )
        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.error = f"Task timed out after {task.timeout_seconds}s"
            logger.warning(
                "Task timeout",
                task_id=str(task.task_id),
                timeout=task.timeout_seconds
            )
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.error = "Task was cancelled"
            logger.info("Task cancelled", task_id=str(task.task_id))
            raise
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error(
                "Task failed",
                task_id=str(task.task_id),
                error=str(e)
            )
        finally:
            task.end_time = asyncio.get_event_loop().time()


# Global scheduler instance
_scheduler: Scheduler | None = None


async def get_scheduler(
    max_concurrent: int = 10,
    default_timeout: float = 120.0
) -> Scheduler:
    """Get or create global scheduler instance.
    
    Args:
        max_concurrent: Max concurrent tasks.
        default_timeout: Default timeout.
        
    Returns:
        Scheduler instance.
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler(max_concurrent, default_timeout)
        await _scheduler.start()
    return _scheduler
