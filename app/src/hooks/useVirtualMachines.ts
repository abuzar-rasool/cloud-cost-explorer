import { useQuery } from "@tanstack/react-query";

interface VMPricing {
  id: number;
  vm_name: string;
  provider_name: string;
  virtual_cpu_count: number;
  memory_gb: number;
  cpu_arch: string;
  price_per_hour_usd: number;
  gpu_count: number;
  gpu_name: string | null;
  gpu_memory: number;
  os_type: string;
  region: string;
  other_details: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

interface PaginationInfo {
  page: number;
  limit: number;
  totalCount: number;
  totalPages: number;
  hasNextPage: boolean;
  hasPrevPage: boolean;
}

interface VMFilters {
  provider: string;
  region: string;
  osType: string;
  minPrice: string;
  maxPrice: string;
  minCpu: string;
  maxCpu: string;
  minMemory: string;
  maxMemory: string;
}

interface VMSorting {
  sortBy: string;
  sortOrder: "asc" | "desc";
}

interface VMResponse {
  data: VMPricing[];
  pagination: PaginationInfo;
}

const fetchVMData = async (
  page: number,
  pageSize: number,
  filters: VMFilters,
  sorting?: VMSorting
): Promise<VMResponse> => {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: pageSize.toString(),
    ...Object.fromEntries(
      Object.entries(filters).filter(
        ([, value]) => value !== "" && value !== "all"
      )
    ),
  });

  // Add sorting parameters
  if (sorting) {
    params.append("sortBy", sorting.sortBy);
    params.append("sortOrder", sorting.sortOrder);
  }

  console.log("Fetching VM data with params:", params.toString());
  const response = await fetch(`/api/virtual-machines?${params}`);
  if (!response.ok) {
    throw new Error("Failed to fetch VM data");
  }
  const data = await response.json();
  console.log("VM data received:", data);
  return data;
};

export const useVirtualMachines = (
  page: number,
  pageSize: number,
  filters: VMFilters,
  sorting?: VMSorting
) => {
  return useQuery({
    queryKey: ["virtual-machines", page, pageSize, filters, sorting],
    queryFn: () => fetchVMData(page, pageSize, filters, sorting),
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
};

const fetchVMFilters = async () => {
  const response = await fetch("/api/virtual-machines/filters");
  if (!response.ok) {
    throw new Error("Failed to fetch VM filters");
  }
  return response.json();
};

export const useVMFilters = () => {
  return useQuery({
    queryKey: ["vm-filters"],
    queryFn: fetchVMFilters,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  });
};
