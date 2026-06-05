// Chat interface — AJAX-based chat with session memory

const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const typingIndicator = document.getElementById('typingIndicator');
const chatStatus = document.getElementById('chatStatus');

let sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

function addMessage(role, content) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.textContent = content;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping(show) {
    typingIndicator.classList.toggle('show', show);
    if (show) chatMessages.scrollTop = chatMessages.scrollHeight;
}

function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    // Check for exit command
    if (text.toLowerCase() === 'exit()') {
        addMessage('system', 'Chat session ended. Refreshing...');
        chatInput.value = '';
        setTimeout(() => window.location.reload(), 1000);
        return;
    }

    addMessage('user', text);
    chatInput.value = '';
    chatInput.disabled = true;
    showTyping(true);
    chatStatus.textContent = 'Thinking...';
    chatStatus.className = 'badge badge-warning';

    fetch(`/domain/${DOMAIN_NAME}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId })
    })
    .then(r => r.json())
    .then(data => {
        showTyping(false);
        chatInput.disabled = false;
        chatInput.focus();
        chatStatus.textContent = 'Ready';
        chatStatus.className = 'badge badge-success';

        if (data.error) {
            addMessage('system', 'Error: ' + data.error);
        } else {
            addMessage('assistant', data.response);
        }
    })
    .catch(err => {
        showTyping(false);
        chatInput.disabled = false;
        chatInput.focus();
        chatStatus.textContent = 'Error';
        chatStatus.className = 'badge badge-warning';
        addMessage('system', 'Connection error. Please try again.');
    });
}
