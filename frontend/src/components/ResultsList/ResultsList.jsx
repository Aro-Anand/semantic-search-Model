/**
 * ResultsList Component
 * 
 * Displays a list of search results or autocomplete suggestions.
 * Handles different result formats and displays appropriate messages
 * for error states and empty results.
 * 
 * @module components/ResultsList
 */

import PropTypes from 'prop-types';

/**
 * ResultItem component for rendering a single result.
 * 
 * @param {Object} props - Component props
 * @param {Object|string} props.item - The result item to display
 * @param {number} props.index - Index of the item in the list
 * @returns {JSX.Element} Rendered result item
 */
function ResultItem({ item, index }) {
    return (
        <div
            key={index}
            className="result-item"
            style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}
        >
            {/* Handle string results */}
            {typeof item === 'string' && <span>{item}</span>}

            {/* Handle object results with 'text' property */}
            {typeof item === 'object' && item.text && (
                <>
                    <span style={{ color: 'var(--text)' }}>{item.text}</span>
                    {item.category && (
                        <span style={{
                            fontSize: '0.75rem',
                            padding: '2px 8px',
                            borderRadius: '12px',
                            backgroundColor: 'rgba(139, 92, 246, 0.2)',
                            color: '#a78bfa',
                            width: 'fit-content'
                        }}>
                            {item.category}
                        </span>
                    )}
                </>
            )}

            {/* Fallback for other object shapes */}
            {typeof item === 'object' && !item.text && (
                <span>
                    {item.name || item.title || item.description || JSON.stringify(item)}
                </span>
            )}
        </div>
    );
}

ResultItem.propTypes = {
    item: PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.object
    ]).isRequired,
    index: PropTypes.number.isRequired
};

/**
 * ResultsList component for displaying search results.
 * 
 * @param {Object} props - Component props
 * @param {Array} props.results - Array of result items
 * @param {string|null} props.error - Error message if any
 * @param {string} props.query - Current search query
 * @param {boolean} props.loading - Whether results are loading
 * @param {boolean} props.showResults - Whether to show the results dropdown
 * 
 * @example
 * <ResultsList
 *   results={results}
 *   error={error}
 *   query={query}
 *   loading={loading}
 *   showResults={showResults}
 * />
 */
export default function ResultsList({ results, error, query, loading, showResults }) {
    if (!showResults) {
        return null;
    }

    const hasBorder = results.length > 0 || error;

    return (
        <div style={{
            borderTop: hasBorder ? '1px solid var(--border)' : 'none',
            maxHeight: '300px',
            overflowY: 'auto'
        }}>
            {error ? (
                <div style={{
                    padding: '16px',
                    color: '#ef4444',
                    textAlign: 'center'
                }}>
                    {error}
                </div>
            ) : results.length > 0 ? (
                results.map((item, index) => (
                    <ResultItem key={index} item={item} index={index} />
                ))
            ) : query.length > 2 && !loading ? (
                <div style={{
                    padding: '16px',
                    color: 'var(--text-muted)',
                    textAlign: 'center'
                }}>
                    No results found
                </div>
            ) : null}
        </div>
    );
}

ResultsList.propTypes = {
    results: PropTypes.array.isRequired,
    error: PropTypes.string,
    query: PropTypes.string.isRequired,
    loading: PropTypes.bool.isRequired,
    showResults: PropTypes.bool.isRequired
};
