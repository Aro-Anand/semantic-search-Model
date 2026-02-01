/**
 * API Service Module
 * 
 * This module provides functions to interact with the Semantic Search API.
 * It handles all HTTP requests to the backend API endpoints.
 * 
 * @module services/api
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://search-api-model-559078627637.asia-south1.run.app/api';

/**
 * Fetch autocomplete suggestions based on a query.
 * 
 * @param {string} query - The search query string
 * @param {number} [maxSuggestions=8] - Maximum number of suggestions to return
 * @returns {Promise<Object>} Promise resolving to autocomplete response
 * @throws {Error} If the API request fails
 * 
 * @example
 * const suggestions = await fetchAutocomplete('coffee', 5);
 * console.log(suggestions.suggestions);
 */
export async function fetchAutocomplete(query, maxSuggestions = 8) {
    const url = `${API_BASE_URL}/autocomplete?q=${encodeURIComponent(query)}&max=${maxSuggestions}`;

    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`);
    }

    return await response.json();
}

/**
 * Perform a hybrid search query.
 * 
 * @param {string} query - The search query string
 * @param {Object} [options={}] - Search options
 * @param {number} [options.topN=10] - Number of results to return
 * @param {number} [options.semanticWeight=0.6] - Weight for semantic search (0-1)
 * @param {string} [options.sector] - Filter by sector
 * @param {string} [options.location] - Filter by location
 * @param {string[]} [options.tags] - Filter by tags
 * @returns {Promise<Object>} Promise resolving to search results
 * @throws {Error} If the API request fails
 * 
 * @example
 * const results = await searchListings('restaurant', { topN: 5, sector: 'Food & Beverage' });
 * console.log(results.results);
 */
export async function searchListings(query, options = {}) {
    const params = new URLSearchParams({
        q: query,
        ...(options.topN && { top_n: options.topN }),
        ...(options.semanticWeight && { semantic_weight: options.semanticWeight }),
        ...(options.sector && { sector: options.sector }),
        ...(options.location && { location: options.location }),
        ...(options.tags && { tags: options.tags.join(',') })
    });

    const url = `${API_BASE_URL}/search?${params}`;
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`);
    }

    return await response.json();
}

/**
 * Get recommendations for a specific listing.
 * 
 * @param {number} listingId - The ID of the listing
 * @param {Object} [options={}] - Recommendation options
 * @param {number} [options.topN=5] - Number of recommendations to return
 * @param {boolean} [options.sectorFilter=true] - Filter to same sector
 * @returns {Promise<Object>} Promise resolving to recommendations
 * @throws {Error} If the API request fails
 * 
 * @example
 * const recommendations = await getRecommendations(42, { topN: 5 });
 * console.log(recommendations.recommendations);
 */
export async function getRecommendations(listingId, options = {}) {
    const params = new URLSearchParams({
        ...(options.topN && { top_n: options.topN }),
        ...(options.sectorFilter !== undefined && { sector_filter: options.sectorFilter })
    });

    const url = `${API_BASE_URL}/recommend/${listingId}?${params}`;
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`);
    }

    return await response.json();
}

/**
 * Check API health status.
 * 
 * @returns {Promise<Object>} Promise resolving to health status
 * @throws {Error} If the API request fails
 * 
 * @example
 * const health = await checkHealth();
 * console.log(health.status);
 */
export async function checkHealth() {
    const url = `${API_BASE_URL}/health`;
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`);
    }

    return await response.json();
}

/**
 * Add a new franchise listing.
 * 
 * @param {Object} listing - The listing data
 * @returns {Promise<Object>} Promise resolving to the created listing
 */
export async function addListing(listing) {
    const url = `${API_BASE_URL}/add/listings`;
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(listing),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.message || `Failed to add listing: ${response.statusText}`);
    }

    return await response.json();
}

/**
 * Trigger model retraining.
 * 
 * @returns {Promise<Object>} Promise resolving to the retrain status
 */
export async function retrainModel() {
    // Note: This endpoint might fail on Cloud Run but works on EC2/Local
    const url = `${API_BASE_URL}/admin/retrain`;
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: '{}',
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.message || `Retrain failed: ${response.statusText}`);
    }

    return await response.json();
}

