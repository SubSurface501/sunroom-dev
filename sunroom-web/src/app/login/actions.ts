'use server';

import { createClient } from '@/lib/supabase-server';
import { redirect } from 'next/navigation';

export async function login(formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  
  console.log("Server Action: Attempting login for", email);
  
  try {
    const supabase = await createClient();
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      console.error("Supabase Auth Error:", error);
      return { error: error.message };
    }
  } catch (e) {
    console.error("Server Action Exception:", e);
    return { error: 'Connection failed' };
  }

  redirect('/dashboard');
}

export async function signup(formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  const supabase = await createClient();

  // Need to define the URL for redirection after email confirmation
  // const origin = headers().get('origin'); // Can't use in server action easily sometimes, hardcode for now
  const origin = 'http://localhost:3000';

  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: `${origin}/auth/callback`,
    },
  });

  if (error) {
    return { error: error.message };
  }

  return { message: 'Check email to continue sign in process' };
}
