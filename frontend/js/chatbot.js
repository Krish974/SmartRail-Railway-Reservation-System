/**
 * SMART RAILWAY - AI ASSISTANT CHATBOT CONTROLLER
 */

document.addEventListener('DOMContentLoaded', () => {
  setupChatbotUI();
});

function setupChatbotUI() {
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const msg = input.value.trim();
      if (msg) {
        sendUserMessage(msg);
        input.value = '';
      }
    });
  }

  // Quick suggestion chips
  document.querySelectorAll('.suggestion-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const query = chip.getAttribute('data-query') || chip.textContent.trim();
      sendUserMessage(query);
    });
  });

  // Action buttons delegated click handler
  const messagesContainer = document.getElementById('chat-messages-container');
  if (messagesContainer) {
    messagesContainer.addEventListener('click', (e) => {
      const btn = e.target.closest('.chat-action-btn[data-query]');
      if (btn) {
        const query = btn.getAttribute('data-query');
        if (query) sendUserMessage(query);
      }
    });
  }
}

function appendMessage(sender, htmlContent) {
  const messagesContainer = document.getElementById('chat-messages-container');
  if (!messagesContainer) return;

  const msgDiv = document.createElement('div');
  msgDiv.className = `chat-bubble chat-${sender}`;

  const isBot = sender === 'bot';
  const avatar = isBot 
    ? `<div class="chat-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>`
    : `<div class="chat-avatar user-avatar"><i class="fa-solid fa-user"></i></div>`;

  msgDiv.innerHTML = `
    ${avatar}
    <div class="chat-bubble-content">
      ${htmlContent}
    </div>
  `;

  messagesContainer.appendChild(msgDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showTypingIndicator() {
  const messagesContainer = document.getElementById('chat-messages-container');
  const indicator = document.createElement('div');
  indicator.id = 'chat-typing-indicator';
  indicator.className = 'chat-bubble chat-bot';
  indicator.innerHTML = `
    <div class="chat-avatar bot-avatar"><i class="fa-solid fa-robot"></i></div>
    <div class="chat-bubble-content typing-dots">
      <span></span><span></span><span></span>
    </div>
  `;
  messagesContainer.appendChild(indicator);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById('chat-typing-indicator');
  if (el) el.remove();
}

let chatSessionId = sessionStorage.getItem('smartrail_chat_session') || ('sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9));
sessionStorage.setItem('smartrail_chat_session', chatSessionId);

async function sendUserMessage(text) {
  // Render user message bubble
  appendMessage('user', `<p>${escapeHtml(text)}</p>`);

  showTypingIndicator();

  const res = await fetchApi('/chatbot', {
    method: 'POST',
    body: JSON.stringify({ message: text, session_id: chatSessionId })
  });

  removeTypingIndicator();

  if (!res.success) {
    appendMessage('bot', `<p style="color: var(--accent-red);">${res.message}</p>`);
    return;
  }

  const replyData = res.data;
  // Convert markdown headers, bold, inline code, and newlines to HTML
  let formattedReply = replyData.response
    .replace(/^### (.*$)/gim, '<h4 style="margin: 0.25rem 0 0.5rem; color: var(--primary-navy); font-size: 1.05rem;">$1</h4>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code style="background: rgba(0,0,0,0.06); padding: 1px 5px; border-radius: 4px; font-weight: 600;">$1</code>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>');

  // Append action buttons if present
  if (replyData.suggested_actions && replyData.suggested_actions.length > 0) {
    const actionsHtml = replyData.suggested_actions.map(act => {
      if (act.url) {
        return `<a href="${act.url}" class="btn btn-sm btn-outline chat-action-btn">${act.label} <i class="fa-solid fa-arrow-up-right-from-square"></i></a>`;
      } else {
        return `<button type="button" data-query="${escapeHtml(act.query || '')}" class="btn btn-sm btn-outline chat-action-btn">${escapeHtml(act.label)}</button>`;
      }
    }).join(' ');
    formattedReply += `<div class="chat-actions-container" style="margin-top: 0.75rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">${actionsHtml}</div>`;
  }

  appendMessage('bot', formattedReply);
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.innerText = text;
  return div.innerHTML;
}
