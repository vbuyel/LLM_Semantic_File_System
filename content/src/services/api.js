import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// File Management
export const fileAPI = {
  // Get list of files (with optional folder path)
  listFiles: (path = '/') => {
    return api.get('/files/list', { params: { path } });
  },

  // Upload file
  uploadFile: (formData, path = '/') => {
    return api.post('/files/upload', formData, {
      params: { path },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // Delete file
  deleteFile: (filePath) => {
    return api.delete('/files/delete', { params: { path: filePath } });
  },

  // Rename file
  renameFile: (oldPath, newName) => {
    return api.put('/files/rename', null, {
      params: { old_path: oldPath, new_name: newName },
    });
  },

  // Get file details/metadata
  getFileDetails: (filePath) => {
    return api.get('/files/details', { params: { path: filePath } });
  },

  // Download file
  downloadFile: (filePath) => {
    return api.get('/files/download', {
      params: { path: filePath },
      responseType: 'blob',
    });
  },
};

// Google Drive/Cloud Integration
export const authAPI = {
  // Get current user info
  getUserInfo: () => {
    return api.get('/auth/user-info');
  },

  // Get Google Drive files (for authenticated users)
  getGoogleDriveFiles: () => {
    return api.get('/auth/google-drive-files');
  },

  // Logout
  logout: () => {
    return api.post('/auth/logout');
  },
};

// Semantic Search with LLM
export const searchAPI = {
  // Semantic search in files
  semanticSearch: (query, folderPath = '/') => {
    return api.post('/search/semantic', {
      query,
      folder_path: folderPath,
    });
  },

  // Analyze file content with LLM
  analyzeFile: (filePath) => {
    return api.post('/search/analyze', {
      file_path: filePath,
    });
  },

  // Get search suggestions based on file content
  getSearchSuggestions: (folderPath = '/') => {
    return api.get('/search/suggestions', {
      params: { folder_path: folderPath },
    });
  },
};

export default api;
