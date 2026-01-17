"""
Agentic Web UI - Main Entry Point
启动 FastAPI WebSocket 服务器，提供实时交互界面
"""

import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import uvicorn


def main():
    """启动 Web 服务器"""

    print("=" * 60)
    print("Agentic Interactive UI")
    print("=" * 60)
    print(f"Project Root: {project_root}")
    print(f"Static Files: {project_root / 'static'}")
    print(f"WebSocket Endpoint: ws://localhost:8001/ws/{{session_id}}")
    print(f"Web UI: http://localhost:8001/")
    print("=" * 60)
    print()

    # 启动 uvicorn 服务器
    uvicorn.run(
        "src.web_server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
