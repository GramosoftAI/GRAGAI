(function () {
    // 1. EXTRACT CONFIGURATION FROM THE EMBEDDED SCRIPT TAG
    const scriptTag = document.currentScript || document.querySelector('script[src*="chat.js"]');
    if (!scriptTag) {
        console.error("❌ GraphMind Widget: Script tag not found. Cannot initialize.");
        return;
    }

    const agentId = scriptTag.getAttribute('data-agent-id') || scriptTag.getAttribute('agent-id');
    const tenantId = scriptTag.getAttribute('data-tenant-id') || scriptTag.getAttribute('tenant-id');

    if (!agentId || !tenantId) {
        console.error("❌ GraphMind Widget: Missing data-agent-id or data-tenant-id on script tag.");
        return;
    }

    // Dynamic backend URL injected by the server on serve, fallback to localhost:8000
    const baseUrl = "{{BACKEND_URL}}" || "http://localhost:8000";

    // 2. CREATE INJECTED ELEMENT AND SHADOW DOM (TO PREVENT CSS BLEED)
    const widgetContainer = document.createElement('div');
    widgetContainer.id = 'graphmind-chat-widget';
    document.body.appendChild(widgetContainer);

    const shadowRoot = widgetContainer.attachShadow({ mode: 'open' });

    // 3. DEFINE SLEEK MODERN GLASSMORPHISM DESIGN STYLES
    const styles = `
        :host {
            --primary-gradient: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
            --accent-gradient: linear-gradient(135deg, #10b981 0%, #059669 100%);
            --panel-bg: rgba(255, 255, 255, 0.95);
            --panel-shadow: 0 12px 40px rgba(31, 38, 135, 0.12);
            --user-bubble: #6366f1;
            --assistant-bubble: #f3f4f6;
            --text-dark: #1f2937;
            --text-light: #f9fafb;
            --text-muted: #6b7280;
            --font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            
            font-family: var(--font-family);
            box-sizing: border-box;
        }

        /* Float Launcher */
        .launcher-btn {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: var(--primary-gradient);
            box-shadow: 0 8px 30px rgba(79, 70, 229, 0.4);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 999999;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            border: none;
            outline: none;
        }

        .launcher-btn:hover {
            transform: scale(1.1) rotate(5deg);
            box-shadow: 0 12px 35px rgba(79, 70, 229, 0.5);
        }

        .launcher-btn:active {
            transform: scale(0.95);
        }

        .launcher-btn svg {
            width: 28px;
            height: 28px;
            fill: white;
            transition: transform 0.3s ease;
        }

        .launcher-btn.active svg {
            transform: rotate(90deg) scale(0.85);
        }

        /* Notification badge */
        .pulse-badge {
            position: absolute;
            top: -2px;
            right: -2px;
            width: 14px;
            height: 14px;
            background: #ef4444;
            border: 2px solid white;
            border-radius: 50%;
            animation: badge-pulse 2s infinite;
        }

        @keyframes badge-pulse {
            0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
            70% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
            100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }

        /* Chat Panel Container */
        .chat-panel {
            position: fixed;
            bottom: 96px;
            right: 24px;
            width: 380px;
            height: 580px;
            max-height: calc(100vh - 120px);
            background: var(--panel-bg);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            box-shadow: var(--panel-shadow);
            z-index: 999999;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            opacity: 0;
            visibility: hidden;
            transform: translateY(30px) scale(0.95);
            transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
        }

        .chat-panel.open {
            opacity: 1;
            visibility: visible;
            transform: translateY(0) scale(1);
        }

        /* Header design */
        .chat-header {
            background: var(--primary-gradient);
            padding: 16px 20px;
            color: var(--text-light);
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }

        .agent-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .agent-avatar {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.15);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: inset 0 2px 5px rgba(255, 255, 255, 0.2);
        }

        .agent-status-container {
            display: flex;
            flex-direction: column;
        }

        .agent-name {
            font-weight: 600;
            font-size: 15px;
            letter-spacing: -0.2px;
        }

        .agent-status {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            opacity: 0.85;
            margin-top: 2px;
        }

        .status-dot {
            width: 7px;
            height: 7px;
            background: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 8px #10b981;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .header-btn {
            background: rgba(255, 255, 255, 0.1);
            border: none;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            color: white;
            transition: all 0.2s;
        }

        .header-btn:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        .header-btn svg {
            width: 14px;
            height: 14px;
            fill: currentColor;
        }

        /* Message flow area */
        .chat-body {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
            background: #fafafc;
            scroll-behavior: smooth;
        }

        .message-row {
            display: flex;
            width: 100%;
            animation: message-fade-in 0.3s ease forwards;
        }

        @keyframes message-fade-in {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message-row.user {
            justify-content: flex-end;
        }

        .message-row.assistant {
            justify-content: flex-start;
        }

        .bubble {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 16px;
            font-size: 14px;
            line-height: 1.5;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.02);
            word-wrap: break-word;
        }

        .message-row.user .bubble {
            background: var(--user-bubble);
            color: white;
            border-bottom-right-radius: 4px;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.2);
        }

        .message-row.assistant .bubble {
            background: white;
            color: var(--text-dark);
            border-bottom-left-radius: 4px;
            border: 1px solid rgba(229, 231, 235, 0.5);
        }

        /* Markdown rendering helper classes */
        .bubble p {
            margin: 0 0 8px 0;
        }
        .bubble p:last-child {
            margin-bottom: 0;
        }
        .bubble ul, .bubble ol {
            margin: 4px 0 8px 18px;
            padding: 0;
        }
        .bubble li {
            margin-bottom: 4px;
        }
        .bubble strong {
            font-weight: 600;
        }

        /* Sources formatting */
        .sources-wrapper {
            margin-top: 10px;
            border-top: 1px dashed rgba(229, 231, 235, 0.8);
            padding-top: 8px;
        }

        .sources-toggle {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            color: var(--primary-gradient);
            background: none;
            border: none;
            padding: 0;
            cursor: pointer;
            font-weight: 500;
            color: #4f46e5;
        }

        .sources-toggle svg {
            width: 10px;
            height: 10px;
            fill: currentColor;
            transition: transform 0.2s;
        }

        .sources-toggle.active svg {
            transform: rotate(90deg);
        }

        .sources-list {
            margin-top: 6px;
            display: none;
            flex-direction: column;
            gap: 4px;
            animation: slide-down 0.2s ease-out forwards;
        }

        @keyframes slide-down {
            from { opacity: 0; transform: translateY(-5px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .source-item {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 11px;
            color: var(--text-muted);
            line-height: 1.4;
        }

        /* Typing indicator bounce */
        .typing-bubble {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 12px 18px;
        }

        .typing-dot {
            width: 7px;
            height: 7px;
            background: var(--text-muted);
            border-radius: 50%;
            opacity: 0.6;
            animation: bounce-typing 1.4s infinite ease-in-out both;
        }

        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce-typing {
            0%, 80%, 100% { transform: scale(0.6); }
            40% { transform: scale(1) translateY(-5px); opacity: 1; }
        }

        /* Footer inputs design */
        .chat-footer {
            padding: 14px 20px;
            background: white;
            border-top: 1px solid #f3f4f6;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .input-row {
            display: flex;
            align-items: flex-end;
            gap: 10px;
        }

        .message-input {
            flex: 1;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 10px 14px;
            font-size: 13.5px;
            outline: none;
            resize: none;
            max-height: 100px;
            min-height: 20px;
            font-family: inherit;
            line-height: 1.4;
            transition: border-color 0.2s, box-shadow 0.2s;
            box-sizing: border-box;
        }

        .message-input:focus {
            border-color: #6366f1;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }

        .send-btn {
            background: var(--primary-gradient);
            border: none;
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            color: white;
            transition: all 0.2s;
            flex-shrink: 0;
            box-shadow: 0 4px 10px rgba(79, 70, 229, 0.15);
        }

        .send-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 12px rgba(79, 70, 229, 0.25);
        }

        .send-btn:disabled {
            background: #e5e7eb;
            color: #9ca3af;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .send-btn svg {
            width: 18px;
            height: 18px;
            fill: currentColor;
            transform: translateX(1px);
        }

        .branding {
            text-align: center;
            font-size: 10px;
            color: var(--text-muted);
            letter-spacing: 0.2px;
            opacity: 0.7;
        }
        .branding a {
            color: inherit;
            text-decoration: none;
            font-weight: 500;
        }
        
        /* Mobile adaptation */
        @media (max-width: 480px) {
            .chat-panel {
                width: 100% !important;
                height: 100% !important;
                bottom: 0 !important;
                right: 0 !important;
                border-radius: 0 !important;
                max-height: 100vh !important;
            }
        }
    `;

    // 4. HTML MARKUP BUILDER
    const markup = `
        <!-- Pulse Launcher Button -->
        <button class="launcher-btn" id="gm-launcher">
            <span class="pulse-badge" id="gm-badge"></span>
            <svg viewBox="0 0 24 24" id="gm-svg-chat">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-3 3V4h17v12z"/>
            </svg>
            <svg viewBox="0 0 24 24" id="gm-svg-close" style="display:none;">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/>
            </svg>
        </button>

        <!-- Floating Chat Panel -->
        <div class="chat-panel" id="gm-panel">
            <!-- Header -->
            <div class="chat-header">
                <div class="agent-info">
                    <div class="agent-avatar" id="gm-avatar">🤖</div>
                    <div class="agent-status-container">
                        <div class="agent-name" id="gm-agent-name">AI Assistant</div>
                        <div class="agent-status">
                            <span class="status-dot"></span>
                            <span>Online</span>
                        </div>
                    </div>
                </div>
                <div class="header-actions">
                    <button class="header-btn" id="gm-reset" title="Clear conversation">
                        <svg viewBox="0 0 24 24"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
                    </button>
                    <button class="header-btn" id="gm-close" title="Minimize panel">
                        <svg viewBox="0 0 24 24"><path d="M19 13H5v-2h14v2z"/></svg>
                    </button>
                </div>
            </div>

            <!-- Messages Area -->
            <div class="chat-body" id="gm-body">
                <!-- Message Bubbles will be injected dynamically -->
            </div>

            <!-- Input Footer -->
            <div class="chat-footer">
                <div class="input-row">
                    <textarea class="message-input" id="gm-input" rows="1" placeholder="Ask anything..."></textarea>
                    <button class="send-btn" id="gm-send" disabled>
                        <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                    </button>
                </div>
                <div class="branding">
                    Powered by <a href="#" target="_blank">GraphMind AI</a>
                </div>
            </div>
        </div>
    `;

    // 5. ATTACH WORKSPACE TO THE SHADOW ROOT
    const styleElement = document.createElement('style');
    styleElement.textContent = styles;
    shadowRoot.appendChild(styleElement);

    const mainDiv = document.createElement('div');
    mainDiv.innerHTML = markup;
    shadowRoot.appendChild(mainDiv);

    // 6. QUERY DOM ELEMENTS
    const launcher = shadowRoot.querySelector('#gm-launcher');
    const badge = shadowRoot.querySelector('#gm-badge');
    const svgChat = shadowRoot.querySelector('#gm-svg-chat');
    const svgClose = shadowRoot.querySelector('#gm-svg-close');
    const panel = shadowRoot.querySelector('#gm-panel');
    const body = shadowRoot.querySelector('#gm-body');
    const input = shadowRoot.querySelector('#gm-input');
    const sendBtn = shadowRoot.querySelector('#gm-send');
    const closeBtn = shadowRoot.querySelector('#gm-close');
    const resetBtn = shadowRoot.querySelector('#gm-reset');
    const agentNameLabel = shadowRoot.querySelector('#gm-agent-name');
    const agentAvatar = shadowRoot.querySelector('#gm-avatar');

    // State Variables
    let isChatOpen = false;
    let sessionId = localStorage.getItem(`gm_sess_${agentId}`) || null;
    let agentDetails = null;
    let historyLoaded = false;

    // 7. UTILITY: MARKDOWN PARSER (REGULAR EXPRESSION CONVERSIONS)
    function parseMarkdown(text) {
        if (!text) return '';

        let html = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Convert double asterisks to strong
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Convert single asterisks/underscores to emphasis
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Handle code blocks
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Split lines by double line-breaks (paragraphs)
        const lines = html.split('\n');
        let formattedLines = [];
        let inList = false;

        for (let line of lines) {
            line = line.trim();

            // Check for bullet list items starting with '-' or '*'
            if (line.startsWith('- ') || line.startsWith('* ')) {
                if (!inList) {
                    formattedLines.push('<ul>');
                    inList = true;
                }
                formattedLines.push(`<li>${line.substring(2)}</li>`);
            } else {
                if (inList) {
                    formattedLines.push('</ul>');
                    inList = false;
                }

                if (line.length > 0) {
                    formattedLines.push(`<p>${line}</p>`);
                }
            }
        }

        if (inList) {
            formattedLines.push('</ul>');
        }

        return formattedLines.join('');
    }

    // 8. API ACTIONS

    // Fetch Agent Details (Name, Personality Tone, Greeting prompt)
    async function fetchAgentDetails() {
        try {
            const res = await fetch(`${baseUrl}/api/v1/embed/chats/${agentId}/details?tenant_id=${tenantId}`);
            if (res.ok) {
                const payload = await res.json();
                if (payload.success && payload.data) {
                    agentDetails = payload.data;
                    agentNameLabel.textContent = agentDetails.name;

                    // Set an appropriate emoji avatar based on personality
                    const tone = (agentDetails.personality || '').toLowerCase();
                    if (tone.includes('formal')) agentAvatar.textContent = '👨‍💼';
                    else if (tone.includes('sales')) agentAvatar.textContent = '💰';
                    else if (tone.includes('tech')) agentAvatar.textContent = '💻';
                    else if (tone.includes('sarcastic') || tone.includes('arrogant')) agentAvatar.textContent = '😏';
                    else agentAvatar.textContent = '🤖';
                }
            }
        } catch (e) {
            console.warn("⚠️ GraphMind Widget: Could not fetch agent details", e);
        }
    }

    // Load message history from existing localStorage session
    async function loadSessionHistory() {
        if (!sessionId || historyLoaded) return;

        try {
            const res = await fetch(`${baseUrl}/api/v1/embed/chats/${agentId}/sessions/${sessionId}?tenant_id=${tenantId}`);
            if (res.ok) {
                const payload = await res.json();
                if (payload.success && payload.data) {
                    const messages = payload.data.messages || [];
                    if (messages.length > 0) {
                        body.innerHTML = ''; // clear initial greeters
                        messages.forEach(msg => {
                            appendMessage(msg.role, msg.content, msg.metadata);
                        });
                        scrollToBottom();
                    }
                    historyLoaded = true;
                    badge.style.display = 'none'; // Clear notification once history is read
                }
            } else if (res.status === 404) {
                // If the session was deleted on server, reset locally
                sessionId = null;
                localStorage.removeItem(`gm_sess_${agentId}`);
            }
        } catch (e) {
            console.warn("⚠️ GraphMind Widget: Failed to load session history", e);
        }
    }

    // Append single bubble into scroll area
    function appendMessage(role, content, metadata = null) {
        const row = document.createElement('div');
        row.className = `message-row ${role}`;

        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        bubble.innerHTML = parseMarkdown(content);

        // If there are sources chunk citations, list them elegantly!
        const sources = metadata && metadata.sources ? metadata.sources : [];
        if (sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'sources-wrapper';

            const toggleBtn = document.createElement('button');
            toggleBtn.className = 'sources-toggle';
            toggleBtn.innerHTML = `
                <svg viewBox="0 0 24 24"><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg>
                <span>Sources verified (${sources.length})</span>
            `;

            const listDiv = document.createElement('div');
            listDiv.className = 'sources-list';

            // Render top 3 sources to keep it concise and beautiful
            sources.slice(0, 3).forEach((src, idx) => {
                const item = document.createElement('div');
                item.className = 'source-item';
                const scorePercent = src.score ? `(${Math.round(src.score * 100)}% match)` : '';
                item.innerHTML = `<strong>Source #${idx + 1} ${scorePercent}:</strong> ${src.text || src.content || 'Grounded knowledge chunk reference.'}`;
                listDiv.appendChild(item);
            });

            toggleBtn.addEventListener('click', () => {
                const isActive = toggleBtn.classList.toggle('active');
                listDiv.style.display = isActive ? 'flex' : 'none';
            });

            sourcesDiv.appendChild(toggleBtn);
            sourcesDiv.appendChild(listDiv);
            bubble.appendChild(sourcesDiv);
        }

        row.appendChild(bubble);
        body.appendChild(row);
        scrollToBottom();
    }

    // Typing/thinking indicator bubble
    function showTypingIndicator() {
        const row = document.createElement('div');
        row.className = 'message-row assistant';
        row.id = 'gm-typing-indicator';

        const bubble = document.createElement('div');
        bubble.className = 'bubble typing-bubble';
        bubble.innerHTML = `
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        `;

        row.appendChild(bubble);
        body.appendChild(row);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const indicator = shadowRoot.querySelector('#gm-typing-indicator');
        if (indicator) indicator.remove();
    }

    function scrollToBottom() {
        body.scrollTop = body.scrollHeight;
    }

    function injectGreeting() {
        if (body.children.length === 0) {
            appendMessage('assistant', "Hello! I am grounded on this website's knowledge graph. How can I help you today?");
        }
    }

    // 9. CORE: SEND WIDGET INTERACTION TO BACKEND
    async function handleSendMessage() {
        const msg = input.value.trim();
        if (!msg) return;

        // Clear input box
        input.value = '';
        input.style.height = 'auto';
        sendBtn.disabled = true;

        // Render user message instantly
        appendMessage('user', msg);
        showTypingIndicator();

        try {
            const res = await fetch(`${baseUrl}/api/v1/embed/chats/${agentId}/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    message: msg,
                    session_id: sessionId
                })
            });

            removeTypingIndicator();

            if (res.ok) {
                const payload = await res.json();
                if (payload.success && payload.data) {
                    const result = payload.data;

                    // Save session ID for future turns
                    if (result.session_id && !sessionId) {
                        sessionId = result.session_id;
                        localStorage.setItem(`gm_sess_${agentId}`, sessionId);
                        historyLoaded = true;
                    }

                    appendMessage('assistant', result.answer, {
                        sources: result.sources,
                        confidence: result.confidence
                    });
                } else {
                    appendMessage('assistant', "I apologize, but I could not compute a grounded answer. Please try again.");
                }
            } else {
                appendMessage('assistant', "My connection to the server was interrupted. Please check your network.");
            }
        } catch (e) {
            removeTypingIndicator();
            appendMessage('assistant', "An error occurred while transmitting your request.");
            console.error(e);
        }
    }

    // 10. EVENT HANDLERS

    // Toggle Panel Open/Closed
    function toggleChat() {
        isChatOpen = !isChatOpen;

        if (isChatOpen) {
            panel.classList.add('open');
            launcher.classList.add('active');
            svgChat.style.display = 'none';
            svgClose.style.display = 'block';
            badge.style.display = 'none';

            // Initialize greeter & fetch agent metadata
            fetchAgentDetails();
            injectGreeting();

            // Resume history if first time opening panel
            if (sessionId && !historyLoaded) {
                loadSessionHistory();
            }

            setTimeout(() => input.focus(), 250);
        } else {
            panel.classList.remove('open');
            launcher.classList.remove('active');
            svgChat.style.display = 'block';
            svgClose.style.display = 'none';
        }
    }

    launcher.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    // Reset/Clear conversation history
    resetBtn.addEventListener('click', () => {
        if (confirm("Reset current chat history? This cannot be undone.")) {
            sessionId = null;
            localStorage.removeItem(`gm_sess_${agentId}`);
            body.innerHTML = '';
            historyLoaded = false;
            injectGreeting();
        }
    });

    // Handle typing inputs
    input.addEventListener('input', () => {
        // Auto-sizing text area
        input.style.height = 'auto';
        input.style.height = (input.scrollHeight - 20) + 'px';

        // Send button enable/disable
        sendBtn.disabled = input.value.trim().length === 0;
    });

    // Send on Enter (unless holding shift)
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });

    sendBtn.addEventListener('click', handleSendMessage);

    // Initial Badge Pulse to draw attention if there is no session
    if (!sessionId) {
        badge.style.display = 'block';
    } else {
        badge.style.display = 'none';
    }
})();
