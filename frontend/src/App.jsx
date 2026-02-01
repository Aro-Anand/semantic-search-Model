/**
 * Main Application Component
 * 
 * This is the root component of the Semantic Search application.
 * It provides a search interface with autocomplete functionality.
 * 
 * @module App
 */

import { useRef, useEffect } from 'react';
import { Sparkles } from 'lucide-react';
import SearchBar from './components/SearchBar';
import ResultsList from './components/ResultsList';
import { useSearch } from './hooks/useSearch';
import './index.css';

/**
 * Main App component providing the search interface.
 * 
 * Features:
 * - Real-time autocomplete search
 * - Debounced API calls
 * - Click-outside detection to close results
 * - Responsive design with glassmorphism effects
 * 
 * @returns {JSX.Element} The rendered application
 * 
 * @example
 * import App from './App';
 * 
 * function Root() {
 *   return <App />;
 * }
 */
export default function App() {
    const {
        query,
        setQuery,
        results,
        loading,
        error,
        showResults,
        setShowResults,
        handleClear
    } = useSearch();

    const wrapperRef = useRef(null);

    /**
     * Handle clicks outside the search wrapper to close results.
     */
    useEffect(() => {
        function handleClickOutside(event) {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
                setShowResults(false);
            }
        }

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [setShowResults]);

    /**
     * Handle query changes and show results if query is long enough.
     * 
     * @param {string} value - New query value
     */
    const handleQueryChange = (value) => {
        setQuery(value);
        if (value.length > 2) {
            setShowResults(true);
        }
    };

    /**
     * Handle input focus to show existing results.
     */
    const handleFocus = () => {
        if (results.length > 0) {
            setShowResults(true);
        }
    };

    return (
        <div style={{
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '2rem'
        }}>
            {/* Header */}
            <div style={{ textAlign: 'center' }}>
                <h1 style={{
                    fontSize: '2.5rem',
                    fontWeight: '600',
                    marginBottom: '0.5rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '10px'
                }}>
                    <Sparkles className="text-primary" size={32} color="#8b5cf6" />
                    <span style={{
                        background: 'linear-gradient(to right, #fff, #94a3b8)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent'
                    }}>
                        Semantic Search
                    </span>
                </h1>
                <p style={{ color: 'var(--text-muted)' }}>
                    Start typing to explore...
                </p>
            </div>

            {/* Search Container */}
            <div
                className="glass-panel"
                style={{ width: '100%', position: 'relative', padding: '0' }}
                ref={wrapperRef}
            >
                <SearchBar
                    query={query}
                    onQueryChange={handleQueryChange}
                    loading={loading}
                    onClear={handleClear}
                    onFocus={handleFocus}
                />

                <ResultsList
                    results={results}
                    error={error}
                    query={query}
                    loading={loading}
                    showResults={showResults}
                />
            </div>

            {/* Animation Styles */}
            <style>{`
                @keyframes spin { 
                    from { transform: rotate(0deg); } 
                    to { transform: rotate(360deg); } 
                }
            `}</style>
        </div>
    );
}
