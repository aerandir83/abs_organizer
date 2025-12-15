import { useState, useEffect } from 'react'
import { Book, RefreshCw, Check, X, Search, Settings } from 'lucide-react'
import QueueItem from './components/QueueItem'

const API_BASE = "/api"

export default function App() {
    const [items, setItems] = useState([])
    const [stats, setStats] = useState({})
    const [loading, setLoading] = useState(true)
    const [refreshing, setRefreshing] = useState(false)
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

    const fetchStatus = async () => {
        try {
            const res = await fetch(`${API_BASE}/status`)
            if (res.ok) {
                setStats(await res.json())
            }
        } catch (e) { }
    }

    const handleRefresh = async () => {
        setRefreshing(true)
        try {
            await fetch(`${API_BASE}/refresh`, { method: 'POST' })
            // Give it a moment to trigger scan
            setTimeout(() => {
                fetchStatus()
                setRefreshing(false)
            }, 1000)
        } catch (e) {
            console.error(e)
            setRefreshing(false)
        }
    }

    useEffect(() => {
        fetchQueue()
        fetchStatus()
        const interval = setInterval(() => {
            fetchQueue()
            fetchStatus()
        }, 5000)
        return () => clearInterval(interval)
    }, [])

    const pendingCount = (stats.tracked_files_count || 0) + (stats.grouping_files_count || 0)

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
                <div className="flex items-center gap-4">
                    {pendingCount > 0 && (
                        <div className="text-sm text-muted flex items-center gap-2 animate-pulse">
                            <RefreshCw size={14} className="spin" />
                            <span>Processing {pendingCount} new files...</span>
                        </div>
                    )}
                    <button className="btn btn-ghost" onClick={handleRefresh} disabled={refreshing}>
                        <RefreshCw size={18} className={refreshing ? "spin" : ""} />
                        {refreshing ? "Scanning..." : "Rescan Folder"}
                    </button>
                </div>
            </header>

            <main>
                <div className="flex justify-between items-end" style={{ marginBottom: '1rem' }}>
                    <h2 className="text-lg">Processing Queue ({items.length})</h2>
                    <div className="text-sm text-muted">
                        {stats.tracked_files_count > 0 && <span className="mr-4">Stabilizing: {stats.tracked_files_count}</span>}
                        {stats.groups_count > 0 && <span>Grouping: {stats.groups_count}</span>}
                    </div>
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
