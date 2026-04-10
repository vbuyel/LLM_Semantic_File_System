# Semantic File Manager GUI

Современный веб-интерфейс для управления файлами с поддержкой семантического поиска через LLM. Интерфейс похож на Microsoft File Explorer.

## 🎯 Особенности

- 📁 **Файловый браузер** - просмотр, загрузка, удаление и переименование файлов
- 🔍 **Семантический поиск** - поиск файлов по содержанию и смыслу с помощью LLM
- ☁️ **Интеграция Google Drive** - работа с файлами пользователя и облачным хранилищем
- 📊 **Интуитивный UI** - дизайн, похожий на Windows File Explorer
- ⚡ **Быстрая разработка** - Vite + React

## 🚀 Быстрый старт

### Установка и запуск

```bash
# Зависимости уже установлены
npm run dev
```

Откройте браузер: `http://localhost:5173`

## 🔌 API Интеграция

GUI взаимодействует с FastAPI сервером на `localhost:8000`.

**Требуемые endpoint:**
- `GET /files/list` - список файлов
- `POST /files/upload` - загрузка файлов
- `DELETE /files/delete` - удаление файла
- `PUT /files/rename` - переименование
- `POST /search/semantic` - поиск по смыслу
- `GET /auth/user-info` - информация о пользователе

**Полная документация:** [API_INTEGRATION_GUIDE.md](./API_INTEGRATION_GUIDE.md)

## 🎨 Структура

```
src/
├── components/          # React компоненты
├── services/           # API клиент
├── styles/            # CSS стили
└── App.jsx            # Главный компонент
```

## 🛠 Разработка

```bash
npm run dev       # Разработка
npm run build     # Build
npm run preview   # Preview build
```

## 🌐 CORS

Убедитесь в CORS конфигурации на FastAPI сервере для `http://localhost:5173`
