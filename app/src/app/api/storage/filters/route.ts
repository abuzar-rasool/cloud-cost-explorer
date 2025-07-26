import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";

export async function GET() {
  try {
    // Optimized: Use a single query with multiple aggregations instead of separate queries
    const [providers, regions, storageClasses, accessTiers, priceRange] =
      await Promise.all([
        // Get unique providers
        prisma.storagePricing.findMany({
          select: { provider_name: true },
          distinct: ["provider_name"],
          orderBy: { provider_name: "asc" },
        }),

        // Get unique regions
        prisma.storagePricing.findMany({
          select: { region: true },
          distinct: ["region"],
          orderBy: { region: "asc" },
        }),

        // Get unique storage classes
        prisma.storagePricing.findMany({
          select: { storage_class: true },
          distinct: ["storage_class"],
          orderBy: { storage_class: "asc" },
        }),

        // Get unique access tiers
        prisma.storagePricing.findMany({
          select: { access_tier: true },
          distinct: ["access_tier"],
          orderBy: { access_tier: "asc" },
        }),

        // Get price range using partial index for non-null values
        prisma.storagePricing.aggregate({
          _min: { capacity_price: true },
          _max: { capacity_price: true },
          where: {
            capacity_price: { not: null },
          },
        }),
      ]);

    const response = NextResponse.json({
      providers: providers.map((p) => p.provider_name),
      regions: regions.map((r) => r.region),
      storageClasses: storageClasses.map((s) => s.storage_class),
      accessTiers: accessTiers.map((a) => a.access_tier),
      priceRange: {
        min: priceRange._min.capacity_price || 0,
        max: priceRange._max.capacity_price || 0,
      },
    });

    // Add cache headers for better performance
    response.headers.set(
      "Cache-Control",
      "public, s-maxage=300, stale-while-revalidate=600"
    );

    return response;
  } catch (error) {
    console.error("Error fetching storage filters:", error);
    return NextResponse.json(
      { error: "Failed to fetch filter data" },
      { status: 500 }
    );
  }
}
