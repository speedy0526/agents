"""
FastAPI WebSocket Server - agentic 实时交互后端
"""

import os
import uuid
from pathlib import Path
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .agent import MinimalAgent
from .tools import SearchGoogleTool, FileReadTool, FileWriteTool
from .stream_manager import StreamManager


# Create FastAPI app
app = FastAPI(
    title="Agentic Interactive UI",
    description="Real-time interactive interface for agentic AI system",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    """管理 WebSocket 连接"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """建立连接"""
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        """断开连接"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    def get_connection(self, session_id: str) -> WebSocket:
        """获取连接"""
        return self.active_connections.get(session_id)


# 全局连接管理器
manager = ConnectionManager()


# Agent 实例管理器
class AgentManager:
    """管理 Agent 实例"""

    def __init__(self):
        self.agents: Dict[str, MinimalAgent] = {}

    def get_or_create_agent(self, session_id: str) -> MinimalAgent:
        """获取或创建 Agent 实例"""
        if session_id not in self.agents:
            # Get project root directory
            project_root = Path(__file__).parent.parent.absolute()

            # Define skills directories
            skills_dirs = [
                str(project_root / "skills"),
            ]

            # Create tools
            tools = [
                SearchGoogleTool(),
                FileReadTool(),
                FileWriteTool()
            ]

            # Create agent
            self.agents[session_id] = MinimalAgent(
                tools=tools,
                skills_dirs=skills_dirs
            )

        return self.agents[session_id]


agent_manager = AgentManager()


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Agentic Interactive UI",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/ws/{session_id}",
            "static": "/static/"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket 端点
    
    接收消息格式:
    {
        "event": "user_message",
        "content": "用户消息内容"
    }
    
    发送事件格式:
    {
        "event": "user_message" | "agent_thinking" | "agent_action" | 
                 "agent_result" | "agent_complete" | "error",
        "content": "事件内容",
        "metadata": {...},
        "session_id": "...",
        "timestamp": "..."
    }
    """
    await manager.connect(websocket, session_id)

    try:
        # 获取或创建 Agent
        agent = agent_manager.get_or_create_agent(session_id)

        # 创建 StreamManager
        stream_manager = StreamManager(websocket, session_id)

        # 监听用户消息
        while True:
            data = await websocket.receive_json()

            event = data.get("event")
            content = data.get("content", "")

            if event == "user_message":
                # 执行 Agent 并流式输出
                await stream_manager.stream_agent_run(
                    agent=agent,
                    user_request=content,
                    max_steps=50
                )

            elif event == "clear_context":
                # 清空上下文
                agent.clear_context()
                await stream_manager.send_event("agent_info", "Context cleared")

            elif event == "new_session":
                # 创建新会话
                new_session_id = uuid.uuid4().hex[:8]
                agent = agent_manager.get_or_create_agent(new_session_id)
                await stream_manager.send_event("new_session", new_session_id)

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"WebSocket disconnected: {session_id}")

    except Exception as e:
        # 发送错误消息
        try:
            await websocket.send_json({
                "event": "error",
                "content": str(e),
                "session_id": session_id
            })
        except:
            pass

        print(f"WebSocket error: {e}")
        manager.disconnect(session_id)


# 挂载静态文件服务
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.web_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
