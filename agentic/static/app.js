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
    connectionInfo: null
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

        default:
            console.log('Unknown event:', event);
    }
}

/**
 * 处理 Agent 思考事件
 */
function handleAgentThinking(content, metadata) {
    // 累积内容到当前思考消息
    if (!currentThinkingElement) {
        // 第一次收到思考内容，创建新消息并显示等待状态
        addMessage('thinking', content, metadata);
        // 获取刚创建的消息内容元素
        const messages = elements.messagesContainer.querySelectorAll('.message.thinking .message-content');
        currentThinkingElement = messages[messages.length - 1];

        // 显示等待状态
        updateMessageExecutingStatus(currentThinkingElement, true, '正在思考...');

        currentThinkingContent = content;
    } else {
        // 收到实际内容，移除等待状态并显示思考内容
        updateMessageExecutingStatus(currentThinkingElement, false);

        // 追加内容到当前思考消息
        currentThinkingContent += content;
        currentThinkingElement.innerHTML = formatMessage(currentThinkingContent);
    }

    // 添加到执行时间轴（只在第一次时添加）
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

    // 重置思考累积
    currentThinkingElement = null;
    currentThinkingContent = '';

    // 添加到消息列表
    addMessage('action', `${actionType}: ${description}`, metadata);

    // 获取刚创建的消息内容元素，并显示等待状态
    const messages = elements.messagesContainer.querySelectorAll('.message.action .message-content');
    currentActionElement = messages[messages.length - 1];

    // 根据不同类型显示不同的等待文本
    let statusText = '执行中...';
    if (metadata?.tool_name) {
        statusText = `正在调用工具: ${metadata.tool_name}`;
    } else if (metadata?.subagent_command) {
        statusText = `正在调用技能: ${metadata.subagent_command}`;
    }
    updateMessageExecutingStatus(currentActionElement, true, statusText);

    // 添加到执行时间轴
    addTimelineItem('action', actionType, description, metadata);
}

/**
 * 处理 Agent 结果事件
 */
function handleAgentResult(content, metadata) {
    // 移除动作消息的等待状态
    if (currentActionElement) {
        updateMessageExecutingStatus(currentActionElement, false);
        currentActionElement = null;
    }

    // 重置思考累积
    currentThinkingElement = null;
    currentThinkingContent = '';

    // 添加到消息列表
    addMessage('result', content, metadata);

    // 添加到执行时间轴
    addTimelineItem('result', '结果', content, metadata);
}

/**
 * 处理 Agent 完成事件
 */
function handleAgentComplete(content) {
    // 移除动作消息的等待状态（如果有）
    if (currentActionElement) {
        updateMessageExecutingStatus(currentActionElement, false);
        currentActionElement = null;
    }

    // 重置思考累积
    currentThinkingElement = null;
    currentThinkingContent = '';

    // 添加到消息列表
    addMessage('assistant', content);

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
    if (currentActionElement) {
        updateMessageExecutingStatus(currentActionElement, false);
        currentActionElement = null;
    }

    // 重置思考累积
    currentThinkingElement = null;
    currentThinkingContent = '';

    // 添加错误消息
    addMessage('error', content);

    // 添加到执行时间轴
    addTimelineItem('error', '错误', content);

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

    // 清空输入框
    elements.messageInput.value = '';

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
    } else {
        addMessage('error', 'WebSocket 未连接，请等待连接建立');
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
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
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
function updateMessageExecutingStatus(contentElement, show, text = '执行中...') {
    if (!contentElement) return;

    if (show) {
        // 检查是否已有等待状态
        if (!contentElement.querySelector('.executing-status')) {
            // 添加等待状态
            const executingDiv = document.createElement('div');
            executingDiv.className = 'executing-status';
            executingDiv.innerHTML = `
                <div class="spinner"></div>
                <span>${text}</span>
            `;
            contentElement.appendChild(executingDiv);
        }
    } else {
        // 移除等待状态
        const executingDiv = contentElement.querySelector('.executing-status');
        if (executingDiv) {
            executingDiv.remove();
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

    messageDiv.appendChild(headerDiv);
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeDiv);

    // 移除欢迎消息
    const welcomeMessage = elements.messagesContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }

    elements.messagesContainer.appendChild(messageDiv);
    scrollToBottom();
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
    scrollToExecutionBottom();
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
 * 新建会话
 */
function newSession() {
    sessionId = generateSessionId();
    updateSessionIdDisplay(sessionId);

    // 重置思考累积
    currentThinkingElement = null;
    currentThinkingContent = '';

    // 清空消息
    elements.messagesContainer.innerHTML = '';

    // 添加欢迎消息
    addWelcomeMessage();

    // 清空执行时间轴
    elements.executionTimeline.innerHTML = '';
    addEmptyState();

    // 重新连接 WebSocket
    if (ws) {
        ws.close();
    }
    setTimeout(() => connectWebSocket(), 500);
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
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
