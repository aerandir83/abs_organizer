import { useState } from 'react'
import { Check, X, Search, Edit2, Play, Save, ChevronDown, ChevronUp } from 'lucide-react'

const API_BASE = "http://localhost:8000/api"

export default function QueueItem({ item, onUpdate }) {
    const [expanded, setExpanded] = useState(false)
    const [editing, setEditing] = useState(false)
    const [searching, setSearching] = useState(false)
    const [loading, setLoading] = useState(false)
    const [searchResults, setSearchResults] = useState([])
    const [formData, setFormData] = useState(item.metadata || {})

    const [showConfirm, setShowConfirm] = useState(false)
    const [previewPath, setPreviewPath] = useState("")

    const handleProcessClick = async () => {
        setLoading(true)
        try {
            const res = await fetch(`${API_BASE}/queue/${item.id}/preview`)
            if (res.ok) {
                const data = await res.json()
                setPreviewPath(data.destination)
                setShowConfirm(true)
            }
        } catch (e) { console.error(e) }
        setLoading(false)
    }

    const confirmProcess = async () => {
        setShowConfirm(false)
        setLoading(true)
        await fetch(`${API_BASE}/queue/${item.id}/process`, { method: 'POST' })
        setLoading(false)
        onUpdate()
    }

    const handleRemove = async () => {
        if (!confirm("Are you sure you want to remove this item?")) return
        await fetch(`${API_BASE}/queue/${item.id}`, { method: 'DELETE' })
        onUpdate()
    }

    const [hasSearched, setHasSearched] = useState(false)

    const handleSearch = async () => {
        setSearching(true)
        setHasSearched(false)
        // Handle both forward and back slashes for path splitting
        const pathParts = item.dirpath.split(/[/\\]/)
        let folderName = pathParts.pop()
        if (!folderName && pathParts.length > 0) folderName = pathParts.pop() // Handle trailing slash

        const q = formData.title || folderName || ""
        try {
            const res = await fetch(`${API_BASE}/queue/${item.id}/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: q,
                    author: formData.author,
                    audible_id: formData.asin
                })
            })
            const data = await res.json()
            setSearchResults(data)
            setHasSearched(true)
        } catch (e) { console.error(e) }
        setSearching(false)
    }

    const applyMatch = async (match) => {
        const updates = {
            title: match.title,
            author: match.author,
            year: match.year,
            isbn: match.isbn,
            asin: match.asin,
            description: match.description,
            cover_url: match.cover_url
        }
        setFormData({ ...formData, ...updates })
        await saveUpdates(updates)
        setSearchResults([])
    }

    const saveUpdates = async (data = formData) => {
        await fetch(`${API_BASE}/queue/${item.id}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        if (onUpdate) onUpdate()
        setEditing(false)
    }

    const confidenceColor = (score) => {
        if (score >= 90) return 'text-green-400';
        if (score >= 70) return 'text-yellow-400';
        return 'text-red-400';
    }

    return (
        <div className="card animate-fade-in" style={{ opacity: loading ? 0.5 : 1, position: 'relative' }}>
            {showConfirm && (
                <div style={{
                    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(0,0,0,0.85)', zIndex: 10, borderRadius: 'inherit',
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    padding: '1rem', textAlign: 'center'
                }}>
                    <h3 className="text-lg font-bold mb-2">Confirm Processing</h3>
                    <p className="text-sm text-muted mb-4">The files will be moved to:</p>
                    <div className="code-block text-xs mb-4" style={{ background: '#1e293b', padding: '0.5rem', borderRadius: 4, width: '100%', wordBreak: 'break-all' }}>
                        {previewPath}
                    </div>
                    <div className="flex gap-2">
                        <button className="btn btn-ghost" onClick={() => setShowConfirm(false)}>Cancel</button>
                        <button className="btn btn-primary" onClick={confirmProcess}><Check size={16} /> Confirm & Process</button>
                    </div>
                </div>
            )}

            <div className="flex justify-between items-center">
                <div className="flex items-center gap-4" style={{ flex: 1 }}>
                    <div style={{ width: 50, height: 75, backgroundColor: '#334155', borderRadius: 4, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                        {formData.cover_url ? <img src={formData.cover_url} alt="Cover" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <span className="text-xs text-muted">No Cover</span>}
                    </div>

                    <div>
                        <h3 className="text-lg font-bold">{formData.title || "Unknown Title"}</h3>
                        <p className="text-muted">{formData.author || "Unknown Author"} {formData.year && `(${formData.year})`}</p>
                        <div className="flex items-center gap-2" style={{ marginTop: '0.25rem' }}>
                            <span className={`badge ${item.status === 'processing' ? 'badge-yellow' : 'badge-blue'}`}>{item.status}</span>
                            <span className={`text-xs ${confidenceColor(formData.confidence)}`}>
                                Confidence: {Math.round(formData.confidence || 0)}%
                            </span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <button className="btn btn-primary" onClick={handleProcessClick} title="Start Processing" disabled={loading}>
                        <Play size={18} />
                    </button>
                    <button className="btn btn-ghost" onClick={() => setExpanded(!expanded)}>
                        {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                    </button>
                </div>
            </div>

            {expanded && (
                <div style={{ marginTop: '1rem', borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                    <div className="flex gap-2" style={{ marginBottom: '1rem' }}>
                        <button className="btn btn-ghost" onClick={() => setEditing(!editing)}>
                            <Edit2 size={16} /> {editing ? 'Cancel Edit' : 'Edit Metadata'}
                        </button>
                        <button className="btn btn-ghost" onClick={handleSearch} disabled={searching}>
                            {searching ? <div className="loader">...</div> : <Search size={16} />} Search Match
                        </button>
                        <div style={{ flex: 1 }}></div>
                        <button className="btn btn-ghost text-red-400" onClick={handleRemove}>
                            <X size={16} /> Ignore
                        </button>
                    </div>

                    {searchResults.length > 0 && (
                        <div style={{ marginBottom: '1rem', background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '0.5rem' }}>
                            <div className="flex justify-between items-center" style={{ marginBottom: '0.5rem' }}>
                                <h4 className="text-sm font-bold text-muted">Search Results</h4>
                                <button className="btn btn-xs btn-ghost" onClick={() => setSearchResults([])}><X size={14} /></button>
                            </div>
                            <div className="flex flex-col gap-2">
                                {searchResults.map((res, i) => (
                                    <div key={i} className="flex justify-between items-center" style={{ padding: '0.5rem', background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: '0.5rem' }}>
                                        <div className="flex gap-2">
                                            {res.cover_url && <img src={res.cover_url} style={{ width: 30, height: 45, objectFit: 'cover' }} />}
                                            <div>
                                                <div className="font-bold text-sm">{res.title}</div>
                                                <div className="text-xs text-muted">by {res.author} ({res.year})</div>
                                            </div>
                                        </div>
                                        <button className="btn btn-sm btn-ghost" onClick={() => applyMatch(res)}>Apply</button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {hasSearched && searchResults.length === 0 && (
                        <div className="text-sm text-center p-2 text-muted animate-fade-in" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '0.5rem', marginBottom: '1rem' }}>
                            No matches found. Try editing the title or author manually to improve search results.
                        </div>
                    )}

                    {editing ? (
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs text-muted">Title</label>
                                <input className="input" value={formData.title || ''} onChange={e => setFormData({ ...formData, title: e.target.value })} />
                            </div>
                            <div>
                                <label className="text-xs text-muted">Author</label>
                                <input className="input" value={formData.author || ''} onChange={e => setFormData({ ...formData, author: e.target.value })} />
                            </div>
                            <div>
                                <label className="text-xs text-muted">Year</label>
                                <input className="input" value={formData.year || ''} onChange={e => setFormData({ ...formData, year: e.target.value })} />
                            </div>
                            <div>
                                <label className="text-xs text-muted">Series</label>
                                <input className="input" value={formData.series || ''} onChange={e => setFormData({ ...formData, series: e.target.value })} />
                            </div>
                            <div>
                                <label className="text-xs text-muted">ISBN</label>
                                <input className="input" value={formData.isbn || ''} onChange={e => setFormData({ ...formData, isbn: e.target.value })} />
                            </div>
                            <div>
                                <label className="text-xs text-muted">Audible ID (ASIN)</label>
                                <input className="input" value={formData.asin || ''} onChange={e => setFormData({ ...formData, asin: e.target.value })} placeholder="B0..." />
                            </div>
                            <div style={{ gridColumn: 'span 2' }}>
                                <label className="text-xs text-muted">Description</label>
                                <textarea className="input" rows={3} value={formData.description || ''} onChange={e => setFormData({ ...formData, description: e.target.value })} />
                            </div>
                            <div style={{ gridColumn: 'span 2' }}>
                                <button className="btn btn-primary w-full" onClick={() => saveUpdates()}>Save Changes</button>
                            </div>
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div style={{ gridColumn: 'span 2' }}><span className="text-muted">Path:</span> <br /><span className="text-xs" style={{ wordBreak: 'break-all', fontFamily: 'monospace' }}>{item.dirpath}</span></div>
                            <div><span className="text-muted">ISBN:</span> {formData.isbn || '-'}</div>
                            <div><span className="text-muted">ASIN:</span> {formData.asin || '-'}</div>
                            <div><span className="text-muted">Source:</span> {formData.source || 'Unknown'}</div>
                            {formData.description && (
                                <div style={{ gridColumn: 'span 2', maxHeight: '100px', overflowY: 'auto' }}><span className="text-muted">Description:</span> <br />{formData.description}</div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
