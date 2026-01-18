"""
统一的错误处理模块
定义错误类型、错误码和恢复建议
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class AgentErrorType(Enum):
    """Agent 错误类型枚举"""

    # 工具相关错误
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"
    TOOL_TIMEOUT = "tool_timeout"
    TOOL_INVALID_PARAMETERS = "tool_invalid_parameters"

    # Skill 相关错误
    SKILL_NOT_FOUND = "skill_not_found"
    SKILL_EXECUTION_FAILED = "skill_execution_failed"
    SKILL_MISSING_TOOLS = "skill_missing_tools"
    SKILL_TIMEOUT = "skill_timeout"

    # Chain 相关错误
    CHAIN_INVALID_FORMAT = "chain_invalid_format"
    CHAIN_STEP_FAILED = "chain_step_failed"
    CHAIN_TIMEOUT = "chain_timeout"

    # Agent 相关错误
    AGENT_TIMEOUT = "agent_timeout"
    AGENT_MAX_STEPS_REACHED = "agent_max_steps_reached"
    AGENT_CONTEXT_ERROR = "agent_context_error"

    # WebSocket 相关错误
    WEBSOCKET_CONNECTION_ERROR = "websocket_connection_error"
    WEBSOCKET_SEND_ERROR = "websocket_send_error"

    # 通用错误
    UNKNOWN_ERROR = "unknown_error"


class ErrorCode(Enum):
    """错误码枚举"""

    # 工具错误码: ERR_TOOL_XXX
    ERR_TOOL_001 = "ERR_TOOL_001"
    ERR_TOOL_002 = "ERR_TOOL_002"
    ERR_TOOL_003 = "ERR_TOOL_003"
    ERR_TOOL_004 = "ERR_TOOL_004"

    # Skill 错误码: ERR_SKILL_XXX
    ERR_SKILL_001 = "ERR_SKILL_001"
    ERR_SKILL_002 = "ERR_SKILL_002"
    ERR_SKILL_003 = "ERR_SKILL_003"
    ERR_SKILL_004 = "ERR_SKILL_004"

    # Chain 错误码: ERR_CHAIN_XXX
    ERR_CHAIN_001 = "ERR_CHAIN_001"
    ERR_CHAIN_002 = "ERR_CHAIN_002"
    ERR_CHAIN_003 = "ERR_CHAIN_003"

    # Agent 错误码: ERR_AGENT_XXX
    ERR_AGENT_001 = "ERR_AGENT_001"
    ERR_AGENT_002 = "ERR_AGENT_002"
    ERR_AGENT_003 = "ERR_AGENT_003"

    # WebSocket 错误码: ERR_WS_XXX
    ERR_WS_001 = "ERR_WS_001"
    ERR_WS_002 = "ERR_WS_002"

    # 通用错误码
    ERR_UNKNOWN = "ERR_UNKNOWN"


@dataclass
class AgentError:
    """Agent 错误数据类"""

    error_type: AgentErrorType
    error_code: ErrorCode
    message: str
    details: Optional[str] = None
    suggestions: List[str] = None
    recovery_actions: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """初始化后处理，确保列表不为 None"""
        if self.suggestions is None:
            self.suggestions = []
        if self.recovery_actions is None:
            self.recovery_actions = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 WebSocket 发送）"""
        return {
            "error_type": self.error_type.value,
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details,
            "suggestions": self.suggestions,
            "recovery_actions": self.recovery_actions,
            "metadata": self.metadata,
        }


class ErrorHandler:
    """错误处理器 - 统一错误处理和建议生成"""

    # 错误类型与错误码的映射
    ERROR_CODE_MAPPING: Dict[AgentErrorType, ErrorCode] = {
        # 工具错误
        AgentErrorType.TOOL_NOT_FOUND: ErrorCode.ERR_TOOL_001,
        AgentErrorType.TOOL_EXECUTION_FAILED: ErrorCode.ERR_TOOL_002,
        AgentErrorType.TOOL_TIMEOUT: ErrorCode.ERR_TOOL_003,
        AgentErrorType.TOOL_INVALID_PARAMETERS: ErrorCode.ERR_TOOL_004,

        # Skill 错误
        AgentErrorType.SKILL_NOT_FOUND: ErrorCode.ERR_SKILL_001,
        AgentErrorType.SKILL_EXECUTION_FAILED: ErrorCode.ERR_SKILL_002,
        AgentErrorType.SKILL_MISSING_TOOLS: ErrorCode.ERR_SKILL_003,
        AgentErrorType.SKILL_TIMEOUT: ErrorCode.ERR_SKILL_004,

        # Chain 错误
        AgentErrorType.CHAIN_INVALID_FORMAT: ErrorCode.ERR_CHAIN_001,
        AgentErrorType.CHAIN_STEP_FAILED: ErrorCode.ERR_CHAIN_002,
        AgentErrorType.CHAIN_TIMEOUT: ErrorCode.ERR_CHAIN_003,

        # Agent 错误
        AgentErrorType.AGENT_TIMEOUT: ErrorCode.ERR_AGENT_001,
        AgentErrorType.AGENT_MAX_STEPS_REACHED: ErrorCode.ERR_AGENT_002,
        AgentErrorType.AGENT_CONTEXT_ERROR: ErrorCode.ERR_AGENT_003,

        # WebSocket 错误
        AgentErrorType.WEBSOCKET_CONNECTION_ERROR: ErrorCode.ERR_WS_001,
        AgentErrorType.WEBSOCKET_SEND_ERROR: ErrorCode.ERR_WS_002,

        # 通用错误
        AgentErrorType.UNKNOWN_ERROR: ErrorCode.ERR_UNKNOWN,
    }

    # 错误建议映射
    ERROR_SUGGESTIONS: Dict[AgentErrorType, List[str]] = {
        # 工具错误建议
        AgentErrorType.TOOL_NOT_FOUND: [
            "检查工具名称是否拼写正确",
            "查看可用工具列表",
            "确认工具已正确注册",
        ],
        AgentErrorType.TOOL_EXECUTION_FAILED: [
            "检查工具参数是否完整和正确",
            "查看工具执行日志获取详细信息",
            "尝试使用其他可用工具",
            "检查网络连接（如果需要网络访问）",
        ],
        AgentErrorType.TOOL_TIMEOUT: [
            "检查网络连接是否稳定",
            "尝试减小任务规模",
            "查看服务器状态",
        ],
        AgentErrorType.TOOL_INVALID_PARAMETERS: [
            "检查参数类型和格式",
            "查看工具文档了解参数要求",
            "确认必需参数已提供",
        ],

        # Skill 错误建议
        AgentErrorType.SKILL_NOT_FOUND: [
            "检查 skill 名称是否正确",
            "查看可用 skills 列表",
            "确认 skill 文件已正确放置在 skills 目录",
        ],
        AgentErrorType.SKILL_EXECUTION_FAILED: [
            "查看 skill 执行日志",
            "检查 skill 依赖的工具是否可用",
            "尝试重新执行 skill",
        ],
        AgentErrorType.SKILL_MISSING_TOOLS: [
            "确认所需工具已注册",
            "检查工具配置",
            "使用其他可用的替代工具",
        ],
        AgentErrorType.SKILL_TIMEOUT: [
            "检查网络连接",
            "尝试简化任务",
            "增加超时时间",
        ],

        # Chain 错误建议
        AgentErrorType.CHAIN_INVALID_FORMAT: [
            "检查 chain 定义的 JSON 格式",
            "确认每个步骤都有必需字段",
            "查看 chain 定义示例",
        ],
        AgentErrorType.CHAIN_STEP_FAILED: [
            "查看失败步骤的详细错误信息",
            "检查步骤配置是否正确",
            "尝试单独执行失败的步骤",
        ],
        AgentErrorType.CHAIN_TIMEOUT: [
            "检查整体执行时间",
            "尝试减少 chain 步骤",
            "优化每个步骤的执行效率",
        ],

        # Agent 错误建议
        AgentErrorType.AGENT_TIMEOUT: [
            "检查任务复杂度",
            "尝试分解任务为更小的步骤",
            "增加最大执行步数限制",
        ],
        AgentErrorType.AGENT_MAX_STEPS_REACHED: [
            "查看执行日志了解进展",
            "尝试更明确的任务描述",
            "增加最大步数限制",
            "优化任务流程",
        ],
        AgentErrorType.AGENT_CONTEXT_ERROR: [
            "检查上下文长度",
            "尝试清空部分历史记录",
            "重新开始任务",
        ],

        # WebSocket 错误建议
        AgentErrorType.WEBSOCKET_CONNECTION_ERROR: [
            "检查网络连接",
            "刷新页面重新连接",
            "检查服务器是否运行",
        ],
        AgentErrorType.WEBSOCKET_SEND_ERROR: [
            "刷新页面",
            "检查浏览器控制台错误",
            "重新连接 WebSocket",
        ],

        # 通用错误建议
        AgentErrorType.UNKNOWN_ERROR: [
            "查看详细错误日志",
            "尝试重新执行任务",
            "联系技术支持",
        ],
    }

    # 恢复操作映射
    RECOVERY_ACTIONS: Dict[AgentErrorType, List[str]] = {
        AgentErrorType.TOOL_NOT_FOUND: ["查看可用工具", "重试"],
        AgentErrorType.TOOL_EXECUTION_FAILED: ["重试", "查看日志", "使用其他工具"],
        AgentErrorType.TOOL_TIMEOUT: ["重试", "检查网络"],
        AgentErrorType.TOOL_INVALID_PARAMETERS: ["修改参数", "查看文档"],

        AgentErrorType.SKILL_NOT_FOUND: ["查看可用 skills", "重试"],
        AgentErrorType.SKILL_EXECUTION_FAILED: ["重试", "查看日志"],
        AgentErrorType.SKILL_MISSING_TOOLS: ["检查工具配置", "使用替代方案"],
        AgentErrorType.SKILL_TIMEOUT: ["重试", "简化任务"],

        AgentErrorType.CHAIN_INVALID_FORMAT: ["检查配置", "查看示例"],
        AgentErrorType.CHAIN_STEP_FAILED: ["重试步骤", "查看详细日志"],
        AgentErrorType.CHAIN_TIMEOUT: ["重试", "优化流程"],

        AgentErrorType.AGENT_TIMEOUT: ["重试", "分解任务"],
        AgentErrorType.AGENT_MAX_STEPS_REACHED: ["增加步数", "优化描述"],
        AgentErrorType.AGENT_CONTEXT_ERROR: ["清空上下文", "重新开始"],

        AgentErrorType.WEBSOCKET_CONNECTION_ERROR: ["刷新页面", "检查服务器"],
        AgentErrorType.WEBSOCKET_SEND_ERROR: ["刷新页面", "重新连接"],

        AgentErrorType.UNKNOWN_ERROR: ["重试", "查看日志", "联系支持"],
    }

    @classmethod
    def handle_tool_error(cls, tool_name: str, error: Exception) -> AgentError:
        """处理工具执行错误"""
        error_msg = str(error)

        # 根据错误消息判断具体错误类型
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            error_type = AgentErrorType.TOOL_NOT_FOUND
        elif "timeout" in error_msg.lower():
            error_type = AgentErrorType.TOOL_TIMEOUT
        elif "parameter" in error_msg.lower() or "argument" in error_msg.lower():
            error_type = AgentErrorType.TOOL_INVALID_PARAMETERS
        else:
            error_type = AgentErrorType.TOOL_EXECUTION_FAILED

        return cls.create_error(
            error_type=error_type,
            message=f"工具 '{tool_name}' 执行失败: {error_msg}",
            details=f"错误类型: {type(error).__name__}\n错误消息: {error_msg}",
            metadata={"tool_name": tool_name, "error_class": type(error).__name__},
        )

    @classmethod
    def handle_skill_error(cls, skill_name: str, error: Exception) -> AgentError:
        """处理 Skill 执行错误"""
        error_msg = str(error)

        if "not found" in error_msg.lower():
            error_type = AgentErrorType.SKILL_NOT_FOUND
        elif "timeout" in error_msg.lower():
            error_type = AgentErrorType.SKILL_TIMEOUT
        elif "missing tools" in error_msg.lower() or "required tools" in error_msg.lower():
            error_type = AgentErrorType.SKILL_MISSING_TOOLS
        else:
            error_type = AgentErrorType.SKILL_EXECUTION_FAILED

        return cls.create_error(
            error_type=error_type,
            message=f"Skill '{skill_name}' 执行失败: {error_msg}",
            details=f"错误类型: {type(error).__name__}\n错误消息: {error_msg}",
            metadata={"skill_name": skill_name, "error_class": type(error).__name__},
        )

    @classmethod
    def handle_chain_error(cls, error: Exception) -> AgentError:
        """处理 Chain 执行错误"""
        error_msg = str(error)

        if "JSON" in error_msg or "format" in error_msg.lower():
            error_type = AgentErrorType.CHAIN_INVALID_FORMAT
        elif "timeout" in error_msg.lower():
            error_type = AgentErrorType.CHAIN_TIMEOUT
        else:
            error_type = AgentErrorType.CHAIN_STEP_FAILED

        return cls.create_error(
            error_type=error_type,
            message=f"Chain 执行失败: {error_msg}",
            details=f"错误类型: {type(error).__name__}\n错误消息: {error_msg}",
        )

    @classmethod
    def handle_agent_error(cls, error: Exception, context: str = "") -> AgentError:
        """处理 Agent 执行错误"""
        error_msg = str(error)

        if "timeout" in error_msg.lower():
            error_type = AgentErrorType.AGENT_TIMEOUT
        elif "max steps" in error_msg.lower() or "maximum steps" in error_msg.lower():
            error_type = AgentErrorType.AGENT_MAX_STEPS_REACHED
        elif "context" in error_msg.lower():
            error_type = AgentErrorType.AGENT_CONTEXT_ERROR
        else:
            error_type = AgentErrorType.UNKNOWN_ERROR

        return cls.create_error(
            error_type=error_type,
            message=f"Agent 执行错误: {error_msg}",
            details=f"上下文: {context}\n错误类型: {type(error).__name__}\n错误消息: {error_msg}",
        )

    @classmethod
    def handle_websocket_error(cls, error: Exception) -> AgentError:
        """处理 WebSocket 错误"""
        error_msg = str(error)

        if "connection" in error_msg.lower():
            error_type = AgentErrorType.WEBSOCKET_CONNECTION_ERROR
        else:
            error_type = AgentErrorType.WEBSOCKET_SEND_ERROR

        return cls.create_error(
            error_type=error_type,
            message=f"WebSocket 错误: {error_msg}",
            details=f"错误类型: {type(error).__name__}\n错误消息: {error_msg}",
        )

    @classmethod
    def create_error(
        cls,
        error_type: AgentErrorType,
        message: str,
        details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentError:
        """
        创建统一的错误对象

        Args:
            error_type: 错误类型
            message: 错误消息
            details: 详细错误信息
            metadata: 额外的元数据

        Returns:
            AgentError 对象
        """
        error_code = cls.ERROR_CODE_MAPPING.get(error_type, ErrorCode.ERR_UNKNOWN)
        suggestions = cls.ERROR_SUGGESTIONS.get(error_type, [])
        recovery_actions = cls.RECOVERY_ACTIONS.get(error_type, [])

        return AgentError(
            error_type=error_type,
            error_code=error_code,
            message=message,
            details=details,
            suggestions=suggestions,
            recovery_actions=recovery_actions,
            metadata=metadata or {},
        )
