import { NextResponse } from 'next/server';
import { prisma } from '@/lib/db';

// Map enum values to display names
const REGION_DISPLAY_NAMES: Record<string, string> = {
  north_america: "North America",
  south_america: "South America",
  europe: "Europe",
  asia: "Asia",
  africa: "Africa",
  oceania: "Oceania",
  antarctica: "Antarctica"
};

// Define types for our pricing data
interface RegionalPricingItem {
  provider: string;
  region: string;
  avg_price: string;
}

interface FormattedRegionData {
  region: string;
  aws_price: number;
  azure_price: number;
  gcp_price: number;
  count: number;
}

export async function GET() {
  try {
    // Get all pricing data grouped by provider and region
    const regionalPricingData = await prisma.$queryRaw`
      SELECT 
        provider_name::text as provider,
        region::text as region,
        ROUND(AVG(price_per_hour_usd)::numeric, 4) as avg_price
      FROM "public"."on-demand-vm-pricing"
      GROUP BY provider_name, region
      ORDER BY region, provider_name
    `;

    // Group pricing by region
    const pricingByRegion = (regionalPricingData as RegionalPricingItem[]).reduce<Record<string, FormattedRegionData>>((acc, item) => {
      if (!acc[item.region]) {
        acc[item.region] = {
          region: REGION_DISPLAY_NAMES[item.region] || item.region,
          aws_price: 0,
          azure_price: 0,
          gcp_price: 0,
          count: 0
        };
      }
      
      if (item.provider.toLowerCase() === 'aws') {
        acc[item.region].aws_price = parseFloat(item.avg_price);
        acc[item.region].count++;
      } else if (item.provider.toLowerCase() === 'azure') {
        acc[item.region].azure_price = parseFloat(item.avg_price);
        acc[item.region].count++;
      } else if (item.provider.toLowerCase() === 'gcp') {
        acc[item.region].gcp_price = parseFloat(item.avg_price);
        acc[item.region].count++;
      }
      
      return acc;
    }, {});
    
    // Convert to array and sort by count descending to get most represented regions first
    // then filter to only include regions with data from at least 2 providers
    const formattedData = Object.values(pricingByRegion)
      .filter((item: FormattedRegionData) => item.count >= 2)
      .sort((a: FormattedRegionData, b: FormattedRegionData) => b.count - a.count)
      .slice(0, 5);
    
    return NextResponse.json(formattedData);
  } catch (error) {
    console.error('Error fetching regional VM pricing data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch regional VM pricing data' },
      { status: 500 }
    );
  }
} 