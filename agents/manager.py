"""Manager Agent：负责任务拆解与流程编排"""
from typing import Dict, Any

from agents.base import BaseAgent
from core.state import TaskState


class ManagerAgent(BaseAgent):
    """Manager Agent — 任务规划与 orchestration"""

    SYSTEM_PROMPT = """你是 Manager Agent，负责将用户的研究需求拆解为可执行子任务。
你需要：
1. 分析用户问题的核心诉求
2. 拆解为 2-5 个并行的研究子任务
3. 为每个子任务指定搜索关键词和预期产出
4. 以 JSON 格式输出执行计划

输出格式（严格 JSON）：
{
  "analysis": "对用户问题的分析",
  "subtasks": [
    {
      "id": "task_1",
      "description": "子任务描述",
      "search_queries": ["搜索关键词1", "搜索关键词2"],
      "expected_output": "预期产出"
    }
  ],
  "final_report_requirements": "最终报告的要求"
}"""

    def __init__(self, mq, client=None):
        super().__init__("Manager", mq, client)

    def run(self, task: TaskState, **kwargs) -> Dict[str, Any]:
        task.add_log(self.name, "开始任务拆解", f"query: {task.original_query}")

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"请为以下研究需求制定执行计划：\n\n{task.original_query}"},
        ]

        plan = self.chat_completion_json(messages, temperature=0.3)
        task.plan = plan
        task.status = "planning"
        task.add_log(self.name, "任务拆解完成", f"共 {len(plan.get('subtasks', []))} 个子任务")

        # 通知 Researcher Agent 开始研究
        self.send_message(
            to_agent="Researcher",
            message_type="start_research",
            content={
                "task_id": task.task_id,
                "plan": plan,
            },
        )

        return plan
