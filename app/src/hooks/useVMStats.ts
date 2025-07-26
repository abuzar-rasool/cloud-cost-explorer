import { useQuery } from "@tanstack/react-query";

interface VMFilters {
  provider?: string;
  region?: string;
  osType?: string;
  minPrice?: string;
  maxPrice?: string;
  minCpu?: string;
  maxCpu?: string;
  minMemory?: string;
  maxMemory?: string;
}

interface VMStatsResponse {
  totalCount: number;
  priceStats: {
    avg: number;
    min: number;
    max: number;
  };
  cpuStats: {
    avg: number;
    min: number;
    max: number;
  };
  memoryStats: {
    avg: number;
    min: number;
    max: number;
  };
}

const fetchVMStats = async (filters: VMFilters): Promise<VMStatsResponse> => {
  const params = new URLSearchParams(
    Object.fromEntries(
      Object.entries(filters).filter(
        ([, value]) => value !== "" && value !== "all" && value !== undefined
      )
    )
  );

  const response = await fetch(`/api/virtual-machines/stats?${params}`);
  if (!response.ok) {
    throw new Error("Failed to fetch VM statistics");
  }
  return response.json();
};

export const useVMStats = (filters: VMFilters) => {
  return useQuery({
    queryKey: ["vm-stats", filters],
    queryFn: () => fetchVMStats(filters),
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
};
