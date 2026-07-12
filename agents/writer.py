"""Writer Agent：负责报告撰写"""
from typing import Dict, Any

from agents.base import BaseAgent
from core.state import TaskState
import config


class WriterAgent(BaseAgent):
    """Writer Agent — 基于研究成果撰写报告"""

    SYSTEM_PROMPT = """你是 Writer Agent，负责基于研究成果撰写高质量的研究报告。
要求：
1. 结构清晰，包含标题、摘要、正文、结论
2. 引用研究发现中的数据来源
3. 语言专业、逻辑严谨
4. 报告使用 Markdown 格式
5. 在报告末尾附上参考来源列表

直接输出完整的 Markdown 报告即可。"""

    def __init__(self, mq, client=None):
        super().__init__("Writer", mq, client)

    def run(self, task: TaskState, **kwargs) -> Dict[str, Any]:
        task.add_log(self.name, "开始撰写报告")
        task.status = "writing"

        research_results = kwargs.get("research_results") or task.research_results
        plan = kwargs.get("plan") or task.plan

        # 构建研究上下文
        context_parts = []
        for i, res in enumerate(research_results, 1):
            topic = res.get("topic", res.get("subtask_id", f"研究{i}"))
            summary = res.get("summary", "")
            findings = res.get("key_findings", [])
            findings_text = "\n".join(
                f"- {f.get('finding', '')} (来源: {f.get('source', 'N/A')}, 置信度: {f.get('confidence', 'medium')})"
                for f in findings
            )
            context_parts.append(f"## 研究主题: {topic}\n### 总结\n{summary}\n### 关键发现\n{findings_text}\n")

        research_context = "\n".join(context_parts)
        requirements = ""
        if plan and isinstance(plan, dict):
            requirements = plan.get("final_report_requirements", "")

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"""原始问题: {task.original_query}

报告要求: {requirements}

研究成果:
{research_context}

请撰写完整的研究报告。"""},
        ]

        report = self.chat_completion(
            messages=messages,
            temperature=0.5,
            max_tokens=config.MAX_OUTPUT_TOKENS,
        )

        task.report = report
        task.status = "writing_done"
        task.add_log(self.name, "报告撰写完成", f"报告长度: {len(report)} 字符")

        # 通知 Reviewer Agent
        self.send_message(
            to_agent="Reviewer",
            message_type="start_review",
            content={
                "task_id": task.task_id,
                "report": report,
                "original_query": task.original_query,
            },
        )

        return {"report": report}
