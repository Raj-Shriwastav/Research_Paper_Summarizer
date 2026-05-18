import { createClient } from '@/lib/supabase/server';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Calendar, FileText, Clock } from 'lucide-react';
import DownloadButton from '@/components/DownloadButton';

export default async function DigestDetailPage({ params }: { params: { id: string } }) {
  const supabase = await createClient();

  const { data: digest } = await supabase
    .from('digests')
    .select('*')
    .eq('id', params.id)
    .single();

  if (!digest) {
    notFound();
  }

  const readingTime = Math.max(1, Math.floor((digest.word_count || 0) / 220));

  return (
    <div className="min-h-screen bg-background">
      {/* Header Bar */}
      <div className="sticky top-0 z-10 glass-panel border-b border-white/5 py-4 px-6 flex items-center justify-between">
        <Link 
          href="/dashboard" 
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span className="font-medium hidden sm:inline">Back to Dashboard</span>
        </Link>
        <div className="flex gap-4 text-xs sm:text-sm font-medium text-gray-400">
          <span className="flex items-center gap-1.5 bg-white/5 px-3 py-1 rounded-full border border-white/5 hidden sm:flex">
            <Calendar className="w-4 h-4 text-primary" />
            {new Date(digest.digest_date).toLocaleDateString()}
          </span>
          <span className="flex items-center gap-1.5 bg-white/5 px-3 py-1 rounded-full border border-white/5 hidden sm:flex">
            <FileText className="w-4 h-4 text-primary" />
            {digest.paper_count} papers
          </span>
          <span className="flex items-center gap-1.5 bg-white/5 px-3 py-1 rounded-full border border-white/5">
            <Clock className="w-4 h-4 text-primary" />
            ~{readingTime} min
          </span>
          <DownloadButton 
            digestId={digest.id} 
            topic={digest.topic} 
            date={digest.digest_date} 
            content={digest.markdown_content || digest.html_content || ""} 
          />
        </div>
      </div>

      {/* Main Content Area */}
      <main className="max-w-4xl mx-auto px-6 py-12 animate-slide-up">
        <div className="mb-10 text-center">
          <span className="inline-block px-3 py-1 mb-4 bg-primary/10 text-primary border border-primary/20 rounded-full text-xs font-bold uppercase tracking-wider">
            {digest.cadence} Digest
          </span>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-white mb-6">
            {digest.topic}
          </h1>
        </div>

        {/* 
          Since the backend stores the digest content in both Markdown and HTML,
          we will render the HTML content directly. The email template HTML 
          might contain full HTML tags (<html>, <body>, etc.), so we might need
          to extract just the content or use an iframe if styles clash.
          To keep it simple and native, we'll render the markdown_content using a markdown parser, 
          or just safely inject the html_content if it's well-formed.
          For best visual results matching the web app, let's use the markdown content 
          and format it beautifully.
        */}
        <div className="glass-panel p-8 sm:p-12 rounded-3xl border border-white/5 prose prose-invert prose-lg max-w-none prose-headings:text-primary prose-a:text-accent prose-a:no-underline hover:prose-a:underline prose-pre:bg-black/50 prose-pre:border-white/10 prose-pre:border">
          {digest.html_content ? (
            <div dangerouslySetInnerHTML={{ __html: extractContent(digest.html_content) }} />
          ) : (
            <div className="text-gray-400 text-center italic">No content available.</div>
          )}
        </div>
      </main>
    </div>
  );
}

// Utility to extract just the body content from the email HTML template
function extractContent(html: string) {
  const bodyMatch = html.match(/<div class="content">([\s\S]*?)<\/div>\s*<div class="footer">/);
  if (bodyMatch && bodyMatch[1]) {
    return bodyMatch[1];
  }
  return html;
}
