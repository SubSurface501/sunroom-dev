'use client';
import ReactMarkdown from 'react-markdown';
import { X, BookOpen, Download } from 'lucide-react';

interface VolumeReaderProps {
  content: string;
  title: string;
  onClose: () => void;
}

export default function VolumeReader({ content, title, onClose }: VolumeReaderProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-white text-gray-900 w-full max-w-4xl h-[90vh] rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in duration-200">
        
        {/* Header */}
        <div className="border-b px-6 py-4 flex justify-between items-center bg-gray-50">
          <div className="flex items-center gap-3">
            <BookOpen className="w-5 h-5 text-indigo-600" />
            <h2 className="font-serif text-xl font-bold truncate max-w-md">{title}</h2>
          </div>
          <div className="flex gap-2">
            <button className="p-2 hover:bg-gray-200 rounded-full transition-colors" title="Download Markdown">
                <Download className="w-5 h-5 text-gray-600" />
            </button>
            <button onClick={onClose} className="p-2 hover:bg-red-100 hover:text-red-600 rounded-full transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content - Typography Pro */}
        <div className="flex-1 overflow-y-auto p-8 md:p-12 prose prose-lg prose-indigo max-w-none">
          <ReactMarkdown 
            components={{
              h1: ({node, ...props}) => <h1 className="font-serif text-4xl mb-6 text-indigo-900 border-b pb-4" {...props} />,
              h2: ({node, ...props}) => <h2 className="font-serif text-2xl mt-8 mb-4 text-gray-800" {...props} />,
              p: ({node, ...props}) => <p className="leading-relaxed text-gray-700 mb-4" {...props} />,
              blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-indigo-300 pl-4 italic bg-gray-50 py-2 pr-4 rounded-r" {...props} />
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
