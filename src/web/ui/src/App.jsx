import { useState, useEffect } from 'react'
import { Book, RefreshCw, Check, X, Search, Settings } from 'lucide-react'
import QueueItem from './components/QueueItem'

const API_BASE = "http://localhost:8000/api"

export default function App() {
    const [items, setItems] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const fetchQueue = async () => {
        try {
            const res = await fetch(`${API_BASE}/queue`)
            if (!res.ok) throw new Error("Failed to connect to API")
            const data = await res.json()
            // Sort items: processing first, then ID desc
            const sorted = data.sort((a, b) => {
                if (a.status === 'processing' && b.status !== 'processing') return -1;
                if (b.status === 'processing' && a.status !== 'processing') return 1;
                return b.id.localeCompare(a.id);
            })
            setItems(sorted)
            setLoading(false)
            setError(null)
        } catch (e) {
            console.error(e)
            setError("Could not connect to AutoLibrarian API. Is it running?")
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchQueue()
        const interval = setInterval(fetchQueue, 5000)
        return () => clearInterval(interval)
    }, [])

    return (
        <div className="container">
            <header className="flex justify-between items-center" style={{ marginBottom: '2rem' }}>
                <div className="flex items-center gap-2">
                    <div style={{ background: 'linear-gradient(135deg, #0ea5e9 0%, #3b82f6 100%)', padding: '0.5rem', borderRadius: '0.5rem' }}>
                        <Book color="white" size={24} />
                    </div>
                    <div>
                        <h1 className="text-xl" style={{ margin: 0 }}>MagLibrarian</h1>
                        <span className="text-sm text-muted">Auto-Organizer Dashboard</span>
                    </div>
                </div>
                <button className="btn btn-ghost" onClick={fetchQueue}>
                    <RefreshCw size={18} /> Refresh
                </button>
            </header>

            <main>
                <div className="flex justify-between items-end" style={{ marginBottom: '1rem' }}>
                    <h2 className="text-lg">Processing Queue ({items.length})</h2>
                </div>

                {error && (
                    <div className="card text-red-400" style={{ border: '1px solid var(--danger)', marginBottom: '1rem' }}>
                        {error}
                    </div>
                )}

                {loading ? (
                    <div className="text-muted text-center" style={{ padding: '2rem' }}>Loading...</div>
                ) : items.length === 0 ? (
                    <div className="card text-center" style={{ padding: '3rem' }}>
                        <div style={{ background: 'rgba(255,255,255,0.05)', display: 'inline-flex', padding: '1rem', borderRadius: '50%', marginBottom: '1rem' }}>
                            <Check size={32} color="var(--success)" />
                        </div>
                        <p className="text-muted">All caught up! No items pending review.</p>
                        <p className="text-xs text-muted" style={{ marginTop: '0.5rem' }}>
                            Any new books detected will appear here.
                        </p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-4">
                        {items.map(item => (
                            <QueueItem key={item.id} item={item} onUpdate={fetchQueue} />
                        ))}
                    </div>
                )}
            </main>
        </div>
    )
}
