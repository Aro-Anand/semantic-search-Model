/**
 * Main Application Component
 * 
 * This is the root component of the Semantic Search application.
 * It provides a search interface with autocomplete functionality.
 * 
 * @module App
 */

import { useRef, useEffect, useState } from 'react';
import { Sparkles, PlusCircle, RefreshCw, Loader2 } from 'lucide-react';
import SearchBar from './components/SearchBar';
import ResultsList from './components/ResultsList';
import AddFranchiseModal from './components/AddFranchiseModal';
import ConfirmationModal from './components/ConfirmationModal';
import { useSearch } from './hooks/useSearch';
import { retrainModel } from './services/api';
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

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isRetraining, setIsRetraining] = useState(false);
    const [retrainStatus, setRetrainStatus] = useState(null); // { type: 'success' | 'error', message: string } | null
    const [showConfirm, setShowConfirm] = useState(false);

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

    /**
     * Handle Manual Retrain
     */
    const executeRetrain = async () => {
        setShowConfirm(false);
        setIsRetraining(true);
        setRetrainStatus(null);
        try {
            await retrainModel();
            setRetrainStatus({ type: 'success', message: 'Model retrained successfully!' });
            setTimeout(() => setRetrainStatus(null), 3000);
        } catch (err) {
            setRetrainStatus({ type: 'error', message: 'Retrain failed. (Cloud Run requires local training)' });
            setTimeout(() => setRetrainStatus(null), 5000);
        } finally {
            setIsRetraining(false);
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
            {/* Retrain Status Toast */}
            {retrainStatus && (
                <div style={{
                    position: 'fixed',
                    top: '20px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    zIndex: 2000,
                    padding: '0.75rem 1.5rem',
                    borderRadius: '50px',
                    background: retrainStatus.type === 'success' ? '#22c55e' : '#ef4444',
                    color: 'white',
                    fontWeight: 500,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    animation: 'fadeIn 0.3s ease'
                }}>
                    {retrainStatus.type === 'success' ? <Sparkles size={16} /> : <Loader2 size={16} />}
                    {retrainStatus.message}
                </div>
            )}

            {/* Header */}
            <div style={{ width: '100%', position: 'relative' }}>

                {/* Top Right Controls - Fixed */}
                <div style={{
                    display: 'flex',
                    gap: '0.75rem',
                    position: 'fixed',
                    top: '2rem',
                    right: '2rem',
                    zIndex: 100
                }}>
                    {/* Retrain Button */}
                    <button
                        onClick={() => setShowConfirm(true)}
                        disabled={isRetraining}
                        title="Retrain Model"
                        className="glass-btn secondary-action"
                    >
                        <RefreshCw size={18} className={isRetraining ? 'spin' : ''} />
                    </button>

                    {/* Add Button */}
                    <button
                        onClick={() => setIsModalOpen(true)}
                        className="glass-btn primary-action"
                    >
                        <PlusCircle size={18} />
                        <span style={{ fontWeight: 500 }}>Add Franchise</span>
                    </button>
                </div>

                {/* Centered Title */}
                <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    marginBottom: '1rem',
                    marginTop: '2rem' // Space for the top buttons if screen is small? No, absolute is taken out of flow.
                }}>
                    <h1 style={{
                        fontSize: '2.5rem',
                        fontWeight: '600',
                        margin: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '10px',
                        whiteSpace: 'nowrap'
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
                    <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                        Start typing to explore...
                    </p>
                </div>
            </div>

            {/* Custom Styles for Buttons */}
            <style>{`
                .glass-btn {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    padding: 0.6rem 1rem;
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    background: rgba(255, 255, 255, 0.05);
                    backdrop-filter: blur(8px);
                    color: var(--text-muted);
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-size: 0.9rem;
                    height: 40px;
                }
                
                .glass-btn:hover {
                    background: rgba(255, 255, 255, 0.1);
                    color: white;
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                }

                .glass-btn.primary-action {
                    background: linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(59, 130, 246, 0.2) 100%);
                    border: 1px solid rgba(139, 92, 246, 0.3);
                    color: white;
                }

                .glass-btn.primary-action:hover {
                    background: linear-gradient(135deg, rgba(139, 92, 246, 0.3) 0%, rgba(59, 130, 246, 0.3) 100%);
                    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.2);
                }

                .glass-btn.secondary-action {
                    padding: 0;
                    width: 40px;
                    justify-content: center;
                }
            `}</style>

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

            {/* Modal */}
            <AddFranchiseModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
            />

            <ConfirmationModal
                isOpen={showConfirm}
                onClose={() => setShowConfirm(false)}
                onConfirm={executeRetrain}
                title="Retrain Model?"
                message="This will update the search engine with all recent data. It typically takes few seconds."
            />

            {/* Animation Styles */}
            <style>{`
                    to { transform: rotate(360deg); } 
                }
            `}</style>
        </div>
    );
}
