import { useState } from 'react'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import FileManager from './components/FileManager'
import AISearcher from './components/AISearcher'
import './App.css'

function App() {
  const [currentPath, setCurrentPath] = useState('/')
  const [refreshKey, setRefreshKey] = useState(0)

  const handlePathChange = (path) => {
    setCurrentPath(path)
  }

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1)
  }

  const handleLogout = () => {
    console.log('User logged out')
  }

  return (
    <div className="app-container">
      <Header onLogout={handleLogout} />
      
      <div className="app-layout">
        <Sidebar onPathChange={handlePathChange} currentPath={currentPath} />
        
        <main className="main-content">
          <FileManager key={refreshKey} currentPath={currentPath} onRefresh={handleRefresh} />
          
          <footer className="ai-searcher-footer">
            <AISearcher currentPath={currentPath} />
          </footer>
        </main>
      </div>
    </div>
  )
}

export default App
