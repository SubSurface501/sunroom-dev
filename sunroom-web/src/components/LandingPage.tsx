import Link from 'next/link';
import Image from 'next/image';

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen bg-white text-gray-800 font-sans">
      {/* Header */}
      <header className="container mx-auto px-6 py-8 flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">The Sun Room</h1>
        <nav className="flex gap-4">
          <Link 
            href="/login" 
            className="px-6 py-2 rounded-full bg-yellow-500 text-white font-medium hover:bg-yellow-600 transition-colors"
          >
            Sign In
          </Link>
        </nav>
      </header>

      <main className="flex-grow">
        {/* Hero Section */}
        <section className="container mx-auto px-6 py-20 text-center lg:text-left lg:flex lg:items-center lg:justify-between">
          <div className="lg:w-1/2">
            <h2 className="text-5xl lg:text-6xl font-extrabold text-gray-900 leading-tight mb-6">
              Curated Connections for <span className="text-yellow-500">Intelligent Research</span>.
            </h2>
            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
              Transform how creators, scholars, and thinkers connect ideas. 
              Capture notes, synthesize knowledge, and refine insights with an AI partner that truly understands your library.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <Link 
                href="/login" 
                className="px-8 py-4 bg-gray-900 text-white text-lg font-semibold rounded-lg hover:bg-gray-800 transition-colors shadow-lg"
              >
                Get Started
              </Link>
            </div>
          </div>
          <div className="lg:w-1/2 mt-12 lg:mt-0 relative">
            <div className="relative w-full h-[400px] lg:h-[500px]">
               {/* Hero Image / Mockup 1 */}
               <Image 
                 src="/images/mockup_1.jpg" 
                 alt="Sun Room Interface" 
                 fill
                 className="object-contain"
                 priority
               />
            </div>
          </div>
        </section>

        {/* Features / Mockups Grid */}
        <section className="bg-gray-50 py-20">
          <div className="container mx-auto px-6">
            <h3 className="text-3xl font-bold text-center text-gray-900 mb-12">See Your Mind at Work</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
               <div className="space-y-6">
                 <div className="relative h-64 w-full bg-white rounded-lg shadow-md overflow-hidden">
                    <Image src="/images/mockup_2.jpg" alt="Feature 1" fill className="object-cover" />
                 </div>
                 <h4 className="text-2xl font-bold text-gray-800">Visual Knowledge Graph</h4>
                 <p className="text-gray-600">Navigate your thoughts spatially. See connections you didn't know existed.</p>
               </div>
               <div className="space-y-6">
                 <div className="relative h-64 w-full bg-white rounded-lg shadow-md overflow-hidden">
                    <Image src="/images/mockup_3.jpg" alt="Feature 2" fill className="object-cover" />
                 </div>
                 <h4 className="text-2xl font-bold text-gray-800">AI-Powered Synthesis</h4>
                 <p className="text-gray-600">Turn scattered notes into cohesive narratives with our energy-based reasoning engine.</p>
               </div>
               <div className="space-y-6">
                 <div className="relative h-64 w-full bg-white rounded-lg shadow-md overflow-hidden">
                    <Image src="/images/mockup_4.jpg" alt="Feature 3" fill className="object-cover" />
                 </div>
                 <h4 className="text-2xl font-bold text-gray-800">Deep Search</h4>
                 <p className="text-gray-600">Find exactly what you need, even if you forgot the keywords.</p>
               </div>
               <div className="space-y-6">
                 <div className="relative h-64 w-full bg-white rounded-lg shadow-md overflow-hidden">
                    <Image src="/images/mockup_5.jpg" alt="Feature 4" fill className="object-cover" />
                 </div>
                 <h4 className="text-2xl font-bold text-gray-800">Collaborative Intelligence</h4>
                 <p className="text-gray-600">Work with your team in a shared cognitive space.</p>
               </div>
            </div>
          </div>
        </section>

        {/* Founder Section */}
        <section className="container mx-auto px-6 py-20">
          <div className="flex flex-col md:flex-row items-center gap-12 bg-gray-900 rounded-2xl p-10 text-white shadow-xl">
            <div className="w-full md:w-1/3 relative h-80 rounded-xl overflow-hidden">
               <Image 
                 src="/images/Jacob-Headshot.jpg" 
                 alt="Jacob Elliott" 
                 fill
                 className="object-cover"
               />
            </div>
            <div className="w-full md:w-2/3">
              <h3 className="text-3xl font-bold mb-4 text-yellow-500">Meet the Founder</h3>
              <p className="text-lg leading-relaxed mb-6 text-gray-300">
                Jacob Elliott is building the future of augmented cognition. 
                With a background in research and systems engineering, he designed The Sun Room 
                to bridge the gap between human creativity and machine intelligence.
              </p>
              <p className="font-semibold">Jacob Elliott</p>
              <p className="text-sm text-gray-400">Founder, The Sun Room</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-gray-100 py-10">
        <div className="container mx-auto px-6 text-center text-gray-500">
          &copy; {new Date().getFullYear()} The Sun Room. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
