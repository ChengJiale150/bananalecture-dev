import { NextResponse } from 'next/server';

export async function GET() {
  const basePath = process.env.RUNTIME_BASE_PATH || '';
  return NextResponse.json({ basePath });
}
