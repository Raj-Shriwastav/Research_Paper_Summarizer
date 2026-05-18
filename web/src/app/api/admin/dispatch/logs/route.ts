import { createClient as createServerClient } from '@/lib/supabase/server';
import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  if (!id) return NextResponse.json({ error: 'Missing ID' }, { status: 400 });

  const supabase = await createServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { data: adminCheck } = await supabase
    .from('users')
    .select('role')
    .eq('id', user.id)
    .single();

  if (adminCheck?.role !== 'admin') {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
  }

  try {
    const logFilePath = path.resolve(process.cwd(), '../logs', `${id}.log`);
    
    if (fs.existsSync(logFilePath)) {
      const logs = fs.readFileSync(logFilePath, 'utf-8');
      return NextResponse.json({ logs });
    } else {
      return NextResponse.json({ logs: '' });
    }
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
