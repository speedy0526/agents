/**
 * Agentic Interactive UI - WebSocket Client
 * 
 * 实现 WebSocket 通信、消息渲染和交互逻辑
 */

// 全局变量
let ws = null;
let sessionId = null;
let isConnected = false;
let isExecuting = false;

// 流式消息累积
let currentThinkingElement = null;
let currentThinkingContent = '';
let currentActionElement = null;
let currentThinkingCursor = null;

// 等待状态移除标记
let thinkingWaitingRemoved = false;

// 内容chunk计数
let thinkingChunkCount = 0;

// 动态状态文字
let thinkingStatusTexts = ['思考中', '分析中', '推理中'];
let thinkingStatusIndex = 0;
let thinkingStatusTimer = null;

let actionStatusTexts = ['执行中', '处理中', '完成中'];
let actionStatusIndex = 0;
let actionStatusTimer = null;

// 执行进度跟踪
const executionProgress = {
    currentStep: 0,
    totalSteps: 0,
    startTime: null,
    elapsed: 0,
    progress: 0
};

// DOM 元素引用
const elements = {
    messagesContainer: null,
    messageInput: null,
    sendButton: null,
    executionTimeline: null,
    statusDot: null,
    statusText: null,
    statusIndicator: null,
    sessionId: null,
    connectionInfo: null,
    executionProgressContainer: null,
    progressBar: null,
    progressStats: null,
    progressSteps: null,
    sessionHistoryBtn: null,
    sessionHistoryMenu: null,
    sessionHistoryList: null
};

// 会话管理
const SESSION_STORAGE_KEY = 'agentic_sessions';
const MAX_SESSIONS = 20;
let sessions = [];
let currentSessionData = {
    messages: [],
    timeline: [],
    task: '',
    status: 'idle',
    steps: 0
};

/**
 * 初始化应用
 */
function init() {
    // 获取 DOM 元素
    elements.messagesContainer = document.getElementById('messagesContainer');
    elements.messageInput = document.getElementById('messageInput');
    elements.sendButton = document.getElementById('sendButton');
    elements.executionTimeline = document.getElementById('executionTimeline');
    elements.statusDot = document.getElementById('statusDot');
    elements.statusText = document.getElementById('statusText');
    elements.statusIndicator = document.getElementById('statusIndicator');
    elements.sessionId = document.getElementById('sessionId');
    elements.connectionInfo = document.getElementById('connectionInfo');

    // 获取进度条元素
    elements.executionProgressContainer = document.getElementById('executionProgressContainer');
    elements.progressStats = document.getElementById('progressStats');
    elements.progressSteps = document.getElementById('progressSteps');
    
    // 获取会话历史相关元素
    elements.sessionHistoryBtn = document.getElementById('sessionHistoryBtn');
    elements.sessionHistoryMenu = document.getElementById('sessionHistoryMenu');
    elements.sessionHistoryList = document.getElementById('sessionHistoryList');
    
    // 加载会话历史
    loadSessions();
    
    // 绑定会话历史事件
    bindSessionEvents();

    // 生成会话 ID
    sessionId = generateSessionId();
    updateSessionIdDisplay(sessionId);

    // 连接 WebSocket
    connectWebSocket();

    // 绑定事件
    elements.sendButton.addEventListener('click', sendMessage);
    elements.messageInput.addEventListener('input', handleInput);
}

/**
 * 生成会话 ID
 */
function generateSessionId() {
    return Math.random().toString(36).substring(2, 10);
}

/**
 * 更新会话 ID 显示
 */
function updateSessionIdDisplay(id) {
    if (elements.sessionId) {
        elements.sessionId.textContent = id;
    }
}

/**
 * 连接 WebSocket
 */
function connectWebSocket() {
    updateConnectionStatus('connecting', '连接中...');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/${sessionId}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = handleWebSocketOpen;
    ws.onmessage = handleWebSocketMessage;
    ws.onerror = handleWebSocketError;
    ws.onclose = handleWebSocketClose;
}

/**
 * WebSocket 连接打开处理
 */
function handleWebSocketOpen() {
    isConnected = true;
    updateConnectionStatus('connected', '已连接');
    console.log('WebSocket connected');
}

/**
 * WebSocket 消息处理
 */
function handleWebSocketMessage(event) {
    try {
        const data = JSON.parse(event.data);
        handleEvent(data);
    } catch (error) {
        console.error('Failed to parse message:', error);
    }
}

/**
 * 处理不同类型的事件
 */
function handleEvent(data) {
    const { event, content, metadata } = data;

    switch (event) {
        case 'user_message':
            // 用户消息（由客户端发送，不处理）
            break;

        case 'agent_thinking':
            handleAgentThinking(content, metadata);
            break;

        case 'agent_action':
            handleAgentAction(content, metadata);
            break;

        case 'agent_result':
            handleAgentResult(content, metadata);
            break;

        case 'agent_complete':
            handleAgentComplete(content);
            break;

        case 'agent_info':
            handleAgentInfo(content);
            break;

        case 'new_session':
            handleNewSession(content);
            break;

        case 'error':
            handleError(content);
            break;

        case 'error_enhanced':
            handleEnhancedError(content, metadata);
            break;

        default:
            console.log('Unknown event:', event);
    }
}

/**
 * 创建闪烁光标元素
 */
function createTypingCursor() {
    const cursor = document.createElement('span');
    cursor.className = 'typing-cursor';
    cursor.innerHTML = '|';
    return cursor;
}

/**
 * 移除光标元素
 */
function removeTypingCursor(element) {
    const cursor = element.querySelector('.typing-cursor');
    if (cursor) {
        cursor.remove();
    }
}

/**
 * 重置思考状态
 */
function resetThinkingState() {
    if (currentThinkingElement) {
        removeTypingCursor(currentThinkingElement);
    }
    currentThinkingElement = null;
    currentThinkingContent = '';
    currentThinkingCursor = null;
    thinkingWaitingRemoved = false;
    thinkingChunkCount = 0;
    thinkingStatusIndex = 0;
    
    // 停止动态状态文字更新
    if (thinkingStatusTimer) {
        clearInterval(thinkingStatusTimer);
        thinkingStatusTimer = null;
    }
}

/**
 * 重置动作状态
 */
function resetActionState() {
    if (currentActionElement) {
        removeTypingCursor(currentActionElement);
    }
    currentActionElement = null;
    actionStatusIndex = 0;
    
    // 停止动态状态文字更新
    if (actionStatusTimer) {
        clearInterval(actionStatusTimer);
        actionStatusTimer = null;
    }
}

/**
 * 判断是否是子代理事件
 * 子代理事件不在对话区域显示，只在时间轴中显示
 */
function isSubagentEvent(metadata) {
    return metadata?.subagent_id !== undefined;
}

/**
 * 更新思考状态文字
 */
function updateThinkingStatusText() {
    if (!currentThinkingElement || thinkingWaitingRemoved) return;
    
    thinkingStatusIndex = (thinkingStatusIndex + 1) % thinkingStatusTexts.length;
    const statusText = thinkingStatusTexts[thinkingStatusIndex];
    updateMessageExecutingStatus(currentThinkingElement, true, statusText);
}

/**
 * 处理 Agent 思考事件
 */
function handleAgentThinking(content, metadata) {
    // 判断是否是子代理事件
    const isSubagent = isSubagentEvent(metadata);

    // 子代理思考事件只在时间轴显示，不添加到对话区域
    if (!isSubagent) {
        // 累积内容到当前思考消息
        if (!currentThinkingElement) {
            // 第一次收到思考内容，创建空消息并显示等待状态
            addMessage('thinking', '', metadata);
            // 获取刚创建的消息内容元素
            const messages = elements.messagesContainer.querySelectorAll('.message.thinking .message-content');
            currentThinkingElement = messages[messages.length - 1];

            // 显示等待状态
            updateMessageExecutingStatus(currentThinkingElement, true, '思考中');
            thinkingStatusIndex = 0;
            
            // 启动动态状态文字更新
            if (thinkingStatusTimer) {
                clearInterval(thinkingStatusTimer);
            }
            thinkingStatusTimer = setInterval(updateThinkingStatusText, 1500);

            currentThinkingContent = '';
            currentThinkingCursor = createTypingCursor();
            currentThinkingElement.appendChild(currentThinkingCursor);
            thinkingChunkCount = 0;
            thinkingWaitingRemoved = false;
        }
        
        // 实时更新思考内容（保留光标）
        currentThinkingContent += content;

        // 先移除光标，再更新内容，最后重新添加光标
        if (currentThinkingCursor && currentThinkingCursor.parentNode === currentThinkingElement) {
            currentThinkingCursor.remove();
        }

        currentThinkingElement.innerHTML = formatMessage(currentThinkingContent);
        currentThinkingElement.appendChild(currentThinkingCursor);

        // 滚动到底部以显示最新内容
        scrollToBottom();
        
        // 延迟移除等待状态（等待至少3个chunk或500ms）
        thinkingChunkCount++;
        if (!thinkingWaitingRemoved && thinkingChunkCount >= 3) {
            updateMessageExecutingStatus(currentThinkingElement, false);
            thinkingWaitingRemoved = true;
            
            // 停止动态状态文字更新
            if (thinkingStatusTimer) {
                clearInterval(thinkingStatusTimer);
                thinkingStatusTimer = null;
            }
        }
    }

    // 添加到执行时间轴（所有事件都添加）
    if (metadata && metadata.step) {
        addTimelineItem('thinking', '思考', content, metadata);
    }

    // 更新执行状态
    isExecuting = true;
    updateSendButtonState();
}

/**
 * 处理 Agent 动作事件
 */
function handleAgentAction(content, metadata) {
    const actionType = metadata?.action_type || '执行动作';
    const description = content;

    // 判断是否是子代理事件
    const isSubagent = isSubagentEvent(metadata);

    // 初始化进度（第一次执行动作时）
    if (metadata?.step_number && metadata?.total_steps && executionProgress.totalSteps === 0) {
        initExecutionProgress(metadata.total_steps);
    }

    // 更新进度
    if (metadata?.step_number) {
        updateExecutionProgress(metadata.step_number, metadata.elapsed || executionProgress.elapsed);
    }

    // 移除思考消息的光标并重置
    resetThinkingState();

    // 子代理动作事件只在时间轴显示，不添加到对话区域
    if (!isSubagent) {
        // 添加到消息列表
        addMessage('action', `${actionType}: ${description}`, metadata);

        // 获取刚创建的消息内容元素，并显示等待状态
        const messages = elements.messagesContainer.querySelectorAll('.message.action .message-content');
        currentActionElement = messages[messages.length - 1];

        // 根据不同类型显示不同的等待文本
        let statusText = '执行中';
        let baseStatusText = '执行中';
        if (metadata?.tool_name) {
            baseStatusText = `调用工具: ${metadata.tool_name}`;
        } else if (metadata?.subagent_command) {
            baseStatusText = `调用技能: ${metadata.subagent_command}`;
        }
        
        // 如果有步骤信息，添加进度提示
        if (metadata?.step_number && metadata?.total_steps) {
            statusText = `${baseStatusText} (步骤 ${metadata.step_number}/${metadata.total_steps})`;
        } else {
            statusText = baseStatusText;
        }
        
        updateMessageExecutingStatus(currentActionElement, true, statusText);
        actionStatusIndex = 0;
        
        // 启动动态状态文字更新（仅在无步骤信息时）
        if (!metadata?.step_number) {
            if (actionStatusTimer) {
                clearInterval(actionStatusTimer);
            }
            actionStatusTimer = setInterval(() => {
                if (!currentActionElement || actionWaitingRemoved) return;
                
                actionStatusIndex = (actionStatusIndex + 1) % actionStatusTexts.length;
                const newText = actionStatusTexts[actionStatusIndex];
                if (metadata?.tool_name) {
                    updateMessageExecutingStatus(currentActionElement, true, `${newText}: ${metadata.tool_name}`);
                } else if (metadata?.subagent_command) {
                    updateMessageExecutingStatus(currentActionElement, true, `${newText}: ${metadata.subagent_command}`);
                } else {
                    updateMessageExecutingStatus(currentActionElement, true, newText);
                }
            }, 1500);
        }
    }

    // 添加到执行时间轴（所有事件都添加）
    addTimelineItem('action', actionType, description, metadata);
}

/**
 * 处理 Agent 结果事件
 */
function handleAgentResult(content, metadata) {
    // 移除动作消息的等待状态
    resetActionState();

    // 移除思考消息的光标并重置
    resetThinkingState();

    // 判断是否是子代理事件
    const isSubagent = isSubagentEvent(metadata);

    // 子代理结果事件只在时间轴显示，不添加到对话区域
    // 除非是主代理的成功结果
    if (!isSubagent && metadata?.success !== false) {
        // 添加到消息列表
        addMessage('result', content, metadata);
    }

    // 添加到执行时间轴（所有事件都添加）
    addTimelineItem('result', '结果', content, metadata);
}

/**
 * 处理 Agent 完成事件
 */
function handleAgentComplete(content) {
    // 移除动作消息的等待状态（如果有）
    resetActionState();

    // 移除思考消息的光标并重置
    resetThinkingState();

    // 完成执行进度
    if (executionProgress.totalSteps > 0) {
        completeExecutionProgress();
    }

    // 添加到消息列表
    addMessage('assistant', content);

    // 更新任务概览为已完成
    updateTaskOverview(null, 'completed', executionProgress.currentStep);

    // 保存当前会话到历史
    saveCurrentSession();

    // 完成执行
    isExecuting = false;
    updateSendButtonState();

    // 滚动到底部
    scrollToBottom();
}

/**
 * 处理 Agent 信息事件
 */
function handleAgentInfo(content) {
    // 显示系统信息
    addMessage('system', content);

    // 如果是中止信息，重置执行状态
    if (content.includes('中止') || content.includes('aborted')) {
        isExecuting = false;
        updateSendButtonState();
    }
}

/**
 * 处理新会话事件
 */
function handleNewSession(newSessionId) {
    sessionId = newSessionId;
    updateSessionIdDisplay(sessionId);

    // 重新连接
    if (ws) {
        ws.close();
    }
    setTimeout(() => connectWebSocket(), 500);
}

/**
 * 处理错误事件
 */
function handleError(content) {
    // 移除动作消息的等待状态（如果有）
    resetActionState();

    // 移除思考消息的光标并重置
    resetThinkingState();

    // 添加错误消息
    addMessage('error', content);

    // 添加到执行时间轴
    addTimelineItem('error', '错误', content);

    // 更新任务概览为错误状态
    updateTaskOverview(null, 'error', executionProgress.currentStep);

    // 完成执行
    isExecuting = false;
    updateSendButtonState();
}

/**
 * 处理增强的错误事件
 */
function handleEnhancedError(content, metadata) {
    // 移除动作消息的等待状态（如果有）
    resetActionState();

    // 移除思考消息的光标并重置
    resetThinkingState();

    // 添加增强的错误消息
    addEnhancedErrorMessage(content, metadata);

    // 添加到执行时间轴
    addTimelineItem('error', '错误', content, metadata);

    // 完成执行
    isExecuting = false;
    updateSendButtonState();
}

/**
 * WebSocket 错误处理
 */
function handleWebSocketError(error) {
    console.error('WebSocket error:', error);
    updateConnectionStatus('disconnected', '连接错误');
}

/**
 * WebSocket 关闭处理
 */
function handleWebSocketClose() {
    isConnected = false;
    updateConnectionStatus('disconnected', '未连接');

    // 5秒后自动重连
    setTimeout(() => {
        if (!isConnected) {
            connectWebSocket();
        }
    }, 5000);
}

/**
 * 更新连接状态
 */
function updateConnectionStatus(status, text) {
    if (elements.statusDot && elements.statusText && elements.connectionInfo) {
        elements.statusDot.className = `status-dot ${status}`;
        elements.statusText.textContent = text;
        elements.connectionInfo.textContent = `WebSocket: ${text}`;
    }
}

/**
 * 发送消息
 */
function sendMessage() {
    const content = elements.messageInput.value.trim();

    if (!content || isExecuting || !isConnected) {
        return;
    }

    // 保存当前任务到任务概览
    updateTaskOverview(content, 'running');

    // 清空输入框并重置高度
    elements.messageInput.value = '';
    elements.messageInput.style.height = 'auto';

    // 添加用户消息到聊天界面
    addMessage('user', content);

    // 发送消息到 WebSocket
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            event: 'user_message',
            content: content
        }));

        // 更新执行状态
        isExecuting = true;
        updateSendButtonState();

        // 发送后自动聚焦回输入框
        setTimeout(() => {
            elements.messageInput.focus();
        }, 100);
    } else {
        addMessage('error', 'WebSocket 未连接，请等待连接建立');
    }
}

/**
 * 更新任务概览
 */
function updateTaskOverview(task, status = 'idle', steps = 0) {
    const taskElement = document.getElementById('currentTask');
    const statusElement = document.getElementById('taskStatus');
    const stepsElement = document.getElementById('taskSteps');

    if (task && taskElement) {
        // 截断过长的任务名称
        taskElement.textContent = task.length > 50 ? task.substring(0, 50) + '...' : task;
    }

    if (status && statusElement) {
        statusElement.textContent = status === 'running' ? '执行中' : status === 'completed' ? '已完成' : status === 'error' ? '出错' : '空闲';
        statusElement.className = `task-value status-${status}`;
    }

    if (stepsElement) {
        stepsElement.textContent = `${steps} 步`;
    }
}

/**
 * 切换任务概览显示
 */
function toggleTaskOverview() {
    const card = document.getElementById('taskOverviewCard');
    if (card) {
        card.classList.toggle('collapsed');
    }
}

/**
 * 处理输入
 */
function handleInput() {
    updateSendButtonState();
}

/**
 * 处理键盘事件
 */
function handleKeyDown(event) {
    // Cmd+Enter (Mac) 或 Ctrl+Enter (Windows/Linux) 发送
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        event.preventDefault();
        sendMessage();
    }
}

/**
 * 输入框自动调整高度
 */
function handleInputAutoResize(textarea) {
    textarea.style.height = 'auto';
    const newHeight = Math.min(textarea.scrollHeight, 12 * 24); // 最大 12 行
    textarea.style.height = Math.max(newHeight, 3 * 24) + 'px'; // 最小 3 行 (3rem = 48px, 1.5rem = 24px/line)
}

/**
 * 更新发送按钮状态
 */
function updateSendButtonState() {
    const hasContent = elements.messageInput.value.trim().length > 0;
    const canSend = hasContent && !isExecuting && isConnected;

    if (elements.sendButton) {
        elements.sendButton.disabled = !canSend;
    }

    // 更新中止按钮显示
    const abortButton = document.getElementById('abortButton');
    if (abortButton) {
        abortButton.style.display = isExecuting ? 'flex' : 'none';
    }
}

/**
 * 更新消息块的等待状态
 * @param {HTMLElement} contentElement - 消息的内容元素
 * @param {boolean} show - 是否显示等待状态
 * @param {string} text - 显示的文本
 */
function updateMessageExecutingStatus(contentElement, show, text = '执行中') {
    if (!contentElement) return;

    // 获取父级message元素
    const messageElement = contentElement.closest('.message');
    if (!messageElement) return;

    // 获取等待状态容器
    let executingStatusContainer = messageElement.querySelector('.message-executing-status');
    if (!executingStatusContainer) {
        // 如果容器不存在，创建它
        executingStatusContainer = document.createElement('div');
        executingStatusContainer.className = 'message-executing-status';
        const header = messageElement.querySelector('.message-header');
        if (header) {
            messageElement.insertBefore(executingStatusContainer, header.nextSibling);
        } else {
            messageElement.insertBefore(executingStatusContainer, contentElement);
        }
    }

    if (show) {
        // 检查是否已有等待状态
        if (!executingStatusContainer.querySelector('.executing-status')) {
            // 添加等待状态
            const executingDiv = document.createElement('div');
            executingDiv.className = 'executing-status';
            executingDiv.innerHTML = `
                <div class="spinner">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <span class="status-text">${text}</span>
            `;
            executingStatusContainer.appendChild(executingDiv);
            
            // 添加进度条
            if (!messageElement.querySelector('.executing-progress-bar')) {
                const progressBar = document.createElement('div');
                progressBar.className = 'executing-progress-bar';
                messageElement.appendChild(progressBar);
            }
        } else {
            // 更新现有状态文本
            const statusText = executingStatusContainer.querySelector('.status-text');
            if (statusText) {
                statusText.textContent = text;
            }
        }
    } else {
        // 移除等待状态
        const executingDiv = executingStatusContainer.querySelector('.executing-status');
        if (executingDiv) {
            executingDiv.remove();
        }
        
        // 移除进度条
        const progressBar = messageElement.querySelector('.executing-progress-bar');
        if (progressBar) {
            progressBar.remove();
        }
    }
}

/**
 * 添加消息到聊天界面
 */
function addMessage(type, content, metadata = {}) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    const headerDiv = document.createElement('div');
    headerDiv.className = 'message-header';

    // 设置消息标题
    let headerText = '';
    switch (type) {
        case 'user':
            headerText = '你';
            break;
        case 'assistant':
            headerText = 'Agentic';
            break;
        case 'thinking':
            headerText = '思考中';
            break;
        case 'action':
            headerText = metadata?.action_type || '执行动作';
            break;
        case 'result':
            headerText = '结果';
            break;
        case 'system':
            headerText = '系统';
            break;
        case 'error':
            headerText = '错误';
            break;
        default:
            headerText = '消息';
    }

    headerDiv.textContent = headerText;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // 格式化内容（支持 Markdown 基本格式）
    contentDiv.innerHTML = formatMessage(content);

    const timeDiv = document.createElement('div');
    timeDiv.className = 'message time';
    timeDiv.textContent = getCurrentTime();

    // 创建等待状态容器（在header之后，content之前）
    const executingStatusContainer = document.createElement('div');
    executingStatusContainer.className = 'message-executing-status';
    
    messageDiv.appendChild(headerDiv);
    messageDiv.appendChild(executingStatusContainer);
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeDiv);

    // 移除欢迎消息
    const welcomeMessage = elements.messagesContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }

    elements.messagesContainer.appendChild(messageDiv);
    scrollToBottom();
    
    // 保存到当前会话数据
    if (type === 'user' || type === 'assistant' || type === 'system' || type === 'error') {
        currentSessionData.messages.push({
            type,
            content,
            metadata,
            timestamp: new Date().toISOString()
        });
    }
}

/**
 * 添加增强的错误消息到聊天界面
 */
function addEnhancedErrorMessage(content, metadata = {}) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message expanded';

    const errorType = metadata?.error_type || 'UNKNOWN_ERROR';
    const errorCode = metadata?.error_code || 'ERR_UNKNOWN';
    const errorDetails = metadata?.details || '';
    const suggestions = metadata?.suggestions || [];
    const recoveryActions = metadata?.recovery_actions || [];

    errorDiv.innerHTML = `
        <div class="error-header">
            <div class="error-title">
                <span class="error-icon">❌</span>
                <span class="error-type">${formatErrorType(errorType)}</span>
            </div>
            <div class="error-actions">
                <button class="btn btn-secondary" onclick="copyError('${content.replace(/'/g, "\\'")}')">复制</button>
            </div>
        </div>
        <div class="error-content">
            <p class="error-message-text">${content}</p>
            ${errorDetails ? `<pre class="error-details">${errorDetails}</pre>` : ''}

            ${suggestions.length > 0 ? `
                <div class="error-suggestions">
                    <h4>💡 建议解决方案:</h4>
                    <ul>
                        ${suggestions.map(s => `<li>${s}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        </div>
    `;

    // 移除欢迎消息
    const welcomeMessage = elements.messagesContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }

    elements.messagesContainer.appendChild(errorDiv);
    scrollToBottom();
}

/**
 * 格式化错误类型（转换为可读的文本）
 */
function formatErrorType(errorType) {
    const typeMap = {
        'tool_not_found': '工具未找到',
        'tool_execution_failed': '工具执行失败',
        'tool_timeout': '工具超时',
        'tool_invalid_parameters': '工具参数无效',
        'skill_not_found': 'Skill 未找到',
        'skill_execution_failed': 'Skill 执行失败',
        'skill_missing_tools': 'Skill 缺少工具',
        'skill_timeout': 'Skill 超时',
        'chain_invalid_format': 'Chain 格式无效',
        'chain_step_failed': 'Chain 步骤失败',
        'chain_timeout': 'Chain 超时',
        'agent_timeout': 'Agent 超时',
        'agent_max_steps_reached': '达到最大步数',
        'agent_context_error': 'Agent 上下文错误',
        'websocket_connection_error': 'WebSocket 连接错误',
        'websocket_send_error': 'WebSocket 发送错误',
        'unknown_error': '未知错误'
    };
    return typeMap[errorType] || errorType;
}

/**
 * 复制错误信息到剪贴板
 */
function copyError(errorText) {
    navigator.clipboard.writeText(errorText).then(() => {
        alert('错误信息已复制到剪贴板');
    }).catch(err => {
        console.error('复制失败:', err);
    });
}

/**
 * 添加时间轴项目
 */
function addTimelineItem(type, typeText, content, metadata = {}) {
    // 移除空状态
    const emptyState = elements.executionTimeline.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }

    // 判断是否是子代理事件
    const subagentId = metadata?.subagent_id;

    if (subagentId) {
        // 子代理事件：创建可折叠容器
        const subagentContainer = createSubagentContainer(metadata, content);
        elements.executionTimeline.appendChild(subagentContainer);
    } else {
        // 主代理事件：正常添加
        const timelineItem = document.createElement('div');
        timelineItem.className = 'timeline-item';

        const dot = document.createElement('div');
        dot.className = `timeline-dot ${type}`;

        const timelineContent = document.createElement('div');
        timelineContent.className = 'timeline-content';

        const header = document.createElement('div');
        header.className = 'timeline-header';

        const typeSpan = document.createElement('span');
        typeSpan.className = `timeline-type ${type}`;
        typeSpan.textContent = typeText;

        const timeSpan = document.createElement('span');
        timeSpan.className = 'timeline-time';
        timeSpan.textContent = getCurrentTime();

        header.appendChild(typeSpan);
        header.appendChild(timeSpan);

        const body = document.createElement('div');
        body.className = 'timeline-body';

        // 格式化内容
        if (metadata && Object.keys(metadata).length > 0) {
            const pre = document.createElement('pre');
            pre.textContent = formatMetadata(metadata);
            body.appendChild(pre);
        }

        if (content) {
            const p = document.createElement('p');
            p.textContent = content;
            body.appendChild(p);
        }

        timelineContent.appendChild(header);
        timelineContent.appendChild(body);

        timelineItem.appendChild(dot);
        timelineItem.appendChild(timelineContent);

        elements.executionTimeline.appendChild(timelineItem);
    }

    scrollToExecutionBottom();
}

/**
 * 创建子代理可折叠容器
 */
function createSubagentContainer(metadata, initialContent) {
    const subagentId = metadata.subagent_id;
    const subagentType = metadata.subagent_type || 'unknown';
    const subagentCommand = metadata.subagent_command || metadata.tool_name || 'Unknown';
    const elapsed = metadata.elapsed || 0;

    const container = document.createElement('div');
    container.className = 'subagent-container';
    container.dataset.subagentId = subagentId;

    container.innerHTML = `
        <div class="subagent-header" onclick="toggleSubagent('${subagentId}')">
            <div class="subagent-info">
                <span class="subagent-icon">${getSubagentIcon(subagentType)}</span>
                <span class="subagent-name">${subagentCommand}</span>
                <span class="subagent-id">(${subagentId})</span>
            </div>
            <div class="subagent-stats">
                <span class="stat">⏱️ ${formatTime(elapsed)}</span>
                <button class="toggle-icon">▼</button>
            </div>
        </div>
        <div class="subagent-events" id="subagent-events-${subagentId}" style="display: none;">
            <!-- 子事件将在这里动态添加 -->
        </div>
    `;

    // 如果有初始内容，添加到子事件容器
    if (initialContent) {
        setTimeout(() => {
            addSubagentEvent(subagentId, initialContent);
        }, 100);
    }

    return container;
}

/**
 * 获取子代理图标
 */
function getSubagentIcon(type) {
    const iconMap = {
        'tool': '🛠️',
        'skill': '📚',
        'chain': '🔗',
        'unknown': '❓'
    };
    return iconMap[type] || iconMap['unknown'];
}

/**
 * 格式化时间（秒转换为可读格式）
 */
function formatTime(seconds) {
    if (seconds < 60) {
        return `${Math.round(seconds)}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
}

/**
 * 切换子代理容器的展开/收起状态
 */
function toggleSubagent(subagentId) {
    const eventsContainer = document.getElementById(`subagent-events-${subagentId}`);
    const container = document.querySelector(`.subagent-container[data-subagent-id="${subagentId}"]`);
    const toggleIcon = container.querySelector('.toggle-icon');

    if (eventsContainer.style.display === 'none') {
        // 展开
        eventsContainer.style.display = 'block';
        container.classList.add('expanded');
        toggleIcon.textContent = '▲';
    } else {
        // 收起
        eventsContainer.style.display = 'none';
        container.classList.remove('expanded');
        toggleIcon.textContent = '▼';
    }
}

/**
 * 添加子代理事件到对应的容器
 */
function addSubagentEvent(subagentId, content, metadata = {}) {
    const eventsContainer = document.getElementById(`subagent-events-${subagentId}`);
    if (!eventsContainer) return;

    const eventItem = document.createElement('div');
    eventItem.className = 'subagent-event';

    const eventTime = metadata?.timestamp ? new Date(metadata.timestamp).toLocaleTimeString() : getCurrentTime();

    eventItem.innerHTML = `
        <div class="subevent-header">
            <span class="subevent-time">${eventTime}</span>
        </div>
        <div class="subevent-content">${content}</div>
    `;

    eventsContainer.appendChild(eventItem);
}

/**
 * 初始化执行进度
 */
function initExecutionProgress(totalSteps) {
    executionProgress.currentStep = 0;
    executionProgress.totalSteps = totalSteps;
    executionProgress.startTime = Date.now();
    executionProgress.elapsed = 0;
    executionProgress.progress = 0;

    // 显示进度条容器
    if (elements.executionProgressContainer) {
        elements.executionProgressContainer.style.display = 'block';
    }

    // 隐藏步骤指示器（不需要显示50个点的标识）
    if (elements.progressSteps) {
        elements.progressSteps.style.display = 'none';
    }

    updateProgressDisplay();
}

/**
 * 更新执行进度
 */
function updateExecutionProgress(step, elapsed) {
    executionProgress.currentStep = step;
    executionProgress.elapsed = elapsed;
    executionProgress.progress = step / executionProgress.totalSteps;

    updateProgressDisplay();
}

/**
 * 更新进度显示
 */
function updateProgressDisplay() {
    // 更新进度条宽度
    if (elements.progressBar) {
        elements.progressBar.style.width = `${executionProgress.progress * 100}%`;
    }

    // 更新统计信息
    if (elements.progressStats) {
        const progressPercent = Math.round(executionProgress.progress * 100);
        elements.progressStats.textContent = `步骤 ${executionProgress.currentStep}/${executionProgress.totalSteps} | 已耗时 ${formatTime(executionProgress.elapsed)} (${progressPercent}%)`;
    }

    // 更新步骤指示器高亮（如果显示）
    if (elements.progressSteps && elements.progressSteps.style.display !== 'none') {
        const indicators = elements.progressSteps.querySelectorAll('.progress-step-indicator');
        indicators.forEach((indicator, index) => {
            const stepNum = index + 1;
            if (stepNum < executionProgress.currentStep) {
                indicator.classList.add('completed');
                indicator.classList.remove('current');
            } else if (stepNum === executionProgress.currentStep) {
                indicator.classList.add('current');
                indicator.classList.remove('completed');
            } else {
                indicator.classList.remove('current', 'completed');
            }
        });
    }
}

/**
 * 完成执行进度
 */
function completeExecutionProgress() {
    executionProgress.progress = 1;
    updateProgressDisplay();
}

/**
 * 格式化消息内容（支持 Markdown 基本格式）
 */
function formatMessage(content) {
    if (!content) return '';

    // 确保是字符串
    let text = typeof content === 'string' ? content : String(content);

    // 转义 HTML
    let formatted = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');

    // 代码块
    formatted = formatted.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

    // 行内代码
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

    // 粗体
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // 斜体
    formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 换行
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
}

/**
 * 格式化元数据
 */
function formatMetadata(metadata) {
    try {
        return JSON.stringify(metadata, null, 2);
    } catch (error) {
        return String(metadata);
    }
}

/**
 * 获取当前时间
 */
function getCurrentTime() {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
}

/**
 * 滚动到底部
 */
function scrollToBottom() {
    if (elements.messagesContainer) {
        elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
    }
}

/**
 * 滚动执行时间轴到底部
 */
function scrollToExecutionBottom() {
    if (elements.executionTimeline) {
        elements.executionTimeline.scrollTop = elements.executionTimeline.scrollHeight;
    }
}

/**
 * 中止当前执行
 */
function abortExecution() {
    if (!isConnected || !isExecuting) {
        return;
    }

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            event: 'abort'
        }));

        // 添加中止提示
        addMessage('system', '正在中止执行...');

        // 移除动作消息的等待状态（如果有）
        if (currentActionElement) {
            updateMessageExecutingStatus(currentActionElement, false);
            currentActionElement = null;
        }

        // 立即更新状态（等待后端确认）
        isExecuting = false;
        updateSendButtonState();
    }
}

/**
 * 保存当前会话到历史
 */
function saveCurrentSession() {
    if (!currentSessionData.task) return;
    
    const sessionIndex = sessions.findIndex(s => s.id === sessionId);
    
    const sessionData = {
        id: sessionId,
        name: currentSessionData.task.length > 30 ? currentSessionData.task.substring(0, 30) + '...' : currentSessionData.task,
        task: currentSessionData.task,
        status: currentSessionData.status,
        steps: currentSessionData.steps,
        timestamp: new Date().toISOString(),
        preview: currentSessionData.messages.slice(-2).map(m => m.content).join(' ') || '无对话内容'
    };
    
    if (sessionIndex >= 0) {
        sessions[sessionIndex] = sessionData;
    } else {
        sessions.unshift(sessionData);
    }
    
    // 限制会话数量
    if (sessions.length > MAX_SESSIONS) {
        sessions = sessions.slice(0, MAX_SESSIONS);
    }
    
    saveSessions();
    renderSessionHistory();
}

/**
 * 加载会话历史
 */
function loadSessions() {
    try {
        const stored = localStorage.getItem(SESSION_STORAGE_KEY);
        if (stored) {
            sessions = JSON.parse(stored);
        }
    } catch (error) {
        console.error('Failed to load sessions:', error);
        sessions = [];
    }
}

/**
 * 保存会话历史到 LocalStorage
 */
function saveSessions() {
    try {
        localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions));
    } catch (error) {
        console.error('Failed to save sessions:', error);
    }
}

/**
 * 绑定会话历史相关事件
 */
function bindSessionEvents() {
    // 点击外部关闭菜单
    document.addEventListener('click', (e) => {
        if (elements.sessionHistoryMenu && 
            !elements.sessionHistoryBtn.contains(e.target) && 
            !elements.sessionHistoryMenu.contains(e.target)) {
            elements.sessionHistoryMenu.style.display = 'none';
        }
    });
}

/**
 * 切换会话历史菜单显示
 */
function toggleSessionHistory() {
    if (!elements.sessionHistoryMenu) return;
    
    const isVisible = elements.sessionHistoryMenu.style.display === 'block';
    elements.sessionHistoryMenu.style.display = isVisible ? 'none' : 'block';
    
    if (!isVisible) {
        renderSessionHistory();
    }
}

/**
 * 渲染会话历史列表
 */
function renderSessionHistory() {
    if (!elements.sessionHistoryList) return;
    
    elements.sessionHistoryList.innerHTML = '';
    
    if (sessions.length === 0) {
        elements.sessionHistoryList.innerHTML = `
            <div class="empty-sessions">
                <p>暂无历史会话</p>
            </div>
        `;
        return;
    }
    
    sessions.forEach(session => {
        const item = document.createElement('div');
        item.className = `session-history-item ${session.id === sessionId ? 'active' : ''}`;
        item.dataset.sessionId = session.id;
        
        item.innerHTML = `
            <div class="session-history-info">
                <div class="session-history-name">${session.name}</div>
                <div class="session-history-meta">
                    ${session.status === 'completed' ? '✓' : session.status === 'error' ? '✗' : '●'} 
                    ${session.steps} 步 · ${formatDate(session.timestamp)}
                </div>
            </div>
            <div class="session-history-actions">
                <button class="btn-icon btn-sm" onclick="renameSession('${session.id}', event)" title="重命名">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M8.5 2.5L9.5 3.5L4 9L3 8L8.5 2.5Z" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M9.5 3.5L3 10" stroke="currentColor" stroke-width="1" stroke-linecap="round"/>
                    </svg>
                </button>
                <button class="btn-icon btn-sm" onclick="deleteSession('${session.id}', event)" title="删除">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M2 3H10M3 3V10C3 10.2652 3.10536 10.5196 3.29289 10.7071C3.48043 10.8946 3.73478 11 4 11H8C8.26522 11 8.51957 10.8946 8.70711 10.7071C8.89464 10.5196 9 10.2652 9 10V3M4 3V1H8V3" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
            </div>
        `;
        
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.session-history-actions')) {
                loadSession(session.id);
            }
        });
        
        elements.sessionHistoryList.appendChild(item);
    });
}

/**
 * 格式化日期
 */
function formatDate(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;
    
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

/**
 * 加载指定会话
 */
function loadSession(sessionId) {
    const session = sessions.find(s => s.id === sessionId);
    if (!session) return;
    
    // 清空当前视图
    elements.messagesContainer.innerHTML = '';
    elements.executionTimeline.innerHTML = '';
    
    // 恢复会话数据
    currentSessionData = {
        task: session.task,
        status: session.status,
        steps: session.steps,
        messages: [], // 这里可以从后端加载完整消息
        timeline: [] // 从后端加载时间轴
    };
    
    // 更新任务概览
    updateTaskOverview(session.task, session.status, session.steps);
    
    // 添加欢迎消息
    addWelcomeMessage();
    
    // 添加空状态
    addEmptyState();
    
    // 更新当前会话ID
    window.sessionId = sessionId;
    updateSessionIdDisplay(sessionId);
    
    // 关闭菜单
    if (elements.sessionHistoryMenu) {
        elements.sessionHistoryMenu.style.display = 'none';
    }
    
    // 提示用户
    addMessage('system', `已切换到会话：${session.name}`);
}

/**
 * 重命名会话
 */
function renameSession(sessionId, event) {
    event.stopPropagation();
    
    const session = sessions.find(s => s.id === sessionId);
    if (!session) return;
    
    const newName = prompt('请输入新的会话名称：', session.name);
    if (newName && newName.trim()) {
        session.name = newName.trim().length > 30 ? newName.trim().substring(0, 30) + '...' : newName.trim();
        saveSessions();
        renderSessionHistory();
    }
}

/**
 * 删除会话
 */
function deleteSession(sessionId, event) {
    event.stopPropagation();
    
    if (!confirm('确定要删除这个会话吗？此操作不可撤销。')) return;
    
    sessions = sessions.filter(s => s.id !== sessionId);
    saveSessions();
    renderSessionHistory();
}

/**
 * 清空会话历史
 */
function clearSessionHistory() {
    if (!confirm('确定要清空所有会话历史吗？此操作不可撤销。')) return;
    
    sessions = [];
    saveSessions();
    renderSessionHistory();
    
    // 关闭菜单
    if (elements.sessionHistoryMenu) {
        elements.sessionHistoryMenu.style.display = 'none';
    }
}

/**
 * 新建会话
 */
function newSession() {
    sessionId = generateSessionId();
    updateSessionIdDisplay(sessionId);

    // 重置当前会话数据
    currentSessionData = {
        messages: [],
        timeline: [],
        task: '',
        status: 'idle',
        steps: 0
    };

    // 重置思考状态
    resetThinkingState();
    // 重置动作状态
    resetActionState();

    // 清空消息
    elements.messagesContainer.innerHTML = '';

    // 添加欢迎消息
    addWelcomeMessage();

    // 清空执行时间轴
    elements.executionTimeline.innerHTML = '';
    addEmptyState();

    // 更新任务概览
    updateTaskOverview('', 'idle', 0);

    // 重新连接 WebSocket
    if (ws) {
        ws.close();
    }
    setTimeout(() => connectWebSocket(), 500);
    
    // 关闭会话历史菜单
    if (elements.sessionHistoryMenu) {
        elements.sessionHistoryMenu.style.display = 'none';
    }
}

/**
 * 清空上下文
 */
function clearContext() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            event: 'clear_context'
        }));
    }
}

/**
 * 切换执行面板显示
 */
function toggleExecutionPanel() {
    const section = document.querySelector('.execution-section');
    if (section) {
        section.classList.toggle('collapsed');
    }
}

/**
 * 添加欢迎消息
 */
function addWelcomeMessage() {
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'welcome-message';
    welcomeDiv.innerHTML = `
        <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="32" cy="32" r="28" stroke="#2563EB" stroke-width="2"/>
            <path d="M20 32L28 40L44 24" stroke="#2563EB" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <h2>欢迎使用 Agentic</h2>
        <p>一个强大的 AI Agent 系统，支持实时对话和智能任务执行</p>
        <div class="feature-tags">
            <span class="tag">🤖 智能推理</span>
            <span class="tag">🛠️ 工具调用</span>
            <span class="tag">📚 Skills 系统</span>
            <span class="tag">⚡ 实时交互</span>
        </div>
    `;
    elements.messagesContainer.appendChild(welcomeDiv);
}

/**
 * 添加空状态
 */
function addEmptyState() {
    const emptyDiv = document.createElement('div');
    emptyDiv.className = 'empty-state';
    emptyDiv.innerHTML = `
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="24" cy="24" r="20" stroke="#E5E7EB" stroke-width="2"/>
            <path d="M24 14V24M24 24L20 20" stroke="#9CA3AF" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <p>Agent 执行过程将在这里显示</p>
    `;
    elements.executionTimeline.appendChild(emptyDiv);
}

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        init();
        // 初始化任务概览为默认状态
        updateTaskOverview('', 'idle', 0);
    });
} else {
    init();
    // 初始化任务概览为默认状态
    updateTaskOverview('', 'idle', 0);
}
