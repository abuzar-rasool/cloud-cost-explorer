'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ProviderStats } from '@/types'
import { TrendingUp, TrendingDown, DollarSign, Zap, Award } from 'lucide-react'

interface MainCostComparisonCardProps {
  providerStats: ProviderStats[]
}

export function MainCostComparisonCard({ providerStats }: MainCostComparisonCardProps) {
  // Early return if no data
  if (!providerStats || providerStats.length === 0) {
    return (
      <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6 h-full">
        <CardContent className="flex items-center justify-center h-64 text-white/70">
          No provider data available
        </CardContent>
      </Card>
    )
  }

  // Sort providers for consistent ordering
  const sortedProviders = [...providerStats].sort((a, b) => a.provider.localeCompare(b.provider))
  
  // Calculate key metrics
  const totalVMs = sortedProviders.reduce((sum, p) => sum + p.vm_count, 0)
  
  // Find best and worst performers based on average price
  const cheapestProvider = sortedProviders.reduce((min, p) => p.avg_vm_price < min.avg_vm_price ? p : min)
  const mostExpensiveProvider = sortedProviders.reduce((max, p) => p.avg_vm_price > max.avg_vm_price ? p : max)
  
  // Calculate potential savings
  const avgPrices = sortedProviders.map(p => p.avg_vm_price)
  const maxAvgPrice = Math.max(...avgPrices)
  const minAvgPrice = Math.min(...avgPrices)
  const potentialSavings = maxAvgPrice - minAvgPrice
  const monthlySavings = potentialSavings * 24 * 30
  
  // Calculate cost efficiency scores
  const providersWithScores = sortedProviders.map(provider => ({
    ...provider,
    costEfficiency: (1 / provider.avg_vm_price) * 1000, // Higher is better
    marketShare: (provider.vm_count / totalVMs) * 100,
    monthlyMin: Math.floor(provider.min_vm_price * 24 * 30),
    monthlyMax: Math.floor(provider.max_vm_price * 24 * 30),
    monthlyAvg: Math.floor(provider.avg_vm_price * 24 * 30)
  }))

  const getProviderColor = (provider: string) => {
    const colors = {
      AWS: 'bg-orange-500',
      AZURE: 'bg-blue-500', 
      GCP: 'bg-green-500'
    }
    return colors[provider as keyof typeof colors] || 'bg-white'
  }

  const getTrendIcon = (provider: string) => {
    // Based on market position - this could be dynamic based on historical data
    const trends = {
      AWS: { icon: TrendingUp, color: 'text-white/70', label: '↑' },
      AZURE: { icon: TrendingDown, color: 'text-white/50', label: '↓' },
      GCP: { icon: TrendingUp, color: 'text-white/70', label: '↑' }
    }
    return trends[provider as keyof typeof trends] || { icon: TrendingUp, color: 'text-white/50', label: '→' }
  }

  return (
    <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6 h-full">
      <CardHeader className="flex flex-row items-center justify-between pb-6">
        <CardTitle className="text-white text-xl font-medium">Cloud Cost Comparison Overview</CardTitle>
        <Button variant="outline" size="sm" className="text-white/70 border-white/20 hover:bg-white/10">
          Change module
        </Button>
      </CardHeader>
      
      <CardContent className="p-0 space-y-8">
        
        {/* Key Insights Bar */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-white/5 rounded-lg border border-white/10">
          <div className="text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Award className="h-4 w-4 text-white/70" />
              <span className="text-white/70 text-sm">Best Value</span>
            </div>
            <div className="text-white font-medium">{cheapestProvider.provider}</div>
            <div className="text-white/70 text-xs">Avg ${cheapestProvider.avg_vm_price.toFixed(3)}/hr</div>
          </div>
          
          <div className="text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-white/70" />
              <span className="text-white/70 text-sm">Potential Savings</span>
            </div>
            <div className="text-white font-medium">${monthlySavings.toLocaleString()}</div>
            <div className="text-white/70 text-xs">per month</div>
          </div>
          
          <div className="text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Zap className="h-4 w-4 text-white/70" />
              <span className="text-white/70 text-sm">Total Resources</span>
            </div>
            <div className="text-white font-medium">{totalVMs.toLocaleString()}</div>
            <div className="text-white/70 text-xs">VM instances</div>
          </div>
        </div>

        {/* Provider Comparison Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {providersWithScores.map((provider) => {
            const trend = getTrendIcon(provider.provider)
            // Ensure mutually exclusive badges - prioritize lowest cost
            const isLowest = provider.provider === cheapestProvider.provider && sortedProviders.length > 1
            const isHighest = provider.provider === mostExpensiveProvider.provider && !isLowest && sortedProviders.length > 1
            
            return (
              <div key={provider.provider} className="p-6 rounded-lg border bg-white/5 border-white/10 relative">
                
                {/* Status Badge */}
                {isLowest && (
                  <div className="absolute top-3 right-3 bg-white/10 text-white px-2 py-1 rounded-full text-xs border border-white/20">
                    LOWEST COST
                  </div>
                )}
                {isHighest && (
                  <div className="absolute top-3 right-3 bg-white/10 text-white/70 px-2 py-1 rounded-full text-xs border border-white/20">
                    HIGHEST COST
                  </div>
                )}
                
                {/* Provider Header */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 ${getProviderColor(provider.provider)} rounded-full`}></div>
                    <span className="text-white font-medium text-lg">{provider.provider}</span>
                  </div>
                  {!isLowest && !isHighest && (
                    <div className={`${trend.color}`}>
                      <trend.icon className="h-4 w-4" />
                    </div>
                  )}
                </div>

                {/* Cost Display */}
                <div className="mb-4">
                  <div className="text-white text-2xl font-light mb-1">
                    ${provider.monthlyMin.toLocaleString()}–${provider.monthlyMax.toLocaleString()}
                  </div>
                  <div className="text-white/50 text-sm">USD per month</div>
                </div>

                {/* Visual Cost Bar */}
                <div className="mb-4">
                  <div className="flex justify-between text-xs text-white/60 mb-2">
                    <span>Cost Range</span>
                    <span>Avg: ${provider.monthlyAvg.toLocaleString()}</span>
                  </div>
                  <div className="bg-white/10 rounded-full h-2 overflow-hidden">
                    <div 
                      className="h-full bg-white rounded-full transition-all duration-700"
                      style={{ width: `${(provider.avg_vm_price / maxAvgPrice) * 100}%` }}
                    ></div>
                  </div>
                </div>

                {/* Key Metrics */}
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-white/70">Market Share</span>
                    <span className="text-white">{provider.marketShare.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/70">VM Instances</span>
                    <span className="text-white">{provider.vm_count.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/70">Storage Services</span>
                    <span className="text-white">{provider.storage_services}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/70">Regions</span>
                    <span className="text-white">{provider.regions.length}</span>
                  </div>
                </div>

                {/* Efficiency Score */}
                <div className="mt-4 pt-4 border-t border-white/10">
                  <div className="text-white/70 text-xs mb-2">Cost Efficiency Score</div>
                  <div className="flex items-center gap-2">
                    <div className="bg-white/10 rounded-full h-1.5 flex-1 overflow-hidden">
                      <div 
                        className="h-full bg-white rounded-full transition-all duration-700"
                        style={{ width: `${Math.min((provider.costEfficiency / Math.max(...providersWithScores.map(p => p.costEfficiency))) * 100, 100)}%` }}
                      ></div>
                    </div>
                    <span className="text-white text-sm font-medium">
                      {Math.round(provider.costEfficiency)}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

      </CardContent>
    </Card>
  )
} 