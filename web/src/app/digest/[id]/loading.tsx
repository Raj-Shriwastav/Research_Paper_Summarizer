export default function DigestDetailLoading() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header Bar Skeleton */}
      <div className="sticky top-0 z-10 glass-panel border-b border-white/5 py-4 px-6 flex items-center justify-between">
        <div className="h-6 w-40 skeleton rounded-full"></div>
        <div className="flex gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-6 w-24 skeleton rounded-full"></div>
          ))}
        </div>
      </div>

      {/* Main Content Area Skeleton */}
      <main className="max-w-4xl mx-auto px-6 py-12 animate-fade-in">
        <div className="mb-10 text-center flex flex-col items-center">
          <div className="h-6 w-32 skeleton rounded-full mb-4"></div>
          <div className="h-12 w-3/4 skeleton rounded-xl mb-6"></div>
        </div>

        <div className="glass-panel p-8 sm:p-12 rounded-3xl border border-white/5 space-y-8">
          {[1, 2, 3].map((section) => (
            <div key={section} className="space-y-4">
              <div className="h-8 w-1/3 skeleton rounded-lg mb-6"></div>
              <div className="h-4 w-full skeleton"></div>
              <div className="h-4 w-full skeleton"></div>
              <div className="h-4 w-5/6 skeleton"></div>
              <div className="h-4 w-11/12 skeleton"></div>
              <br />
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
