"""统一入口：支持 CLI 和 Web 两种模式"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Orchestrator")
    parser.add_argument("--mode", choices=["cli", "web"], default="cli", help="运行模式")
    parser.add_argument("--port", type=int, default=None, help="Web 服务端口")
    args = parser.parse_args()

    if args.mode == "cli":
        from cli import run_cli
        run_cli()
    else:
        from web.app import run_web
        import config
        if args.port:
            config.WEB_PORT = args.port
        run_web()


if __name__ == "__main__":
    main()
