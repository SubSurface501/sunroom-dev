import { createBrowserClient } from '@supabase/ssr';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error("CRITICAL: Supabase Env Vars missing in client!");
}

export const createClient = () =>
  createBrowserClient(
    supabaseUrl!,
    supabaseKey!
  );

// Singleton instance for simple usage
export const supabase = createClient();