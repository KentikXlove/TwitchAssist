const socket = io();
const chatBox = document.getElementById('chat-box');
const channelDisplay = document.getElementById('channelDisplay');

let emotes = {};
// Теперь получаем значение из window
let filterUser = window.FILTER_USER || '';

// ---- Автоматическое управление прокруткой ----
let autoScrollEnabled = true;

chatBox.addEventListener('scroll', function() {
    const threshold = 50; // пикселей до низа
    const atBottom = chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < threshold;
    if (atBottom) {
        autoScrollEnabled = true;
    } else {
        autoScrollEnabled = false;
    }
});

// ---- Загрузка смайликов ----
function loadEmotes() {
    fetch('/api/emotes')
        .then(res => res.json())
        .then(data => { emotes = data; })
        .catch(console.error);
}
loadEmotes();

// ---- Замена смайликов ----
function replaceEmotes(text) {
    if (!text) return text;
    let result = text;
    const keys = Object.keys(emotes).sort((a, b) => b.length - a.length);
    for (const key of keys) {
        const url = emotes[key];
        const escapedKey = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        let pattern;
        if (/^[a-zA-Z0-9_]+$/.test(key)) {
            pattern = '\\b' + escapedKey + '\\b';
        } else {
            pattern = escapedKey;
        }
        const regex = new RegExp('(?<![a-zA-Z0-9_.-])' + pattern + '(?![a-zA-Z0-9_.-])', 'g');
        result = result.replace(regex, (match) => {
            const startIndex = result.indexOf(match);
            const before = result.substring(Math.max(0, startIndex - 10), startIndex);
            if (before.includes('://') || before.includes('http')) {
                return match;
            }
            return `<img class="emote" src="${url}" alt="${key}" title="${key}" />`;
        });
    }
    return result;
}

// ---- Добавление сообщения (с фильтром) ----
function addChatMessage(msg) {
    // Фильтр по пользователю (регистронезависимо)
    if (filterUser && msg.username.toLowerCase() !== filterUser.toLowerCase()) {
        return;
    }
    const empty = chatBox.querySelector('.empty-chat');
    if (empty) empty.remove();
    const div = document.createElement('div');
    div.className = 'chat-message';
    const time = new Date(msg.timestamp).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' });
    const color = msg.color || '#9147ff';
    const messageHtml = msg.processed_text || replaceEmotes(escapeHtml(msg.message));
    div.innerHTML = `
        <span class="chat-time">${time}</span>
        <span class="chat-username" style="color:${color}">${escapeHtml(msg.username)}</span>
        <span class="chat-text">${messageHtml}</span>
    `;
    chatBox.appendChild(div);
    if (autoScrollEnabled) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g,"&amp;")
        .replace(/</g,"&lt;")
        .replace(/>/g,"&gt;")
        .replace(/"/g,"&quot;")
        .replace(/'/g,"&#039;");
}

// ---- Socket.IO ----
socket.on('connect', () => console.log('Окно чата подключено к WebSocket'));

socket.on('chat_history', (messages) => {
    chatBox.innerHTML = '';
    let filtered = messages;
    if (filterUser) {
        filtered = messages.filter(m => m.username.toLowerCase() === filterUser.toLowerCase());
    }
    if (filtered.length === 0) {
        chatBox.innerHTML = '<div class="empty-chat">Сообщений пока нет</div>';
    } else {
        filtered.forEach(msg => addChatMessage(msg));
    }
    // Принудительно прокручиваем вниз и включаем автопрокрутку
    autoScrollEnabled = true;
    chatBox.scrollTop = chatBox.scrollHeight;
});

socket.on('new_message', (msg) => {
    addChatMessage(msg);
});

socket.on('channel_changed', (data) => {
    channelDisplay.textContent = data.channel;
    chatBox.innerHTML = '<div class="empty-chat">Сообщения появятся здесь...</div>';
    autoScrollEnabled = true;
    chatBox.scrollTop = chatBox.scrollHeight;
});

// ---- Загрузка имени канала ----
fetch('/api/config')
    .then(res => res.json())
    .then(data => {
        if (data.channel) channelDisplay.textContent = data.channel;
    })
    .catch(() => {});