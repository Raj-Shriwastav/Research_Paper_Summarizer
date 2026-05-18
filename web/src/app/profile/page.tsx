'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@/lib/supabase/client';
import { User, Activity, Edit2, Save, Trash2, Camera } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function ProfilePage() {
  const supabase = createClient();
  const router = useRouter();
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [profile, setProfile] = useState<any>(null);
  const [stats, setStats] = useState({ digestsRead: 0, papersCovered: 0 });

  // Form state
  const [displayName, setDisplayName] = useState('');
  const [institution, setInstitution] = useState('');
  const [bio, setBio] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  // For research interests, we'll keep it simple as a comma-separated string for now, or just array
  const [interests, setInterests] = useState('');

  useEffect(() => {
    async function loadProfile() {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return router.push('/auth');

      // Fetch profile
      const { data } = await supabase.from('users').select('*').eq('id', user.id).single();
      if (data) {
        setProfile(data);
        setDisplayName(data.display_name || '');
        setInstitution(data.institution || '');
        setBio(data.bio || '');
        setAvatarUrl(data.avatar_url || '');
        setInterests((data.research_interests || []).join(', '));
      }

      // Fetch basic stats
      const { data: activity } = await supabase
        .from('user_activity')
        .select('action')
        .eq('user_id', user.id);
      
      const digestsRead = activity?.filter(a => a.action === 'view_digest').length || 0;

      // Also get total papers covered from preferences or similar, but for now just mock or use actual digests
      const { data: userDigests } = await supabase.from('digests').select('paper_count');
      const papersCovered = userDigests?.reduce((sum, d) => sum + (d.paper_count || 0), 0) || 0;

      setStats({ digestsRead, papersCovered });
      setLoading(false);
    }
    loadProfile();
  }, [supabase, router]);

  const handleSave = async () => {
    setSaving(true);
    const interestsArray = interests.split(',').map(i => i.trim()).filter(Boolean);
    
    const updates = {
      display_name: displayName,
      institution,
      bio,
      research_interests: interestsArray,
      avatar_url: avatarUrl
    };

    const res = await fetch('/api/profile', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });

    if (res.ok) {
      setProfile({ ...profile, ...updates });
      setIsEditing(false);
    } else {
      console.error('Failed to update profile');
    }
    setSaving(false);
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    // In a full implementation, this would upload to Supabase Storage
    // For now, we will prompt for a URL as a placeholder or allow base64 
    const file = e.target.files?.[0];
    if (file) {
      // Basic client side placeholder - in real prod, upload to bucket
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarUrl(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  if (loading) {
    return (
      <div className="p-8 max-w-4xl mx-auto flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  const memberSince = new Date(profile?.created_at).toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

  return (
    <div className="p-8 max-w-4xl mx-auto animate-fade-in pb-24">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Your Profile</h1>
          <p className="text-gray-400">Manage your identity and public details.</p>
        </div>
        {!isEditing ? (
          <button 
            onClick={() => setIsEditing(true)}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 text-white rounded-xl transition-colors border border-white/10"
          >
            <Edit2 className="w-4 h-4" /> Edit Profile
          </button>
        ) : (
          <button 
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2 bg-primary text-black font-semibold rounded-xl hover:scale-105 transition-transform"
          >
            {saving ? <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" /> : <Save className="w-4 h-4" />}
            Save Changes
          </button>
        )}
      </header>

      <div className="space-y-6">
        {/* Profile Identity Card */}
        <div className="glass-panel p-8 rounded-2xl border border-white/5 flex flex-col md:flex-row gap-8 items-start relative overflow-hidden">
          {/* Decorative background blob */}
          <div className="absolute -top-24 -right-24 w-48 h-48 bg-primary/10 rounded-full blur-3xl pointer-events-none"></div>
          
          <div className="relative group">
            <div className="w-24 h-24 rounded-full bg-white/5 border-2 border-white/10 flex items-center justify-center overflow-hidden shrink-0 bg-cover bg-center" style={avatarUrl ? { backgroundImage: `url(${avatarUrl})` } : {}}>
              {!avatarUrl && <User className="w-10 h-10 text-gray-500" />}
            </div>
            {isEditing && (
              <label className="absolute inset-0 flex items-center justify-center bg-black/60 rounded-full opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
                <Camera className="w-6 h-6 text-white" />
                <input type="file" accept="image/*" className="hidden" onChange={handleAvatarUpload} />
              </label>
            )}
          </div>

          <div className="flex-1 space-y-4">
            <div>
              {isEditing ? (
                <input 
                  type="text" 
                  value={displayName} 
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-white focus:outline-none focus:border-primary/50 text-xl font-bold"
                  placeholder="Your Name"
                />
              ) : (
                <h2 className="text-2xl font-bold text-white">{profile?.display_name || 'Anonymous User'}</h2>
              )}
              <p className="text-gray-400 mt-1">{profile?.email}</p>
            </div>
            <div className="inline-block px-3 py-1 bg-white/5 rounded-full text-xs text-gray-400 border border-white/5">
              Member since {memberSince}
            </div>
          </div>
        </div>

        {/* Detailed Info Card */}
        <div className="glass-panel p-8 rounded-2xl border border-white/5 space-y-6">
          <h3 className="text-lg font-semibold text-white mb-4">Professional Details</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm text-gray-400">Institution / Company</label>
              {isEditing ? (
                <input 
                  type="text" 
                  value={institution} 
                  onChange={(e) => setInstitution(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-primary/50"
                  placeholder="e.g. Stanford University"
                />
              ) : (
                <p className="text-white bg-white/5 px-4 py-3 rounded-xl border border-white/5 min-h-[50px]">{profile?.institution || 'Not specified'}</p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm text-gray-400">Research Interests</label>
              {isEditing ? (
                <input 
                  type="text" 
                  value={interests} 
                  onChange={(e) => setInterests(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-primary/50"
                  placeholder="e.g. AI, Quantum Computing, NLP"
                />
              ) : (
                <div className="flex flex-wrap gap-2 min-h-[50px]">
                  {profile?.research_interests?.length ? (
                    profile.research_interests.map((i: string) => (
                      <span key={i} className="px-3 py-1.5 bg-primary/10 text-primary border border-primary/20 rounded-full text-sm">
                        {i}
                      </span>
                    ))
                  ) : (
                    <span className="text-gray-500 italic">None specified</span>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm text-gray-400">Bio</label>
            {isEditing ? (
              <textarea 
                value={bio} 
                onChange={(e) => setBio(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-primary/50 min-h-[100px] resize-none"
                placeholder="A short bio about your research focus..."
              />
            ) : (
              <p className="text-white bg-white/5 px-4 py-3 rounded-xl border border-white/5 min-h-[100px] whitespace-pre-wrap">{profile?.bio || 'Not specified'}</p>
            )}
          </div>
        </div>

        {/* Activity Stats */}
        <div className="glass-panel p-8 rounded-2xl border border-white/5">
          <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary" /> Your Activity
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-black/30 p-4 rounded-xl border border-white/5 text-center">
              <div className="text-3xl font-bold text-white mb-1">{stats.digestsRead}</div>
              <div className="text-xs text-gray-400 uppercase tracking-wider">Digests Read</div>
            </div>
            <div className="bg-black/30 p-4 rounded-xl border border-white/5 text-center">
              <div className="text-3xl font-bold text-white mb-1">{stats.papersCovered}</div>
              <div className="text-xs text-gray-400 uppercase tracking-wider">Papers Covered</div>
            </div>
            <div className="bg-black/30 p-4 rounded-xl border border-white/5 text-center">
              <div className="text-3xl font-bold text-white mb-1">{profile?.login_count || 1}</div>
              <div className="text-xs text-gray-400 uppercase tracking-wider">Total Logins</div>
            </div>
            <div className="bg-black/30 p-4 rounded-xl border border-white/5 text-center">
              <div className="text-3xl font-bold text-white mb-1">{profile?.role === 'admin' ? 'Admin' : 'User'}</div>
              <div className="text-xs text-gray-400 uppercase tracking-wider">Account Tier</div>
            </div>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="glass-panel p-8 rounded-2xl border border-red-500/20 bg-red-500/5 mt-12">
          <h3 className="text-lg font-semibold text-red-400 mb-2 flex items-center gap-2">
            <Trash2 className="w-5 h-5" /> Danger Zone
          </h3>
          <p className="text-sm text-gray-400 mb-4">
            Permanently delete your account and all associated data. This action cannot be undone.
          </p>
          <button className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg text-sm font-medium transition-colors border border-red-500/20">
            Delete Account
          </button>
        </div>
      </div>
    </div>
  );
}
