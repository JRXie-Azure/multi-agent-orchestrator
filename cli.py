"""Rich 美化终端 CLI"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.spinner import Spinner

from orchestrator import Orchestrator
from core.state import TaskState
import config


console = Console()


def make_status_table(task: TaskState) -> Table:
    """构建状态表格"""
    table = Table(title=f"任务 {task.task_id} 状态", expand=True)
    table.add_column("Agent", style="cyan", no_wrap=True)
    table.add_column("动作", style="green")
    table.add_column("详情", style="dim")
    table.add_column("时间", style="yellow", no_wrap=True)

    for log in task.logs[-10:]:
        ts = log.get("timestamp", "")[11:19]
        table.add_row(
            log.get("agent", ""),
            log.get("action", ""),
            log.get("detail", "")[:50],
            ts,
        )
    return table


def run_cli():
    """运行 CLI 模式"""
    console.print(Panel.fit(
        "[bold blue]Multi-Agent Orchestrator[/bold blue]\n"
        "[dim]面向复杂研究场景的多 Agent 协作系统[/dim]",
        border_style="blue",
    ))

    if not config.OPENAI_API_KEY:
        console.print("[red]错误: 未设置 OPENAI_API_KEY，请在 .env 文件中配置。[/red]")
        console.print("示例: OPENAI_API_KEY=sk-xxxx")
        sys.exit(1)

    query = console.input("[bold green]请输入研究问题: [/bold green]").strip()
    if not query:
        console.print("[yellow]输入为空，退出。[/yellow]")
        return

    orch = Orchestrator()

    with Live(console=console, refresh_per_second=4) as live:
        def on_progress(task: TaskState):
            layout = Layout()
            layout.split_column(
                Layout(Panel(f"[bold]当前状态:[/bold] {task.status}", style="blue")),
                Layout(make_status_table(task)),
            )
            live.update(layout)

        task = orch.run(query, progress_callback=on_progress)

        # 等待任务完成（轮询）
        while task.status not in ("completed", "failed", "needs_revision"):
            time.sleep(0.5)

    # 输出最终结果
    console.print("\n[bold green]" + "=" * 50 + "[/bold green]")
    console.print("[bold green]研究完成！[/bold green]")

    if task.report:
        console.print(Panel(Markdown(task.report), title="研究报告", border_style="green"))

    if task.review_result and isinstance(task.review_result, dict):
        score = task.review_result.get("overall_score", "N/A")
        verdict = task.review_result.get("verdict", "N/A")
        console.print(f"[bold]审查评分:[/bold] {score}/10  [bold]结论:[/bold] {verdict}")

    # 保存报告
    filename = f"report_{task.task_id}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# 研究报告\n\n**原始问题**: {task.original_query}\n\n")
        f.write(task.report or "")
        f.write(f"\n\n---\n\n**审查结果**: {task.review_result}\n")
    console.print(f"[dim]报告已保存至: {filename}[/dim]")


if __name__ == "__main__":
    run_cli()
