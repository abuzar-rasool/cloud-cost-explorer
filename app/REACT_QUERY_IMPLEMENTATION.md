# React Query Implementation

This document outlines the React Query (TanStack Query) implementation in the Cloud Cost Explorer application.

## Overview

React Query has been integrated to provide efficient caching, background updates, and improved data handling for both Virtual Machines and Storage pages.

## Architecture

### 1. Query Provider Setup

- **Location**: `src/components/providers/query-provider.tsx`
- **Purpose**: Client-side QueryClient provider with optimized defaults
- **Configuration**:
  - `staleTime`: 5 minutes (data considered fresh for 5 minutes)
  - `gcTime`: 10 minutes (garbage collection time)
  - `retry`: 1 attempt on failure
  - `refetchOnWindowFocus`: Disabled for better UX

### 2. Custom Hooks

#### Virtual Machines (`src/hooks/useVirtualMachines.ts`)

- **`useVirtualMachines(page, pageSize, filters)`**: Fetches VM data with pagination and filtering

  - Query key: `["virtual-machines", page, pageSize, filters]`
  - Stale time: 2 minutes
  - GC time: 5 minutes

- **`useVMFilters()`**: Fetches filter options (providers, regions, OS types)
  - Query key: `["vm-filters"]`
  - Stale time: 10 minutes
  - GC time: 30 minutes

#### Storage (`src/hooks/useStorage.ts`)

- **`useStorage(page, pageSize, filters)`**: Fetches storage data with pagination and filtering

  - Query key: `["storage", page, pageSize, filters]`
  - Stale time: 2 minutes
  - GC time: 5 minutes

- **`useStorageFilters()`**: Fetches filter options (providers, regions, storage classes, access tiers)
  - Query key: `["storage-filters"]`
  - Stale time: 10 minutes
  - GC time: 30 minutes

## Benefits

### 1. **Automatic Caching**

- Data is cached based on query keys
- Reduces unnecessary API calls
- Improves performance and user experience

### 2. **Background Updates**

- Data is automatically refetched when stale
- Users see fresh data without manual refresh
- Seamless updates in the background

### 3. **Optimistic Updates**

- UI updates immediately on user actions
- Better perceived performance
- Automatic rollback on errors

### 4. **Error Handling**

- Built-in error states and retry logic
- Consistent error handling across the app
- Better user feedback

### 5. **Loading States**

- Automatic loading state management
- Skeleton screens and loading indicators
- Improved user experience during data fetching

## Query Key Strategy

### Data Queries

- Include all parameters that affect the data: `[resource, page, pageSize, filters]`
- Ensures proper cache invalidation when parameters change
- Prevents cache conflicts between different filter combinations

### Filter Queries

- Static keys for filter options: `[resource-filters]`
- Longer cache times since filter options change infrequently
- Reduces API calls for filter data

## Cache Management

### Stale Time vs GC Time

- **Stale Time**: How long data is considered fresh
- **GC Time**: How long data stays in cache after becoming stale
- Optimized for different data types:
  - **Data**: Short stale time (2 min) for fresh data
  - **Filters**: Long stale time (10 min) for stability

### Cache Invalidation

- Automatic invalidation when query keys change
- Manual invalidation available if needed
- Background refetching when data becomes stale

## Development Tools

### React Query DevTools

- Available in development mode
- Shows cache state, queries, and mutations
- Helps with debugging and optimization
- Accessible via floating button in bottom-right corner

## Performance Optimizations

### 1. **Query Deduplication**

- Multiple components requesting same data share cache
- Reduces network requests
- Improves overall performance

### 2. **Background Refetching**

- Data is refreshed automatically when stale
- Users always see relatively fresh data
- No manual refresh required

### 3. **Pagination Optimization**

- Each page is cached separately
- Quick navigation between pages
- Efficient memory usage

### 4. **Filter Optimization**

- Filter options cached for longer periods
- Reduces API calls for static data
- Better user experience

## Migration Benefits

### Before React Query

- Manual state management with `useState` and `useEffect`
- No automatic caching
- Manual loading and error states
- Potential for race conditions
- No background updates

### After React Query

- Automatic caching and state management
- Built-in loading and error states
- Automatic background updates
- Race condition prevention
- Optimistic updates
- Better developer experience

## Future Enhancements

### 1. **Mutations**

- Add mutations for data updates
- Optimistic updates for better UX
- Automatic cache invalidation

### 2. **Infinite Queries**

- Implement infinite scrolling for large datasets
- Better performance for pagination

### 3. **Prefetching**

- Prefetch data on hover or navigation
- Even better perceived performance

### 4. **Offline Support**

- Cache data for offline viewing
- Sync when connection restored

## Usage Examples

### Basic Data Fetching

```typescript
const { data, isLoading, error } = useVirtualMachines(page, pageSize, filters);
```

### Filter Options

```typescript
const { data: filterOptions, isLoading: filtersLoading } = useVMFilters();
```

### Error Handling

```typescript
if (error) {
  return <ErrorComponent message={error.message} />;
}
```

### Loading States

```typescript
if (isLoading) {
  return <LoadingSpinner />;
}
```

This implementation provides a solid foundation for efficient data management and excellent user experience in the Cloud Cost Explorer application.
