# Multi-Agent Orchestrator

面向复杂研究场景的多智能体协作系统。通过 Manager、Researcher、Writer、Reviewer 四个专业 Agent 的协作，自动完成「任务拆解 → 并行搜索 → 报告撰写 → 质量审查」的完整研究闭环。

## 核心能力

- **四层 Agent 架构**：Manager 拆解任务，Researcher 并行搜索，Writer 生成报告，Reviewer 五维度评分
- **消息队列通信**：Agent 之间通过线程安全的发布/订阅消息队列解耦，支持灵活扩展
- **JSON Mode 结构化输出**：Agent 间数据格式稳定可解析
- **零成本搜索**：集成 DuckDuckGo，无需额外搜索 API 费用
- **双模式交互**：Rich 美化 CLI + Flask Web（SSE 实时推送）

## 目录结构

```
multi_agent_orchestrator/
├── agents/              # Agent 实现
│   ├── base.py          # Agent 基类（LLM 调用、消息通信封装）
│   ├── manager.py       # Manager Agent：任务拆解与流程编排
│   ├── researcher.py    # Researcher Agent：并行搜索与信息提取
│   ├── writer.py        # Writer Agent：基于研究成果撰写报告
│   └── reviewer.py      # Reviewer Agent：报告质量审查与评分
├── core/                # 核心基础设施
│   ├── message_queue.py # 线程安全的消息队列（发布/订阅）
│   └── state.py         # 全局任务状态管理
├── web/                 # Flask Web 服务
│   └── app.py           # SSE 实时推送 + REST API
├── templates/           # Web 前端
│   └── index.html
├── cli.py               # Rich 美化终端 CLI
├── orchestrator.py      # 工作流编排器
├── config.py            # 配置（支持 .env）
├── run.py               # 统一入口（CLI / Web 双模式）
├── requirements.txt     # 依赖
└── .env.example         # 环境变量示例
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 OPENAI_API_KEY
# 支持任意兼容 OpenAI 的 API：OpenAI、DeepSeek、硅基流动、OpenRouter 等

# 3. CLI 模式
python run.py --mode cli

# 4. Web 模式
python run.py --mode web --port 5000
# 浏览器访问 http://localhost:5000
```

## 效果展示

输入研究问题后，系统会在 30~60 秒内自动：
1. Manager 将问题拆分为 2~5 个并行子任务
2. 多个 Researcher 同时搜索，约 7 秒内返回研究发现
3. Writer 整合生成结构化 Markdown 报告
4. Reviewer 从相关性、完整性、准确性、结构、可读性五维度评分

Web 界面可实时查看四个 Agent 的协作日志与状态流转。

## 技术栈

Python · Flask · DeepSeek API · DuckDuckGo · SSE · ThreadPoolExecutor · JSON Mode · Rich
