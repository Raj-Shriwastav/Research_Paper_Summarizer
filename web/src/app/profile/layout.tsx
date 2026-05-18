import Sidebar from '@/components/Sidebar';

export default function ProfileLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-black/20 relative">
        {children}
      </main>
    </div>
  );
}
