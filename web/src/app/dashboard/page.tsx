import { createClient } from '@/lib/supabase/server';
import Link from 'next/link';
import { Clock, FileText, Calendar, ArrowRight } from 'lucide-react';

export default async function DashboardPage() {
  const supabase = await createClient();

  const { data: { user } } = await supabase.auth.getUser();

  // Fetch the latest 2 digests
  const { data: digests } = await supabase
    .from('digests')
    .select('id, topic, cadence, digest_date, paper_count, word_count')
    .order('digest_date', { ascending: false })
    .limit(2);

  return (
    <div className="p-8 max-w-5xl mx-auto animate-fade-in">
      <header className="mb-10">
        <h1 className="text-3xl font-bold text-white mb-2">Welcome Back</h1>
        <p className="text-gray-400">Here are your latest research digests.</p>
      </header>

      {(!digests || digests.length === 0) ? (
        <div className="glass-panel p-12 text-center rounded-2xl border border-white/5 border-dashed">
          <FileText className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">No digests yet</h3>
          <p className="text-gray-400 max-w-md mx-auto">
            Your first digest will appear here once the pipeline runs. Make sure your preferences are configured.
          </p>
          <Link href="/settings" className="inline-block mt-6 px-6 py-2 bg-white/10 hover:bg-white/20 text-white rounded-full transition-colors">
            Configure Preferences
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {digests.map((digest) => (
            <DigestCard key={digest.id} digest={digest} />
          ))}
        </div>
      )}

      {digests && digests.length > 0 && (
        <div className="mt-6 text-right">
          <Link href="/digests" className="inline-flex items-center gap-2 text-primary hover:text-primary-hover font-medium transition-colors">
            View All Past Digests <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      <div className="mt-12 glass-panel p-8 rounded-2xl bg-gradient-to-br from-primary/10 to-transparent border border-primary/20">
        <h3 className="text-xl font-semibold text-white mb-2">Need to adjust your topics?</h3>
        <p className="text-gray-300 mb-6">
          You can change the research topics you're tracking at any time in your settings.
        </p>
        <Link href="/settings" className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-black font-semibold rounded-xl hover:scale-105 transition-transform shadow-[0_0_15px_rgba(0,212,255,0.3)]">
          Go to Settings <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}

function DigestCard({ digest }: { digest: any }) {
  const readingTime = Math.max(1, Math.floor((digest.word_count || 0) / 220));
  
  return (
    <div className="glass-panel p-6 rounded-2xl hover:bg-white/[0.03] transition-all hover:-translate-y-1 hover:shadow-xl border border-white/5 hover:border-primary/30 group flex flex-col h-full">
      <div className="flex justify-between items-start mb-4">
        <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs font-medium text-gray-300 uppercase tracking-wider">
          {digest.cadence}
        </span>
        <span className="flex items-center gap-1 text-xs text-gray-400">
          <Calendar className="w-3 h-3" />
          {new Date(digest.digest_date).toLocaleDateString()}
        </span>
      </div>
      
      <h3 className="text-2xl font-bold text-white mb-4 group-hover:text-primary transition-colors">
        {digest.topic}
      </h3>
      
      <div className="flex gap-4 text-sm text-gray-400 mt-auto mb-6">
        <div className="flex items-center gap-1.5">
          <FileText className="w-4 h-4 text-gray-500" />
          <span>{digest.paper_count} papers</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="w-4 h-4 text-gray-500" />
          <span>~{readingTime} min read</span>
        </div>
      </div>

      <Link 
        href={`/digest/${digest.id}`}
        className="w-full py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-center font-medium text-white transition-colors flex items-center justify-center gap-2 group-hover:bg-primary/10 group-hover:border-primary/30 group-hover:text-primary"
      >
        Read Full Digest <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  );
}
