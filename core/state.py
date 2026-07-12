"""全局状态管理"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class TaskState:
    """任务状态"""
    task_id: str
    original_query: str
    status: str = "pending"  # pending, planning, researching, writing, reviewing, completed, failed
    plan: Optional[Dict[str, Any]] = None
    research_results: List[Dict[str, Any]] = field(default_factory=list)
    report: Optional[str] = None
    review_result: Optional[Dict[str, Any]] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_log(self, agent: str, action: str, detail: str = ""):
        self.logs.append({
            "agent": agent,
            "action": action,
            "detail": detail,
            "timestamp": datetime.now().isoformat(),
        })
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "original_query": self.original_query,
            "status": self.status,
            "plan": self.plan,
            "research_results": self.research_results,
            "report": self.report,
            "review_result": self.review_result,
            "logs": self.logs,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class StateManager:
    """管理所有任务状态"""

    def __init__(self):
        self._tasks: Dict[str, TaskState] = {}

    def create_task(self, task_id: str, query: str) -> TaskState:
        task = TaskState(task_id=task_id, original_query=query)
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[TaskState]:
        return self._tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs):
        task = self._tasks.get(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = datetime.now().isoformat()

    def list_tasks(self) -> List[TaskState]:
        return list(self._tasks.values())
