---
name: unify-session-concept
overview: 统一使用 Session 概念，修改前端将 Agent 改为 Session，确保与后端 API 完全兼容。
todos:
  - id: explore-codebase
    content: 使用 [subagent:code-explorer] 搜索所有 Agent 相关文件和引用
    status: completed
  - id: update-types
    content: 更新类型定义，将 Agent 接口改为 Session
    status: completed
    dependencies:
      - explore-codebase
  - id: update-api-service
    content: 更新 API 服务，使用 /api/sessions 端点
    status: completed
    dependencies:
      - explore-codebase
  - id: rename-components
    content: 重命名所有 Agent 相关组件为 Session 组件
    status: completed
    dependencies:
      - update-types
  - id: update-websocket
    content: 更新 WebSocket 连接路径为 /ws/{client_id}
    status: completed
    dependencies:
      - update-api-service
  - id: update-state-management
    content: 更新状态管理 hooks 和 stores
    status: completed
    dependencies:
      - update-types
  - id: verify-compatibility
    content: 验证前后端 API 兼容性
    status: completed
    dependencies:
      - rename-components
      - update-websocket
      - update-state-management
---

## Product Overview

统一前后端概念，将前端代码中的 Agent 概念改为 Session，确保与后端 API 端点 /api/sessions 和 WebSocket 路径 /ws/{client_id} 完全兼容。

## Core Features

- 将前端所有 Agent 相关的组件、状态管理、API 调用重命名为 Session
- 更新数据类型定义，使用 Session 替代 Agent
- 确保前端 API 调用与后端 /api/sessions 端点匹配
- 更新 WebSocket 连接逻辑，使用 /ws/{client_id} 路径
- 更新路由配置和导航链接
- 更新用户界面文本和提示信息

## Tech Stack

- 重构现有前端代码，保持原技术栈不变
- 类型定义更新：TypeScript 接口重命名

## Tech Architecture

### System Architecture

保持现有架构不变，仅进行概念层面的重构。

### Module Division

- **类型定义模块**: 更新 TypeScript 接口定义
- **API 服务模块**: 更新 API 端点路径和参数
- **组件模块**: 更新组件名称和引用
- **状态管理模块**: 更新状态变量和 actions
- **路由模块**: 更新路由配置

### Data Flow

前端组件 → API 调用 (/api/sessions) → 后端处理 → WebSocket (/ws/{client_id}) 实时通信

## Implementation Details

### Core Directory Structure

```
project-root/
├── src/
│   ├── types/
│   │   ├── session.ts        # 重命名或新增：Session 类型定义
│   │   └── agent.ts          # 删除或废弃：Agent 类型定义
│   ├── services/
│   │   └── sessionService.ts # 更新：Session API 服务
│   ├── components/
│   │   ├── SessionList.tsx   # 重命名：Session 列表组件
│   │   └── SessionItem.tsx   # 重命名：Session 列表项组件
│   ├── hooks/
│   │   └── useSessions.ts    # 重命名：Session 状态管理 hooks
│   └── pages/
│       └── Sessions.tsx      # 重命名：Session 页面
```

### Key Code Structures

**Session 接口**: 定义 Session 的核心数据结构

```typescript
interface Session {
  id: string;
  clientId: string;
  status: 'active' | 'inactive' | 'closed';
  createdAt: Date;
  updatedAt: Date;
}
```

**SessionService 类**: 处理 Session 相关的 API 调用

```typescript
class SessionService {
  async fetchSessions(): Promise<Session[]> { }
  async createSession(data: CreateSessionDTO): Promise<Session> { }
  async updateSession(id: string, data: Partial<Session>): Promise<void> { }
  async deleteSession(id: string): Promise<void> { }
}
```

### Technical Implementation Plan

1. **代码探索与定位**

- 搜索所有包含 "agent" 和 "Agent" 的文件
- 识别所有需要修改的组件、类型、服务
- 建立修改清单和依赖关系

2. **类型定义重构**

- 创建新的 Session 类型定义
- 迁移 Agent 类型字段到 Session
- 更新所有类型引用

3. **API 服务更新**

- 更新 API 端点为 /api/sessions
- 更新 WebSocket 连接为 /ws/{client_id}
- 更新请求和响应数据结构

4. **组件重命名与更新**

- 重命名所有 Agent 相关组件
- 更新组件内部状态和逻辑
- 更新组件 props 接口

5. **状态管理重构**

- 更新状态管理 hooks 和 stores
- 更新 action 和 reducer 命名
- 确保状态数据结构一致

### Integration Points

- 后端 API: /api/sessions (RESTful)
- WebSocket: /ws/{client_id} (实时通信)
- 数据格式: JSON

## Agent Extensions

### SubAgent

- **code-explorer**
- Purpose: 搜索并定位代码库中所有使用 Agent 概念的文件，包括组件、类型定义、API 服务等
- Expected outcome: 完整的文件列表和代码位置，包含所有需要重构的代码片段