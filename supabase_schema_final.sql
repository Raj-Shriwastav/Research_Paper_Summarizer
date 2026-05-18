-- ============================================
-- Research Paper Summarizer — Consolidated Schema
-- ============================================
-- Run this ONCE in your Supabase SQL Editor:
-- https://supabase.com/dashboard → SQL Editor → New Query
-- This file combines all schema versions into one.

-- ──────────────────────────────────────────────
-- 1. Users table (extended with profile fields)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  display_name TEXT,
  delivery_email TEXT,                          -- Gmail where digests are sent (defaults to email)
  auth_provider TEXT DEFAULT 'magic_link',
  avatar_url TEXT,
  institution TEXT,
  role TEXT DEFAULT 'user',                     -- 'user' | 'admin'
  bio TEXT,
  research_interests TEXT[],
  onboarding_completed BOOLEAN DEFAULT false,
  last_login_at TIMESTAMPTZ,
  login_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ──────────────────────────────────────────────
-- 2. User preferences (subscription settings)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  topics TEXT[] DEFAULT ARRAY['Artificial Intelligence'],
  cadence TEXT[] DEFAULT ARRAY['daily'],
  max_papers_per_digest INT DEFAULT 2,
  email_enabled BOOLEAN DEFAULT true,
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id)
);

-- ──────────────────────────────────────────────
-- 3. Digest storage
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS digests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic TEXT NOT NULL,
  cadence TEXT NOT NULL CHECK (cadence IN ('daily', 'weekly', 'monthly')),
  digest_date DATE NOT NULL,
  markdown_content TEXT NOT NULL,
  html_content TEXT,
  paper_count INT DEFAULT 0,
  word_count INT DEFAULT 0,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(topic, cadence, digest_date)
);

-- ──────────────────────────────────────────────
-- 4. User activity tracking
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_activity (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  action TEXT NOT NULL,           -- 'login', 'view_digest', 'chat', 'settings_update'
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ──────────────────────────────────────────────
-- 5. Chat tables (for future RAG feature)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  digest_id UUID REFERENCES digests(id) ON DELETE CASCADE,
  context_type TEXT DEFAULT 'global',
  section_index INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ──────────────────────────────────────────────
-- Indexes
-- ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_digests_topic_date ON digests(topic, digest_date DESC);
CREATE INDEX IF NOT EXISTS idx_digests_cadence ON digests(cadence);
CREATE INDEX IF NOT EXISTS idx_digests_created ON digests(created_at);
CREATE INDEX IF NOT EXISTS idx_user_activity_user ON user_activity(user_id, created_at DESC);

-- ──────────────────────────────────────────────
-- Row Level Security
-- ──────────────────────────────────────────────
ALTER TABLE digests ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_activity ENABLE ROW LEVEL SECURITY;

-- Digests: Authenticated users can read all digests
CREATE POLICY "Authenticated users can read digests"
  ON digests FOR SELECT TO authenticated USING (true);

-- Users: can read own profile
CREATE POLICY "Users read own profile"
  ON users FOR SELECT TO authenticated USING (auth.uid() = id);

-- Users: can update own profile
CREATE POLICY "Users update own profile"
  ON users FOR UPDATE TO authenticated USING (auth.uid() = id);

-- Users: can insert own profile (first login auto-create)
CREATE POLICY "Users can insert own profile"
  ON users FOR INSERT TO authenticated WITH CHECK (auth.uid() = id);

-- User preferences: can read own
CREATE POLICY "Users can read own preferences"
  ON user_preferences FOR SELECT TO authenticated USING (auth.uid() = user_id);

-- User preferences: can update own
CREATE POLICY "Users can update own preferences"
  ON user_preferences FOR UPDATE TO authenticated USING (auth.uid() = user_id);

-- User preferences: can insert own
CREATE POLICY "Users can insert own preferences"
  ON user_preferences FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

-- User activity: can read own
CREATE POLICY "Users read own activity"
  ON user_activity FOR SELECT TO authenticated USING (auth.uid() = user_id);

-- User activity: can insert own
CREATE POLICY "Users can insert own activity"
  ON user_activity FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

-- Service role: full access to everything (backend pipeline)
CREATE POLICY "Service role full access to digests"
  ON digests FOR ALL TO service_role USING (true);

CREATE POLICY "Service role full access to users"
  ON users FOR ALL TO service_role USING (true);

CREATE POLICY "Service role full access to user_preferences"
  ON user_preferences FOR ALL TO service_role USING (true);

CREATE POLICY "Service role full access to user_activity"
  ON user_activity FOR ALL TO service_role USING (true);

-- ──────────────────────────────────────────────
-- NOTE: Admin RLS policies intentionally omitted.
-- Admin operations (read all users, delete users, etc.)
-- are performed via service_role client in the API routes,
-- which bypasses RLS entirely. This avoids infinite recursion
-- caused by policies that query the users table itself.
-- ──────────────────────────────────────────────

-- ──────────────────────────────────────────────
-- 6. Email delivery log (admin dispatch tracking)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS email_delivery_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sent_by UUID REFERENCES users(id),
  cadence TEXT NOT NULL,
  target TEXT NOT NULL,                   -- 'self' or 'all'
  recipient_count INT DEFAULT 0,
  status TEXT DEFAULT 'sent',
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE email_delivery_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access to delivery log"
  ON email_delivery_log FOR ALL TO service_role USING (true);

-- ──────────────────────────────────────────────
-- RPC: Increment login count
-- ──────────────────────────────────────────────
CREATE OR REPLACE FUNCTION increment_login_count(p_user_id UUID)
RETURNS void AS $$
BEGIN
  UPDATE users SET login_count = COALESCE(login_count, 0) + 1 WHERE id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ──────────────────────────────────────────────
-- Reload PostgREST schema cache
-- ──────────────────────────────────────────────
NOTIFY pgrst, 'reload schema';
