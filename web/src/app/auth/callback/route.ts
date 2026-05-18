import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const next = searchParams.get('next') ?? '/dashboard'

  if (code) {
    const supabase = await createClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)
    
    if (!error) {
      // Get the newly authenticated user
      const { data: { user } } = await supabase.auth.getUser();
      
      let nextRoute = next;

      if (user) {
        // Auto-create or update profile
        const role = user.email === 'raazof5@gmail.com' ? 'admin' : 'user';
        
        // Get display name from user metadata (set during signUp or by Google)
        const metadataName = user.user_metadata?.display_name || user.user_metadata?.full_name || user.user_metadata?.name;
        
        const { data: existingUser } = await supabase
          .from('users')
          .select('onboarding_completed, display_name')
          .eq('id', user.id)
          .single();

        // Determine what display name to save
        // 1. If metadata has a name (from signUp data or Google), use it for new users
        // 2. Otherwise keep existing, or fallback to email prefix
        let finalName = existingUser?.display_name;
        if (metadataName && !existingUser?.display_name) {
          finalName = metadataName;
        } else if (!existingUser?.display_name) {
          finalName = user.email?.split('@')[0] || 'Anonymous';
        }

        await supabase.from('users').upsert({
          id: user.id,
          email: user.email,
          delivery_email: user.email,
          display_name: finalName,
          auth_provider: user.app_metadata?.provider || 'email',
          role: role,
          last_login_at: new Date().toISOString(),
        }, { onConflict: 'id' });

        // If it's a new user, they won't have onboarding_completed
        if (!existingUser || !existingUser.onboarding_completed) {
          // Add default preferences if missing
          await supabase.from('user_preferences').upsert({
            user_id: user.id,
            topics: ['Artificial Intelligence'],
            cadence: ['daily'],
            email_enabled: true,
            max_papers_per_digest: 2,
          }, { onConflict: 'user_id' });
          
          nextRoute = '/onboarding';
        } else {
          // Increment login count for returning users
          const { error: rpcError } = await supabase.rpc('increment_login_count', { p_user_id: user.id });
          if (rpcError) {
            // Fallback if RPC doesn't exist
            await supabase.from('users').update({ login_count: 1 }).eq('id', user.id);
          }
        }

        // Log login activity
        await supabase.from('user_activity').insert({
          user_id: user.id,
          action: 'login',
        });
      }

      const forwardedHost = request.headers.get('x-forwarded-host')
      const isLocalEnv = process.env.NODE_ENV === 'development'
      
      if (isLocalEnv) {
        return NextResponse.redirect(`${origin}${nextRoute}`)
      } else if (forwardedHost) {
        return NextResponse.redirect(`https://${forwardedHost}${nextRoute}`)
      } else {
        return NextResponse.redirect(`${origin}${nextRoute}`)
      }
    }
  }

  // return the user to an error page with instructions
  return NextResponse.redirect(`${origin}/auth?error=auth-failed`)
}
