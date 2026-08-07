# 🎨 Руководство по кастомизации стилей оверлеев

Этот документ описывает **только** способы изменения внешнего вида двух оверлеев – **чат** и **Telegram**. Здесь вы найдёте все CSS-классы, переменные, способы загрузки и примеры.

---

## 📦 Общий принцип

Оба оверлея поддерживают два способа применения стилей:

1. **Встроенный CSS** – через параметры `custom_css` (для чата) и `telegram_custom_css` (для Telegram). Вы передаёте строку с CSS-кодом, который вставляется в тег `<style>`.

2. **Предустановленный стиль** – через параметры `style` (чат) и `telegram_style` (Telegram). Указываете имя стиля, и сервер по запросу `/api/style?name=...` отдаёт его содержимое. Если стиль не найден, используется `custom_css`.

> **Приоритет:** если задан `style` (и он не равен `"custom"`), то загружается стиль с сервера. Иначе берётся `custom_css`.

Стили применяются **мгновенно** без перезагрузки страницы благодаря WebSocket-событию `settings_updated`.

---

## 🖥 Чат-оверлей (`chat.html`)

### DOM-структура сообщения
```html
<div class="chat-msg">
  <img class="chat-avatar" src="..." alt="username">
  <span class="chat-badges">
    <img class="chat-badge" src="...">
  </span>
  <span class="chat-username" style="color: #FF0000;">Username</span>
  : <span>Текст с <img class="chat-emote" src="..."></span>
  <span class="chat-time">12:34:56</span>
</div>
```

### Доступные CSS-классы и переменные

| Селектор / Переменная | Описание |
|------------------------|----------|
| `#messages` | Контейнер всех сообщений (имеет вертикальный скролл, скрытую полосу прокрутки) |
| `.chat-msg` | Блок одного сообщения (flex-контейнер) |
| `.chat-avatar` | Аватар пользователя (круг, размер через `--avatar-size`) |
| `.chat-badges` | Обёртка для бэйджей (flex) |
| `.chat-badge` | Отдельный бэйдж (изображение) |
| `.chat-username` | Имя пользователя (цвет задаётся через атрибут `style`) |
| `.chat-time` | Время сообщения (по умолчанию скрыто до наведения, но вы можете переопределить) |
| `.chat-emote` | Картинка смайлика (вставляется через `img`) |
| `--avatar-size` | CSS-переменная, определяющая размер аватара (по умолчанию `28px`, меняется через настройки `avatar_size`) |
| `--anim-speed` | CSS-переменная для длительности анимации (устанавливается из конфига `animation.speed`) |

### Примеры кастомизации

#### 1. Изменить фон и скругление сообщений
```css
.chat-msg {
    background: rgba(20, 20, 30, 0.85);
    border-radius: 16px;
    padding: 10px 18px;
    margin-bottom: 6px;
    border-left: 4px solid #9147ff;
    backdrop-filter: blur(6px);
}
```

#### 2. Сделать имя ярче и с тенью
```css
.chat-username {
    font-weight: 800;
    text-shadow: 0 0 12px currentColor;
}
```

#### 3. Показать время всегда (не только при наведении)
```css
.chat-time {
    opacity: 1 !important; /* перебиваем поведение по умолчанию */
    font-size: 11px;
    color: #aaa;
}
```

#### 4. Увеличить смайлики
```css
.chat-emote {
    height: 1.8em;
    vertical-align: middle;
}
```

#### 5. Изменить размер аватара через переменную (глобально)
```css
:root {
    --avatar-size: 40px; /* или можно в .chat-msg, но лучше через настройки */
}
```

#### 6. Добавить плавное появление сообщений (если включены анимации)
```css
.chat-msg {
    animation: fadeIn 0.3s ease-out;
}
/* или используйте встроенные классы .anim-* */
```

---

## 📱 Telegram-оверлей (`telegram.html`)

### DOM-структура
```html
<div class="telegram-container">
    <h2>Подпишитесь на Telegram</h2>
    <img src="data:image/png;base64,..." alt="QR-код для @username">
    <div class="username">@username</div>
</div>
```
> При выключенном оверлее отображается `<div class="overlay-disabled"></div>` (содержимое пустое, но вы можете задать текст через CSS-псевдоэлементы или в JS).

### Доступные CSS-классы

| Селектор | Описание |
|----------|----------|
| `body` | Корневой элемент (можно задать фон, шрифт) |
| `.telegram-container` | Основной блок (центрирован, содержит QR и текст) |
| `h2` | Заголовок "Подпишитесь на Telegram" |
| `img` | QR-код (вы можете задать размер, тень, обводку) |
| `.username` | Имя пользователя (с символом @) |
| `.overlay-disabled` | Отображается, когда оверлей выключен (можно скрыть или оформить) |

### Примеры кастомизации

#### 1. Тёмно-фиолетовый фон с градиентом
```css
body {
    background: linear-gradient(135deg, #0d0d1a, #1a0a2e);
    font-family: 'Montserrat', sans-serif;
}
.telegram-container {
    background: rgba(0,0,0,0.7);
    border: 2px solid #9147ff;
    border-radius: 30px;
    padding: 40px 50px;
    box-shadow: 0 0 40px rgba(145, 71, 255, 0.3);
}
```

#### 2. Изменить оформление QR-кода
```css
.telegram-container img {
    max-width: 250px;
    border-radius: 20px;
    border: 4px solid #ffd700;
    box-shadow: 0 0 30px rgba(255, 215, 0, 0.4);
}
```

#### 3. Сделать имя пользователя более заметным
```css
.username {
    font-size: 24px;
    font-weight: bold;
    color: #ffd700;
    text-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
    margin-top: 10px;
}
```

#### 4. Скрыть заголовок (оставить только QR и имя)
```css
h2 {
    display: none;
}
```

#### 5. Изменить фон при выключенном оверлее
```css
.overlay-disabled {
    display: none; /* или */
    background: #222;
    color: #555;
    font-size: 20px;
    padding: 20px;
}
```

---

## 🔧 Как применить свой стиль

### Через интерфейс (админ-панель)

1. Перейдите в настройки оверлея.
2. Для чата найдите поля:
   - `custom_css` – вставьте свой CSS-код.
   - `style` – укажите имя предустановленного стиля (если загружен на сервер).
3. Для Telegram аналогично:
   - `telegram_custom_css`
   - `telegram_style`
4. Сохраните настройки – изменения применятся автоматически.

### Через API (для разработчиков)

- Обновите конфигурацию через `POST /api/config` (если реализовано) с нужными полями.
- Либо просто загрузите стиль на сервер по имени и укажите это имя.

---

## ⚠️ Особенности и советы

- **Специфичность:** пользовательские стили вставляются в `<style id="custom-style">` (чат) или `<style id="dynamic-style">` (Telegram) в самом конце `<head>`, поэтому они имеют приоритет над базовыми стилями при одинаковой специфичности.
- **Избегайте `!important`**, если можно обойтись увеличением специфичности (например, `.chat-msg .chat-username`).
- Для изменения размера аватара в чате предпочтительнее использовать настройку `avatar_size`, а не переопределять `--avatar-size` вручную, чтобы JS корректно обновлял размеры.
- При работе с анимациями учтите, что в минимальной версии чата анимации удалены; если вы хотите их использовать, добавьте свои `@keyframes` и классы `.anim-*` / `.exit-*`.
- Для Telegram-оверлея вы можете полностью переопределить внешний вид, включая позиционирование на экране (например, сместить в угол), используя `position: absolute` для `.telegram-container`.
- Чтобы проверить изменения, используйте инспектор браузера (F12) – все стили видны во вкладке Elements.

---

## 📝 Пример полного кастомного стиля для чата

```css
/* Тёмная тема с неоновыми акцентами */
#messages {
    padding: 20px;
    background: rgba(10, 10, 20, 0.8);
    border-radius: 20px;
    backdrop-filter: blur(8px);
}

.chat-msg {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 20px;
    padding: 12px 20px;
    margin-bottom: 8px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    transition: all 0.2s;
}
.chat-msg:hover {
    background: rgba(255, 255, 255, 0.12);
    transform: scale(1.02);
}

.chat-username {
    font-weight: 700;
    text-shadow: 0 0 15px currentColor;
    margin-right: 8px;
}

.chat-avatar {
    border: 2px solid #9147ff;
    box-shadow: 0 0 15px rgba(145, 71, 255, 0.3);
}

.chat-time {
    opacity: 0.6;
    font-size: 10px;
    margin-left: 15px;
    color: #aaa;
}

.chat-badge {
    height: 22px;
    margin-right: 2px;
}

.chat-emote {
    height: 1.6em;
    vertical-align: middle;
}
```

---

## 📝 Пример полного кастомного стиля для Telegram

```css
body {
    background: #0a0a0f;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    margin: 0;
    font-family: 'Inter', sans-serif;
}

.telegram-container {
    background: rgba(20, 20, 30, 0.9);
    padding: 40px 60px;
    border-radius: 40px;
    border: 1px solid #333;
    box-shadow: 0 20px 60px rgba(0,0,0,0.8);
    text-align: center;
    backdrop-filter: blur(10px);
}

h2 {
    color: #fff;
    font-size: 28px;
    font-weight: 300;
    letter-spacing: 1px;
    margin-bottom: 20px;
}

.telegram-container img {
    max-width: 280px;
    border-radius: 16px;
    border: 4px solid #2a2a3e;
    box-shadow: 0 0 40px rgba(0, 150, 255, 0.2);
}

.username {
    color: #8a8aff;
    font-size: 22px;
    font-weight: 500;
    margin-top: 20px;
}
```

---

## 📚 Заключение

Теперь вы можете создавать уникальный дизайн для каждого оверлея, используя простые CSS-правила. Экспериментируйте, комбинируйте и не забывайте проверять в инспекторе браузера, чтобы точно попасть в нужные классы. Удачи в кастомизации! 🚀
