'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { formatCurrency, getProviderBgColor } from '@/lib/utils'
import { VMComparisonData, StorageComparisonData, Provider, Region } from '@/types'
import { ArrowUpDown, Filter } from 'lucide-react'

interface ComparisonTableProps {
  vmData: VMComparisonData[]
  storageData: StorageComparisonData[]
  onFiltersChange?: (filters: { providers: Provider[], regions: Region[] }) => void
}

export function ComparisonTable({ vmData, storageData, onFiltersChange }: ComparisonTableProps) {
  const [selectedProviders] = useState<Provider[]>([])
  const [selectedRegions] = useState<Region[]>([])
  const [sortField, setSortField] = useState<string>('price_per_hour_usd')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')

  const providers: Provider[] = ['AWS', 'AZURE', 'GCP']
  const regions: Region[] = ['north_america', 'south_america', 'europe', 'asia', 'africa', 'oceania']

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  const sortedVMData = [...vmData].sort((a, b) => {
    let aValue = a[sortField as keyof VMComparisonData] as number | string
    let bValue = b[sortField as keyof VMComparisonData] as number | string
    
    if (typeof aValue === 'string') {
      aValue = aValue.toLowerCase()
      bValue = (bValue as string).toLowerCase()
    }
    
    if (sortDirection === 'asc') {
      return aValue < bValue ? -1 : aValue > bValue ? 1 : 0
    } else {
      return aValue > bValue ? -1 : aValue < bValue ? 1 : 0
    }
  })

  const handleFilterChange = () => {
    onFiltersChange?.({
      providers: selectedProviders,
      regions: selectedRegions,
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Cost Comparison</span>
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4" />
            <span className="text-sm text-muted-foreground">Filter & Compare</span>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Filters */}
        <div className="flex space-x-4 mb-6">
          <div className="flex-1">
            <label className="text-sm font-medium mb-2 block">Providers</label>
            <Select>
              <SelectTrigger>
                <SelectValue placeholder="Select providers" />
              </SelectTrigger>
              <SelectContent>
                {providers.map((provider) => (
                  <SelectItem key={provider} value={provider}>
                    {provider}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex-1">
            <label className="text-sm font-medium mb-2 block">Regions</label>
            <Select>
              <SelectTrigger>
                <SelectValue placeholder="Select regions" />
              </SelectTrigger>
              <SelectContent>
                {regions.map((region) => (
                  <SelectItem key={region} value={region}>
                    {region.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-end">
            <Button onClick={handleFilterChange} variant="outline">
              Apply Filters
            </Button>
          </div>
        </div>

        <Tabs defaultValue="vm" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="vm">Virtual Machines</TabsTrigger>
            <TabsTrigger value="storage">Storage</TabsTrigger>
          </TabsList>
          
          <TabsContent value="vm" className="space-y-4">
            <div className="rounded-md border">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left p-3 font-medium">
                        <button 
                          onClick={() => handleSort('provider')}
                          className="flex items-center space-x-1 hover:text-primary"
                        >
                          <span>Provider</span>
                          <ArrowUpDown className="h-3 w-3" />
                        </button>
                      </th>
                      <th className="text-left p-3 font-medium">VM Name</th>
                      <th className="text-left p-3 font-medium">
                        <button 
                          onClick={() => handleSort('virtual_cpu_count')}
                          className="flex items-center space-x-1 hover:text-primary"
                        >
                          <span>CPU</span>
                          <ArrowUpDown className="h-3 w-3" />
                        </button>
                      </th>
                      <th className="text-left p-3 font-medium">
                        <button 
                          onClick={() => handleSort('memory_gb')}
                          className="flex items-center space-x-1 hover:text-primary"
                        >
                          <span>Memory (GB)</span>
                          <ArrowUpDown className="h-3 w-3" />
                        </button>
                      </th>
                      <th className="text-left p-3 font-medium">
                        <button 
                          onClick={() => handleSort('price_per_hour_usd')}
                          className="flex items-center space-x-1 hover:text-primary"
                        >
                          <span>Price/Hour</span>
                          <ArrowUpDown className="h-3 w-3" />
                        </button>
                      </th>
                      <th className="text-left p-3 font-medium">Region</th>
                      <th className="text-left p-3 font-medium">OS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedVMData.map((vm, index) => (
                      <tr key={index} className="border-t hover:bg-muted/25">
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getProviderBgColor(vm.provider)}`}>
                            {vm.provider}
                          </span>
                        </td>
                        <td className="p-3 text-sm">{vm.vm_name}</td>
                        <td className="p-3 font-mono">{vm.virtual_cpu_count}</td>
                        <td className="p-3 font-mono">{vm.memory_gb}</td>
                        <td className="p-3 font-mono font-semibold text-green-600">
                          {formatCurrency(vm.price_per_hour_usd)}
                        </td>
                        <td className="p-3 text-sm capitalize">
                          {vm.region.replace('_', ' ')}
                        </td>
                        <td className="p-3 text-sm">{vm.os_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </TabsContent>
          
          <TabsContent value="storage" className="space-y-4">
            <div className="rounded-md border">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left p-3 font-medium">Provider</th>
                      <th className="text-left p-3 font-medium">Service</th>
                      <th className="text-left p-3 font-medium">Storage Class</th>
                      <th className="text-left p-3 font-medium">Access Tier</th>
                      <th className="text-left p-3 font-medium">Price/GB</th>
                      <th className="text-left p-3 font-medium">Region</th>
                    </tr>
                  </thead>
                  <tbody>
                    {storageData.map((storage, index) => (
                      <tr key={index} className="border-t hover:bg-muted/25">
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getProviderBgColor(storage.provider)}`}>
                            {storage.provider}
                          </span>
                        </td>
                        <td className="p-3 text-sm">{storage.service_name}</td>
                        <td className="p-3 text-sm">{storage.storage_class}</td>
                        <td className="p-3 text-sm capitalize">
                          {storage.access_tier.replace('_', ' ').toLowerCase()}
                        </td>
                        <td className="p-3 font-mono font-semibold text-blue-600">
                          {formatCurrency(storage.capacity_price)}
                        </td>
                        <td className="p-3 text-sm capitalize">
                          {storage.region.replace('_', ' ')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
} 