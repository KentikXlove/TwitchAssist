// ---- Форматирование числа с разделителем тысяч (точка) ----
function formatNumber(num) {
    if (num === undefined || num === null) return '0';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

// ---- Защита от выделения и копирования ----
document.addEventListener('contextmenu', e => e.preventDefault());
document.addEventListener('copy', e => e.preventDefault());
document.addEventListener('selectstart', e => e.preventDefault());

// ---- Подключение к WebSocket ----
const socket = io();

// ---- DOM-элементы ----
const tabs = document.querySelectorAll('.tab-btn');
const tabContents = {
    main: document.getElementById('tab-main'),
    settings: document.getElementById('tab-settings'),
    tts: document.getElementById('tab-tts'),
    overlays: document.getElementById('tab-overlays'),
    charts: document.getElementById('tab-charts')
};
const channelInput = document.getElementById('channelInput');
const saveChannelBtn = document.getElementById('saveChannelBtn');
const statusMsg = document.getElementById('statusMsg');
const openChatBtn = document.getElementById('openChatWindowBtn');
const channelName = document.getElementById('channelName');
const gameEl = document.getElementById('game');
const titleEl = document.getElementById('title');
const viewersEl = document.getElementById('viewers');
const followersEl = document.getElementById('followers');
const followersDiffEl = document.getElementById('followersDiff');
const uptimeEl = document.getElementById('uptime');
const avatarImg = document.getElementById('avatarImg');
const chatBox = document.getElementById('chat-box');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');

// ---- Элементы настроек ----
const overlayStyle = document.getElementById('overlayStyle');
const customCSS = document.getElementById('customCSS');
const showAvatar = document.getElementById('showAvatar');
const badWords = document.getElementById('badWords');
const logEnabled = document.getElementById('logEnabled');
const chartIntervalInput = document.getElementById('chartInterval');
const channelUpdateIntervalInput = document.getElementById('channelUpdateInterval');

// ---- TTS элементы ----
const ttsEnabled = document.getElementById('ttsEnabled');
const ttsMode = document.getElementById('ttsMode');
const ttsUsers = document.getElementById('ttsUsers');
const ttsSpeed = document.getElementById('ttsSpeed');
const ttsVolume = document.getElementById('ttsVolume');
const ttsEngine = document.getElementById('ttsEngine');
const ttsVoice = document.getElementById('ttsVoice');

// ---- Элементы оверлеев ----
const overlayChatEnabled = document.getElementById('overlayChatEnabled');
const overlayTelegramEnabled = document.getElementById('overlayTelegramEnabled');
const telegramUsername = document.getElementById('telegramUsername');
const telegramStyle = document.getElementById('telegramStyle');
const telegramCustomCSS = document.getElementById('telegramCustomCSS');
const previewTelegramQR = document.getElementById('previewTelegramQR');
const qrPreviewContainer = document.getElementById('qrPreviewContainer');

// ---- Always on Top ----
const alwaysOnTopCheck = document.getElementById('alwaysOnTop');

// ---- Элементы Telegram уведомлений ----
const telegramNotifyEnabled = document.getElementById('telegramNotifyEnabled');
const telegramBotToken = document.getElementById('telegramBotToken');
const telegramChatId = document.getElementById('telegramChatId');
const proxyUrl = document.getElementById('proxyUrl');
const testTelegramBtn = document.getElementById('testTelegramBtn');
const telegramTestStatus = document.getElementById('telegramTestStatus');
const testProxyBtn = document.getElementById('testProxyBtn');
const proxyTestStatus = document.getElementById('proxyTestStatus');

// ---- НОВЫЙ ЭЛЕМЕНТ: шаблон уведомления ----
const telegramTemplate = document.getElementById('telegramTemplate');

// ---- НОВЫЙ ЭЛЕМЕНТ: кнопка отправки уведомления и статус ----
const sendNotificationBtn = document.getElementById('sendNotificationBtn');
const notificationStatus = document.getElementById('notificationStatus');

// ---- Автоматическое управление прокруткой ----
let autoScrollEnabled = true;

chatBox.addEventListener('scroll', function() {
    const threshold = 50;
    const atBottom = chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < threshold;
    if (atBottom) {
        autoScrollEnabled = true;
    } else {
        autoScrollEnabled = false;
    }
});

// ---- Хранилище смайликов ----
let emotes = {};

// ---- Графики ----
let viewersChart = null;
let followersChart = null;
let viewersChartFull = null;
let followersChartFull = null;

// ---- Отслеживание изменения подписчиков ----
let lastFollowers = null;

// ---- Интервал обновления канала ----
let channelUpdateIntervalId = null;

// ---- Загрузка смайликов ----
function loadEmotes() {
    fetch('/api/emotes')
        .then(res => res.json())
        .then(data => { emotes = data; })
        .catch(err => console.error('Ошибка загрузки смайликов:', err));
}
loadEmotes();

// ---- Функция замены смайликов ----
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

// ---- Переключение вкладок ----
tabs.forEach(btn => {
    btn.addEventListener('click', () => {
        tabs.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tabId = btn.dataset.tab;
        Object.keys(tabContents).forEach(id => {
            tabContents[id].classList.toggle('active', id === tabId);
        });
        if (tabId === 'charts') {
            setTimeout(() => {
                if (viewersChartFull) viewersChartFull.resize();
                if (followersChartFull) followersChartFull.resize();
                window.dispatchEvent(new Event('resize'));
            }, 100);
        }
    });
});

// ---- Форматирование uptime ----
function formatUptime(str) {
    if (!str || str === 'Offline' || str.includes('Offline')) return 'Offline';
    const parts = str.split(',').map(s => s.trim());
    let hours = 0, minutes = 0;
    for (const p of parts) {
        if (p.includes('hour')) {
            const num = parseInt(p, 10);
            if (!isNaN(num)) hours = num;
        } else if (p.includes('minute')) {
            const num = parseInt(p, 10);
            if (!isNaN(num)) minutes = num;
        }
    }
    if (hours === 0 && minutes === 0) return '0m';
    let result = '';
    if (hours > 0) result += hours + 'h ';
    result += minutes + 'm';
    return result.trim();
}

// ---- Добавление сообщения в чат (главная) ----
function addChatMessage(msg) {
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
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ---- Инициализация графиков ----
function initViewersChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const labels = data.map(p => new Date(p.timestamp).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' }));
    const values = data.map(p => p.value);
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Зрители',
                data: values,
                borderColor: '#9147ff',
                backgroundColor: 'rgba(145, 71, 255, 0.2)',
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { maxTicksLimit: 15, color: '#adadb8' } },
                y: { beginAtZero: true, ticks: { color: '#adadb8' } }
            },
            plugins: { legend: { labels: { color: '#adadb8' } } }
        }
    });
    setTimeout(() => chart.resize(), 50);
    return chart;
}

function initFollowersChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const labels = data.map(p => new Date(p.timestamp).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' }));
    const values = data.map(p => p.value);
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Follow',
                data: values,
                borderColor: '#ff6b6b',
                backgroundColor: 'rgba(255, 107, 107, 0.2)',
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { maxTicksLimit: 15, color: '#adadb8' } },
                y: { beginAtZero: true, ticks: { color: '#adadb8' } }
            },
            plugins: { legend: { labels: { color: '#adadb8' } } }
        }
    });
    setTimeout(() => chart.resize(), 50);
    return chart;
}

function updateChart(chart, point) {
    if (!chart) return;
    const time = new Date(point.timestamp).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' });
    chart.data.labels.push(time);
    chart.data.datasets[0].data.push(point.value);
    if (chart.data.labels.length > 200) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
    }
    chart.update('none');
}

// ---- Socket.IO обработчики ----
socket.on('connect', () => {
    console.log('Подключено к WebSocket');
});

socket.on('chat_history', (messages) => {
    chatBox.innerHTML = '';
    if (messages.length === 0) {
        chatBox.innerHTML = '<div class="empty-chat">Сообщений пока нет</div>';
    } else {
        messages.forEach(msg => addChatMessage(msg));
    }
    autoScrollEnabled = true;
    chatBox.scrollTop = chatBox.scrollHeight;
    window.dispatchEvent(new Event('resize'));
});

socket.on('new_message', (msg) => {
    addChatMessage(msg);
});

socket.on('channel_changed', (data) => {
    channelName.textContent = data.channel;
    chatBox.innerHTML = '<div class="empty-chat">Сообщения появятся здесь...</div>';
    fetchChannelInfo();
    channelInput.value = data.channel;
    statusMsg.textContent = 'Канал обновлён';
    statusMsg.className = 'settings-status';
    setTimeout(() => { statusMsg.textContent = ''; }, 3000);
    autoScrollEnabled = true;
    chatBox.scrollTop = chatBox.scrollHeight;
    lastFollowers = null;
    followersDiffEl.innerHTML = '';
    window.dispatchEvent(new Event('resize'));
});

socket.on('settings_updated', (data) => {
    loadSettings();
});

socket.on('overlay_settings_updated', (overlays) => {
    overlayChatEnabled.checked = overlays.chat_enabled !== false;
    overlayTelegramEnabled.checked = overlays.telegram_enabled || false;
    telegramUsername.value = overlays.telegram_username || '';
    telegramStyle.value = overlays.telegram_style || 'dark.css';
    telegramCustomCSS.value = overlays.telegram_custom_css || '';
    const settingsBlock = document.getElementById('telegramSettings');
    if (settingsBlock) {
        settingsBlock.style.display = overlays.telegram_enabled ? 'block' : 'none';
    }
});

// ---- Графики ----
socket.on('viewers_chart_history', (data) => {
    viewersChart = initViewersChart('viewersChart', data);
    viewersChartFull = initViewersChart('viewersChartFull', data);
    window.dispatchEvent(new Event('resize'));
});

socket.on('followers_chart_history', (data) => {
    followersChart = initFollowersChart('followersChart', data);
    followersChartFull = initFollowersChart('followersChartFull', data);
    window.dispatchEvent(new Event('resize'));
});

socket.on('viewers_chart_update', (point) => {
    updateChart(viewersChart, point);
    updateChart(viewersChartFull, point);
});

socket.on('followers_chart_update', (point) => {
    updateChart(followersChart, point);
    updateChart(followersChartFull, point);
});

// ---- Получение информации о канале ----
function fetchChannelInfo() {
    fetch('/api/channel')
        .then(res => res.json())
        .then(data => {
            if (data.error) return;
            channelName.textContent = data.channel || '—';
            gameEl.textContent = data.game || '—';
            titleEl.textContent = data.title || '—';
            viewersEl.textContent = formatNumber(data.viewers || 0);
            followersEl.textContent = formatNumber(data.followers || 0);

            const viewers = data.viewers || 0;
            const isOnline = viewers > 0;

            if (isOnline) {
                statusDot.className = 'status-dot online';
                statusText.textContent = 'В эфире';
                statusText.style.color = '#ff0000';
                uptimeEl.textContent = formatUptime(data.uptime || 'Offline');
            } else {
                statusDot.className = 'status-dot offline';
                statusText.textContent = '';
                statusText.style.color = '#adadb8';
                uptimeEl.textContent = 'Offline';
            }

            if (data.avatar_url) {
                avatarImg.src = data.avatar_url;
                avatarImg.onload = () => {
                    window.dispatchEvent(new Event('resize'));
                };
            }

            const currentFollowers = data.followers || 0;
            if (lastFollowers === null) {
                lastFollowers = currentFollowers;
                followersDiffEl.innerHTML = '';
            } else {
                const diff = currentFollowers - lastFollowers;
                let diffHtml = '';
                if (diff > 0) {
                    diffHtml = `<span class="diff positive">+${diff}</span>`;
                } else if (diff < 0) {
                    diffHtml = `<span class="diff negative">${diff}</span>`;
                } else {
                    diffHtml = `<span class="diff neutral">0</span>`;
                }
                followersDiffEl.innerHTML = diffHtml;
                lastFollowers = currentFollowers;
            }
            window.dispatchEvent(new Event('resize'));
        })
        .catch(console.error);
}

// ---- Запуск интервала обновления канала ----
function startChannelUpdateInterval(intervalSeconds) {
    if (channelUpdateIntervalId) {
        clearInterval(channelUpdateIntervalId);
        channelUpdateIntervalId = null;
    }
    if (intervalSeconds && intervalSeconds > 0) {
        channelUpdateIntervalId = setInterval(fetchChannelInfo, intervalSeconds * 1000);
        console.log(`Интервал обновления канала установлен: ${intervalSeconds} сек`);
    }
}

// ---- Загрузка списка стилей ----
function loadStylesList() {
    fetch('/api/styles')
        .then(res => res.json())
        .then(styles => {
            const select = document.getElementById('overlayStyle');
            if (!select) return;
            select.innerHTML = '';
            const customOpt = document.createElement('option');
            customOpt.value = 'custom';
            customOpt.textContent = 'Пользовательский CSS';
            select.appendChild(customOpt);
            styles.forEach(file => {
                const opt = document.createElement('option');
                opt.value = file;
                opt.textContent = file.replace('.css', '').replace(/_/g, ' ').toUpperCase();
                select.appendChild(opt);
            });
        })
        .catch(console.error);
}

function loadStylesListForTelegram() {
    fetch('/api/styles')
        .then(res => res.json())
        .then(styles => {
            const select = telegramStyle;
            select.innerHTML = '';
            const customOpt = document.createElement('option');
            customOpt.value = 'custom';
            customOpt.textContent = 'Пользовательский CSS';
            select.appendChild(customOpt);
            styles.forEach(file => {
                const opt = document.createElement('option');
                opt.value = file;
                opt.textContent = file.replace('.css', '').replace(/_/g, ' ').toUpperCase();
                select.appendChild(opt);
            });
        })
        .catch(console.error);
}

// ---- Загрузка голосов TTS ----
function loadTTSVoices(engine) {
    return fetch(`/api/tts/voices?engine=${engine}`)
        .then(res => res.json())
        .then(voices => {
            const select = ttsVoice;
            select.innerHTML = '';
            voices.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.id;
                opt.textContent = v.name + (v.lang ? ` (${v.lang})` : '');
                select.appendChild(opt);
            });
        })
        .catch(console.error);
}

// ---- Функция сохранения только оверлея (для автосохранения) ----
function saveOverlayOnly() {
    const overlay = {
        style: overlayStyle.value,
        custom_css: customCSS.value,
        show_avatar: showAvatar.checked,
        bad_words: badWords.value.split(',').map(s => s.trim()).filter(Boolean),
        log_enabled: logEnabled.checked,
        chart_interval: parseInt(chartIntervalInput.value, 10) || 300,
        channel_update_interval: parseInt(channelUpdateIntervalInput.value, 10) || 60,
        always_on_top: alwaysOnTopCheck.checked,
        message_ttl: parseInt(document.getElementById('messageTTL').value, 10) || 0,
        tts: {
            enabled: ttsEnabled.checked,
            mode: ttsMode.value,
            users: ttsUsers.value.split(',').map(s => s.trim()).filter(Boolean),
            speed: parseInt(ttsSpeed.value, 10) || 200,
            volume: parseInt(ttsVolume.value, 10) || 50,
            engine: ttsEngine.value,
            voice: ttsVoice.value
        },
        overlays: {
            chat_enabled: overlayChatEnabled.checked,
            telegram_enabled: overlayTelegramEnabled.checked,
            telegram_username: telegramUsername.value.trim(),
            telegram_style: telegramStyle.value,
            telegram_custom_css: telegramCustomCSS.value
        },
        telegram_notify_enabled: telegramNotifyEnabled.checked,
        telegram_bot_token: telegramBotToken.value.trim(),
        telegram_chat_id: telegramChatId.value.trim(),
        proxy_url: proxyUrl.value.trim(),
        telegram_notification_template: telegramTemplate.value.trim()
    };

    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ overlay: overlay })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            console.error('Ошибка автосохранения:', data.error);
        } else {
            console.log('Настройки автосохранены');
            const newInterval = overlay.channel_update_interval;
            startChannelUpdateInterval(newInterval);
        }
    })
    .catch(err => console.error('Ошибка:', err));
}

// ---- Debounce для автосохранения ----
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

const autoSave = debounce(saveOverlayOnly, 500);

// ---- Навешиваем автосохранение на все элементы с классом auto-save ----
function setupAutoSave() {
    const elements = document.querySelectorAll('.auto-save');
    elements.forEach(el => {
        const eventType = (el.tagName === 'INPUT' && el.type === 'text') || el.tagName === 'TEXTAREA' ? 'input' : 'change';
        el.addEventListener(eventType, autoSave);
    });
}

// ---- Загрузка настроек в форму ----
function loadSettings() {
    fetch('/api/config')
        .then(res => res.json())
        .then(data => {
            const overlay = data.overlay || {};
            channelInput.value = data.channel || '';
            overlayStyle.value = overlay.style || 'dark.css';
            customCSS.value = overlay.custom_css || '';
            showAvatar.checked = overlay.show_avatar !== false;
            badWords.value = (overlay.bad_words || []).join(', ');
            logEnabled.checked = overlay.log_enabled !== false;
            const channelInterval = overlay.channel_update_interval || 60;
            channelUpdateIntervalInput.value = channelInterval;
            const chartInterval = overlay.chart_interval || 300;
            chartIntervalInput.value = chartInterval;
            document.getElementById('messageTTL').value = overlay.message_ttl || 0;
            startChannelUpdateInterval(channelInterval);

            alwaysOnTopCheck.checked = overlay.always_on_top || false;

            const tts = overlay.tts || {};
            ttsEnabled.checked = tts.enabled || false;
            ttsMode.value = tts.mode || 'all_except';
            ttsUsers.value = (tts.users || []).join(', ');
            ttsSpeed.value = tts.speed || 200;
            ttsVolume.value = tts.volume || 50;
            ttsEngine.value = tts.engine || 'pyttsx3';
            const engine = tts.engine || 'pyttsx3';
            loadTTSVoices(engine).then(() => {
                ttsVoice.value = tts.voice || '';
            });

            const overlays = overlay.overlays || {};
            overlayChatEnabled.checked = overlays.chat_enabled !== false;
            overlayTelegramEnabled.checked = overlays.telegram_enabled || false;
            telegramUsername.value = overlays.telegram_username || '';
            telegramStyle.value = overlays.telegram_style || 'dark.css';
            telegramCustomCSS.value = overlays.telegram_custom_css || '';
            const settingsBlock = document.getElementById('telegramSettings');
            if (settingsBlock) {
                settingsBlock.style.display = overlays.telegram_enabled ? 'block' : 'none';
            }

            telegramNotifyEnabled.checked = overlay.telegram_notify_enabled || false;
            telegramBotToken.value = overlay.telegram_bot_token || '';
            telegramChatId.value = overlay.telegram_chat_id || '';
            proxyUrl.value = overlay.proxy_url || '';
            // Загружаем шаблон
            telegramTemplate.value = overlay.telegram_notification_template || '';

            window.dispatchEvent(new Event('resize'));
        })
        .catch(console.error);
}

// ---- Обработчики событий ----
saveChannelBtn.addEventListener('click', () => {
    const newChannel = channelInput.value.trim();
    if (!newChannel) {
        statusMsg.textContent = 'Введите ник!';
        statusMsg.className = 'settings-status error';
        return;
    }
    fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel: newChannel })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            statusMsg.textContent = 'Ошибка: ' + data.error;
            statusMsg.className = 'settings-status error';
        } else {
            statusMsg.textContent = 'Канал обновлён!';
            statusMsg.className = 'settings-status';
            fetchChannelInfo();
            setTimeout(() => { statusMsg.textContent = ''; }, 3000);
            window.dispatchEvent(new Event('resize'));
        }
    })
    .catch(err => {
        statusMsg.textContent = 'Ошибка: ' + err;
        statusMsg.className = 'settings-status error';
    });
});

openChatBtn.addEventListener('click', () => {
    fetch('/chat', { method: 'POST' })
        .then(res => res.json())
        .then(data => console.log('Окно чата открыто:', data))
        .catch(console.error);
});

// ---- Мгновенное сохранение при переключении тумблеров оверлеев ----
overlayTelegramEnabled.addEventListener('change', function() {
    const settingsBlock = document.getElementById('telegramSettings');
    if (settingsBlock) {
        settingsBlock.style.display = this.checked ? 'block' : 'none';
    }
    window.dispatchEvent(new Event('resize'));
});

// ---- Предпросмотр QR ----
previewTelegramQR.addEventListener('click', function() {
    const username = telegramUsername.value.trim();
    if (!username) {
        qrPreviewContainer.innerHTML = '<span style="color:#ff6b6b;">Введите username</span>';
        return;
    }
    qrPreviewContainer.innerHTML = '<img src="/api/qr?username=' + encodeURIComponent(username) + '" alt="QR" style="max-width:150px; border-radius:8px; margin-top:10px;" />';
    window.dispatchEvent(new Event('resize'));
});

// ---- Тестовая отправка Telegram ----
testTelegramBtn.addEventListener('click', function() {
    telegramTestStatus.textContent = 'Отправка...';
    telegramTestStatus.className = 'settings-status';
    fetch('/api/test_telegram', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                telegramTestStatus.textContent = '✓ Сообщение отправлено';
                telegramTestStatus.style.color = '#00e5a0';
            } else {
                telegramTestStatus.textContent = '✗ Ошибка: ' + (data.error || 'неизвестная');
                telegramTestStatus.style.color = '#ff6b6b';
            }
        })
        .catch(err => {
            telegramTestStatus.textContent = '✗ Ошибка запроса';
            telegramTestStatus.style.color = '#ff6b6b';
        });
});

// ---- Проверка прокси ----
testProxyBtn.addEventListener('click', function() {
    const proxy = proxyUrl.value.trim();
    if (!proxy) {
        proxyTestStatus.textContent = 'Введите прокси';
        proxyTestStatus.style.color = '#ff6b6b';
        return;
    }
    proxyTestStatus.textContent = 'Проверка...';
    proxyTestStatus.style.color = '#adadb8';
    fetch('/api/test_proxy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proxy_url: proxy })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            proxyTestStatus.textContent = '✓ ' + (data.message || 'Прокси работает');
            proxyTestStatus.style.color = '#00e5a0';
        } else {
            proxyTestStatus.textContent = '✗ ' + (data.error || 'Ошибка');
            proxyTestStatus.style.color = '#ff6b6b';
        }
    })
    .catch(err => {
        proxyTestStatus.textContent = '✗ Ошибка запроса';
        proxyTestStatus.style.color = '#ff6b6b';
    });
});

// ---- НОВЫЙ ОБРАБОТЧИК: ручная отправка уведомления ----
sendNotificationBtn.addEventListener('click', function() {
    notificationStatus.textContent = 'Отправка...';
    notificationStatus.style.color = '#adadb8';
    fetch('/api/send_telegram_notification', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                notificationStatus.textContent = '✓ Уведомление отправлено';
                notificationStatus.style.color = '#00e5a0';
            } else {
                notificationStatus.textContent = '✗ Ошибка: ' + (data.error || 'неизвестная');
                notificationStatus.style.color = '#ff6b6b';
            }
            // Скрываем через 5 секунд
            setTimeout(() => {
                notificationStatus.textContent = '';
            }, 5000);
        })
        .catch(err => {
            notificationStatus.textContent = '✗ Ошибка запроса';
            notificationStatus.style.color = '#ff6b6b';
            setTimeout(() => {
                notificationStatus.textContent = '';
            }, 5000);
        });
});

// ---- Контекстное меню ----
const contextMenu = document.getElementById('contextMenu');
let currentUsername = '';

document.addEventListener('contextmenu', function(e) {
    const target = e.target.closest('.chat-username');
    if (target) {
        e.preventDefault();
        currentUsername = target.textContent.trim();
        contextMenu.style.display = 'block';
        contextMenu.style.left = e.pageX + 'px';
        contextMenu.style.top = e.pageY + 'px';
        const ttsItem = contextMenu.querySelector('[data-action="tts-toggle"]');
        fetch('/api/config')
            .then(res => res.json())
            .then(data => {
                const tts = data.overlay?.tts || {};
                const users = tts.users || [];
                const mode = tts.mode || 'all_except';
                const isInList = users.some(u => u.toLowerCase() === currentUsername.toLowerCase());
                if (mode === 'all_except') {
                    ttsItem.innerHTML = isInList ? '<i class="fas fa-microphone-slash"></i> Удалить из TTS (исключить)' : '<i class="fas fa-microphone"></i> Добавить в TTS (исключить)';
                } else {
                    ttsItem.innerHTML = isInList ? '<i class="fas fa-microphone-slash"></i> Удалить из TTS (только)' : '<i class="fas fa-microphone"></i> Добавить в TTS (только)';
                }
            })
            .catch(() => {});
    } else {
        contextMenu.style.display = 'none';
    }
});

document.addEventListener('click', function(e) {
    if (!contextMenu.contains(e.target)) {
        contextMenu.style.display = 'none';
    }
});

contextMenu.querySelectorAll('.ctx-item').forEach(item => {
    item.addEventListener('click', function() {
        const action = this.dataset.action;
        if (action === 'open-user') {
            fetch(`/chat/user/${encodeURIComponent(currentUsername)}`, { method: 'POST' })
                .then(res => res.json())
                .then(data => console.log('Окно открыто'))
                .catch(console.error);
        } else if (action === 'tts-toggle') {
            toggleTTSUser(currentUsername);
        }
        contextMenu.style.display = 'none';
    });
});

function toggleTTSUser(username) {
    fetch('/api/config')
        .then(res => res.json())
        .then(data => {
            const overlay = data.overlay || {};
            const tts = overlay.tts || {};
            let users = tts.users || [];
            const lowerUsername = username.toLowerCase();
            const index = users.findIndex(u => u.toLowerCase() === lowerUsername);
            if (index !== -1) {
                users.splice(index, 1);
            } else {
                users.push(username);
            }
            const newTTS = { ...tts, users: users };
            const newOverlay = { ...overlay, tts: newTTS };
            fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ overlay: newOverlay })
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    alert('Ошибка обновления TTS: ' + data.error);
                } else {
                    alert('Настройки TTS обновлены');
                    ttsUsers.value = newTTS.users.join(', ');
                    window.dispatchEvent(new Event('resize'));
                }
            })
            .catch(err => alert('Ошибка: ' + err));
        })
        .catch(err => alert('Ошибка получения настроек: ' + err));
}

// ---- Переключение горизонтальных табов в настройках ----
document.addEventListener('DOMContentLoaded', function() {
    const settingsTabs = document.querySelectorAll('.settings-tab');
    const settingsCategories = document.querySelectorAll('.settings-category');

    settingsTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            settingsTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const category = tab.dataset.category;
            settingsCategories.forEach(cat => {
                cat.classList.toggle('active', cat.id === 'category-' + category);
            });
            window.dispatchEvent(new Event('resize'));
        });
    });
});

// ---- Инициализация ----
document.addEventListener('DOMContentLoaded', function() {
    fetchChannelInfo();
    loadStylesList();
    loadStylesListForTelegram();
    loadSettings();
    setupAutoSave();

    ttsEngine.addEventListener('change', function() {
        loadTTSVoices(this.value);
    });

    window.addEventListener('resize', function() {
        if (viewersChart) viewersChart.resize();
        if (followersChart) followersChart.resize();
        if (viewersChartFull) viewersChartFull.resize();
        if (followersChartFull) followersChartFull.resize();
    });
});