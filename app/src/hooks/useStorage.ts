import { useQuery } from "@tanstack/react-query";

interface StoragePricing {
  id: number;
  provider_name: string;
  service_name: string;
  storage_class: string;
  region: string;
  access_tier: string;
  capacity_price: number | null;
  read_price: number | null;
  write_price: number | null;
  flat_item_price: number | null;
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

interface StorageFilters {
  provider: string;
  region: string;
  storageClass: string;
  accessTier: string;
  minPrice: string;
  maxPrice: string;
}

interface StorageSorting {
  sortBy: string;
  sortOrder: "asc" | "desc";
}

interface StorageResponse {
  data: StoragePricing[];
  pagination: PaginationInfo;
}

const fetchStorageData = async (
  page: number,
  pageSize: number,
  filters: StorageFilters,
  sorting?: StorageSorting
): Promise<StorageResponse> => {
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

  const response = await fetch(`/api/storage?${params}`);
  if (!response.ok) {
    throw new Error("Failed to fetch storage data");
  }
  return response.json();
};

export const useStorage = (
  page: number,
  pageSize: number,
  filters: StorageFilters,
  sorting?: StorageSorting
) => {
  return useQuery({
    queryKey: ["storage", page, pageSize, filters, sorting],
    queryFn: () => fetchStorageData(page, pageSize, filters, sorting),
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
};

const fetchStorageFilters = async () => {
  const response = await fetch("/api/storage/filters");
  if (!response.ok) {
    throw new Error("Failed to fetch storage filters");
  }
  return response.json();
};

export const useStorageFilters = () => {
  return useQuery({
    queryKey: ["storage-filters"],
    queryFn: fetchStorageFilters,
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  });
};
