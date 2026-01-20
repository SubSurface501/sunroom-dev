import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white selection:bg-cyan-500 selection:text-white flex flex-col overflow-x-hidden">
      
      {/* --- NAVIGATION BAR --- */}
      <nav className="fixed w-full z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-6 h-20 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-tr from-cyan-400 to-purple-500 rounded-lg flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <span className="text-lg">☀️</span>
            </div>
            <span className="text-xl font-bold tracking-tight text-white">
              The Sun Room
            </span>
          </div>

          <div className="flex items-center gap-6">
            <Link href="/login" className="text-sm font-medium text-slate-400 hover:text-white transition-colors">
              Log In
            </Link>
            <Link 
              href="/dashboard" 
              className="bg-white text-slate-950 px-5 py-2.5 rounded-full text-sm font-bold hover:bg-cyan-50 transition-all hover:scale-105 shadow-lg shadow-cyan-500/20"
            >
              Enter Dashboard
            </Link>
          </div>
        </div>
      </nav>

      {/* --- HERO SECTION --- */}
      <main className="relative pt-32 pb-20 px-6 flex flex-col items-center justify-center text-center overflow-hidden">
        
        {/* Background Gradients */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-cyan-500/10 rounded-full blur-[100px] -z-10 pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-[800px] h-[600px] bg-purple-500/5 rounded-full blur-[120px] -z-10 pointer-events-none" />

        <div className="max-w-5xl mx-auto relative z-10">
          <div className="inline-flex items-center gap-2 mb-8 px-4 py-1.5 rounded-full bg-slate-900/50 border border-slate-800 text-cyan-400 text-xs font-mono font-medium animate-fade-in backdrop-blur-sm">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
            </span>
            System Online: V7.5 "Collective"
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8 leading-tight">
            Turn Information <br />
            into <span className="bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400">Insight.</span>
          </h1>
          
          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            The Sun Room is an AI-powered cognitive engine that reads your research, maps your ideas, and helps you write complex narratives.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-20">
            <Link 
              href="/dashboard" 
              className="w-full sm:w-auto px-8 py-4 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl font-bold text-lg transition-all shadow-xl shadow-cyan-900/20 hover:shadow-cyan-500/30 ring-1 ring-cyan-400/20"
            >
              Start Building
            </Link>
            <Link 
              href="/login" 
              className="w-full sm:w-auto px-8 py-4 bg-slate-900/50 hover:bg-slate-800/80 text-slate-300 rounded-xl font-medium text-lg border border-slate-800 backdrop-blur-sm transition-all"
            >
              View Demo
            </Link>
          </div>

          {/* Hero Dashboard Shot */}
          <div className="relative w-full rounded-2xl overflow-hidden shadow-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm group">
             <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-20 pointer-events-none" />
             <img 
               src="/images/mockup_1.jpg" 
               alt="Sun Room Dashboard" 
               className="w-full h-auto object-cover opacity-90 transition-opacity group-hover:opacity-100"
             />
          </div>
        </div>
      </main>

      {/* --- HOW IT WORKS (3 Pillars) --- */}
      <section className="py-24 bg-slate-950 relative border-t border-slate-900">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">From Chaos to Crystallization</h2>
            <p className="text-slate-400 max-w-2xl mx-auto">
              Most tools are just storage bins. The Sun Room is an active partner in your creative process.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="p-8 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-cyan-500/30 transition-colors">
              <div className="w-12 h-12 bg-cyan-900/30 rounded-lg flex items-center justify-center mb-6 text-cyan-400">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">1. Ingest</h3>
              <p className="text-slate-400 leading-relaxed">
                Drop in PDFs, YouTube videos, and raw notes. Our agents read, analyze, and tag everything automatically.
              </p>
            </div>

            {/* Step 2 */}
            <div className="p-8 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-purple-500/30 transition-colors">
              <div className="w-12 h-12 bg-purple-900/30 rounded-lg flex items-center justify-center mb-6 text-purple-400">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">2. Connect</h3>
              <p className="text-slate-400 leading-relaxed">
                The "Prism" engine maps your content into a 3D semantic graph, finding hidden connections between disparate ideas.
              </p>
            </div>

            {/* Step 3 */}
            <div className="p-8 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-pink-500/30 transition-colors">
              <div className="w-12 h-12 bg-pink-900/30 rounded-lg flex items-center justify-center mb-6 text-pink-400">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
              </div>
              <h3 className="text-xl font-bold text-white mb-3">3. Create</h3>
              <p className="text-slate-400 leading-relaxed">
                Collaborate with the "Writer's Room"—a team of AI agents that help you draft, edit, and refine your work.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* --- FEATURE DEEP DIVES --- */}
      <section className="py-24 bg-slate-900 overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 space-y-32">
          
          {/* Feature 1: The Graph */}
          <div className="flex flex-col md:flex-row items-center gap-12 md:gap-20">
            <div className="flex-1 space-y-6">
              <div className="inline-block px-3 py-1 rounded-full bg-cyan-900/30 text-cyan-400 text-sm font-medium border border-cyan-800">
                The Prism
              </div>
              <h3 className="text-3xl md:text-4xl font-bold text-white">
                See what you know.
              </h3>
              <p className="text-lg text-slate-400 leading-relaxed">
                Traditional folders hide information. The Sun Room visualizes it. 
                Navigate your knowledge base like a galaxy, filtering by topic, time, or resonance.
                Discover the "structural holes" in your research that lead to breakthrough insights.
              </p>
              <ul className="space-y-3 text-slate-300">
                <li className="flex items-center gap-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" /> 3D Semantic Clustering
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" /> Temporal Resonance Timeline
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" /> Real-time "gap detection"
                </li>
              </ul>
            </div>
            <div className="flex-1 relative">
               <div className="absolute inset-0 bg-cyan-500/20 blur-[80px] rounded-full -z-10" />
               <div className="rounded-xl overflow-hidden border border-slate-700 shadow-2xl bg-slate-800">
                 <img src="/images/mockup_2.jpg" alt="Graph View" className="w-full h-auto hover:scale-105 transition-transform duration-700" />
               </div>
            </div>
          </div>

          {/* Feature 2: Synthesis */}
          <div className="flex flex-col md:flex-row-reverse items-center gap-12 md:gap-20">
             <div className="flex-1 space-y-6">
              <div className="inline-block px-3 py-1 rounded-full bg-purple-900/30 text-purple-400 text-sm font-medium border border-purple-800">
                The Writer's Room
              </div>
              <h3 className="text-3xl md:text-4xl font-bold text-white">
                Never write from a blank page.
              </h3>
              <p className="text-lg text-slate-400 leading-relaxed">
                Summon a team of virtual research assistants. Ask them to "synthesize everything I know about X," 
                and watch them crawl your archive, finding citations and drafting prose that mimics your unique voice.
              </p>
              <ul className="space-y-3 text-slate-300">
                <li className="flex items-center gap-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400" /> Style-matching algorithms
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400" /> Automatic citation tracking
                </li>
                <li className="flex items-center gap-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400" /> Multi-agent collaboration
                </li>
              </ul>
            </div>
            <div className="flex-1 relative">
               <div className="absolute inset-0 bg-purple-500/20 blur-[80px] rounded-full -z-10" />
               <div className="rounded-xl overflow-hidden border border-slate-700 shadow-2xl bg-slate-800">
                 <img src="/images/mockup_3.jpg" alt="Synthesis Interface" className="w-full h-auto hover:scale-105 transition-transform duration-700" />
               </div>
            </div>
          </div>

        </div>
      </section>

      {/* --- FOUNDER PROFILE CARD --- */}
      <section className="py-24 bg-slate-950 border-t border-slate-900">
        <div className="max-w-4xl mx-auto px-6">
          <div className="bg-gradient-to-br from-slate-900 to-slate-950 rounded-3xl p-8 md:p-12 border border-slate-800 shadow-2xl relative overflow-hidden">
            {/* Decorative BG */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2" />

            <div className="flex flex-col md:flex-row items-center md:items-start gap-8 relative z-10">
              {/* Avatar */}
              <div className="flex-shrink-0">
                <div className="w-32 h-32 md:w-40 md:h-40 rounded-full p-1 bg-gradient-to-br from-cyan-400 to-purple-500">
                  <div className="w-full h-full rounded-full overflow-hidden border-4 border-slate-900">
                    <img 
                      src="/images/Jacob-Headshot.jpg" 
                      alt="Jacob" 
                      className="w-full h-full object-cover"
                    />
                  </div>
                </div>
              </div>

              {/* Text */}
              <div className="flex-1 text-center md:text-left">
                <h3 className="text-2xl font-bold text-white mb-1">Jacob</h3>
                <p className="text-cyan-400 text-sm font-mono mb-6 uppercase tracking-wider">Architect & Founder</p>
                <p className="text-slate-300 leading-relaxed mb-6">
                  "I built The Sun Room because I was tired of tools that just stored my notes. 
                  I wanted a system that would *think* with me. 
                  This isn't just a database; it's a mirror for your mind, designed to amplify human creativity rather than replace it."
                </p>
                
                {/* Signature / Link */}
                <div className="flex items-center justify-center md:justify-start gap-4">
                  <a href="#" className="text-slate-500 hover:text-white transition-colors text-sm">
                    @JacobOnTwitter
                  </a>
                  <span className="text-slate-700">•</span>
                  <a href="#" className="text-slate-500 hover:text-white transition-colors text-sm">
                    Read the Manifesto
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className="py-12 text-center text-slate-600 text-sm bg-slate-950 border-t border-slate-900">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-6">
          <div>
            &copy; 2025 The Sun Room. <span className="hidden md:inline">|</span> All rights reserved.
          </div>
          <div className="flex gap-6">
            <Link href="/privacy" className="hover:text-slate-400 transition-colors">Privacy</Link>
            <Link href="/terms" className="hover:text-slate-400 transition-colors">Terms</Link>
            <Link href="/login" className="hover:text-slate-400 transition-colors">Login</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
