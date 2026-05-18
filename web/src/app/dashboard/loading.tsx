export default function DashboardLoading() {
  return (
    <div className="p-8 max-w-5xl mx-auto animate-fade-in">
      <header className="mb-10">
        <div className="h-9 w-48 skeleton mb-2"></div>
        <div className="h-5 w-64 skeleton"></div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {[1, 2].map((i) => (
          <div key={i} className="glass-panel p-6 rounded-2xl border border-white/5 flex flex-col h-full min-h-[200px]">
            <div className="flex justify-between items-start mb-4">
              <div className="h-6 w-16 skeleton rounded-full"></div>
              <div className="h-4 w-24 skeleton"></div>
            </div>
            
            <div className="h-8 w-3/4 skeleton mb-4"></div>
            
            <div className="flex gap-4 mt-auto mb-6">
              <div className="h-4 w-20 skeleton"></div>
              <div className="h-4 w-24 skeleton"></div>
            </div>

            <div className="w-full py-3 h-12 skeleton rounded-xl"></div>
          </div>
        ))}
      </div>

      <div className="mt-12 glass-panel p-8 rounded-2xl border border-white/5">
        <div className="h-7 w-64 skeleton mb-2"></div>
        <div className="h-5 w-96 skeleton mb-6"></div>
        <div className="h-12 w-40 skeleton rounded-xl"></div>
      </div>
    </div>
  );
}
