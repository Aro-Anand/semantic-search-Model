import { useState } from 'react';
import { X, Plus, Loader2, RefreshCw } from 'lucide-react';
import { addListing, retrainModel } from '../../services/api';

export default function AddFranchiseModal({ isOpen, onClose }) {
    const [formData, setFormData] = useState({
        title: '',
        sector: '',
        description: '',
        investment_range: '',
        location: '',
        tags: ''
    });
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState(null); // 'success', 'error', 'retraining', 'retrained'
    const [message, setMessage] = useState('');

    if (!isOpen) return null;

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setStatus(null);
        setMessage('');

        try {
            // 1. Add Listing
            const tagsArray = formData.tags.split(',').map(t => t.trim()).filter(Boolean);
            const payload = { ...formData, tags: tagsArray };

            await addListing(payload);

            setStatus('success');
            setMessage('Listing added successfully! Please click "Retrain Model" to update search results.');

            // Reset form after success
            setTimeout(() => {
                onClose();
                setFormData({
                    title: '',
                    sector: '',
                    description: '',
                    investment_range: '',
                    location: '',
                    tags: ''
                });
                setStatus(null);
                setMessage('');
            }, 2000);

        } catch (err) {
            setStatus('error');
            setMessage(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(4px)'
        }}>
            <div className="glass-panel" style={{
                width: '90%',
                maxWidth: '500px',
                padding: '2rem',
                maxHeight: '90vh',
                overflowY: 'auto'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>Execute New Franchise</h2>
                    <button
                        onClick={onClose}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-primary)' }}
                    >
                        <X size={24} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

                    <div className="form-group">
                        <label>Franchise Title *</label>
                        <input
                            required
                            name="title"
                            value={formData.title}
                            onChange={handleChange}
                            placeholder="e.g. Burger King"
                            style={inputStyle}
                        />
                    </div>

                    <div className="form-group">
                        <label>Sector *</label>
                        <input
                            required
                            name="sector"
                            value={formData.sector}
                            onChange={handleChange}
                            placeholder="e.g. Food & Beverage"
                            style={inputStyle}
                        />
                    </div>

                    <div className="form-group">
                        <label>Description</label>
                        <textarea
                            name="description"
                            value={formData.description}
                            onChange={handleChange}
                            rows={3}
                            placeholder="Brief description..."
                            style={{ ...inputStyle, resize: 'vertical' }}
                        />
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div className="form-group">
                            <label>Investment Range</label>
                            <input
                                name="investment_range"
                                value={formData.investment_range}
                                onChange={handleChange}
                                placeholder="$10k - $50k"
                                style={inputStyle}
                            />
                        </div>
                        <div className="form-group">
                            <label>Location</label>
                            <input
                                name="location"
                                value={formData.location}
                                onChange={handleChange}
                                placeholder="City, Country"
                                style={inputStyle}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Tags (comma separated)</label>
                        <input
                            name="tags"
                            value={formData.tags}
                            onChange={handleChange}
                            placeholder="fast food, burgers, cheap"
                            style={inputStyle}
                        />
                    </div>

                    {message && (
                        <div style={{
                            padding: '0.75rem',
                            borderRadius: '8px',
                            fontSize: '0.9rem',
                            backgroundColor: status === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)',
                            color: status === 'error' ? '#ef4444' : '#22c55e',
                            border: `1px solid ${status === 'error' ? '#ef4444' : '#22c55e'}`
                        }}>
                            {message}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            marginTop: '1rem',
                            padding: '0.75rem',
                            borderRadius: '8px',
                            border: 'none',
                            background: 'linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)',
                            color: 'white',
                            fontWeight: 600,
                            cursor: loading ? 'not-allowed' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.5rem',
                            opacity: loading ? 0.7 : 1
                        }}
                    >
                        {loading ? (
                            <>
                                <Loader2 className="spin" size={20} />
                                Processing...
                            </>
                        ) : (
                            <>
                                <Plus size={20} />
                                Add Listing
                            </>
                        )}
                    </button>
                </form>
            </div>
            <style>{`
                .form-group {
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                }
                .form-group label {
                    font-size: 0.9rem;
                    color: var(--text-muted);
                    font-weight: 500;
                }
                .spin {
                    animation: spin 1s linear infinite;
                }
            `}</style>
        </div>
    );
}

const inputStyle = {
    padding: '0.75rem',
    borderRadius: '8px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    background: 'rgba(255, 255, 255, 0.05)',
    color: 'var(--text-primary)',
    fontSize: '1rem',
    outline: 'none',
    width: '100%'
};
