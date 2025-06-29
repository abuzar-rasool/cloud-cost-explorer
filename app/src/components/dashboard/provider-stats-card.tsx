import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatCurrency, formatNumber, getProviderBgColor } from '@/lib/utils'
import { ProviderStats } from '@/types'
import { Server, Database, Globe } from 'lucide-react'

interface ProviderStatsCardProps {
  stats: ProviderStats
}

export function ProviderStatsCard({ stats }: ProviderStatsCardProps) {
  return (
    <Card className="transition-all hover:shadow-lg">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">
            {stats.provider}
          </CardTitle>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getProviderBgColor(stats.provider)}`}>
            {stats.provider}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center space-x-2">
            <Server className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">VM Instances</p>
              <p className="text-lg font-semibold">{formatNumber(stats.vm_count)}</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <Database className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Storage Services</p>
              <p className="text-lg font-semibold">{formatNumber(stats.storage_services)}</p>
            </div>
          </div>
        </div>

        <div className="border-t pt-4">
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Avg VM Price</span>
              <span className="text-sm font-medium">{formatCurrency(stats.avg_vm_price)}/hr</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Min VM Price</span>
              <span className="text-sm font-medium text-green-600">{formatCurrency(stats.min_vm_price)}/hr</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">Max VM Price</span>
              <span className="text-sm font-medium text-red-600">{formatCurrency(stats.max_vm_price)}/hr</span>
            </div>
          </div>
        </div>

        <div className="border-t pt-4">
          <div className="flex items-center space-x-2 mb-2">
            <Globe className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Available Regions</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {stats.regions.map((region) => (
              <span
                key={region}
                className="px-2 py-1 text-xs bg-secondary rounded-md capitalize"
              >
                {region.replace('_', ' ')}
              </span>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
} 