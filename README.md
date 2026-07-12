# Multi-Agent Orchestrator

独立设计与实现的多智能体协作研究系统。针对传统单一 LLM 在处理复杂研究任务时容易出现的"逻辑跳跃、信息遗漏、输出不可控"问题，通过任务拆分、多角色协作与质量闭环，将复杂调研类问题的执行过程从人工数小时压缩到分钟级。

## 为什么不是单 Agent，而是多 Agent？

在最初的原型中，我尝试让单个 LLM 直接完成"搜索 + 写作 + 审查"，但很快暴露三个问题：

1. **上下文过载**：研究资料一多，模型容易遗忘初始任务目标
2. **角色混淆**：同一个 Prompt 既要会搜索又要会写作，输出质量不稳定
3. **无法并行**：单线程执行导致整体耗时长

因此我参考人类研究团队的分工方式，将系统拆分为四个独立 Agent：

| Agent | 职责 | 解决的关键问题 |
|-------|------|---------------|
| **Manager** | 解析用户意图，拆解成可并行子任务 | 避免大任务直接丢给 LLM 导致理解偏差 |
| **Researcher** | 多线程并行搜索，提取结构化发现 | 压缩信息收集时间，扩大资料覆盖 |
| **Writer** | 汇总研究发现，生成带章节结构的报告 | 专注内容组织与表达 |
| **Reviewer** | 从 5 个维度打分并给出修改建议 | 建立质量反馈闭环 |

## 我解决的核心工程问题

### 1. Agent 之间如何稳定协作？

自己实现了一套**线程安全的发布/订阅消息队列**（基于 `queue.Queue` + `threading.Lock`），而不是简单调用函数。这样设计的好处：

- Agent 之间完全解耦，新增 Agent 只需订阅对应消息类型
- 支持异步执行，Researcher 可以并行工作
- 所有协作过程可观测、可回放，便于调试和扩展

### 2. Agent 之间传递的数据如何保证格式一致？

通过 **OpenAI SDK 结构化输出 + JSON Mode + Prompt 模板约束**，强制每个 Agent 输出固定 JSON 格式。例如 Manager 必须输出：

```json
{
  "tasks": [
    {"id": 1, "topic": "技术架构", "description": "..."},
    {"id": 2, "topic": "应用场景", "description": "..."}
  ]
}
```

下游模块可以直接解析，不需要用正则表达式从自由文本里抽取信息。

### 3. 搜索成本怎么控制？

Researcher 使用 **DuckDuckGo 免费搜索**，不依赖付费搜索 API。配合 `ThreadPoolExecutor` 多线程，3 个子任务并行搜索的总耗时控制在 7 秒左右，而串行执行需要 15~20 秒。

### 4. 质量如何保障？

Reviewer 从相关性、完整性、准确性、结构、可读性五个维度对 Writer 输出的报告进行评分。这种设计借鉴了人工审稿流程，让系统具备初步的自我检查能力，而不是"生成完就结束"。

## 项目效果

输入一个研究问题（如"什么是 RAG 技术"）后：

1. Manager 在 5 秒内拆分为 3 个可并行子任务
2. 3 个 Researcher 在 7 秒内完成并行搜索
3. Writer 在 15 秒内生成约 3000 字的结构化 Markdown 报告
4. Reviewer 给出 5 维度质量评分

整个闭环在 **30~60 秒** 内完成，且每个步骤的输入输出都记录在消息队列中，可追溯。

## 与简单 Demo 的区别

| 简单 Demo | 本项目 |
|-----------|--------|
| 单 Agent 直接调用 LLM | 多 Agent 分工协作，角色明确 |
| 硬编码调用链 | 基于消息队列的松耦合架构，易扩展 |
| 输出自由文本，难解析 | JSON Mode 结构化输出，可被下游模块稳定消费 |
| 无质量检查 | Reviewer 五维度评分，形成闭环 |
| 仅 CLI | CLI + Web 双模式，Web 端支持 SSE 实时日志 |

## 技术栈

Python · Flask · DeepSeek API · DuckDuckGo · SSE · ThreadPoolExecutor · JSON Mode · Rich

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 API Key，支持 OpenAI / DeepSeek / 硅基流动 / OpenRouter

# CLI 模式
python run.py --mode cli

# Web 模式
python run.py --mode web --port 5000
```

## 仓库结构

```
multi_agent_orchestrator/
├── agents/              # 四层 Agent 实现
├── core/                # 消息队列与状态管理
├── web/                 # Flask + SSE 实时推送
├── cli.py               # Rich 终端界面
├── orchestrator.py      # 工作流编排
└── run.py               # 统一入口
```
