"""基础 Agent 类"""
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from openai import OpenAI

import config
from core.message_queue import MessageQueue, AgentMessage
from core.state import TaskState


class BaseAgent(ABC):
    """Agent 基类，封装 LLM 调用与消息通信"""

    def __init__(self, name: str, mq: MessageQueue, client: Optional[OpenAI] = None):
        self.name = name
        self.mq = mq
        self.client = client or OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
        )
        self.model = config.OPENAI_MODEL

    def send_message(self, to_agent: str, message_type: str, content: dict):
        """发送消息到指定 Agent"""
        msg = AgentMessage(
            from_agent=self.name,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
        )
        self.mq.publish(msg)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        tools: Optional[List[Dict]] = None,
    ) -> str:
        """调用 LLM，返回文本结果"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if response_format:
            kwargs["response_format"] = response_format
        if tools:
            kwargs["tools"] = tools

        try:
            resp = self.client.chat.completions.create(**kwargs)
            if tools and resp.choices[0].message.tool_calls:
                return resp.choices[0].message
            return resp.choices[0].message.content or ""
        except Exception as e:
            return f"[LLM Error] {e}"

    def chat_completion_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """调用 LLM，返回解析后的 JSON（兼容 DeepSeek）"""
        # 先尝试 response_format=json_object（OpenAI 兼容）
        try:
            content = self.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            # 跳过 LLM Error
            if content.startswith("[LLM Error]"):
                raise ValueError(content)
            return json.loads(content)
        except (json.JSONDecodeError, ValueError, Exception):
            # fallback: 不用 response_format，在 system prompt 中要求 JSON
            msgs = list(messages)
            if msgs and msgs[0].get("role") == "system":
                msgs[0]["content"] += "\n\n重要：你必须且只能输出合法的 JSON 格式，不要输出任何其他内容。"
            else:
                msgs.insert(0, {"role": "system", "content": "你必须且只能输出合法的 JSON 格式，不要输出任何其他内容。"})
            content = self.chat_completion(
                messages=msgs,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            # 尝试从回复中提取 JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            try:
                return json.loads(content.strip())
            except json.JSONDecodeError:
                return {"error": "Invalid JSON", "raw": content}

    @abstractmethod
    def run(self, task: TaskState, **kwargs) -> Dict[str, Any]:
        """执行 Agent 核心逻辑"""
        pass
