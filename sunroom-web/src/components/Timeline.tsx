'use client';
import { useState, useEffect } from 'react';
import { BarChart, Bar, Brush, ResponsiveContainer, XAxis, Tooltip } from 'recharts';
import { supabase } from '@/lib/supabase';

interface TimelineProps {
  selectedLenses: string[];
  onTimeRangeChange: (range: { start: string; end: string } | null) => void;
}

export default function TemporalResonanceTimeline({ selectedLenses, onTimeRangeChange }: TimelineProps) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchData() {
        setLoading(true);
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) return;

            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
            const query = selectedLenses.length > 0 ? `?lenses=${selectedLenses.join(',')}` : '';
            
            const res = await fetch(`${apiUrl}/api/v1/lenses/distribution${query}`, {
                headers: { 'Authorization': `Bearer ${session.access_token}` }
            });
            
            if (res.ok) {
                const result = await res.json();
                setData(result.distribution || []);
            }
        } catch (e) {
            console.error("Timeline fetch error:", e);
        } finally {
            setLoading(false);
        }
    }
    
    fetchData();
  }, [selectedLenses]);

  if (data.length === 0 && !loading) {
      return (
          <div className="w-full h-32 bg-gray-900 border border-gray-800 rounded-lg p-4 flex items-center justify-center">
              <p className="text-gray-600 text-xs uppercase tracking-widest">No temporal data found</p>
          </div>
      );
  }

  return (
    <div className="w-full h-auto min-h-[250px] bg-gray-800 border border-gray-700 rounded-lg p-4 shadow-inner">
      <div className="flex justify-between items-center mb-2">
        <div className="text-xs text-blue-400 font-bold uppercase tracking-widest flex items-center gap-2">
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
            Temporal Resonance
        </div>
        {loading && <span className="text-xs text-gray-500">Syncing...</span>}
      </div>
      
      <div className="w-full h-[200px]">
        <ResponsiveContainer width="99%" height="100%">
            <BarChart data={data}>
            <Tooltip 
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', color: '#fff' }}
                cursor={{fill: 'rgba(255, 255, 255, 0.1)'}}
            />
            <Bar 
                dataKey="count" 
                fill="#3b82f6" 
                radius={[2, 2, 0, 0]}
                className="transition-all duration-500"
                barSize={20}
            />
            <Brush 
                dataKey="month" 
                height={30} 
                stroke="#eab308" 
                fill="#1f2937"
                tickFormatter={(val) => val ? val.toString() : ''}
                onChange={(range) => {
                    if (range.startIndex !== undefined && range.endIndex !== undefined) {
                        const start = data[range.startIndex].month;
                        // For end date, we want the END of that month.
                        // Backend handles filtering simply by month string usually, 
                        // or we can construct ISO strings here.
                        // Let's send YYYY-MM-01 for start and YYYY-MM-31 for end logic
                        // But the backend logic uses >= and <= on TIMESTAMP.
                        // "2023-01" is not a timestamp. 
                        // Let's send just the YYYY-MM string and let backend parse? 
                        // Or construct ISO strings:
                        const endMonth = data[range.endIndex].month;
                        
                        // Construct full ISO dates for the backend filter
                        // Start: 1st of the month
                        const startDate = `${start}-01T00:00:00Z`;
                        
                        // End: Last day of the month (rough approx or calculated)
                        // Easiest: get 1st of next month and subtract 1 sec, or just send first of month and backend handles range.
                        // Let's make it simple: The backend logic is `created_at >= filter_start` and `<= filter_end`.
                        // If we pass 2023-01-01 for start, that works.
                        // If we pass 2023-01-01 for end, we miss everything in Jan.
                        // So we need to pass the LAST day/second of the end month.
                        
                        // Quick hack for end of month:
                        const [y, m] = endMonth.split('-');
                        const nextMonth = new Date(parseInt(y), parseInt(m), 1); // Month is 0-indexed in JS Date? No, in new Date(y, m, 1), m is 0-indexed.
                        // ParseInt("01") -> 1. So new Date(2023, 1, 1) is Feb 1st. Perfect.
                        const endTimestamp = new Date(nextMonth.getTime() - 1).toISOString();
                        
                        onTimeRangeChange({ start: startDate, end: endTimestamp });
                    } else {
                        onTimeRangeChange(null);
                    }
                }}
            />
            </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
