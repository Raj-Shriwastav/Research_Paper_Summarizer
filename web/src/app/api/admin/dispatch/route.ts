import { createClient as createServerClient } from '@/lib/supabase/server';
import { createClient as createAdminClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

export async function POST(request: Request) {
  const supabase = await createServerClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { data: adminProfile } = await supabase
    .from('users')
    .select('role, display_name, email')
    .eq('id', user.id)
    .single();

  if (adminProfile?.role !== 'admin') {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
  }

  try {
    const { cadence, target } = await request.json(); // cadence: 'daily' | 'weekly' | 'monthly', target: 'all' | '<email>'
    
    // Determine the target email. If 'all', we don't pass --target-email so the CLI uses DB.
    let targetEmailArg: string | null = null;
    if (target !== 'all') {
      targetEmailArg = target;
    }

    // Determine the path to the python CLI
    const pythonScriptPath = path.resolve(process.cwd(), '../run_cli.py');
    
    // Use service role to bypass RLS for inserting log
    const adminSupabase = createAdminClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_KEY!
    );

    // Create the dispatch log entry first so we can pass its ID to the CLI
    const { data: logEntry, error: logError } = await adminSupabase.from('email_delivery_log').insert({
      sent_by: user.id,
      cadence,
      target,
      status: 'started_in_background',
      error_message: null
    }).select('id').single();

    if (logError) {
      console.error('Failed to create delivery log:', logError);
    }

    // Build arguments
    const args = ['-m', 'run_cli', '--mode', cadence];
    if (targetEmailArg) {
      args.push('--target-email', targetEmailArg);
    }
    if (logEntry?.id) {
      args.push('--log-id', logEntry.id);
    }

    // Ensure logs directory exists
    const logsDir = path.resolve(process.cwd(), '../logs');
    if (!fs.existsSync(logsDir)) {
      fs.mkdirSync(logsDir, { recursive: true });
    }

    let out, err;
    if (logEntry?.id) {
      const logFilePath = path.join(logsDir, `${logEntry.id}.log`);
      // Create initial log file
      fs.writeFileSync(logFilePath, `[System] Background task initialized. Log ID: ${logEntry.id}\n`);
      out = fs.openSync(logFilePath, 'a');
      err = fs.openSync(logFilePath, 'a');
    }

    // Spawn the background process
    const cwdPath = path.resolve(process.cwd(), '../'); // Run from root to access backend/ properly
    const pyProcess = spawn('python', args, {
      detached: true,
      stdio: ['ignore', out || 'inherit', err || 'inherit'],
      cwd: cwdPath,
      windowsHide: true,
    });

    // Unref allows the parent (Next.js) to exit independently of the child
    pyProcess.unref();

    return NextResponse.json({ 
      success: true, 
      message: `Triggered background generation for ${cadence} digest.`,
      log_id: logEntry?.id
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
