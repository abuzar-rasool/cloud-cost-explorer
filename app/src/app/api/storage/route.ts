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
    const storageClass = searchParams.get("storageClass");
    const accessTier = searchParams.get("accessTier");
    const minPrice = searchParams.get("minPrice");
    const maxPrice = searchParams.get("maxPrice");
    const search = searchParams.get("search");

    // Sorting parameters
    const sortBy = searchParams.get("sortBy") || "capacity_price";
    const sortOrder = searchParams.get("sortOrder") || "asc";

    // Build where clause
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
    if (search) {
      where.OR = [
        { service_name: { contains: search, mode: "insensitive" } },
        { storage_class: { contains: search, mode: "insensitive" } },
      ];
    }

    // Build order by clause
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const orderBy: any = {};
    orderBy[sortBy] = sortOrder;

    // Optimized: Execute queries in parallel and use indexed columns
    const [data, totalCount] = await Promise.all([
      prisma.storagePricing.findMany({
        where,
        orderBy,
        skip: offset,
        take: limit,
        select: {
          id: true,
          provider_name: true,
          service_name: true,
          storage_class: true,
          region: true,
          access_tier: true,
          capacity_price: true,
          read_price: true,
          write_price: true,
          flat_item_price: true,
          other_details: true,
          createdAt: true,
          updatedAt: true,
        },
      }),
      prisma.storagePricing.count({ where }),
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
    console.error("Error fetching storage data:", error);
    return NextResponse.json(
      { error: "Failed to fetch storage data" },
      { status: 500 }
    );
  }
}
