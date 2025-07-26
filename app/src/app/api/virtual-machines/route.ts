import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    // Pagination parameters
    const page = parseInt(searchParams.get("page") || "1");
    const limit = parseInt(searchParams.get("limit") || "50");
    const offset = (page - 1) * limit;

    // Filter parameters
    const provider = searchParams.get("provider");
    const region = searchParams.get("region");
    const osType = searchParams.get("osType");
    const minPrice = searchParams.get("minPrice");
    const maxPrice = searchParams.get("maxPrice");
    const minCpu = searchParams.get("minCpu");
    const maxCpu = searchParams.get("maxCpu");
    const minMemory = searchParams.get("minMemory");
    const maxMemory = searchParams.get("maxMemory");
    const search = searchParams.get("search");

    // Sorting parameters
    const sortBy = searchParams.get("sortBy") || "price_per_hour_usd";
    const sortOrder = searchParams.get("sortOrder") || "asc";

    // Build where clause
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
    if (search) {
      where.OR = [
        { vm_name: { contains: search, mode: "insensitive" } },
        { cpu_arch: { contains: search, mode: "insensitive" } },
        { gpu_name: { contains: search, mode: "insensitive" } },
      ];
    }

    // Build order by clause
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const orderBy: any = {};
    orderBy[sortBy] = sortOrder;

    // Optimized: Execute queries in parallel and use indexed columns
    const [data, totalCount] = await Promise.all([
      prisma.onDemandVMPricing.findMany({
        where,
        orderBy,
        skip: offset,
        take: limit,
        select: {
          id: true,
          vm_name: true,
          provider_name: true,
          virtual_cpu_count: true,
          memory_gb: true,
          cpu_arch: true,
          price_per_hour_usd: true,
          gpu_count: true,
          gpu_name: true,
          gpu_memory: true,
          os_type: true,
          region: true,
          other_details: true,
          createdAt: true,
          updatedAt: true,
        },
      }),
      prisma.onDemandVMPricing.count({ where }),
    ]);

    // Calculate pagination info
    const totalPages = Math.ceil(totalCount / limit);
    const hasNextPage = page < totalPages;
    const hasPrevPage = page > 1;

    return NextResponse.json({
      data,
      pagination: {
        page,
        limit,
        totalCount,
        totalPages,
        hasNextPage,
        hasPrevPage,
      },
    });
  } catch (error) {
    console.error("Error fetching VM data:", error);
    return NextResponse.json(
      { error: "Failed to fetch VM data" },
      { status: 500 }
    );
  }
}
