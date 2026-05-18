import Link from 'next/link';
import { ArrowRight, BookOpen, Clock, ShieldCheck, Mail } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Navbar */}
      <header className="fixed top-0 w-full z-50 glass-panel border-b-0 border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="text-primary w-6 h-6" />
            <span className="font-bold text-lg tracking-tight">Research<span className="text-primary">Summarizer</span></span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/auth" className="text-sm text-gray-300 hover:text-white transition-colors">
              Sign In
            </Link>
            <Link href="/auth" className="bg-primary hover:bg-primary-hover text-black font-semibold text-sm px-5 py-2 rounded-full transition-all hover:scale-105 active:scale-95 shadow-[0_0_15px_rgba(0,212,255,0.3)]">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-40 pb-20 px-6 flex flex-col items-center justify-center text-center flex-grow">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm mb-8 animate-fade-in">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
          <span className="text-xs text-gray-300 font-medium">v2.0 is live with AI Grounding Verification</span>
        </div>

        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6 max-w-4xl animate-slide-up" style={{ animationDelay: '0.1s' }}>
          Stop reading abstracts. <br className="hidden md:block" />
          Start understanding <span className="gradient-text">breakthroughs.</span>
        </h1>
        
        <p className="text-lg md:text-xl text-gray-400 max-w-2xl mb-10 animate-slide-up" style={{ animationDelay: '0.2s' }}>
          An autonomous pipeline that discovers, curates, and summarizes the latest research papers tailored to your interests. Delivered straight to your inbox.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 animate-slide-up" style={{ animationDelay: '0.3s' }}>
          <Link href="/auth" className="flex items-center justify-center gap-2 bg-white text-black font-semibold px-8 py-4 rounded-full transition-all hover:bg-gray-200 hover:scale-105 shadow-[0_0_30px_rgba(255,255,255,0.2)]">
            Start Reading Free <ArrowRight className="w-5 h-5" />
          </Link>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl w-full mt-24 animate-slide-up" style={{ animationDelay: '0.4s' }}>
          <FeatureCard 
            icon={<Clock className="w-6 h-6 text-accent" />}
            title="Dynamic Word Budgeting"
            description="Our Director Agent actively balances word counts so your digest always takes exactly 15 minutes to read."
          />
          <FeatureCard 
            icon={<ShieldCheck className="w-6 h-6 text-primary" />}
            title="Fact-Checked Grounding"
            description="Every sentence is verified against the source text using a Cross-Encoder to guarantee zero hallucinations."
          />
          <FeatureCard 
            icon={<Mail className="w-6 h-6 text-pink-400" />}
            title="Automated Delivery"
            description="Receive beautifully formatted HTML emails daily, weekly, or monthly based on your exact preferences."
          />
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 text-center text-gray-500 text-sm border-t border-white/5">
        <p>© {new Date().getFullYear()} Research Paper Summarizer. Built autonomously.</p>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="glass-panel p-6 rounded-2xl text-left hover:bg-white/[0.03] transition-colors border border-white/5 hover:border-white/10">
      <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-4">
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
      <p className="text-gray-400 text-sm leading-relaxed">{description}</p>
    </div>
  );
}
