import { NextRequest, NextResponse } from 'next/server';
import { getStorageComparison } from '@/services/dashboard';
import { Provider, Region } from '@/types';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const providers = searchParams.getAll('providers') as Provider[];
    const regions = searchParams.getAll('regions') as Region[];
    const limit = parseInt(searchParams.get('limit') || '30', 10);

    const data = await getStorageComparison(
      providers.length > 0 ? providers : undefined,
      regions.length > 0 ? regions : undefined,
      limit
    );

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching storage comparison data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch storage comparison data' },
      { status: 500 }
    );
  }
}

export const dynamic = 'force-dynamic'; 