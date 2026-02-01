/**
 * Custom Hook: useSearch
 * 
 * This hook manages search state and provides debounced autocomplete functionality.
 * It handles fetching suggestions from the API with automatic debouncing to reduce
 * unnecessary API calls.
 * 
 * @module hooks/useSearch
 */

import { useState, useEffect, useRef } from 'react';
import { fetchAutocomplete } from '../services/api';

/**
 * Custom hook for managing search functionality with debounced autocomplete.
 * 
 * @param {number} [debounceMs=300] - Debounce delay in milliseconds
 * @returns {Object} Search state and handlers
 * @returns {string} returns.query - Current search query
 * @returns {Function} returns.setQuery - Function to update query
 * @returns {Array} returns.results - Array of autocomplete results
 * @returns {boolean} returns.loading - Loading state
 * @returns {string|null} returns.error - Error message if any
 * @returns {boolean} returns.showResults - Whether to show results dropdown
 * @returns {Function} returns.setShowResults - Function to control results visibility
 * @returns {Function} returns.handleClear - Function to clear search
 * 
 * @example
 * function SearchComponent() {
 *   const { query, setQuery, results, loading, error } = useSearch();
 *   
 *   return (
 *     <input 
 *       value={query} 
 *       onChange={(e) => setQuery(e.target.value)}
 *       placeholder="Search..."
 *     />
 *   );
 * }
 */
export function useSearch(debounceMs = 300) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [showResults, setShowResults] = useState(false);

    useEffect(() => {
        // Don't search if query is too short
        if (query.length <= 2) {
            setResults([]);
            setShowResults(false);
            return;
        }

        // Debounce the API call
        const timeoutId = setTimeout(async () => {
            setLoading(true);
            setError(null);

            try {
                const data = await fetchAutocomplete(query);

                // Handle different response formats
                let parsedResults = [];
                if (Array.isArray(data)) {
                    parsedResults = data;
                } else if (data && Array.isArray(data.results)) {
                    parsedResults = data.results;
                } else if (data && Array.isArray(data.predictions)) {
                    parsedResults = data.predictions;
                } else if (data && Array.isArray(data.suggestions)) {
                    parsedResults = data.suggestions;
                } else if (data && typeof data === 'object') {
                    parsedResults = [data];
                }

                setResults(parsedResults);
                setShowResults(true);
            } catch (err) {
                console.error('Search error:', err);
                setError('Failed to fetch results');
                setResults([]);
            } finally {
                setLoading(false);
            }
        }, debounceMs);

        // Cleanup timeout on unmount or query change
        return () => clearTimeout(timeoutId);
    }, [query, debounceMs]);

    /**
     * Clear the search query and results.
     */
    const handleClear = () => {
        setQuery('');
        setResults([]);
        setShowResults(false);
        setError(null);
    };

    return {
        query,
        setQuery,
        results,
        loading,
        error,
        showResults,
        setShowResults,
        handleClear
    };
}
