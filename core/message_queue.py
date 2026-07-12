"""Agent 间消息队列，支持事件监听"""
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import threading


@dataclass
class AgentMessage:
    """Agent 间传递的消息"""
    from_agent: str
    to_agent: str
    message_type: str
    content: dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type,
            "content": self.content,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class MessageQueue:
    """线程安全的消息队列，支持订阅/发布模式"""

    def __init__(self):
        self._messages: List[AgentMessage] = []
        self._listeners: Dict[str, List[Callable[[AgentMessage], None]]] = {}
        self._lock = threading.Lock()
        self._global_listeners: List[Callable[[AgentMessage], None]] = []

    def subscribe(self, agent_name: str, callback: Callable[[AgentMessage], None]):
        """订阅特定 Agent 的消息"""
        with self._lock:
            if agent_name not in self._listeners:
                self._listeners[agent_name] = []
            self._listeners[agent_name].append(callback)

    def subscribe_all(self, callback: Callable[[AgentMessage], None]):
        """订阅所有消息"""
        with self._lock:
            self._global_listeners.append(callback)

    def publish(self, message: AgentMessage):
        """发布消息"""
        with self._lock:
            self._messages.append(message)

        # 通知目标 Agent 的订阅者
        listeners = self._listeners.get(message.to_agent, [])
        for cb in listeners:
            try:
                cb(message)
            except Exception as e:
                print(f"[MessageQueue] Listener error: {e}")

        # 通知全局订阅者
        for cb in self._global_listeners:
            try:
                cb(message)
            except Exception as e:
                print(f"[MessageQueue] Global listener error: {e}")

    def get_messages_for(self, agent_name: str) -> List[AgentMessage]:
        """获取发给指定 Agent 的所有消息"""
        with self._lock:
            return [m for m in self._messages if m.to_agent == agent_name]

    def get_all_messages(self) -> List[AgentMessage]:
        """获取所有消息"""
        with self._lock:
            return list(self._messages)

    def clear(self):
        """清空消息队列"""
        with self._lock:
            self._messages.clear()
