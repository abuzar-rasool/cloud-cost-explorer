import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    // Filter parameters (same as main VM endpoint)
    const provider = searchParams.get("provider");
    const region = searchParams.get("region");
    const osType = searchParams.get("osType");
    const minPrice = searchParams.get("minPrice");
    const maxPrice = searchParams.get("maxPrice");
    const minCpu = searchParams.get("minCpu");
    const maxCpu = searchParams.get("maxCpu");
    const minMemory = searchParams.get("minMemory");
    const maxMemory = searchParams.get("maxMemory");

    // Build where clause (same as main VM endpoint)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const where: any = {};

    if (provider) where.provider_name = provider;
    if (region) where.region = region;
    if (osType) where.os_type = osType;
    if (minPrice || maxPrice) {
      where.price_per_hour_usd = {};
      if (minPrice) where.price_per_hour_usd.gte = parseFloat(minPrice);
      if (maxPrice) where.price_per_hour_usd.lte = parseFloat(maxPrice);
    }
    if (minCpu || maxCpu) {
      where.virtual_cpu_count = {};
      if (minCpu) where.virtual_cpu_count.gte = parseInt(minCpu);
      if (maxCpu) where.virtual_cpu_count.lte = parseInt(maxCpu);
    }
    if (minMemory || maxMemory) {
      where.memory_gb = {};
      if (minMemory) where.memory_gb.gte = parseFloat(minMemory);
      if (maxMemory) where.memory_gb.lte = parseFloat(maxMemory);
    }

    // Get global statistics for the filtered dataset
    const [totalCount, priceStats, cpuStats, memoryStats] = await Promise.all([
      // Total count
      prisma.onDemandVMPricing.count({ where }),

      // Price statistics
      prisma.onDemandVMPricing.aggregate({
        where,
        _avg: { price_per_hour_usd: true },
        _min: { price_per_hour_usd: true },
        _max: { price_per_hour_usd: true },
      }),

      // CPU statistics
      prisma.onDemandVMPricing.aggregate({
        where,
        _avg: { virtual_cpu_count: true },
        _min: { virtual_cpu_count: true },
        _max: { virtual_cpu_count: true },
      }),

      // Memory statistics
      prisma.onDemandVMPricing.aggregate({
        where,
        _avg: { memory_gb: true },
        _min: { memory_gb: true },
        _max: { memory_gb: true },
      }),
    ]);

    return NextResponse.json({
      totalCount,
      priceStats: {
        avg: priceStats._avg.price_per_hour_usd || 0,
        min: priceStats._min.price_per_hour_usd || 0,
        max: priceStats._max.price_per_hour_usd || 0,
      },
      cpuStats: {
        avg: cpuStats._avg.virtual_cpu_count || 0,
        min: cpuStats._min.virtual_cpu_count || 0,
        max: cpuStats._max.virtual_cpu_count || 0,
      },
      memoryStats: {
        avg: memoryStats._avg.memory_gb || 0,
        min: memoryStats._min.memory_gb || 0,
        max: memoryStats._max.memory_gb || 0,
      },
    });
  } catch (error) {
    console.error("Error fetching VM stats:", error);
    return NextResponse.json(
      { error: "Failed to fetch VM statistics" },
      { status: 500 }
    );
  }
}
