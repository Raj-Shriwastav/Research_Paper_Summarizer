import { createClient as createServerClient } from '@/lib/supabase/server';
import { createClient as createAdminClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';

// POST /api/profile/ensure — ensures the user row and default preferences exist
export async function POST() {
  const supabase = await createServerClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // Use service role to bypass RLS
  const adminSupabase = createAdminClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_KEY!
  );

  // Ensure user row exists
  const role = user.email === 'raazof5@gmail.com' ? 'admin' : 'user';
  await adminSupabase.from('users').upsert({
    id: user.id,
    email: user.email,
    delivery_email: user.email,
    display_name: user.user_metadata?.display_name || user.user_metadata?.full_name || user.email?.split('@')[0] || 'Anonymous',
    auth_provider: user.app_metadata?.provider || 'email',
    role: role,
  }, { onConflict: 'id', ignoreDuplicates: false });

  // Check if preferences exist
  const { data: prefs } = await adminSupabase
    .from('user_preferences')
    .select('user_id')
    .eq('user_id', user.id)
    .single();

  if (!prefs) {
    await adminSupabase.from('user_preferences').insert({
      user_id: user.id,
      topics: ['Artificial Intelligence'],
      cadence: ['daily'],
      max_papers_per_digest: 2,
      email_enabled: true,
    });
  }

  return NextResponse.json({ success: true });
}
