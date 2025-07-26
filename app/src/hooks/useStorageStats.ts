import { useQuery } from "@tanstack/react-query";

interface StorageFilters {
  provider?: string;
  region?: string;
  storageClass?: string;
  accessTier?: string;
  minPrice?: string;
  maxPrice?: string;
}

interface StorageStatsResponse {
  totalCount: number;
  capacityPriceStats: {
    avg: number;
    min: number;
    max: number;
  };
  readPriceStats: {
    avg: number;
    min: number;
    max: number;
  };
  writePriceStats: {
    avg: number;
    min: number;
    max: number;
  };
}

const fetchStorageStats = async (
  filters: StorageFilters
): Promise<StorageStatsResponse> => {
  const params = new URLSearchParams(
    Object.fromEntries(
      Object.entries(filters).filter(
        ([, value]) => value !== "" && value !== "all" && value !== undefined
      )
    )
  );

  const response = await fetch(`/api/storage/stats?${params}`);
  if (!response.ok) {
    throw new Error("Failed to fetch storage statistics");
  }
  return response.json();
};

export const useStorageStats = (filters: StorageFilters) => {
  return useQuery({
    queryKey: ["storage-stats", filters],
    queryFn: () => fetchStorageStats(filters),
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
};
