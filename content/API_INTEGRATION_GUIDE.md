# API Integration Guide for Semantic File Manager GUI

## Overview
Этот GUI требует следующие endpoint на вашем FastAPI сервере (`localhost:8000`).

## Required Backend API Endpoints

### 1. File Management Endpoints

#### List Files
```
GET /files/list?path=/
Response: {
  "files": [
    {
      "id": "unique_id",
      "name": "filename.ext",
      "type": "file|folder",
      "size": "2.5 MB",
      "modified": "2024-01-15"
    }
  ]
}
```

#### Upload Files
```
POST /files/upload?path=/
Content-Type: multipart/form-data
Files: files (multiple)
Response: {
  "success": true,
  "uploaded_files": ["file1.txt", "file2.pdf"]
}
```

#### Delete File
```
DELETE /files/delete?path=/path/to/file.txt
Response: {
  "success": true,
  "message": "File deleted"
}
```

#### Rename File
```
PUT /files/rename?old_path=/old_name.txt&new_name=new_name.txt
Response: {
  "success": true,
  "new_path": "/new_name.txt"
}
```

#### Get File Details
```
GET /files/details?path=/file.txt
Response: {
  "name": "file.txt",
  "path": "/file.txt",
  "size": "2.5 MB",
  "created": "2024-01-15",
  "modified": "2024-01-15",
  "type": "file"
}
```

#### Download File
```
GET /files/download?path=/file.txt
Response: Binary file data
```

### 2. Authentication Endpoints

#### Get User Info
```
GET /auth/user-info
Response: {
  "id": "user_id",
  "name": "John Doe",
  "email": "john@example.com",
  "avatar": "https://..."
}
```

#### Get Google Drive Files (for authenticated users)
```
GET /auth/google-drive-files
Response: {
  "files": [
    {
      "id": "google_file_id",
      "name": "filename.ext",
      "type": "file|folder",
      "size": "2.5 MB"
    }
  ]
}
```

#### Logout
```
POST /auth/logout
Response: {
  "success": true,
  "message": "Logged out"
}
```

### 3. Semantic Search Endpoints

#### Semantic Search
```
POST /search/semantic
Content-Type: application/json
Body: {
  "query": "search query text",
  "folder_path": "/"
}
Response: {
  "results": [
    {
      "id": "file_id",
      "name": "filename.ext",
      "path": "/path/to/file.txt",
      "relevance": 0.95,
      "snippet": "Preview text from the file..."
    }
  ]
}
```

#### Analyze File
```
POST /search/analyze
Content-Type: application/json
Body: {
  "file_path": "/path/to/file.txt"
}
Response: {
  "analysis": "AI analysis of the file content",
  "summary": "Brief summary",
  "keywords": ["keyword1", "keyword2"]
}
```

#### Get Search Suggestions
```
GET /search/suggestions?folder_path=/
Response: {
  "suggestions": ["common search terms", "file names", "topics"]
}
```

## CORS Configuration
Make sure your FastAPI server has CORS enabled:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Running the GUI

1. Navigate to the `content` directory:
```bash
cd content
```

2. Install dependencies (already done):
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open in browser:
```
http://localhost:5173
```

## Error Handling
The GUI handles API errors gracefully with fallback mock data for UI testing. In production, ensure your API returns proper HTTP status codes and error messages:

```json
{
  "error": "Error message",
  "status": 400
}
```

## Notes
- The API base URL is configured in `src/services/api.js` as `http://localhost:8000`
- All file paths use forward slashes `/`
- The `relevance` score in search results should be between 0 and 1
- File size should be formatted as string (e.g., "2.5 MB")
- Dates should be in format: "YYYY-MM-DD"
