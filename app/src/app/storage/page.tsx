"use client";

import { useState, useEffect } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Navigation } from "@/components/dashboard/navigation";
import {
  Filter,
  Database,
  HardDrive,
  DollarSign,
  Globe,
  Layers,
} from "lucide-react";
import { useStorage, useStorageFilters } from "@/hooks/useStorage";
import { useStorageStats } from "@/hooks/useStorageStats";

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

const columns: ColumnDef<StoragePricing>[] = [
  {
    accessorKey: "service_name",
    header: "Service Name",
    cell: ({ row }) => (
      <div className="font-medium">{row.getValue("service_name")}</div>
    ),
  },
  {
    accessorKey: "provider_name",
    header: "Provider",
    cell: ({ row }) => (
      <div className="flex items-center">
        <Database className="mr-2 h-4 w-4" />
        {row.getValue("provider_name")}
      </div>
    ),
  },
  {
    accessorKey: "storage_class",
    header: "Storage Class",
    cell: ({ row }) => (
      <div className="flex items-center">
        <Layers className="mr-2 h-4 w-4" />
        {row.getValue("storage_class")}
      </div>
    ),
  },
  {
    accessorKey: "capacity_price",
    header: "Capacity Price (USD/GB)",
    cell: ({ row }) => {
      const price = row.getValue("capacity_price") as number | null;
      return (
        <div className="flex items-center">
          <DollarSign className="mr-2 h-4 w-4" />
          {price !== null ? `$${price.toFixed(6)}` : "N/A"}
        </div>
      );
    },
  },
  {
    accessorKey: "region",
    header: "Region",
    cell: ({ row }) => (
      <div className="flex items-center">
        <Globe className="mr-2 h-4 w-4" />
        {row.getValue("region")}
      </div>
    ),
  },
  {
    accessorKey: "access_tier",
    header: "Access Tier",
    cell: ({ row }) => (
      <div className="flex items-center">
        <HardDrive className="mr-2 h-4 w-4" />
        {row.getValue("access_tier")}
      </div>
    ),
  },
  {
    accessorKey: "read_price",
    header: "Read Price (USD/1K)",
    cell: ({ row }) => {
      const price = row.getValue("read_price") as number | null;
      return price !== null ? `$${price.toFixed(6)}` : "N/A";
    },
  },
  {
    accessorKey: "write_price",
    header: "Write Price (USD/1K)",
    cell: ({ row }) => {
      const price = row.getValue("write_price") as number | null;
      return price !== null ? `$${price.toFixed(6)}` : "N/A";
    },
  },
];

export default function StoragePage() {
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    limit: 10,
    totalCount: 0,
    totalPages: 0,
    hasNextPage: false,
    hasPrevPage: false,
  });
  const [filters, setFilters] = useState({
    provider: "all",
    region: "all",
    storageClass: "all",
    accessTier: "all",
    minPrice: "",
    maxPrice: "",
  });
  const [sorting, setSorting] = useState({
    sortBy: "capacity_price",
    sortOrder: "asc" as "asc" | "desc",
  });

  // React Query hooks
  const {
    data: storageData,
    error,
    isLoading,
  } = useStorage(pagination.page, pagination.limit, filters, sorting);
  const { data: filterOptions, isLoading: filtersLoading } =
    useStorageFilters();
  const { data: globalStats, isLoading: statsLoading } =
    useStorageStats(filters);

  // Update pagination when data changes
  useEffect(() => {
    if (storageData?.pagination) {
      setPagination(storageData.pagination);
    }
  }, [storageData?.pagination]);

  // Calculate stats from global data
  const stats = (() => {
    if (!globalStats) {
      return {
        totalServices: storageData?.pagination?.totalCount || 0,
        avgPrice: 0,
        minPrice: 0,
        maxPrice: 0,
        activeFilters: Object.values(filters).filter(
          (v) => v !== "" && v !== "all"
        ).length,
      };
    }

    const activeFilters = Object.values(filters).filter(
      (v) => v !== "" && v !== "all"
    ).length;

    return {
      totalServices: globalStats.totalCount,
      avgPrice: globalStats.capacityPriceStats.avg,
      minPrice: globalStats.capacityPriceStats.min,
      maxPrice: globalStats.capacityPriceStats.max,
      activeFilters,
    };
  })();

  const handlePageChange = (page: number) => {
    setPagination((prev) => ({ ...prev, page }));
  };

  const handlePageSizeChange = (size: number) => {
    setPagination((prev) => ({
      ...prev,
      page: 1,
      limit: size,
    }));
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPagination((prev) => ({ ...prev, page: 1 })); // Reset to first page when filtering
  };

  const handleSortingChange = (sortBy: string, sortOrder: "asc" | "desc") => {
    setSorting({ sortBy, sortOrder });
    setPagination((prev) => ({ ...prev, page: 1 })); // Reset to first page when sorting
  };

  const clearFilters = () => {
    setFilters({
      provider: "all",
      region: "all",
      storageClass: "all",
      accessTier: "all",
      minPrice: "",
      maxPrice: "",
    });
    setPagination((prev) => ({ ...prev, page: 1 }));
  };

  if (error) {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <Navigation />
        <div className="container mx-auto px-4 py-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold mb-4">Error Loading Data</h1>
            <p className="text-muted-foreground">
              {error instanceof Error ? error.message : "An error occurred"}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <div className="px-6 pb-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-medium text-foreground">
              Storage Pricing
            </h1>
            <p className="text-muted-foreground mt-2">
              Compare storage pricing across cloud providers
            </p>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">
                    Total Services
                  </p>
                  <p className="text-2xl font-bold text-foreground">
                    {stats.totalServices}
                  </p>
                </div>
                <Database className="h-8 w-8 text-primary" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Avg Price/GB</p>
                  <p className="text-2xl font-bold text-foreground">
                    ${stats.avgPrice.toFixed(6)}
                  </p>
                </div>
                <DollarSign className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Min Price/GB</p>
                  <p className="text-2xl font-bold text-foreground">
                    ${stats.minPrice.toFixed(6)}
                  </p>
                </div>
                <DollarSign className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Max Price/GB</p>
                  <p className="text-2xl font-bold text-foreground">
                    ${stats.maxPrice.toFixed(6)}
                  </p>
                </div>
                <DollarSign className="h-8 w-8 text-destructive" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">
                    Active Filters
                  </p>
                  <p className="text-2xl font-bold text-foreground">
                    {stats.activeFilters}
                  </p>
                </div>
                <Filter className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="bg-card border-border mb-8">
          <CardHeader>
            <CardTitle className="flex items-center text-foreground">
              <Filter className="mr-2 h-5 w-5" />
              Filters
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {filtersLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="text-foreground flex items-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mr-3"></div>
                  Loading filters...
                </div>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2 text-foreground">
                      Provider
                    </label>
                    <Select
                      value={filters.provider}
                      onValueChange={(value) =>
                        handleFilterChange("provider", value)
                      }
                    >
                      <SelectTrigger className="bg-input border-border text-foreground">
                        <SelectValue placeholder="All Providers" />
                      </SelectTrigger>
                      <SelectContent className="bg-popover border-border">
                        <SelectItem value="all">All Providers</SelectItem>
                        {filterOptions?.providers?.map((provider: string) => (
                          <SelectItem key={provider} value={provider}>
                            {provider}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2 text-foreground">
                      Region
                    </label>
                    <Select
                      value={filters.region}
                      onValueChange={(value) =>
                        handleFilterChange("region", value)
                      }
                    >
                      <SelectTrigger className="bg-input border-border text-foreground">
                        <SelectValue placeholder="All Regions" />
                      </SelectTrigger>
                      <SelectContent className="bg-popover border-border">
                        <SelectItem value="all">All Regions</SelectItem>
                        {filterOptions?.regions?.map((region: string) => (
                          <SelectItem key={region} value={region}>
                            {region}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2 text-foreground">
                      Storage Class
                    </label>
                    <Select
                      value={filters.storageClass}
                      onValueChange={(value) =>
                        handleFilterChange("storageClass", value)
                      }
                    >
                      <SelectTrigger className="bg-input border-border text-foreground">
                        <SelectValue placeholder="All Storage Classes" />
                      </SelectTrigger>
                      <SelectContent className="bg-popover border-border">
                        <SelectItem value="all">All Storage Classes</SelectItem>
                        {filterOptions?.storageClasses?.map(
                          (storageClass: string) => (
                            <SelectItem key={storageClass} value={storageClass}>
                              {storageClass}
                            </SelectItem>
                          )
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2 text-foreground">
                      Access Tier
                    </label>
                    <Select
                      value={filters.accessTier}
                      onValueChange={(value) =>
                        handleFilterChange("accessTier", value)
                      }
                    >
                      <SelectTrigger className="bg-input border-border text-foreground">
                        <SelectValue placeholder="All Access Tiers" />
                      </SelectTrigger>
                      <SelectContent className="bg-popover border-border">
                        <SelectItem value="all">All Access Tiers</SelectItem>
                        {filterOptions?.accessTiers?.map(
                          (accessTier: string) => (
                            <SelectItem key={accessTier} value={accessTier}>
                              {accessTier}
                            </SelectItem>
                          )
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2 text-foreground">
                      Min Price/GB (USD)
                    </label>
                    <input
                      type="number"
                      step="0.000001"
                      value={filters.minPrice}
                      onChange={(e) =>
                        handleFilterChange("minPrice", e.target.value)
                      }
                      className="w-full px-3 py-2 bg-input border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-ring text-foreground placeholder:text-muted-foreground"
                      placeholder="0.000000"
                    />
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2 text-foreground">
                      Max Price/GB (USD)
                    </label>
                    <input
                      type="number"
                      step="0.000001"
                      value={filters.maxPrice}
                      onChange={(e) =>
                        handleFilterChange("maxPrice", e.target.value)
                      }
                      className="w-full px-3 py-2 bg-input border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-ring text-foreground placeholder:text-muted-foreground"
                      placeholder="1.000000"
                    />
                  </div>
                </div>

                <div className="flex justify-end p-6 border-t border-border">
                  <Button
                    onClick={clearFilters}
                    variant="outline"
                    className="border-border text-foreground hover:bg-accent"
                  >
                    Clear All Filters
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Data Table */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="text-foreground">
              Storage Service Pricing
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading || statsLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="text-white flex items-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white mr-3"></div>
                  Loading storage data...
                </div>
              </div>
            ) : error ? (
              <div className="text-center text-red-400">
                Error loading data. Please try again.
              </div>
            ) : (
              <DataTable
                columns={columns}
                data={storageData?.data || []}
                pagination={{
                  pageIndex: Math.max(0, (pagination.page || 1) - 1),
                  pageSize: pagination.limit || 10,
                  pageCount: Math.max(1, pagination.totalPages || 0),
                  totalCount: pagination.totalCount || 0,
                  hasNextPage: pagination.hasNextPage || false,
                  hasPrevPage: pagination.hasPrevPage || false,
                  onPageChange: (pageIndex) =>
                    handlePageChange(Math.max(1, pageIndex + 1)),
                  onPageSizeChange: handlePageSizeChange,
                }}
                sorting={{
                  sortBy: sorting.sortBy,
                  sortOrder: sorting.sortOrder,
                  onSortingChange: handleSortingChange,
                }}
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
