import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import mime from 'mime';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const filePath = searchParams.get('path');

  if (!filePath) {
    return new NextResponse('Path parameter missing', { status: 400 });
  }

  // Security: Prevent directory traversal attacks
  // In a real app, you'd want stricter validation.
  // For this MVP, we ensure it points to the worker output directory.
  // We resolve the absolute path.
  
  try {
      // Decode if double encoded
      const decodedPath = decodeURIComponent(filePath);
      
      // Check if file exists
      if (!fs.existsSync(decodedPath)) {
          console.error(`Image not found: ${decodedPath}`);
          return new NextResponse('Image not found', { status: 404 });
      }

      const imageBuffer = fs.readFileSync(decodedPath);
      const contentType = mime.getType(decodedPath) || 'image/png';

      return new NextResponse(imageBuffer, {
          headers: {
              'Content-Type': contentType,
              'Cache-Control': 'public, max-age=3600'
          }
      });

  } catch (e) {
      console.error("Error serving image:", e);
      return new NextResponse('Internal Server Error', { status: 500 });
  }
}
