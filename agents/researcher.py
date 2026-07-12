"""Researcher Agent：负责并行搜索与信息提取"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

from duckduckgo_search import DDGS

from agents.base import BaseAgent
from core.state import TaskState
import config


class ResearcherAgent(BaseAgent):
    """Researcher Agent — 并行搜索与信息提取"""

    SYSTEM_PROMPT = """你是 Researcher Agent，负责基于搜索结果提取关键信息。
对于每个搜索主题，你需要：
1. 综合多个搜索结果，提取核心事实和数据
2. 标注信息来源
3. 以结构化方式输出研究发现

输出格式（严格 JSON）：
{
  "topic": "研究主题",
  "key_findings": [
    {
      "finding": "发现内容",
      "source": "来源 URL",
      "confidence": "high/medium/low"
    }
  ],
  "summary": "研究总结"
}"""

    def __init__(self, mq, client=None):
        super().__init__("Researcher", mq, client)
        self.ddgs = DDGS()

    def _search(self, query: str, max_results: int = None) -> List[Dict[str, str]]:
        """使用 DuckDuckGo 搜索"""
        max_results = max_results or config.MAX_SEARCH_RESULTS
        try:
            results = self.ddgs.text(query, max_results=max_results, region=config.SEARCH_REGION)
            return [
                {
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", ""),
                }
                for r in results
            ]
        except Exception as e:
            return [{"title": "Search Error", "href": "", "body": str(e)}]

    def _research_topic(self, task_id: str, subtask: Dict[str, Any]) -> Dict[str, Any]:
        """研究单个子任务"""
        queries = subtask.get("search_queries", [])
        all_results = []

        for q in queries:
            results = self._search(q)
            all_results.extend(results)

        # 用 LLM 提炼信息
        search_context = "\n\n".join(
            f"[来源: {r['href']}]\n标题: {r['title']}\n内容: {r['body']}" for r in all_results[:8]
        )

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"研究主题: {subtask['description']}\n\n搜索结果:\n{search_context}\n\n请提取关键发现。"},
        ]

        finding = self.chat_completion_json(messages, temperature=0.3)
        finding["subtask_id"] = subtask.get("id", "")
        finding["all_sources"] = [r["href"] for r in all_results if r.get("href")]
        return finding

    def run(self, task: TaskState, **kwargs) -> Dict[str, Any]:
        task.add_log(self.name, "开始研究")
        task.status = "researching"

        plan = kwargs.get("plan") or task.plan
        subtasks = plan.get("subtasks", []) if plan else []

        if not subtasks:
            task.add_log(self.name, "没有子任务，直接搜索原问题")
            subtasks = [{
                "id": "task_direct",
                "description": task.original_query,
                "search_queries": [task.original_query],
            }]

        results = []
        # 并行研究
        with ThreadPoolExecutor(max_workers=min(len(subtasks), 3)) as executor:
            futures = {executor.submit(self._research_topic, task.task_id, st): st for st in subtasks}
            for future in as_completed(futures):
                try:
                    res = future.result()
                    results.append(res)
                    task.add_log(self.name, "子任务研究完成", res.get("topic", ""))
                except Exception as e:
                    task.add_log(self.name, "子任务研究失败", str(e))

        task.research_results = results
        task.status = "researching_done"
        task.add_log(self.name, "研究阶段完成", f"共 {len(results)} 个子任务")

        # 通知 Writer Agent
        self.send_message(
            to_agent="Writer",
            message_type="start_writing",
            content={
                "task_id": task.task_id,
                "research_results": results,
                "plan": plan,
            },
        )

        return {"research_results": results}
