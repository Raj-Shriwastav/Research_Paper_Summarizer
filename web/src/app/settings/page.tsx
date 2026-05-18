'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@/lib/supabase/client';
import { Save, Loader2, Plus, X } from 'lucide-react';

export default function SettingsPage() {
  const supabase = createClient();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const [preferences, setPreferences] = useState({
    topics: ['Artificial Intelligence'],
    cadence: ['daily'],
    max_papers_per_digest: 2,
    email_enabled: true,
  });

  const [newTopic, setNewTopic] = useState('');

  useEffect(() => {
    async function loadPreferences() {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const { data, error } = await supabase
        .from('user_preferences')
        .select('*')
        .eq('user_id', user.id)
        .single();

      if (data) {
        setPreferences({
          topics: data.topics || ['Artificial Intelligence'],
          cadence: data.cadence || ['daily'],
          max_papers_per_digest: data.max_papers_per_digest || 2,
          email_enabled: data.email_enabled ?? true,
        });
      } else {
        // Ensure user & preferences exist via server-side API (bypasses RLS)
        await fetch('/api/profile/ensure', { method: 'POST' });

        // Re-fetch preferences after creation
        const { data: newData } = await supabase
          .from('user_preferences')
          .select('*')
          .eq('user_id', user.id)
          .single();

        if (newData) {
          setPreferences({
            topics: newData.topics || ['Artificial Intelligence'],
            cadence: newData.cadence || ['daily'],
            max_papers_per_digest: newData.max_papers_per_digest || 2,
            email_enabled: newData.email_enabled ?? true,
          });
        }
      }
      setLoading(false);
    }
    loadPreferences();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) throw new Error('Not authenticated');

      const { error } = await supabase
        .from('user_preferences')
        .upsert({
          user_id: user.id,
          ...preferences,
          updated_at: new Date().toISOString(),
        }, { onConflict: 'user_id' });

      if (error) throw error;
      setMessage({ type: 'success', text: 'Preferences saved successfully.' });
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to save preferences.' });
    } finally {
      setSaving(false);
    }
  };

  const addTopic = () => {
    if (newTopic.trim() && !preferences.topics.includes(newTopic.trim())) {
      setPreferences({
        ...preferences,
        topics: [...preferences.topics, newTopic.trim()],
      });
      setNewTopic('');
    }
  };

  const removeTopic = (topicToRemove: string) => {
    setPreferences({
      ...preferences,
      topics: preferences.topics.filter(t => t !== topicToRemove),
    });
  };

  const toggleCadence = (cad: string) => {
    setPreferences(prev => {
      if (prev.cadence.includes(cad)) {
        return { ...prev, cadence: prev.cadence.filter(c => c !== cad) };
      } else {
        return { ...prev, cadence: [...prev.cadence, cad] };
      }
    });
  };

  if (loading) {
    return <div className="flex h-full items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="p-8 max-w-4xl mx-auto animate-fade-in">
      <header className="mb-10">
        <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
        <p className="text-gray-400">Manage your research digest preferences.</p>
      </header>

      {message && (
        <div className={`mb-6 p-4 rounded-xl border ${message.type === 'success' ? 'bg-green-500/10 border-green-500/20 text-green-400' : 'bg-red-500/10 border-red-500/20 text-red-400'}`}>
          {message.text}
        </div>
      )}

      <div className="space-y-6">
        {/* Topics Section */}
        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-white/5">
          <h2 className="text-xl font-semibold text-white mb-4">Research Topics</h2>
          <p className="text-sm text-gray-400 mb-6">What subjects do you want the pipeline to summarize?</p>

          <div className="flex flex-wrap gap-3 mb-6">
            {preferences.topics.map(topic => (
              <div key={topic} className="flex items-center gap-2 bg-primary/10 border border-primary/20 text-primary px-4 py-2 rounded-full text-sm font-medium">
                {topic}
                <button onClick={() => removeTopic(topic)} className="hover:text-white transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          <div className="flex gap-3">
            <input
              type="text"
              value={newTopic}
              onChange={(e) => setNewTopic(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addTopic()}
              placeholder="e.g. Quantum Computing, AI Safety..."
              className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <button
              onClick={addTopic}
              className="bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-xl transition-colors flex items-center gap-2 font-medium"
            >
              <Plus className="w-4 h-4" /> Add Topic
            </button>
          </div>
        </div>

        {/* Email Preferences */}
        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-white/5">
          <h2 className="text-xl font-semibold text-white mb-4">Email Delivery</h2>

          <div className="flex items-center justify-between mb-8 pb-8 border-b border-white/10">
            <div>
              <p className="font-medium text-white mb-1">Receive Emails</p>
              <p className="text-sm text-gray-400">Toggle whether you want to receive HTML email digests.</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" checked={preferences.email_enabled} onChange={(e) => setPreferences({ ...preferences, email_enabled: e.target.checked })} />
              <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
            </label>
          </div>

          <div>
            <p className="font-medium text-white mb-4">Delivery Frequency</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {['daily', 'weekly', 'monthly'].map((cad) => (
                <label key={cad} className={`flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-colors ${preferences.cadence.includes(cad) ? 'bg-primary/10 border-primary/30' : 'bg-black/20 border-white/5 hover:border-white/10'}`}>
                  <input
                    type="checkbox"
                    className="w-4 h-4 text-primary bg-black/50 border-white/20 rounded focus:ring-primary focus:ring-offset-black"
                    checked={preferences.cadence.includes(cad)}
                    onChange={() => toggleCadence(cad)}
                  />
                  <span className="capitalize text-white font-medium">{cad}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-primary hover:bg-primary-hover text-black font-semibold px-8 py-3 rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(0,212,255,0.2)]"
          >
            {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Save className="w-5 h-5" /> Save Preferences</>}
          </button>
        </div>
      </div>
    </div>
  );
}
