import { NextRequest, NextResponse } from 'next/server';
import { getVMComparison } from '@/services/dashboard';
import { Provider, Region } from '@/types';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const providers = searchParams.getAll('providers') as Provider[];
    const regions = searchParams.getAll('regions') as Region[];
    const limit = parseInt(searchParams.get('limit') || '50', 10);

    const data = await getVMComparison(
      providers.length > 0 ? providers : undefined,
      regions.length > 0 ? regions : undefined,
      limit
    );

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching VM comparison data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch VM comparison data' },
      { status: 500 }
    );
  }
}

export const dynamic = 'force-dynamic'; 