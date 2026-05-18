export default function SettingsLoading() {
  return (
    <div className="p-8 max-w-4xl mx-auto animate-fade-in">
      <header className="mb-10">
        <div className="h-9 w-32 skeleton mb-2"></div>
        <div className="h-5 w-64 skeleton"></div>
      </header>

      <div className="space-y-6">
        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-white/5">
          <div className="h-7 w-48 skeleton mb-4"></div>
          <div className="h-5 w-80 skeleton mb-6"></div>
          
          <div className="flex flex-wrap gap-3 mb-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-9 w-32 skeleton rounded-full"></div>
            ))}
          </div>

          <div className="flex gap-3">
            <div className="h-10 flex-1 skeleton rounded-xl"></div>
            <div className="h-10 w-32 skeleton rounded-xl"></div>
          </div>
        </div>

        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-white/5">
          <div className="h-7 w-40 skeleton mb-4"></div>
          
          <div className="flex items-center justify-between mb-8 pb-8 border-b border-white/10">
            <div>
              <div className="h-5 w-32 skeleton mb-2"></div>
              <div className="h-4 w-64 skeleton"></div>
            </div>
            <div className="h-6 w-11 skeleton rounded-full"></div>
          </div>

          <div>
            <div className="h-5 w-40 skeleton mb-4"></div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-14 w-full skeleton rounded-xl"></div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-4">
          <div className="h-12 w-48 skeleton rounded-xl"></div>
        </div>
      </div>
    </div>
  );
}
