import './globals.css';
import { Inter } from 'next/font/google';
import Navbar from '@/components/Navbar';
import { createClient } from '@/lib/supabase-server';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'The Sun Room',
  description: 'Interactive Story Player',
  icons: {
    icon: '/sun.svg',
  },
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <Navbar /> {/* No longer passes user prop */}
          {children}
        </Providers>
      </body>
    </html>
  );
}
