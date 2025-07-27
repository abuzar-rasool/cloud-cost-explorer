import { useQuery } from "@tanstack/react-query";
import { Provider, Region, ProviderStats, VMComparisonData, StorageComparisonData } from "@/types";

// Function to fetch provider stats
const fetchProviderStats = async (): Promise<ProviderStats[]> => {
  const response = await fetch('/api/dashboard/provider-stats');
  if (!response.ok) {
    throw new Error('Failed to fetch provider stats');
  }
  return response.json();
};

// Function to fetch VM comparison data
const fetchVMComparison = async (
  providers?: Provider[],
  regions?: Region[],
  limit: number = 50
): Promise<VMComparisonData[]> => {
  const params = new URLSearchParams({ limit: limit.toString() });
  
  if (providers && providers.length > 0) {
    providers.forEach(provider => params.append('providers', provider));
  }
  
  if (regions && regions.length > 0) {
    regions.forEach(region => params.append('regions', region));
  }
  
  const response = await fetch(`/api/dashboard/vm-comparison?${params}`);
  if (!response.ok) {
    throw new Error('Failed to fetch VM comparison data');
  }
  return response.json();
};

// Function to fetch storage comparison data
const fetchStorageComparison = async (
  providers?: Provider[],
  regions?: Region[],
  limit: number = 30
): Promise<StorageComparisonData[]> => {
  const params = new URLSearchParams({ limit: limit.toString() });
  
  if (providers && providers.length > 0) {
    providers.forEach(provider => params.append('providers', provider));
  }
  
  if (regions && regions.length > 0) {
    regions.forEach(region => params.append('regions', region));
  }
  
  const response = await fetch(`/api/dashboard/storage-comparison?${params}`);
  if (!response.ok) {
    throw new Error('Failed to fetch storage comparison data');
  }
  return response.json();
};

// Hook for provider stats
export const useProviderStats = () => {
  return useQuery({
    queryKey: ['provider-stats'],
    queryFn: fetchProviderStats,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
};

// Hook for VM comparison data
export const useVMComparisonData = (
  providers?: Provider[],
  regions?: Region[],
  limit: number = 50
) => {
  return useQuery({
    queryKey: ['vm-comparison', providers, regions, limit],
    queryFn: () => fetchVMComparison(providers, regions, limit),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
};

// Hook for storage comparison data
export const useStorageComparisonData = (
  providers?: Provider[],
  regions?: Region[],
  limit: number = 30
) => {
  return useQuery({
    queryKey: ['storage-comparison', providers, regions, limit],
    queryFn: () => fetchStorageComparison(providers, regions, limit),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}; 