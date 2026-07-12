"""Orchestrator：协调各 Agent 完成完整工作流"""
import uuid
from typing import Optional, Callable
from openai import OpenAI

from core.message_queue import MessageQueue
from core.state import StateManager, TaskState
from agents.manager import ManagerAgent
from agents.researcher import ResearcherAgent
from agents.writer import WriterAgent
from agents.reviewer import ReviewerAgent
import config


class Orchestrator:
    """编排 Manager/Researcher/Writer/Reviewer 的协作流程"""

    def __init__(self):
        self.mq = MessageQueue()
        self.state = StateManager()
        self.client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
        )

        # 初始化 Agents
        self.manager = ManagerAgent(self.mq, self.client)
        self.researcher = ResearcherAgent(self.mq, self.client)
        self.writer = WriterAgent(self.mq, self.client)
        self.reviewer = ReviewerAgent(self.mq, self.client)

        # 注册消息处理器
        self._setup_handlers()

    def _setup_handlers(self):
        """设置消息队列的事件处理器"""
        def handle_message(msg):
            if msg.message_type == "start_research":
                task_id = msg.content.get("task_id")
                task = self.state.get_task(task_id)
                if task:
                    self.researcher.run(task, plan=msg.content.get("plan"))

            elif msg.message_type == "start_writing":
                task_id = msg.content.get("task_id")
                task = self.state.get_task(task_id)
                if task:
                    self.writer.run(
                        task,
                        research_results=msg.content.get("research_results"),
                        plan=msg.content.get("plan"),
                    )

            elif msg.message_type == "start_review":
                task_id = msg.content.get("task_id")
                task = self.state.get_task(task_id)
                if task:
                    self.reviewer.run(
                        task,
                        report=msg.content.get("report"),
                        original_query=msg.content.get("original_query"),
                    )

            elif msg.message_type == "task_completed":
                task_id = msg.content.get("task_id")
                task = self.state.get_task(task_id)
                if task:
                    task.status = msg.content.get("status", "completed")

        self.mq.subscribe_all(handle_message)

    def run(self, query: str, progress_callback: Optional[Callable[[TaskState], None]] = None, existing_task: Optional[TaskState] = None) -> TaskState:
        """运行完整的工作流"""
        if existing_task:
            task = existing_task
        else:
            task_id = str(uuid.uuid4())[:8]
            task = self.state.create_task(task_id, query)

        # 注册进度回调
        if progress_callback:
            original_add_log = task.add_log
            def patched_add_log(agent, action, detail=""):
                original_add_log(agent, action, detail)
                progress_callback(task)
            task.add_log = patched_add_log

        # Step 1: Manager 拆解任务
        self.manager.run(task)

        return task

    def get_task(self, task_id: str) -> Optional[TaskState]:
        return self.state.get_task(task_id)
