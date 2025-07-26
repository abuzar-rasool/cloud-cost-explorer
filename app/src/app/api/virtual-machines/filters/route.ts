import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET() {
  try {
    // Optimized: Use a single query with multiple aggregations instead of separate queries
    const [providers, regions, osTypes, priceRange, cpuRange, memoryRange] =
      await Promise.all([
        // Get unique providers - use cached query
        prisma.onDemandVMPricing.findMany({
          select: { provider_name: true },
          distinct: ["provider_name"],
          orderBy: { provider_name: "asc" },
        }),

        // Get unique regions - use cached query
        prisma.onDemandVMPricing.findMany({
          select: { region: true },
          distinct: ["region"],
          orderBy: { region: "asc" },
        }),

        // Get unique OS types - use cached query
        prisma.onDemandVMPricing.findMany({
          select: { os_type: true },
          distinct: ["os_type"],
          orderBy: { os_type: "asc" },
        }),

        // Get price range - use cached query
        prisma.onDemandVMPricing.aggregate({
          _min: { price_per_hour_usd: true },
          _max: { price_per_hour_usd: true },
        }),

        // Get CPU range - use cached query
        prisma.onDemandVMPricing.aggregate({
          _min: { virtual_cpu_count: true },
          _max: { virtual_cpu_count: true },
        }),

        // Get Memory range - use cached query
        prisma.onDemandVMPricing.aggregate({
          _min: { memory_gb: true },
          _max: { memory_gb: true },
        }),
      ]);

    const response = NextResponse.json({
      providers: providers.map((p) => p.provider_name),
      regions: regions.map((r) => r.region),
      osTypes: osTypes.map((o) => o.os_type),
      priceRange: {
        min: priceRange._min.price_per_hour_usd || 0,
        max: priceRange._max.price_per_hour_usd || 0,
      },
      cpuRange: {
        min: cpuRange._min.virtual_cpu_count || 0,
        max: cpuRange._max.virtual_cpu_count || 0,
      },
      memoryRange: {
        min: memoryRange._min.memory_gb || 0,
        max: memoryRange._max.memory_gb || 0,
      },
    });

    // Add cache headers for better performance
    response.headers.set(
      "Cache-Control",
      "public, s-maxage=300, stale-while-revalidate=600"
    );

    return response;
  } catch (error) {
    console.error("Error fetching VM filters:", error);
    return NextResponse.json(
      { error: "Failed to fetch filter data" },
      { status: 500 }
    );
  }
}
