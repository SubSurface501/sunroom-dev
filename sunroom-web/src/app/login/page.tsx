'use client';

import { useState } from 'react';
import { login, signup } from './actions';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleAction = async (formData: FormData, isLogin: boolean) => {
    setLoading(true);
    setMessage('');
    
    // Append current state to formData if not already there (though form inputs usually handle it)
    // We will construct a new FormData to be safe or just let the form do it.
    // Actually, better to just pass the FormData from the event if we used <form action={...}>
    // But we want two buttons.
    
    const result = isLogin ? await login(formData) : await signup(formData);

    if (result?.error) {
      setMessage(result.error);
    } else if (result && 'message' in result) {
      setMessage((result as any).message);
    }
    // If login success, it redirects, so no need to set loading false really.
    setLoading(false);
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white p-4">
      <div className="w-full max-w-md bg-gray-800 rounded-lg shadow-lg p-8 space-y-6">
        <h2 className="text-3xl font-bold text-center text-yellow-500">The Sun Room</h2>
        <p className="text-center text-gray-400">Sign in or create an account</p>

        <form className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-300">Email</label>
            <input
              type="email"
              name="email"
              id="email"
              className="mt-1 block w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-yellow-500 focus:border-yellow-500 sm:text-sm text-white"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-300">Password</label>
            <input
              type="password"
              name="password"
              id="password"
              className="mt-1 block w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-yellow-500 focus:border-yellow-500 sm:text-sm text-white"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          <button
            formAction={(formData) => handleAction(formData, true)}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-black bg-yellow-500 hover:bg-yellow-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500"
            disabled={loading}
          >
            {loading ? 'Processing...' : 'Sign In'}
          </button>

          <p className="text-center text-gray-400 pt-2">Don't have an account?</p>
          <button
            formAction={(formData) => handleAction(formData, false)}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
            disabled={loading}
          >
            Sign Up
          </button>
        </form>

        {message && (
          <p className="mt-4 text-center text-sm font-medium text-yellow-400 break-words">
            {message}
          </p>
        )}
      </div>
    </div>
  );
}
