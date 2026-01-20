'use client';

import React from 'react';
import Link from 'next/link';

export default function KnowledgeGraphPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-950 text-white p-8">
      <h1 className="text-4xl font-bold mb-4">Your Personal Knowledge Graph</h1>
      <p className="text-lg text-gray-400 mb-8 text-center">
        Visualize the connections between your thoughts, sources, and creations.
        This feature is under active development!
      </p>
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 max-w-lg w-full text-center">
        <p className="text-gray-300">
          Stay tuned for updates as we build out this powerful visualization tool.
        </p>
        <Link href="/dashboard" className="mt-6 inline-flex items-center px-6 py-3 border border-purple-600 text-purple-300 bg-purple-900/30 hover:bg-purple-900/50 rounded-md text-base font-medium transition-colors">
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
