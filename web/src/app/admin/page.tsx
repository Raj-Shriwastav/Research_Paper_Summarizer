'use client';

import { useState, useEffect, useRef } from 'react';
import { createClient } from '@/lib/supabase/client';
import { Users, Send, Settings, Trash2, Edit2, Check, X, Shield, Activity, Search } from 'lucide-react';

type UserProfile = {
  id: string;
  email: string;
  delivery_email: string;
  display_name: string;
  role: string;
  created_at: string;
  login_count: number;
  user_preferences: {
    topics: string[];
    cadence: string[];
    email_enabled: boolean;
  }[];
};

export default function AdminDashboard() {
  const supabase = createClient();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [dispatching, setDispatching] = useState<string | null>(null);
  const [activeLogId, setActiveLogId] = useState<string | null>(null);
  const [message, setMessage] = useState<{type: 'success'|'error'|'info', text: string} | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [testEmail, setTestEmail] = useState('');
  const [pipelineLogs, setPipelineLogs] = useState<string>('');
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [pipelineLogs]);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const res = await fetch('/api/admin/users');
      if (!res.ok) throw new Error('Failed to fetch users');
      const data = await res.json();
      setUsers(data);
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!activeLogId) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/admin/dispatch/status?id=${activeLogId}`);
        if (!res.ok) return;
        const data = await res.json();
        
        if (data.status === 'success') {
          setMessage({ type: 'success', text: '✅ Generation complete! Mail has been sent to the target email.' });
          setDispatching(null);
          setActiveLogId(null);
        } else if (data.status === 'error' || data.status === 'partial_error') {
          setMessage({ type: 'error', text: `Failed: ${data.error_message || 'Unknown error'}` });
          setDispatching(null);
          setActiveLogId(null);
        } else {
          // Progress updates
          let progressText = 'Initializing pipeline and loading AI models...';
          if (data.status === 'fetching_papers') progressText = 'Fetching latest papers from arXiv...';
          else if (data.status === 'getting_summary') progressText = 'Extracting data and summarizing papers with AI...';
          else if (data.status === 'crafting_mail') progressText = 'Creating digest report and sending the mail...';
          
          setMessage({ type: 'info', text: `⏳ ${progressText}` });
        }

        // Fetch Logs
        try {
          const logsRes = await fetch(`/api/admin/dispatch/logs?id=${activeLogId}`);
          if (logsRes.ok) {
            const logsData = await logsRes.json();
            if (logsData.logs) {
              setPipelineLogs(logsData.logs);
            }
          }
        } catch (err) {
          console.error('Failed to fetch logs', err);
        }
      } catch (e) {
        console.error('Polling error', e);
      }
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
  }, [activeLogId]);

  const handleDispatch = async (cadence: string, targetType: 'test' | 'all') => {
    if (targetType === 'all' && !confirm(`Are you sure you want to trigger a ${cadence} dispatch to ALL subscribers?`)) return;
    
    let target = targetType === 'all' ? 'all' : testEmail;
    if (targetType === 'test' && !target) {
       setMessage({ type: 'error', text: 'Please enter a test email address.'});
       return;
    }
    
    setDispatching(`${cadence}-${targetType}`);
    setMessage(null);
    try {
      const res = await fetch('/api/admin/dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cadence, target }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Dispatch failed');
      
      setMessage({ type: 'info', text: `⏳ Background generation for ${cadence} started. Initializing...` });
      setPipelineLogs(''); // Clear previous logs
      if (data.log_id) {
        setActiveLogId(data.log_id);
      } else {
        // Fallback if log_id is missing
        setDispatching(null);
      }
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message });
      setDispatching(null);
    }
  };

  const deleteUser = async (id: string) => {
    if (!confirm('Are you sure you want to permanently delete this user?')) return;
    try {
      const res = await fetch(`/api/admin/users/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete user');
      setUsers(users.filter(u => u.id !== id));
      setMessage({ type: 'success', text: 'User deleted.' });
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message });
    }
  };

  const filteredUsers = users.filter(u => 
    u.email.toLowerCase().includes(searchQuery.toLowerCase()) || 
    (u.display_name && u.display_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const activeSubscribers = users.filter(u => u.user_preferences?.[0]?.email_enabled).length;

  if (loading) return <div className="p-8 flex justify-center"><div className="animate-spin w-8 h-8 border-b-2 border-primary rounded-full"></div></div>;

  return (
    <div className="p-8 max-w-7xl mx-auto animate-fade-in pb-24">
      <header className="mb-10">
        <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
          <Shield className="w-8 h-8 text-primary" /> Admin Portal
        </h1>
        <p className="text-gray-400">Manage users and trigger system dispatches.</p>
      </header>

      {message && (
        <div className={`mb-8 p-4 rounded-xl border ${message.type === 'success' ? 'bg-green-500/10 border-green-500/20 text-green-400' : message.type === 'info' ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' : 'bg-red-500/10 border-red-500/20 text-red-400'}`}>
          {message.text}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-12">
        <div className="glass-panel p-6 rounded-2xl border border-white/5">
          <div className="text-3xl font-bold text-white mb-1">{users.length}</div>
          <div className="text-sm text-gray-400 flex items-center gap-2"><Users className="w-4 h-4" /> Total Users</div>
        </div>
        <div className="glass-panel p-6 rounded-2xl border border-white/5">
          <div className="text-3xl font-bold text-white mb-1">{activeSubscribers}</div>
          <div className="text-sm text-gray-400 flex items-center gap-2"><Check className="w-4 h-4" /> Active Subscribers</div>
        </div>
        <div className="glass-panel p-6 rounded-2xl border border-white/5">
          <div className="text-3xl font-bold text-white mb-1">{users.reduce((acc, u) => acc + (u.login_count || 0), 0)}</div>
          <div className="text-sm text-gray-400 flex items-center gap-2"><Activity className="w-4 h-4" /> Total Logins</div>
        </div>
      </div>

      {/* Manual Dispatch Controls */}
      <section className="mb-12">
        <h2 className="text-xl font-bold text-white mb-6">Manual Dispatch Controls</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {['daily', 'weekly', 'monthly'].map((cad) => (
            <div key={cad} className="glass-panel p-6 rounded-2xl border border-white/5 flex flex-col">
              <h3 className="text-lg font-semibold text-white capitalize mb-4">{cad} Pipeline</h3>
              <div className="mt-auto space-y-3">
                <div className="flex gap-2">
                  <input
                    type="email"
                    placeholder="Enter test email..."
                    value={testEmail}
                    onChange={(e) => setTestEmail(e.target.value)}
                    className="flex-1 bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-primary/50"
                  />
                  <button 
                    onClick={() => handleDispatch(cad, 'test')}
                    disabled={dispatching !== null}
                    className="px-4 py-2 bg-white/5 hover:bg-white/10 text-white rounded-xl text-sm font-medium transition-colors border border-white/10 disabled:opacity-50 flex justify-center items-center gap-2"
                  >
                    {dispatching === `${cad}-test` ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/> : <Send className="w-4 h-4" />}
                    Test
                  </button>
                </div>
                <button 
                  onClick={() => handleDispatch(cad, 'all')}
                  disabled={dispatching !== null}
                  className="w-full py-2 bg-primary/10 hover:bg-primary/20 text-primary rounded-xl text-sm font-medium transition-colors border border-primary/20 disabled:opacity-50 flex justify-center items-center gap-2"
                >
                  {dispatching === `${cad}-all` ? <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin"/> : <Send className="w-4 h-4" />}
                  Dispatch to All
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* User Roster */}
      <section className="mb-12">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">User Roster</h2>
          <div className="relative w-64">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input 
              type="text" 
              placeholder="Search users..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-black/40 border border-white/10 rounded-xl py-2 pl-10 pr-4 text-sm text-white focus:outline-none focus:border-primary/50"
            />
          </div>
        </div>

        <div className="glass-panel rounded-2xl border border-white/5 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-black/40 border-b border-white/5 text-gray-400">
                <tr>
                  <th className="px-6 py-4 font-medium">User</th>
                  <th className="px-6 py-4 font-medium">Delivery Email</th>
                  <th className="px-6 py-4 font-medium">Cadence</th>
                  <th className="px-6 py-4 font-medium">Role</th>
                  <th className="px-6 py-4 font-medium">Joined</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-gray-300">
                {filteredUsers.map((user) => {
                  const prefs = user.user_preferences?.[0] || { cadence: [], email_enabled: false };
                  return (
                    <tr key={user.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-medium text-white">{user.display_name || 'Anonymous'}</div>
                        <div className="text-xs text-gray-500">{user.email}</div>
                      </td>
                      <td className="px-6 py-4">{user.delivery_email || user.email}</td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1">
                          {prefs.cadence?.map(c => (
                            <span key={c} className="px-2 py-0.5 bg-white/5 border border-white/10 rounded text-[10px] uppercase tracking-wider">{c}</span>
                          ))}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${user.role === 'admin' ? 'bg-primary/20 text-primary' : 'bg-white/10 text-gray-300'}`}>
                          {user.role}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-500">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button onClick={() => deleteUser(user.id)} className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
                {filteredUsers.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-gray-500">No users found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Terminal / Logs Viewer */}
      {(activeLogId || pipelineLogs) && (
        <section className="animate-fade-in">
          <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary" /> Live Background Pipeline Logs
          </h2>
          <div className="bg-[#0D1117] border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
            <div className="flex items-center px-4 py-2 bg-white/[0.03] border-b border-white/5 gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
              <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
              <span className="ml-2 text-xs text-gray-500 font-mono">system@research-summarizer:~$</span>
            </div>
            <div className="p-4 h-80 overflow-y-auto font-mono text-xs sm:text-sm text-gray-300 leading-relaxed custom-scrollbar">
              <pre className="whitespace-pre-wrap">{pipelineLogs || 'Initializing logs...'}</pre>
              <div ref={logsEndRef} />
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
