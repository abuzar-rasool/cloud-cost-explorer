import { prisma } from "@/lib/db";
import {
  Provider,
  Region,
  ProviderStats,
  VMComparisonData,
  StorageComparisonData,
  OSType,
  AccessTier,
} from "@/types";

interface VMStatsResult {
  provider_name: string;
  _count: { id: number };
  _avg: { price_per_hour_usd: number | null };
  _min: { price_per_hour_usd: number | null };
  _max: { price_per_hour_usd: number | null };
}

interface StorageStatsResult {
  provider_name: string;
  _count: { service_name: number };
  _avg: { capacity_price: number | null };
}

interface RegionStatsResult {
  provider_name: string;
  region: string;
  _count: { id: number };
}

interface VMQueryResult {
  provider_name: string;
  vm_name: string;
  virtual_cpu_count: number;
  memory_gb: number;
  price_per_hour_usd: number;
  region: string;
  os_type: string;
}

interface StorageQueryResult {
  provider_name: string;
  service_name: string;
  storage_class: string | null;
  access_tier: string | null;
  capacity_price: number | null;
  region: string;
}

export async function getProviderStats(): Promise<ProviderStats[]> {
  // Optimized: Use a single query with multiple aggregations instead of separate queries
  const [vmStats, storageStats, regionStats] = await Promise.all([
    // VM stats with optimized grouping including min/max per provider
    prisma.onDemandVMPricing.groupBy({
      by: ["provider_name"],
      _count: {
        id: true,
      },
      _avg: {
        price_per_hour_usd: true,
      },
      _min: {
        price_per_hour_usd: true,
      },
      _max: {
        price_per_hour_usd: true,
      },
    }),

    // Storage stats with optimized grouping
    prisma.storagePricing.groupBy({
      by: ["provider_name"],
      _count: {
        service_name: true,
      },
      _avg: {
        capacity_price: true,
      },
    }),

    // Region stats with optimized grouping
    prisma.onDemandVMPricing.groupBy({
      by: ["provider_name", "region"],
      _count: {
        id: true,
      },
    }),
  ]);

  // Combine stats efficiently
  const stats: ProviderStats[] = vmStats.map((vm: VMStatsResult) => {
    const storage = storageStats.find(
      (s: StorageStatsResult) => s.provider_name === vm.provider_name
    );
    const regions = regionStats
      .filter((r: RegionStatsResult) => r.provider_name === vm.provider_name)
      .map((r: RegionStatsResult) => r.region);

    return {
      provider: vm.provider_name as Provider,
      vm_count: vm._count.id,
      storage_services: storage?._count.service_name || 0,
      avg_vm_price: vm._avg.price_per_hour_usd || 0,
      min_vm_price: vm._min.price_per_hour_usd || 0,
      max_vm_price: vm._max.price_per_hour_usd || 0,
      avg_storage_price: storage?._avg.capacity_price || 0,
      regions: regions,
    };
  });

  return stats;
}

export async function getVMComparison(
  providers?: Provider[],
  regions?: Region[],
  limit: number = 20
): Promise<VMComparisonData[]> {
  const whereClause: Record<string, unknown> = {};

  if (providers && providers.length > 0) {
    whereClause.provider_name = { in: providers };
  }

  if (regions && regions.length > 0) {
    whereClause.region = { in: regions };
  }

  // Optimized: Use indexed columns for ordering and limit
  const vms = await prisma.onDemandVMPricing.findMany({
    where: whereClause,
    select: {
      provider_name: true,
      vm_name: true,
      virtual_cpu_count: true,
      memory_gb: true,
      price_per_hour_usd: true,
      region: true,
      os_type: true,
    },
    orderBy: {
      price_per_hour_usd: "asc",
    },
    take: limit,
  });

  return vms.map((vm: VMQueryResult) => ({
    provider: vm.provider_name as Provider,
    vm_name: vm.vm_name,
    virtual_cpu_count: vm.virtual_cpu_count,
    memory_gb: vm.memory_gb,
    price_per_hour_usd: vm.price_per_hour_usd,
    region: vm.region as Region,
    os_type: vm.os_type as OSType,
  }));
}

export async function getStorageComparison(
  providers?: Provider[],
  regions?: Region[],
  limit: number = 20
): Promise<StorageComparisonData[]> {
  const whereClause: Record<string, unknown> = {
    capacity_price: { not: null },
  };

  if (providers && providers.length > 0) {
    whereClause.provider_name = { in: providers };
  }

  if (regions && regions.length > 0) {
    whereClause.region = { in: regions };
  }

  // Optimized: Use indexed columns and partial index for non-null capacity_price
  const storage = await prisma.storagePricing.findMany({
    where: whereClause,
    select: {
      provider_name: true,
      service_name: true,
      storage_class: true,
      access_tier: true,
      capacity_price: true,
      region: true,
    },
    orderBy: {
      capacity_price: "asc",
    },
    take: limit,
  });

  return storage.map((s: StorageQueryResult) => ({
    provider: s.provider_name as Provider,
    service_name: s.service_name,
    storage_class: s.storage_class || "STANDARD",
    access_tier: (s.access_tier as AccessTier) || "FREQUENT_ACCESS",
    capacity_price: s.capacity_price || 0,
    region: s.region as Region,
  }));
}

export async function getPriceDistribution(provider?: Provider) {
  const whereClause: Record<string, unknown> = {};
  if (provider) {
    whereClause.provider_name = provider;
  }

  // Optimized: Use indexed columns for ordering
  const vmPrices = await prisma.onDemandVMPricing.findMany({
    where: whereClause,
    select: {
      provider_name: true,
      price_per_hour_usd: true,
      virtual_cpu_count: true,
      memory_gb: true,
    },
    orderBy: {
      price_per_hour_usd: "asc",
    },
  });

  return vmPrices;
}

export async function getTopVMsBySpecs(limit: number = 10) {
  // Optimized: Use indexed columns for ordering
  const [topCPU, topMemory] = await Promise.all([
    prisma.onDemandVMPricing.findMany({
      orderBy: {
        virtual_cpu_count: "desc",
      },
      take: limit,
      select: {
        vm_name: true,
        provider_name: true,
        virtual_cpu_count: true,
        memory_gb: true,
        price_per_hour_usd: true,
        region: true,
      },
    }),
    prisma.onDemandVMPricing.findMany({
      orderBy: {
        memory_gb: "desc",
      },
      take: limit,
      select: {
        vm_name: true,
        provider_name: true,
        virtual_cpu_count: true,
        memory_gb: true,
        price_per_hour_usd: true,
        region: true,
      },
    }),
  ]);

  return { topCPU, topMemory };
}
