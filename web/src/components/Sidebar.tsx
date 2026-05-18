'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BookOpen, LayoutDashboard, Settings, LogOut, History, User, Shield } from 'lucide-react';
import { createClient } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();
  const [userProfile, setUserProfile] = useState<{ display_name?: string, email?: string, avatar_url?: string, role?: string } | null>(null);

  useEffect(() => {
    async function loadUser() {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        const { data } = await supabase.from('users').select('display_name, email, avatar_url, role').eq('id', user.id).single();
        if (data) {
          setUserProfile(data);
        } else {
          setUserProfile({ email: user.email });
        }
      }
    }
    loadUser();
  }, [supabase]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push('/');
  };

  const navItems = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Past Digests', href: '/digests', icon: History },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  if (userProfile?.role === 'admin') {
    navItems.push({ name: 'Admin Panel', href: '/admin', icon: Shield });
  }

  return (
    <div className="w-64 border-r border-white/5 glass-panel hidden md:flex flex-col">
      <div className="h-16 flex items-center px-6 border-b border-white/5">
        <Link href="/" className="flex items-center gap-2 text-white">
          <BookOpen className="w-6 h-6 text-primary" />
          <span className="font-bold tracking-tight">Research<span className="text-primary">Summarizer</span></span>
        </Link>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                isActive 
                  ? 'bg-primary/10 text-primary border border-primary/20 shadow-[inset_0_0_10px_rgba(0,212,255,0.1)]' 
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <item.icon className={`w-5 h-5 ${isActive ? 'text-primary' : ''}`} />
              <span className="font-medium">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-white/5 space-y-2">
        <Link
          href="/profile"
          className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
            pathname.startsWith('/profile')
              ? 'bg-primary/10 text-primary border border-primary/20 shadow-[inset_0_0_10px_rgba(0,212,255,0.1)]'
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          {userProfile?.avatar_url ? (
            <img src={userProfile.avatar_url} alt="Profile" className="w-5 h-5 rounded-full object-cover" />
          ) : (
            <User className={`w-5 h-5 ${pathname.startsWith('/profile') ? 'text-primary' : ''}`} />
          )}
          <div className="flex flex-col flex-1 overflow-hidden">
            <span className="font-medium truncate text-sm">
              {userProfile?.display_name || 'Profile'}
            </span>
          </div>
        </Link>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 px-4 py-3 rounded-xl text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span className="font-medium">Sign Out</span>
        </button>
      </div>
    </div>
  );
}
