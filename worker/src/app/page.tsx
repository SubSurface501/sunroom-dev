"use client";

import Link from "next/link";


export default function LandingPage() {

  return (
    <div className="flex flex-col min-h-screen bg-white text-gray-800">
      <header className="container mx-auto px-6 py-10 flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">The Sun Room</h1>
        <nav>
          <Link href="#vision" className="text-lg text-gray-600 hover:text-gray-900 mr-6">Vision</Link>
          <Link href="#founder" className="text-lg text-gray-600 hover:text-gray-900 mr-6">Founder</Link>
          <Link href="/mvp" className="text-lg text-gray-600 hover:text-gray-900">Login</Link>
        </nav>
      </header>

      <main className="flex-grow">
        <section id="hero" className="container mx-auto px-6 py-20 text-center">
          <h2 className="text-5xl font-extrabold mb-4">A Sanctuary for the Mind</h2>
          <p className="text-xl text-gray-600 mb-8">
            An intelligent research environment designed to transform how creators, scholars, and thinkers connect ideas.
          </p>
          <Link href="/mvp" className="bg-blue-600 text-white font-bold py-3 px-8 rounded-full hover:bg-blue-700">
            Get Started
          </Link>
        </section>

        <section id="vision" className="bg-gray-50 py-20">
          <div className="container mx-auto px-6">
            <h3 className="text-4xl font-bold text-center mb-12">The Sunroom: Your AI-Powered Knowledge Synthesis Lab</h3>
            <p className="text-lg text-gray-700 leading-relaxed text-left mb-16">
              The Sunroom is a scalable, AI-powered platform that moves beyond simple note-taking to become a true partner in knowledge synthesis. Built on a unique "Molecular Zettelkasten" methodology, it transforms your information into a dynamic network of interconnected insights. Here's how it works:
            </p>
            <div className="space-y-16">
              <div className="flex flex-col md:flex-row items-center">
                <div className="md:w-1/2 md:pr-12">
                  <h3 className="text-3xl font-bold mb-4">1. Capture</h3>
                  <p className="text-lg text-gray-700 leading-relaxed text-left">It begins with your ideas. Easily gather your notes, articles, and personal writings into one unified, intelligent space.</p>
                </div>
                <div className="md:w-1/2">
                  <img src="/images/mockup_1.jpg" alt="Sunroom capture interface for text, files, and web clipping" className="w-full h-auto rounded-lg shadow-lg" />
                </div>
              </div>
              <div className="flex flex-col md:flex-row-reverse items-center">
                <div className="md:w-1/2 md:pl-12">
                  <h3 className="text-3xl font-bold mb-4">2. Connect</h3>
                  <p className="text-lg text-gray-700 leading-relaxed text-left">Our multi-agent AI system reads and analyzes your content, deconstructing it into its fundamental concepts—the "atoms" of your knowledge. It then surfaces direct connections and their supporting evidence.</p>
                </div>
                <div className="md:w-1/2">
                  <img src="/images/mockup_2.jpg" alt="Search Dashboard showing AI-identified connections and scores" className="w-full h-auto rounded-lg shadow-lg" />
                </div>
              </div>
              <div className="flex flex-col md:flex-row items-center">
                <div className="md:w-1/2 md:pr-12">
                  <h3 className="text-3xl font-bold mb-4">3. Synthesize</h3>
                  <p className="text-lg text-gray-700 leading-relaxed text-left">The platform intelligently links these "atoms" to build complex "molecules" of understanding. This synthesis reveals the hidden architecture of your thoughts, surfacing novel patterns and allowing profound insights to emerge.</p>
                </div>
                <div className="md:w-1/2">
                  <img src="/images/mockup_3.jpg" alt="Graph Explorer showing a network of synthesized knowledge" className="w-full h-auto rounded-lg shadow-lg" />
                </div>
              </div>
              <div className="flex flex-col md:flex-row-reverse items-center">
                <div className="md:w-1/2 md:pl-12">
                  <h3 className="text-3xl font-bold mb-4">4. Refine</h3>
                  <p className="text-lg text-gray-700 leading-relaxed text-left">Dive deeper into insights. Pin promising connections, add your own annotations and notes, and leverage AI-generated briefings to build robust case files and validate your hypotheses with dedicated research tools.</p>
                </div>
                <div className="md:w-1/2">
                  <img src="/images/mockup_4.jpg" alt="Hypothesis Workbench for refining insights and creating case files" className="w-full h-auto rounded-lg shadow-lg" />
                </div>
              </div>
              <div className="flex flex-col md:flex-row items-center">
                <div className="md:w-1/2 md:pr-12">
                  <h3 className="text-3xl font-bold mb-4">5. Collaborate</h3>
                  <p className="text-lg text-gray-700 leading-relaxed text-left">Your refined "molecules" are brought into a shared knowledge graph. The Sunroom identifies and highlights complementary work from other users, connecting your insights to theirs and fostering collective discovery.</p>
                </div>
                <div className="md:w-1/2">
                  <img src="/images/mockup_5.jpg" alt="Collaborative Discovery screen showing shared user insights" className="w-full h-auto rounded-lg shadow-lg" />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="founder" className="py-20">
          <div className="container mx-auto px-6">
            <h3 className="text-4xl font-bold text-center mb-12">About the Founder</h3>
            <div className="flex flex-col md:flex-row items-center">
              <div className="md:w-1/3 mb-8 md:mb-0">
                <div className="h-64 w-64 mx-auto rounded-full overflow-hidden">
                  <img src="/images/Jacob-Headshot.jpg" alt="Jacob Elliott" className="w-full h-full object-cover" />
                </div>
              </div>              <div className="md:w-2/3 md:pl-12">
                <h4 className="text-3xl font-bold">Jacob Elliott, Founder & Lead Developer</h4>
                <p className="text-lg text-gray-700 leading-relaxed mt-4">
                  After a career in Mergers & Acquisitions, I transitioned into software development three years ago. This move was driven by a desire to work in a field that aligns with my greatest strengths—a passion for logic and systems, which stems in part from my experience with a non-verbal learning disorder. I build tools for thinkers, scholars, and creators who, like me, believe in the power of deep analysis to find meaning in a complex world.
                </p>                <h5 className="text-2xl font-bold mt-8 mb-4">Relevant Professional Experience:</h5>
                <ul className="list-disc list-inside space-y-2">
                  <li>Designed and prototyped a sophisticated multi-agent AI research system capable of performing complex data analysis and synthesis tasks (Project Valerius).</li>
                  <li>Developed the &quot;Molecular Zettelkasten&quot; methodology, the core conceptual and technical framework that powers The Sunroom.</li>
                  <li>Created multiple data-pipeline and analysis tools, including a Python-based &quot;Substack Retriever&quot; for data scraping and a &quot;Study Synthesis Lab&quot; for managing and connecting conceptual data.</li>
                </ul>
                <p className="text-lg text-gray-700 leading-relaxed mt-4">
                  Jacob is based in Brockville, Ontario, and is driven by a passion for building scalable technology that helps people think more deeply and creatively.
                </p>
              </div>
            </div>
          </div>
        </section>


      </main>

      <footer className="container mx-auto px-6 py-6 text-center text-gray-500">
        <p>&copy; 2025 The Sun Room. All Rights Reserved.</p>
      </footer>
    </div>
  );
}
