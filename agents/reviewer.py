"""Reviewer Agent：负责质量审查"""
from typing import Dict, Any

from agents.base import BaseAgent
from core.state import TaskState


class ReviewerAgent(BaseAgent):
    """Reviewer Agent — 报告质量审查"""

    SYSTEM_PROMPT = """你是 Reviewer Agent，负责对研究报告进行质量审查。
从以下几个维度评分（1-10分）并给出改进建议：
1. relevance — 报告是否准确回应了原始问题
2. completeness — 内容是否完整，有无遗漏关键信息
3. accuracy — 事实和数据是否准确，引用是否可靠
4. structure — 结构是否清晰，逻辑是否通顺
5. readability — 语言是否流畅，易于理解

输出格式（严格 JSON）：
{
  "overall_score": 8.5,
  "dimensions": {
    "relevance": 9,
    "completeness": 8,
    "accuracy": 8,
    "structure": 9,
    "readability": 8
  },
  "issues": [
    {
      "severity": "major/minor/suggestion",
      "description": "问题描述",
      "suggestion": "改进建议"
    }
  ],
  "verdict": "pass / revise",
  "summary": "审查总结"
}"""

    def __init__(self, mq, client=None):
        super().__init__("Reviewer", mq, client)

    def run(self, task: TaskState, **kwargs) -> Dict[str, Any]:
        task.add_log(self.name, "开始质量审查")
        task.status = "reviewing"

        report = kwargs.get("report") or task.report
        original_query = kwargs.get("original_query") or task.original_query

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"""原始问题: {original_query}

待审查报告:
{report}

请进行质量审查。"""},
        ]

        review = self.chat_completion_json(messages, temperature=0.3)
        task.review_result = review

        overall_score = 0
        if isinstance(review, dict):
            overall_score = review.get("overall_score", 0)
            verdict = review.get("verdict", "pass")
        else:
            verdict = "pass"

        task.status = "completed" if verdict.lower() == "pass" else "needs_revision"
        task.add_log(self.name, "审查完成", f"评分: {overall_score}, 结论: {verdict}")

        # 通知 Manager 任务完成
        self.send_message(
            to_agent="Manager",
            message_type="task_completed",
            content={
                "task_id": task.task_id,
                "status": task.status,
                "review": review,
            },
        )

        return review
