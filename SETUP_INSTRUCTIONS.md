# GUI Setup Instructions

## Что было создано:

Полнофункциональный веб-интерфейс (GUI) для LLM Semantic File System в папке `content/`.

### Структура:

```
content/
├── src/
│   ├── components/
│   │   ├── Header.jsx          - Верхняя панель с меню пользователя
│   │   ├── Sidebar.jsx         - Левая навигационная панель
│   │   ├── FileManager.jsx     - Основной файловый браузер (аналог Windows File Explorer)
│   │   └── AISearcher.jsx      - Компонент семантического поиска (внизу)
│   │
│   ├── services/
│   │   └── api.js              - API клиент для взаимодействия с FastAPI сервером
│   │
│   ├── styles/
│   │   ├── Header.css
│   │   ├── Sidebar.css
│   │   ├── FileManager.css
│   │   └── AISearcher.css
│   │
│   ├── App.jsx                 - Главный компонент
│   ├── main.jsx                - Entry point
│   └── index.css               - Глобальные стили
│
├── public/                     - Статические файлы
├── package.json               - Зависимости (уже установлены)
├── vite.config.js            - Конфигурация Vite
├── README.md                 - Документация проекта
└── API_INTEGRATION_GUIDE.md  - Полная документация API
```

## 🎨 Макет UI:

```
┌─────────────────────────────────────────────────────────┐
│        📁 Semantic File Manager    [👤 User v]          │ Header
├──────────────┬──────────────────────────────────────────┤
│              │                                            │
│  Sidebar     │  📁 Home / ... [Upload]                   │
│  (280px)     ├──────────────────────────────────────────┤
│              │                                            │
│  - Home      │                                            │
│  - Documents │     [File Grid View]                      │ FileManager
│  - Downloads │     - file1.pdf    [file2.docx]          │ (основной)
│  - Recent    │     - folder1      [file3.txt]           │
│  - Shared    │                                            │
│              │                                            │
│  Storage:    ├──────────────────────────────────────────┤
│  45% used    │ 🔍 Search by content... [AI Results ▼]   │ AISearcher
│              │                                            │
└──────────────┴──────────────────────────────────────────┘
```

## 🚀 Как запустить:

### 1. Перейти в папку content
```bash
cd /Users/vladbuyel/Documents/Projects/LLM\ Semantic\ File\ System/content
```

### 2. Запустить dev сервер
```bash
npm run dev
```

Вы увидите:
```
  VITE v8.0.4  ready in 234 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

### 3. Открыть в браузере
```
http://localhost:5173/
```

## 🔌 Требования к Backend (FastAPI):

Ваш FastAPI сервер должен иметь эти endpoint на `http://localhost:8000`:

### File Management:
- `GET /files/list?path=/` - получить список файлов
- `POST /files/upload` - загрузить файлы (multipart/form-data)
- `DELETE /files/delete?path=/file.txt` - удалить файл
- `PUT /files/rename?old_path=/old.txt&new_name=new.txt` - переименовать
- `GET /files/details?path=/file.txt` - информация о файле
- `GET /files/download?path=/file.txt` - скачать файл

### Authentication:
- `GET /auth/user-info` - информация о пользователе
- `POST /auth/logout` - выход

### AI Search (Semantic):
- `POST /search/semantic` - поиск файлов по смыслу
  ```json
  {
    "query": "найти все договора",
    "folder_path": "/"
  }
  ```
  Ответ:
  ```json
  {
    "results": [
      {
        "id": "file_id",
        "name": "contract.pdf",
        "path": "/documents/contract.pdf",
        "relevance": 0.95,
        "snippet": "This is a contract agreement..."
      }
    ]
  }
  ```

## ⚙️ CORS Configuration (для FastAPI):

Добавьте в ваш FastAPI app.py:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000"   # Other dev ports
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📋 Особенности GUI:

✅ **Файловый браузер** с поддержкой:
- Просмотр файлов в сетке (grid layout)
- Загрузка файлов (drag-and-drop готов)
- Удаление файлов
- Переименование (в режиме редактирования)
- Context menu с опциями
- Мок-данные для UI тестирования

✅ **Левая навигация**:
- Быстрый доступ к основным папкам
- Информация об использованном хранилище
- Активное выделение текущей папки

✅ **AI Search**:
- Поиск по смыслу (semantic search)
- Показ relevance score (%)
- Snippets (превью содержимого)
- Обработка ошибок с graceful fallback

✅ **Header**:
- Название приложения
- Меню пользователя с логаутом
- Навигация по пути (breadcrumb)

## 🛠 Разработка:

### Build для production:
```bash
npm run build
```

Создаст оптимизированную версию в папке `dist/`

### Preview production build:
```bash
npm run preview
```

## 🎨 Дизайн:

- **Color Scheme**: Microsoft-like (синий #0078d4)
- **Icons**: react-icons (FiFile, FiFolder, FiUpload, etc.)
- **Responsive**: Работает на всех размерах экранов
- **CSS Modules**: Каждый компонент имеет свой CSS файл

## 📦 Dependencies:

- **react** - UI фреймворк
- **axios** - HTTP клиент для API запросов
- **react-icons** - Иконки
- **vite** - Build tool
- **lucide-react** - Дополнительные иконки (опционально)

## 🔐 Безопасность:

- CORS protection на backend
- Файлы загружаются через multipart/form-data
- Пути файлов обрабатываются на сервере
- Нет хардкода API ключей в frontend коде

## 📝 Примеры использования API:

В `src/services/api.js` готовые методы:

```javascript
import { fileAPI, searchAPI, authAPI } from './services/api'

// Получить файлы
const { data } = await fileAPI.listFiles('/documents')

// Загрузить файл
const formData = new FormData()
formData.append('files', file)
await fileAPI.uploadFile(formData, '/documents')

// Поиск
const { data: results } = await searchAPI.semanticSearch('query')

// Информация о пользователе
const { data: user } = await authAPI.getUserInfo()
```

## 🐛 Troubleshooting:

**"Cannot connect to server"**
- Убедитесь, что FastAPI сервер запущен на localhost:8000
- Проверьте CORS configuration

**CORS Error**
- Добавьте CORS middleware в FastAPI app
- Убедитесь, что http://localhost:5173 в allow_origins

**Файлы не загружаются**
- Проверьте multipart/form-data handling на backend
- Посмотрите Network tab в DevTools (F12)

## ✨ Готово к использованию!

GUI полностью готов к работе. Остается только:
1. Реализовать эти endpoint на вашем FastAPI сервере
2. Запустить `npm run dev` в папке content
3. Наслаждаться семантическим файловым менеджером! 🎉

---

**Author**: Created for LLM Semantic File System
**Created**: 2024
**Port**: 5173 (Vite) + 8000 (FastAPI)
