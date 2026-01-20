import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  const supabaseUrl = process.env['NEXT_PUBLIC_SUPABASE_URL'];
  const supabaseKey = process.env['NEXT_PUBLIC_SUPABASE_ANON_KEY'];

  if (!supabaseUrl || !supabaseKey) {
    console.error('Middleware Error: Missing Supabase Environment Variables');
    console.error('URL:', supabaseUrl ? 'Defined' : 'Missing');
    console.error('Key:', supabaseKey ? 'Defined' : 'Missing');
    // Allow the request to proceed without Supabase logic if env vars are missing
    // This prevents the 500 error loop and allows us to see these logs
    return response;
  }

  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      get(name: string) {
        return request.cookies.get(name)?.value;
      },
      set(name: string, value: string, options) {
        // If the cookie is set, update the request cookies as well.
        request.cookies.set({
          name,
          value,
          ...options,
        });
        response = NextResponse.next({
          request: {
            headers: request.headers,
          },
        });
        response.cookies.set({
          name,
          value,
          ...options,
        });
      },
      remove(name: string, options) {
        // If the cookie is removed, update the request cookies as well.
        request.cookies.set({
          name,
          value: '',
          ...options,
        });
        response = NextResponse.next({
          request: {
            headers: request.headers,
          },
        });
        response.cookies.set({
          name,
          value: '',
          ...options,
        });
      },
    },
  });

  // IMPORTANT: Do not write any logic between createServerClient and
  // supabase.auth.getUser(). A simple mistake could make it very hard to debug
  // issues with users being randomly logged out.

  const { 
    data: { user }, 
  } = await supabase.auth.getUser();

  // Protected Routes Logic
  const publicPaths = ['/login', '/auth/callback'];
  const isPublic = publicPaths.some(path => request.nextUrl.pathname.startsWith(path));
  const isStatic = request.nextUrl.pathname.match(/_next|favicon.ico|worker|public/);

  if (!user && !isPublic && !isStatic && request.nextUrl.pathname !== '/') {
    // Allow "/" for now (StoryPlayer), but redirect Dashboard/etc
     if (request.nextUrl.pathname.startsWith('/dashboard')) {
        return NextResponse.redirect(new URL('/login', request.url));
     }
  }

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - worker/ (images)
     */
    '/((?!_next/static|_next/image|favicon.ico|worker/.*|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};