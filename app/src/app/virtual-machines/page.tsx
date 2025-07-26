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
  Server,
  Cpu,
  HardDrive,
  DollarSign,
  Globe,
  Monitor,
} from "lucide-react";
import { useVirtualMachines, useVMFilters } from "@/hooks/useVirtualMachines";
import { useVMStats } from "@/hooks/useVMStats";

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

const columns: ColumnDef<VMPricing>[] = [
  {
    accessorKey: "vm_name",
    header: "VM Name",
    cell: ({ row }) => (
      <div className="font-medium">{row.getValue("vm_name")}</div>
    ),
  },
  {
    accessorKey: "provider_name",
    header: "Provider",
    cell: ({ row }) => (
      <div className="flex items-center">
        <Server className="mr-2 h-4 w-4" />
        {row.getValue("provider_name")}
      </div>
    ),
  },
  {
    accessorKey: "virtual_cpu_count",
    header: "vCPU",
    cell: ({ row }) => (
      <div className="flex items-center">
        <Cpu className="mr-2 h-4 w-4" />
        {row.getValue("virtual_cpu_count")}
      </div>
    ),
  },
  {
    accessorKey: "memory_gb",
    header: "Memory (GB)",
    cell: ({ row }) => (
      <div className="flex items-center">
        <HardDrive className="mr-2 h-4 w-4" />
        {row.getValue("memory_gb")}
      </div>
    ),
  },
  {
    accessorKey: "price_per_hour_usd",
    header: "Price/Hour (USD)",
    cell: ({ row }) => (
      <div className="flex items-center">
        <DollarSign className="mr-2 h-4 w-4" />$
        {(row.getValue("price_per_hour_usd") as number).toFixed(4)}
      </div>
    ),
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
    accessorKey: "os_type",
    header: "OS Type",
    cell: ({ row }) => (
      <div className="flex items-center">
        <Monitor className="mr-2 h-4 w-4" />
        {row.getValue("os_type")}
      </div>
    ),
  },
  {
    accessorKey: "gpu_count",
    header: "GPU Count",
    cell: ({ row }) => {
      const gpuCount = row.getValue("gpu_count") as number;
      return gpuCount > 0 ? gpuCount : "N/A";
    },
  },
];

export default function VirtualMachinesPage() {
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
    osType: "all",
    minPrice: "",
    maxPrice: "",
    minCpu: "",
    maxCpu: "",
    minMemory: "",
    maxMemory: "",
  });
  const [sorting, setSorting] = useState({
    sortBy: "price_per_hour_usd",
    sortOrder: "asc" as "asc" | "desc",
  });

  // React Query hooks
  const {
    data: vmData,
    error,
    isLoading,
  } = useVirtualMachines(pagination.page, pagination.limit, filters, sorting);
  const { data: filterOptions, isLoading: filtersLoading } = useVMFilters();
  const { data: globalStats, isLoading: statsLoading } = useVMStats(filters);

  // Update pagination when data changes
  useEffect(() => {
    if (vmData?.pagination) {
      setPagination(vmData.pagination);
    }
  }, [vmData?.pagination]);

  // Calculate stats from global data
  const stats = (() => {
    if (!globalStats) {
      return {
        totalVMs: vmData?.pagination?.totalCount || 0,
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
      totalVMs: globalStats.totalCount,
      avgPrice: globalStats.priceStats.avg,
      minPrice: globalStats.priceStats.min,
      maxPrice: globalStats.priceStats.max,
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
      osType: "all",
      minPrice: "",
      maxPrice: "",
      minCpu: "",
      maxCpu: "",
      minMemory: "",
      maxMemory: "",
    });
    setPagination((prev) => ({ ...prev, page: 1 }));
  };

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white">
        <Navigation />
        <div className="container mx-auto px-4 py-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold mb-4">Error Loading Data</h1>
            <p className="text-gray-400">
              {error instanceof Error ? error.message : "An error occurred"}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black">
      <Navigation />
      <div className="px-6 pb-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-medium text-white">
              Virtual Machines
            </h1>
            <p className="text-white/70 mt-2">
              Compare VM pricing across cloud providers
            </p>
          </div>
        </div>

        {/* Stats Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="bg-white/5 backdrop-blur-sm border-white/10 hover:bg-white/10 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-white text-sm font-medium">
                Total Instances
              </CardTitle>
              <Server className="h-5 w-5 text-white/50" />
            </CardHeader>
            <CardContent className="pt-0 pb-4">
              <div className="text-3xl font-bold text-white mb-1">
                {stats.totalVMs.toLocaleString()}
              </div>
              <p className="text-xs text-white/50">VM instances available</p>
            </CardContent>
          </Card>

          <Card className="bg-white/5 backdrop-blur-sm border-white/10 hover:bg-white/10 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-white text-sm font-medium">
                Avg Price/Hour
              </CardTitle>
              <DollarSign className="h-5 w-5 text-white/50" />
            </CardHeader>
            <CardContent className="pt-0 pb-4">
              <div className="text-3xl font-bold text-white mb-1">
                ${stats.avgPrice.toFixed(3)}
              </div>
              <p className="text-xs text-white/50">Average cost per hour</p>
            </CardContent>
          </Card>

          <Card className="bg-white/5 backdrop-blur-sm border-white/10 hover:bg-white/10 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-white text-sm font-medium">
                Price Range
              </CardTitle>
              <Cpu className="h-5 w-5 text-white/50" />
            </CardHeader>
            <CardContent className="pt-0 pb-4">
              <div className="text-3xl font-bold text-white mb-1">
                ${stats.minPrice.toFixed(3)} - ${stats.maxPrice.toFixed(3)}
              </div>
              <p className="text-xs text-white/50">Min to max price</p>
            </CardContent>
          </Card>

          <Card className="bg-white/5 backdrop-blur-sm border-white/10 hover:bg-white/10 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-white text-sm font-medium">
                Active Filters
              </CardTitle>
              <Filter className="h-5 w-5 text-white/50" />
            </CardHeader>
            <CardContent className="pt-0 pb-4">
              <div className="text-3xl font-bold text-white mb-1">
                {stats.activeFilters}
              </div>
              <p className="text-xs text-white/50">Filters applied</p>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="bg-white/5 backdrop-blur-sm border-white/10 mb-6">
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <CardTitle className="text-white text-lg font-medium flex items-center">
              <Filter className="h-5 w-5 mr-2" />
              Advanced Filters
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
              className="text-white/50 hover:text-white p-1"
              disabled={filtersLoading}
            >
              Clear All
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            {filtersLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="text-white flex items-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white mr-3"></div>
                  Loading filters...
                </div>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
                  <div className="w-full">
                    <label className="text-sm text-white/70 mb-2 block flex items-center">
                      <Globe className="h-3 w-3 mr-1" />
                      Provider
                    </label>
                    <Select
                      value={filters.provider}
                      onValueChange={(value) =>
                        handleFilterChange("provider", value)
                      }
                    >
                      <SelectTrigger className="bg-white/5 border-white/10 text-white hover:bg-white/10 w-full">
                        <SelectValue placeholder="All providers" />
                      </SelectTrigger>
                      <SelectContent className="bg-white/10 border-white/20 backdrop-blur-sm">
                        <SelectItem value="all">All providers</SelectItem>
                        {filtersLoading ? (
                          <SelectItem value="loading" disabled>
                            Loading...
                          </SelectItem>
                        ) : (
                          filterOptions?.providers?.map((provider: string) => (
                            <SelectItem key={provider} value={provider}>
                              {provider}
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2">
                      Region
                    </label>
                    <Select
                      value={filters.region}
                      onValueChange={(value) =>
                        handleFilterChange("region", value)
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="All Regions" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Regions</SelectItem>
                        {filtersLoading ? (
                          <SelectItem value="loading" disabled>
                            Loading...
                          </SelectItem>
                        ) : (
                          filterOptions?.regions?.map((region: string) => (
                            <SelectItem key={region} value={region}>
                              {region}
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2">
                      OS Type
                    </label>
                    <Select
                      value={filters.osType}
                      onValueChange={(value) =>
                        handleFilterChange("osType", value)
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="All OS Types" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All OS Types</SelectItem>
                        {filtersLoading ? (
                          <SelectItem value="loading" disabled>
                            Loading...
                          </SelectItem>
                        ) : (
                          filterOptions?.osTypes?.map((osType: string) => (
                            <SelectItem key={osType} value={osType}>
                              {osType}
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2">
                      Min Price/Hour (USD)
                    </label>
                    <input
                      type="number"
                      step="0.0001"
                      value={filters.minPrice}
                      onChange={(e) =>
                        handleFilterChange("minPrice", e.target.value)
                      }
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="0.0000"
                    />
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2">
                      Max Price/Hour (USD)
                    </label>
                    <input
                      type="number"
                      step="0.0001"
                      value={filters.maxPrice}
                      onChange={(e) =>
                        handleFilterChange("maxPrice", e.target.value)
                      }
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="1.0000"
                    />
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2">
                      Min CPU Cores
                    </label>
                    <input
                      type="number"
                      value={filters.minCpu}
                      onChange={(e) =>
                        handleFilterChange("minCpu", e.target.value)
                      }
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="1"
                    />
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2">
                      Max CPU Cores
                    </label>
                    <input
                      type="number"
                      value={filters.maxCpu}
                      onChange={(e) =>
                        handleFilterChange("maxCpu", e.target.value)
                      }
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="32"
                    />
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2">
                      Min Memory (GB)
                    </label>
                    <input
                      type="number"
                      value={filters.minMemory}
                      onChange={(e) =>
                        handleFilterChange("minMemory", e.target.value)
                      }
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="1"
                    />
                  </div>

                  <div className="w-full">
                    <label className="block text-sm font-medium mb-2">
                      Max Memory (GB)
                    </label>
                    <input
                      type="number"
                      value={filters.maxMemory}
                      onChange={(e) =>
                        handleFilterChange("maxMemory", e.target.value)
                      }
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="128"
                    />
                  </div>
                </div>

                <div className="flex justify-end p-6 border-t border-gray-700">
                  <Button
                    onClick={clearFilters}
                    variant="outline"
                    className="border-gray-600 text-gray-300 hover:bg-gray-700"
                  >
                    Clear All Filters
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Data Table */}
        <Card className="bg-white/5 backdrop-blur-sm border-white/10">
          <CardContent className="p-6">
            {isLoading || statsLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="text-white flex items-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white mr-3"></div>
                  Loading VM data...
                </div>
              </div>
            ) : error ? (
              <div className="text-center text-red-400">
                Error loading data. Please try again.
              </div>
            ) : (
              <DataTable
                columns={columns}
                data={vmData?.data || []}
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
