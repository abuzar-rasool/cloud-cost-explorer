import { NextResponse } from 'next/server';
import { getProviderStats } from '@/services/dashboard';

export async function GET() {
  try {
    const data = await getProviderStats();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching provider stats:', error);
    return NextResponse.json(
      { error: 'Failed to fetch provider stats' },
      { status: 500 }
    );
  }
}

export const dynamic = 'force-dynamic'; 