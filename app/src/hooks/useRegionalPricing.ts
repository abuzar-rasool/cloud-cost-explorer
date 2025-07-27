import { useQuery } from '@tanstack/react-query';

export interface RegionPriceData {
  region: string;
  aws_price: number;
  azure_price: number;
  gcp_price: number;
}

async function fetchRegionalPricing(): Promise<RegionPriceData[]> {
  const response = await fetch('/api/dashboard/regional-pricing');
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch regional pricing data: ${response.status} ${errorText}`);
  }
  
  return response.json();
}

export function useRegionalPricing() {
  return useQuery({
    queryKey: ['regionalPricing'],
    queryFn: fetchRegionalPricing,
    refetchOnWindowFocus: false,
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
    staleTime: 5 * 60 * 1000, // Data is considered fresh for 5 minutes
  });
} 