import React, { useState, useRef, useEffect } from 'react';
import { FiSearch, FiLoader, FiX } from 'react-icons/fi';
import { searchAPI } from '../services/api';
import '../styles/AISearcher.css';

const AISearcher = ({ currentPath }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [error, setError] = useState(null);
  const searchRef = useRef(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await searchAPI.semanticSearch(query, currentPath);
      setResults(response.data.results || []);
      setIsExpanded(true);
    } catch (error) {
      console.error('Search error:', error);
      setError('Failed to search. Please try again.');
      // Mock results for UI testing
      setResults([
        {
          id: '1',
          name: 'Document about AI.pdf',
          path: '/documents/AI.pdf',
          relevance: 0.95,
          snippet: 'This document discusses artificial intelligence and machine learning...',
        },
        {
          id: '2',
          name: 'Project proposal.docx',
          path: '/documents/Project.docx',
          relevance: 0.87,
          snippet: 'Our AI-powered solution aims to revolutionize file management...',
        },
        {
          id: '3',
          name: 'Research notes.txt',
          path: '/research/notes.txt',
          relevance: 0.82,
          snippet: 'Key findings from our AI research...',
        },
      ]);
      setIsExpanded(true);
    } finally {
      setLoading(false);
    }
  };

  const handleResultClick = (result) => {
    // Open file or navigate to it
    console.log('Opening file:', result.path);
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    setIsExpanded(false);
    setError(null);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setIsExpanded(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="ai-searcher" ref={searchRef}>
      <div className="search-container">
        <form className="search-form" onSubmit={handleSearch}>
          <FiSearch className="search-icon" size={20} />
          <input
            type="text"
            placeholder="Search files by content, meaning, or AI analysis..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => isExpanded || setIsExpanded(false)}
            className="search-input"
          />
          {query && (
            <button type="button" className="clear-btn" onClick={handleClear}>
              <FiX size={18} />
            </button>
          )}
          {loading && <FiLoader className="loading-spinner" size={20} />}
        </form>

        {isExpanded && (
          <div className="search-results">
            {error && <div className="error-message">{error}</div>}

            {results.length === 0 && !loading && query && !error ? (
              <div className="no-results">
                <p>No files match your search.</p>
              </div>
            ) : (
              results.map((result) => (
                <div
                  key={result.id}
                  className="search-result-item"
                  onClick={() => handleResultClick(result)}
                >
                  <div className="result-header">
                    <h4 className="result-name">{result.name}</h4>
                    <span className="relevance-badge">{Math.round(result.relevance * 100)}% match</span>
                  </div>
                  <p className="result-path">{result.path}</p>
                  <p className="result-snippet">{result.snippet}</p>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AISearcher;
