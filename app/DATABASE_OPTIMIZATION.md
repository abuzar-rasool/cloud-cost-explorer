# Database Performance Optimization Guide

## 🚀 Optimizations Implemented

### 1. Database Indexes Added

#### OnDemandVMPricing Table Indexes:

- **Single Column Indexes**: `provider_name`, `region`, `os_type`, `price_per_hour_usd`, `virtual_cpu_count`, `memory_gb`
- **Composite Indexes**: `(provider_name, region)`, `(provider_name, os_type)`, `(provider_name, price_per_hour_usd)`
- **Multi-column Indexes**: `(provider_name, region, os_type)`, `(provider_name, region, price_per_hour_usd)`
- **Text Search Indexes**: GIN indexes on `vm_name`, `cpu_arch`, `gpu_name` for efficient text search

#### StoragePricing Table Indexes:

- **Single Column Indexes**: `provider_name`, `region`, `storage_class`, `access_tier`, `capacity_price`
- **Composite Indexes**: `(provider_name, region)`, `(provider_name, storage_class)`, `(provider_name, access_tier)`
- **Multi-column Indexes**: `(provider_name, region, storage_class)`, `(provider_name, region, access_tier)`
- **Text Search Indexes**: GIN indexes on `service_name`, `storage_class`
- **Partial Index**: `capacity_price` WHERE `capacity_price IS NOT NULL`

### 2. Query Optimizations

#### API Route Improvements:

- **Parallel Query Execution**: Using `Promise.all()` for concurrent database operations
- **Optimized Filter Queries**: Better WHERE clause construction
- **Indexed Column Usage**: Ensuring queries use indexed columns for sorting and filtering

#### Dashboard Service Optimizations:

- **Reduced Database Calls**: Combined multiple queries into single operations where possible
- **Efficient Aggregations**: Using indexed columns for GROUP BY operations
- **Better Error Handling**: Improved error handling and logging

### 3. Performance Monitoring

Created `performance-test.js` to measure query performance:

- Storage queries with filters
- VM queries with complex filters
- Text search operations
- Aggregation queries
- Filter option queries

## 📊 Current Performance Metrics

Based on the performance test:

- **Storage Query**: ~247ms
- **VM Query**: ~114ms
- **Text Search**: ~120ms
- **Aggregations**: ~1926ms (needs further optimization)
- **Filter Options**: ~365ms

## 🔧 Additional Optimization Recommendations

### 1. Database-Level Optimizations

#### PostgreSQL Configuration:

```sql
-- Increase work_mem for complex queries
ALTER SYSTEM SET work_mem = '256MB';

-- Optimize shared_buffers (25% of RAM)
ALTER SYSTEM SET shared_buffers = '1GB';

-- Enable query plan caching
ALTER SYSTEM SET plan_cache_mode = 'auto';

-- Optimize for read-heavy workloads
ALTER SYSTEM SET effective_cache_size = '3GB';
```

#### Connection Pooling:

```javascript
// In src/lib/db.ts
import { Pool } from "pg";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});
```

### 2. Application-Level Optimizations

#### Caching Strategy:

```javascript
// Implement Redis caching for frequently accessed data
import Redis from "ioredis";

const redis = new Redis(process.env.REDIS_URL);

// Cache filter options for 1 hour
async function getCachedFilters() {
  const cached = await redis.get("storage_filters");
  if (cached) return JSON.parse(cached);

  const filters = await fetchFilters();
  await redis.setex("storage_filters", 3600, JSON.stringify(filters));
  return filters;
}
```

#### Query Optimization:

```javascript
// Use cursor-based pagination for large datasets
const cursor = await prisma.storagePricing.findMany({
  take: 50,
  cursor: { id: lastId },
  orderBy: { id: "asc" },
});
```

### 3. Data Structure Optimizations

#### Partitioning for Large Tables:

```sql
-- Partition by provider for better query performance
CREATE TABLE storage_pricing_partitioned (
  LIKE storage_pricing INCLUDING ALL
) PARTITION BY LIST (provider_name);

CREATE TABLE storage_pricing_aws PARTITION OF storage_pricing_partitioned
  FOR VALUES IN ('AWS');
```

#### Materialized Views for Complex Aggregations:

```sql
-- Create materialized view for dashboard stats
CREATE MATERIALIZED VIEW provider_stats AS
SELECT
  provider_name,
  COUNT(*) as vm_count,
  AVG(price_per_hour_usd) as avg_price,
  MIN(price_per_hour_usd) as min_price,
  MAX(price_per_hour_usd) as max_price
FROM "on-demand-vm-pricing"
GROUP BY provider_name;

-- Refresh periodically
REFRESH MATERIALIZED VIEW provider_stats;
```

### 4. Monitoring and Maintenance

#### Regular Maintenance:

```sql
-- Analyze table statistics
ANALYZE "on-demand-vm-pricing";
ANALYZE "storage-pricing";

-- Vacuum tables
VACUUM ANALYZE "on-demand-vm-pricing";
VACUUM ANALYZE "storage-pricing";
```

#### Performance Monitoring:

```javascript
// Add query timing to Prisma client
const prisma = new PrismaClient({
  log: [
    {
      emit: "event",
      level: "query",
    },
  ],
});

prisma.$on("query", (e) => {
  console.log(`Query: ${e.query}`);
  console.log(`Duration: ${e.duration}ms`);
});
```

## 🚨 Critical Issues to Address

### 1. Aggregation Query Performance

The aggregation queries are taking ~1926ms, which is too slow. Consider:

- Creating materialized views for dashboard stats
- Implementing caching for aggregation results
- Using database views for complex aggregations

### 2. Connection Management

- Implement proper connection pooling
- Add connection timeout handling
- Monitor connection usage

### 3. Query Plan Analysis

```sql
-- Analyze slow queries
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM "on-demand-vm-pricing"
WHERE provider_name = 'AWS'
ORDER BY price_per_hour_usd;
```

## 📈 Expected Performance Improvements

After implementing these optimizations:

- **Filter Queries**: 50-80% faster
- **Text Search**: 70-90% faster
- **Aggregations**: 80-95% faster (with materialized views)
- **Overall Page Load**: 60-80% faster

## 🔄 Next Steps

1. **Immediate**: Monitor current performance with the new indexes
2. **Short-term**: Implement caching for filter options and dashboard stats
3. **Medium-term**: Add materialized views for complex aggregations
4. **Long-term**: Consider database partitioning for very large datasets

## 📝 Maintenance Schedule

- **Daily**: Monitor query performance
- **Weekly**: Refresh materialized views
- **Monthly**: Analyze table statistics and vacuum
- **Quarterly**: Review and optimize indexes based on usage patterns
