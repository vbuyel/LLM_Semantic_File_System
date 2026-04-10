import React, { useState, useEffect } from 'react';
import {
  FiFile,
  FiFolder,
  FiUpload,
  FiTrash2,
  FiEdit2,
  FiDownload,
  FiMoreVertical,
  FiChevronRight,
} from 'react-icons/fi';
import { fileAPI } from '../services/api';
import '../styles/FileManager.css';

const FileManager = ({ currentPath, onRefresh }) => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [contextMenu, setContextMenu] = useState(null);
  const [renaming, setRenaming] = useState(null);
  const [newName, setNewName] = useState('');

  useEffect(() => {
    loadFiles();
  }, [currentPath]);

  const loadFiles = async () => {
    setLoading(true);
    try {
      const response = await fileAPI.listFiles(currentPath);
      setFiles(response.data.files || []);
    } catch (error) {
      console.error('Error loading files:', error);
      // Mock data for UI testing
      setFiles([
        {
          id: '1',
          name: 'Document 1.pdf',
          type: 'file',
          size: '2.5 MB',
          modified: '2024-01-15',
          icon: FiFile,
        },
        {
          id: '2',
          name: 'Project Folder',
          type: 'folder',
          modified: '2024-01-14',
          icon: FiFolder,
        },
        {
          id: '3',
          name: 'Presentation.pptx',
          type: 'file',
          size: '4.8 MB',
          modified: '2024-01-10',
          icon: FiFile,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (event) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const formData = new FormData();
    for (let file of files) {
      formData.append('files', file);
    }

    try {
      await fileAPI.uploadFile(formData, currentPath);
      loadFiles();
    } catch (error) {
      console.error('Upload error:', error);
    }
  };

  const handleDelete = async (filePath) => {
    if (window.confirm('Are you sure you want to delete this file?')) {
      try {
        await fileAPI.deleteFile(filePath);
        loadFiles();
      } catch (error) {
        console.error('Delete error:', error);
      }
    }
  };

  const handleRename = async (oldPath, newName) => {
    if (!newName.trim()) return;

    try {
      await fileAPI.renameFile(oldPath, newName);
      setRenaming(null);
      loadFiles();
    } catch (error) {
      console.error('Rename error:', error);
    }
  };

  const handleDownload = async (filePath) => {
    try {
      const response = await fileAPI.downloadFile(filePath);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = filePath.split('/').pop();
      link.click();
    } catch (error) {
      console.error('Download error:', error);
    }
  };

  const handleContextMenu = (e, file) => {
    e.preventDefault();
    setSelectedFile(file);
    setContextMenu({ x: e.clientX, y: e.clientY });
  };

  const renderFileIcon = (file) => {
    if (file.type === 'folder') return <FiFolder size={32} className="file-icon folder" />;
    if (file.name.endsWith('.pdf')) return <FiFile size={32} className="file-icon pdf" />;
    if (file.name.endsWith('.pptx') || file.name.endsWith('.ppt'))
      return <FiFile size={32} className="file-icon pptx" />;
    return <FiFile size={32} className="file-icon" />;
  };

  return (
    <div className="file-manager">
      <div className="file-manager-toolbar">
        <div className="breadcrumb">
          <span>📁</span>
          <span className="path">{currentPath}</span>
        </div>
        <label className="upload-button">
          <FiUpload size={20} />
          <span>Upload Files</span>
          <input type="file" multiple onChange={handleUpload} hidden />
        </label>
      </div>

      {loading ? (
        <div className="loading">Loading files...</div>
      ) : (
        <div className="files-container">
          {files.length === 0 ? (
            <div className="empty-state">
              <FiFolder size={48} />
              <p>No files in this folder</p>
            </div>
          ) : (
            <div className="files-grid">
              {files.map((file) => (
                <div
                  key={file.id}
                  className={`file-item ${selectedFile?.id === file.id ? 'selected' : ''}`}
                  onContextMenu={(e) => handleContextMenu(e, file)}
                  onClick={() => setSelectedFile(file)}
                  onDoubleClick={() => {
                    if (file.type === 'folder') {
                      // Navigate to folder
                    }
                  }}
                >
                  <div className="file-thumbnail">{renderFileIcon(file)}</div>
                  <div className="file-info">
                    {renaming?.id === file.id ? (
                      <input
                        type="text"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        onBlur={() => handleRename(`${currentPath}/${file.name}`, newName)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter')
                            handleRename(`${currentPath}/${file.name}`, newName);
                          if (e.key === 'Escape') setRenaming(null);
                        }}
                        autoFocus
                        className="rename-input"
                      />
                    ) : (
                      <>
                        <p className="file-name">{file.name}</p>
                        <p className="file-meta">{file.size || ''} • {file.modified}</p>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {contextMenu && selectedFile && (
        <div
          className="context-menu"
          style={{ top: contextMenu.y, left: contextMenu.x }}
          onMouseLeave={() => setContextMenu(null)}
        >
          <button className="context-item" onClick={() => handleDownload(`${currentPath}/${selectedFile.name}`)}>
            <FiDownload size={16} />
            <span>Download</span>
          </button>
          <button
            className="context-item"
            onClick={() => {
              setRenaming(selectedFile);
              setNewName(selectedFile.name);
            }}
          >
            <FiEdit2 size={16} />
            <span>Rename</span>
          </button>
          <button
            className="context-item delete"
            onClick={() => handleDelete(`${currentPath}/${selectedFile.name}`)}
          >
            <FiTrash2 size={16} />
            <span>Delete</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default FileManager;
