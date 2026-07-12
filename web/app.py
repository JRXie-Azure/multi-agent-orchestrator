"""Flask Web 服务 — 实时展示三 Agent 协作日志与进度状态"""
import json
import threading
import time
from flask import Flask, render_template, request, jsonify

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import Orchestrator
from core.state import TaskState
import config

app = Flask(__name__, template_folder="../templates")

# 全局 Orchestrator 实例
orch = Orchestrator()
# SSE 订阅者列表
sse_subscribers = []


def notify_subscribers(task: TaskState):
    """通知所有 SSE 订阅者"""
    data = json.dumps(task.to_dict(), ensure_ascii=False)
    dead = []
    for q in sse_subscribers:
        try:
            q.put(data)
        except Exception:
            dead.append(q)
    for d in dead:
        if d in sse_subscribers:
            sse_subscribers.remove(d)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json() or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400

    def cb(task):
        notify_subscribers(task)

    # 先创建 task（轻量操作，不阻塞）
    import uuid
    task_id = str(uuid.uuid4())[:8]
    task = orch.state.create_task(task_id, query)

    # 在后台线程中运行完整工作流（避免阻塞 SSE）
    def run_workflow():
        try:
            orch.run(query, progress_callback=cb, existing_task=task)
        except Exception as e:
            print(f"[Web] Workflow error: {e}")

    t = threading.Thread(target=run_workflow, daemon=True)
    t.start()

    return jsonify({"task_id": task.task_id, "status": task.status})


@app.route("/api/tasks/<task_id>")
def get_task(task_id):
    task = orch.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task.to_dict())


@app.route("/api/stream")
def stream():
    """SSE 流，实时推送任务状态"""
    import queue
    q = queue.Queue()
    sse_subscribers.append(q)

    def event_stream():
        try:
            while True:
                try:
                    data = q.get(timeout=10)
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    # 发送心跳保持连接
                    yield f": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            if q in sse_subscribers:
                sse_subscribers.remove(q)

    return app.response_class(event_stream(), mimetype="text/event-stream")


def run_web():
    app.run(host="0.0.0.0", port=config.WEB_PORT, debug=config.DEBUG, use_reloader=False)


if __name__ == "__main__":
    run_web()
