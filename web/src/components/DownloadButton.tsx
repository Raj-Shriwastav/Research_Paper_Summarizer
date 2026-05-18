'use client';

import { Download } from 'lucide-react';
import { useState } from 'react';

export default function DownloadButton({ digestId, topic, date, content }: { digestId: string, topic: string, date: string, content: string }) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = () => {
    setDownloading(true);
    try {
      // Create a blob from the content
      // We will save it as markdown if possible, or HTML
      const blob = new Blob([content], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Digest_${topic.replace(/\s+/g, '_')}_${new Date(date).toISOString().split('T')[0]}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Failed to download", e);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <button
      onClick={handleDownload}
      disabled={downloading}
      className="flex items-center gap-1.5 bg-primary/20 text-primary hover:bg-primary/30 px-3 py-1 rounded-full border border-primary/30 transition-colors font-medium text-xs sm:text-sm"
      title="Download and save locally to keep beyond the 45-day retention period"
    >
      <Download className="w-4 h-4" />
      <span className="hidden sm:inline">{downloading ? 'Downloading...' : 'Save Locally'}</span>
    </button>
  );
}
