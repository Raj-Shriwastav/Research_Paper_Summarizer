'use client';

import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';
import { Check, ArrowRight } from 'lucide-react';

const TOPICS = [
  'Artificial Intelligence', 'Natural Language Processing', 'Computer Vision',
  'Robotics', 'Machine Learning Theory', 'Neuroscience', 'Quantum Computing',
  'Bioinformatics'
];

export default function OnboardingPage() {
  const [step, setStep] = useState(1);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [cadence, setCadence] = useState('daily');
  const [loading, setLoading] = useState(false);
  const supabase = createClient();
  const router = useRouter();

  const toggleTopic = (topic: string) => {
    setSelectedTopics(prev => 
      prev.includes(topic) ? prev.filter(t => t !== topic) : [...prev, topic]
    );
  };

  const handleFinish = async () => {
    setLoading(true);
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      // Ensure user profile exists (service role bypasses RLS)
      await fetch('/api/profile/ensure', { method: 'POST' });

      // Save preferences
      await supabase.from('user_preferences').upsert({
        user_id: user.id,
        topics: selectedTopics,
        cadence: [cadence],
        email_enabled: true,
        max_papers_per_digest: 2,
      }, { onConflict: 'user_id' });

      // Mark onboarding complete
      await supabase.from('users').update({ onboarding_completed: true }).eq('id', user.id);
      
      router.push('/dashboard');
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 animate-fade-in">
      <div className="w-full max-w-2xl">
        {step === 1 && (
          <div className="glass-panel p-12 rounded-3xl border border-white/5 text-center">
            <h1 className="text-4xl font-bold text-white mb-4">Welcome to ResearchSummarizer</h1>
            <p className="text-gray-400 text-lg mb-8">Let's set up your personalized research feed in 30 seconds.</p>
            <button 
              onClick={() => setStep(2)}
              className="px-8 py-3 bg-primary text-black font-semibold rounded-full hover:scale-105 transition-transform"
            >
              Get Started →
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="glass-panel p-10 rounded-3xl border border-white/5 animate-slide-up">
            <h2 className="text-2xl font-bold text-white mb-2">What do you want to track?</h2>
            <p className="text-gray-400 mb-8">Select at least one topic. You can change this later.</p>
            
            <div className="flex flex-wrap gap-3 mb-10">
              {TOPICS.map(topic => (
                <button
                  key={topic}
                  onClick={() => toggleTopic(topic)}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors border ${
                    selectedTopics.includes(topic)
                      ? 'bg-primary/20 border-primary text-primary'
                      : 'bg-black/40 border-white/10 text-gray-400 hover:text-white'
                  }`}
                >
                  {topic}
                </button>
              ))}
            </div>

            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">{selectedTopics.length} selected</span>
              <button 
                onClick={() => setStep(3)}
                disabled={selectedTopics.length === 0}
                className="px-6 py-2 bg-primary text-black font-semibold rounded-xl disabled:opacity-50 disabled:hover:scale-100 hover:scale-105 transition-transform flex items-center gap-2"
              >
                Continue <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="glass-panel p-10 rounded-3xl border border-white/5 animate-slide-up">
            <h2 className="text-2xl font-bold text-white mb-2">How often should we send digests?</h2>
            <p className="text-gray-400 mb-8">We'll deliver them straight to your inbox.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
              {['daily', 'weekly', 'monthly'].map(c => (
                <button
                  key={c}
                  onClick={() => setCadence(c)}
                  className={`p-6 rounded-2xl border text-left transition-all ${
                    cadence === c 
                      ? 'bg-primary/10 border-primary shadow-[inset_0_0_15px_rgba(0,212,255,0.1)]' 
                      : 'bg-black/40 border-white/10 hover:border-white/30'
                  }`}
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className="capitalize font-bold text-white">{c}</span>
                    {cadence === c && <Check className="w-5 h-5 text-primary" />}
                  </div>
                  <span className="text-xs text-gray-400">
                    {c === 'daily' && 'A quick summary every morning.'}
                    {c === 'weekly' && 'A comprehensive weekend review.'}
                    {c === 'monthly' && 'A deep dive into the month\'s best.'}
                  </span>
                </button>
              ))}
            </div>

            <button 
              onClick={handleFinish}
              disabled={loading}
              className="w-full py-4 bg-primary text-black font-bold rounded-xl hover:scale-[1.02] transition-transform flex items-center justify-center gap-2"
            >
              {loading ? 'Saving...' : 'Finish Setup'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
