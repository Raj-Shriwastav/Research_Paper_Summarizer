'use client';

import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { BookOpen, Mail, ArrowRight, Loader2, UserIcon, Lock, Eye, EyeOff } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function AuthPage() {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const supabase = createClient();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    // Gmail-only restriction
    if (!email.toLowerCase().endsWith('@gmail.com')) {
      setMessage({ type: 'error', text: 'Please use a Gmail address. We deliver digests via Gmail SMTP.' });
      setLoading(false);
      return;
    }

    if (isSignUp) {
      await handleSignUp();
    } else {
      await handleSignIn();
    }

    setLoading(false);
  };

  const handleSignUp = async () => {
    if (!displayName.trim()) {
      setMessage({ type: 'error', text: 'Please enter your name — we use it to greet you in emails.' });
      return;
    }

    if (password.length < 6) {
      setMessage({ type: 'error', text: 'Password must be at least 6 characters long.' });
      return;
    }

    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${location.origin}/auth/callback`,
          data: {
            display_name: displayName || email.split('@')[0],
          },
        },
      });

      if (error) throw error;

      // Check if the user already exists (Supabase returns a user with identities: [] for existing users)
      if (data.user && data.user.identities && data.user.identities.length === 0) {
        setMessage({ type: 'error', text: 'An account with this email already exists. Please sign in instead.' });
        return;
      }

      setMessage({
        type: 'success',
        text: '✅ Account created! Check your email for a verification link. You can sign in after verifying.',
      });
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to create account.' });
    }
  };

  const handleSignIn = async () => {
    if (!password) {
      setMessage({ type: 'error', text: 'Please enter your password.' });
      return;
    }

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        if (error.message.includes('Email not confirmed')) {
          setMessage({ type: 'error', text: 'Please verify your email first. Check your inbox for the verification link.' });
        } else if (error.message.includes('Invalid login credentials')) {
          setMessage({ type: 'error', text: 'Invalid email or password. Please try again.' });
        } else {
          throw error;
        }
        return;
      }

      if (data.session && data.user) {
        // Password sign-in bypasses the callback, so ensure user profile exists
        const role = data.user.email === 'raazof5@gmail.com' ? 'admin' : 'user';
        const metadataName = data.user.user_metadata?.display_name || data.user.email?.split('@')[0] || 'Anonymous';

        await supabase.from('users').upsert({
          id: data.user.id,
          email: data.user.email,
          delivery_email: data.user.email,
          display_name: metadataName,
          auth_provider: 'email',
          role: role,
          last_login_at: new Date().toISOString(),
        }, { onConflict: 'id' });

        // Increment login count (ignore errors — non-critical)
        try { await supabase.rpc('increment_login_count', { p_user_id: data.user.id }); } catch {}

        router.push('/dashboard');
      }
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to sign in.' });
    }
  };

  const handleGoogleLogin = async () => {
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${location.origin}/auth/callback`,
        },
      });
      if (error) throw error;
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to login with Google.' });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="absolute top-6 left-6">
        <Link href="/" className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
          <BookOpen className="w-5 h-5 text-primary" />
          <span className="font-semibold tracking-tight">ResearchSummarizer</span>
        </Link>
      </div>

      <div className="w-full max-w-md glass-panel p-8 rounded-2xl animate-slide-up shadow-2xl shadow-primary/5">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">{isSignUp ? 'Create an Account' : 'Welcome Back'}</h1>
          <p className="text-gray-400 text-sm">
            {isSignUp ? 'Sign up to receive personalized research digests.' : 'Sign in to manage your digest preferences.'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {isSignUp && (
            <div className="animate-fade-in">
              <label htmlFor="displayName" className="block text-sm font-medium text-gray-300 mb-1">Your Name</label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  id="displayName"
                  type="text"
                  required={isSignUp}
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Your preferred name (used in email greeting)"
                  className="w-full bg-black/40 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                />
              </div>
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1">Gmail Address <span className="text-gray-500">(for login & digest delivery)</span></label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@gmail.com"
                className="w-full bg-black/40 border border-white/10 rounded-xl py-3 pl-10 pr-4 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1">
              Password {isSignUp && <span className="text-gray-500">(min 6 characters)</span>}
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                required
                minLength={isSignUp ? 6 : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={isSignUp ? 'Create a password' : 'Enter your password'}
                className="w-full bg-black/40 border border-white/10 rounded-xl py-3 pl-10 pr-12 text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {message && (
            <div className={`p-3 rounded-lg text-sm ${message.type === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
              {message.text}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !email || !password}
            className="w-full bg-primary hover:bg-primary-hover text-black font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(0,212,255,0.2)]"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <>{isSignUp ? 'Create Account' : 'Sign In'} <ArrowRight className="w-5 h-5" /></>}
          </button>
        </form>

        <div className="mt-4 text-center">
          <button
            onClick={() => { setIsSignUp(!isSignUp); setMessage(null); setPassword(''); }}
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            {isSignUp ? 'Already have an account? Sign in instead.' : 'Need an account? Sign up instead.'}
          </button>
        </div>

        <div className="my-6 flex items-center gap-4">
          <div className="h-px bg-white/10 flex-grow"></div>
          <span className="text-xs text-gray-500 uppercase font-medium">Or continue with</span>
          <div className="h-px bg-white/10 flex-grow"></div>
        </div>

        <button
          onClick={handleGoogleLogin}
          className="w-full bg-white/5 hover:bg-white/10 border border-white/10 text-white font-medium py-3 rounded-xl transition-all flex items-center justify-center gap-3"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
          </svg>
          Google
        </button>
      </div>
    </div>
  );
}
