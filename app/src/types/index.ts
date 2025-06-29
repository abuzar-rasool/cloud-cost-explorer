export type Provider = 'AWS' | 'AZURE' | 'GCP'

export type Region = 'north_america' | 'south_america' | 'europe' | 'asia' | 'africa' | 'oceania' | 'antarctica'

export type OSType = 'LINUX' | 'WINDOWS' | 'OTHER'

export type AccessTier = 'FREQUENT_ACCESS' | 'OCCASIONAL_ACCESS' | 'RARE_ACCESS' | 'ARCHIVE'

export interface VMPricing {
  id: number
  vm_name: string
  provider_name: Provider
  virtual_cpu_count: number
  memory_gb: number
  cpu_arch: string
  price_per_hour_usd: number
  gpu_count: number
  gpu_name: string | null
  gpu_memory: number
  os_type: OSType
  region: Region
  other_details: Record<string, unknown>
  createdAt: Date
  updatedAt: Date
}

export interface StoragePricing {
  id: number
  provider_name: Provider
  service_name: string
  storage_class: string
  region: Region
  access_tier: AccessTier
  capacity_price: number | null
  read_price: number | null
  write_price: number | null
  flat_item_price: number | null
  other_details: Record<string, unknown>
  createdAt: Date
  updatedAt: Date
}

export interface VMComparisonData {
  provider: Provider
  vm_name: string
  virtual_cpu_count: number
  memory_gb: number
  price_per_hour_usd: number
  region: Region
  os_type: OSType
}

export interface StorageComparisonData {
  provider: Provider
  service_name: string
  storage_class: string
  access_tier: AccessTier
  capacity_price: number
  region: Region
}

export interface ProviderStats {
  provider: Provider
  vm_count: number
  storage_services: number
  avg_vm_price: number
  min_vm_price: number
  max_vm_price: number
  avg_storage_price: number
  regions: string[]
}

export interface ComparisonFilters {
  providers: Provider[]
  regions: Region[]
  cpu_min?: number
  cpu_max?: number
  memory_min?: number
  memory_max?: number
  price_min?: number
  price_max?: number
  os_type?: OSType
  access_tier?: AccessTier
} 