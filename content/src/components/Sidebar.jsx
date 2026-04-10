import React, { useState } from 'react';
import { FiChevronDown, FiFolder, FiHome } from 'react-icons/fi';
import '../styles/Sidebar.css';

const Sidebar = ({ onPathChange, currentPath }) => {
  const [expanded, setExpanded] = useState({});

  const defaultFolders = [
    { id: 'home', label: 'Home', path: '/', icon: FiHome },
    { id: 'documents', label: 'Documents', path: '/documents', icon: FiFolder },
    { id: 'downloads', label: 'Downloads', path: '/downloads', icon: FiFolder },
    { id: 'recent', label: 'Recent', path: '/recent', icon: FiFolder },
    { id: 'shared', label: 'Shared with me', path: '/shared', icon: FiFolder },
  ];

  const handleToggle = (id) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handlePathClick = (path) => {
    onPathChange(path);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>File Manager</h2>
      </div>

      <nav className="sidebar-nav">
        {defaultFolders.map((folder) => {
          const Icon = folder.icon;
          return (
            <div key={folder.id} className="sidebar-item">
              <button
                className={`sidebar-link ${currentPath === folder.path ? 'active' : ''}`}
                onClick={() => handlePathClick(folder.path)}
              >
                <Icon size={18} />
                <span>{folder.label}</span>
              </button>
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="storage-info">
          <p className="storage-label">Google Cloud Storage</p>
          <div className="storage-bar">
            <div className="storage-used" style={{ width: '45%' }}></div>
          </div>
          <p className="storage-text">45 GB of 100 GB used</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
