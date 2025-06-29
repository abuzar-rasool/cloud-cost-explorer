'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { VMComparisonData } from '@/types'
import { Globe, MapPin } from 'lucide-react'

interface RegionalStats {
  region: string
  vmCount: number
  avgPrice: number
  minPrice: number
  maxPrice: number
  providers: Set<string>
}

interface RegionalCostComparisonProps {
  vmData: VMComparisonData[]
}

export function RegionalCostComparison({ vmData }: RegionalCostComparisonProps) {
  // Early return if no data
  if (!vmData || vmData.length === 0) {
    return (
      <Card className="bg-card/80 backdrop-blur-sm border-white/10">
        <CardHeader>
          <CardTitle className="text-white text-lg font-medium flex items-center gap-2">
            <Globe className="h-5 w-5" />
            Regional Cost Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-white/70 py-8">
            No data available for regional analysis
          </div>
        </CardContent>
      </Card>
    )
  }

  // Group data by region with deterministic ordering
  const regionStats = vmData.reduce((acc, vm) => {
    if (!acc[vm.region]) {
      acc[vm.region] = {
        region: vm.region,
        vmCount: 0,
        avgPrice: 0,
        minPrice: Number.MAX_SAFE_INTEGER,
        maxPrice: 0,
        providers: new Set()
      }
    }
    
    acc[vm.region].vmCount++
    acc[vm.region].avgPrice += vm.price_per_hour_usd
    acc[vm.region].minPrice = Math.min(acc[vm.region].minPrice, vm.price_per_hour_usd)
    acc[vm.region].maxPrice = Math.max(acc[vm.region].maxPrice, vm.price_per_hour_usd)
    acc[vm.region].providers.add(vm.provider)
    
    return acc
  }, {} as Record<string, RegionalStats>)

  // Calculate averages and sort by cost with stable sort
  const regions = Object.keys(regionStats)
    .sort() // Sort regions alphabetically first for consistency
    .map(regionKey => {
      const region = regionStats[regionKey]
      return {
        ...region,
        avgPrice: Number((region.avgPrice / region.vmCount).toFixed(6)), // Fixed precision
        providerCount: region.providers.size
      }
    })
    .sort((a, b) => {
      // Stable sort with secondary sort by region name
      const priceDiff = a.avgPrice - b.avgPrice
      return priceDiff !== 0 ? priceDiff : a.region.localeCompare(b.region)
    })

  const globalMinPrice = Math.min(...regions.map(r => r.minPrice))
  const globalMaxPrice = Math.max(...regions.map(r => r.maxPrice))

  return (
    <Card className="bg-card/80 backdrop-blur-sm border-white/10">
      <CardHeader>
        <CardTitle className="text-white text-lg font-medium flex items-center gap-2">
          <Globe className="h-5 w-5" />
          Regional Cost Analysis
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {regions.map((region, idx) => {
            const isLowest = region.avgPrice === Math.min(...regions.map(r => r.avgPrice))
            const costAdvantage = isLowest ? 0 : ((region.avgPrice - Math.min(...regions.map(r => r.avgPrice))) / Math.min(...regions.map(r => r.avgPrice)) * 100)
            
            return (
              <div key={region.region} className="relative">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-white/70" />
                    <span className="text-white font-medium capitalize">
                      {region.region.replace('_', ' ')}
                    </span>
                    {isLowest && (
                      <span className="bg-green-500/20 text-green-400 px-2 py-1 rounded-full text-xs border border-green-500/30">
                        BEST VALUE
                      </span>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-white text-sm">${region.avgPrice.toFixed(3)}/hr</div>
                    <div className="text-white/50 text-xs">average</div>
                  </div>
                </div>
                
                <div className="bg-white/10 rounded-full h-2 overflow-hidden mb-2">
                  <div 
                    className="h-full bg-white rounded-full transition-all duration-500"
                    style={{ width: `${((region.avgPrice - globalMinPrice) / (globalMaxPrice - globalMinPrice)) * 100}%` }}
                  ></div>
                </div>
                
                <div className="flex justify-between items-center text-xs text-white/60">
                  <div>
                    <span>{region.vmCount} VMs • </span>
                    <span>{region.providerCount} Providers</span>
                  </div>
                  <div className="text-right">
                    <div>${region.minPrice.toFixed(3)} - ${region.maxPrice.toFixed(3)}</div>
                    {!isLowest && (
                      <div className="text-red-400">+{costAdvantage.toFixed(1)}% vs best</div>
                    )}
                  </div>
                </div>
                
                {idx < regions.length - 1 && (
                  <div className="border-b border-white/10 mt-3"></div>
                )}
              </div>
            )
          })}
        </div>
        
        <div className="mt-6 pt-4 border-t border-white/10">
          <div className="text-center text-white/70 text-sm">
            <div className="mb-2">Global Cost Spread</div>
            <div className="text-white text-lg font-light">
              ${((globalMaxPrice - globalMinPrice) * 24 * 30).toLocaleString()}
            </div>
            <div className="text-white/50 text-xs">Monthly difference between regions</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
} 