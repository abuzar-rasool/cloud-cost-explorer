import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    // Filter parameters (same as main storage endpoint)
    const provider = searchParams.get("provider");
    const region = searchParams.get("region");
    const storageClass = searchParams.get("storageClass");
    const accessTier = searchParams.get("accessTier");
    const minPrice = searchParams.get("minPrice");
    const maxPrice = searchParams.get("maxPrice");

    // Build where clause (same as main storage endpoint)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const where: any = {};

    if (provider) where.provider_name = provider;
    if (region) where.region = region;
    if (storageClass) where.storage_class = storageClass;
    if (accessTier) where.access_tier = accessTier;
    if (minPrice || maxPrice) {
      where.capacity_price = {};
      if (minPrice) where.capacity_price.gte = parseFloat(minPrice);
      if (maxPrice) where.capacity_price.lte = parseFloat(maxPrice);
    }

    // Get global statistics for the filtered dataset
    const [totalCount, capacityPriceStats, readPriceStats, writePriceStats] =
      await Promise.all([
        // Total count
        prisma.storagePricing.count({ where }),

        // Capacity price statistics (only for non-null values)
        prisma.storagePricing.aggregate({
          where: { ...where, capacity_price: { not: null } },
          _avg: { capacity_price: true },
          _min: { capacity_price: true },
          _max: { capacity_price: true },
        }),

        // Read price statistics (only for non-null values)
        prisma.storagePricing.aggregate({
          where: { ...where, read_price: { not: null } },
          _avg: { read_price: true },
          _min: { read_price: true },
          _max: { read_price: true },
        }),

        // Write price statistics (only for non-null values)
        prisma.storagePricing.aggregate({
          where: { ...where, write_price: { not: null } },
          _avg: { write_price: true },
          _min: { write_price: true },
          _max: { write_price: true },
        }),
      ]);

    return NextResponse.json({
      totalCount,
      capacityPriceStats: {
        avg: capacityPriceStats._avg.capacity_price || 0,
        min: capacityPriceStats._min.capacity_price || 0,
        max: capacityPriceStats._max.capacity_price || 0,
      },
      readPriceStats: {
        avg: readPriceStats._avg.read_price || 0,
        min: readPriceStats._min.read_price || 0,
        max: readPriceStats._max.read_price || 0,
      },
      writePriceStats: {
        avg: writePriceStats._avg.write_price || 0,
        min: writePriceStats._min.write_price || 0,
        max: writePriceStats._max.write_price || 0,
      },
    });
  } catch (error) {
    console.error("Error fetching storage stats:", error);
    return NextResponse.json(
      { error: "Failed to fetch storage statistics" },
      { status: 500 }
    );
  }
}
