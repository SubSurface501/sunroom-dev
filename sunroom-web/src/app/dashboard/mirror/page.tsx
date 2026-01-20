'use client';
import PersonaEditor from '@/components/mirror/PersonaEditor';

export default function MirrorPage() {
    return (
        <div className="min-h-screen bg-gray-900 text-white p-6">
             <div className="max-w-4xl mx-auto">
                 <PersonaEditor />
             </div>
        </div>
    );
}
