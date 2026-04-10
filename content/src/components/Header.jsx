import React, { useState } from 'react';
import { FiLogOut, FiUser } from 'react-icons/fi';
import '../styles/Header.css';

const Header = ({ onLogout }) => {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [user, setUser] = useState({
    name: 'John Doe',
    email: 'john@example.com',
    avatar: '👤',
  });

  const handleLogout = () => {
    setUserMenuOpen(false);
    onLogout?.();
  };

  return (
    <header className="header">
      <div className="header-left">
        <h1 className="app-title">📁 Semantic File Manager</h1>
      </div>

      <div className="header-right">
        <div className="user-menu">
          <button className="user-button" onClick={() => setUserMenuOpen(!userMenuOpen)}>
            <span className="user-avatar">{user.avatar}</span>
            <span className="user-name">{user.name}</span>
          </button>

          {userMenuOpen && (
            <div className="dropdown-menu">
              <div className="menu-header">
                <p className="menu-name">{user.name}</p>
                <p className="menu-email">{user.email}</p>
              </div>
              <button className="menu-item" onClick={handleLogout}>
                <FiLogOut size={16} />
                <span>Logout</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
