/**
 * SearchBar Component
 * 
 * A search input component with autocomplete functionality.
 * Displays a search icon, loading spinner, and clear button.
 * 
 * @module components/SearchBar
 */

import { Search, Loader2, X } from 'lucide-react';
import PropTypes from 'prop-types';

/**
 * SearchBar component for user input with visual feedback.
 * 
 * @param {Object} props - Component props
 * @param {string} props.query - Current search query value
 * @param {Function} props.onQueryChange - Callback when query changes
 * @param {boolean} props.loading - Whether search is in progress
 * @param {Function} props.onClear - Callback to clear the search
 * @param {Function} props.onFocus - Callback when input is focused
 * @param {string} [props.placeholder='Search for anything...'] - Input placeholder text
 * 
 * @example
 * <SearchBar
 *   query={query}
 *   onQueryChange={setQuery}
 *   loading={loading}
 *   onClear={handleClear}
 *   onFocus={() => setShowResults(true)}
 * />
 */
export default function SearchBar({
    query,
    onQueryChange,
    loading,
    onClear,
    onFocus,
    placeholder = 'Search for anything...'
}) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', padding: '16px 20px' }}>
            <Search color="#94a3b8" size={20} style={{ marginRight: '12px' }} />
            <input
                type="text"
                onChange={(e) => onQueryChange(e.target.value)}
                value={query}
                placeholder={placeholder}
                onFocus={onFocus}
                autoFocus
                aria-label="Search input"
            />
            {loading && (
                <Loader2
                    className="animate-spin"
                    color="#8b5cf6"
                    size={20}
                    style={{ animation: 'spin 1s linear infinite' }}
                    aria-label="Loading"
                />
            )}
            {!loading && query && (
                <button
                    onClick={onClear}
                    style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center'
                    }}
                    aria-label="Clear search"
                >
                    <X color="#94a3b8" size={20} />
                </button>
            )}
        </div>
    );
}

SearchBar.propTypes = {
    query: PropTypes.string.isRequired,
    onQueryChange: PropTypes.func.isRequired,
    loading: PropTypes.bool.isRequired,
    onClear: PropTypes.func.isRequired,
    onFocus: PropTypes.func.isRequired,
    placeholder: PropTypes.string
};
