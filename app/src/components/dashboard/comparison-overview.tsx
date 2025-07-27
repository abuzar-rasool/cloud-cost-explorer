'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ProviderStats } from '@/types'
import { TrendingDown, DollarSign, Server, Zap, Info } from 'lucide-react'

interface ComparisonOverviewProps {
  providerStats: ProviderStats[]
}

export function ComparisonOverview({ providerStats }: ComparisonOverviewProps) {
  // Early return if no data
  if (!providerStats || providerStats.length === 0) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        <Card className="bg-card/80 backdrop-blur-sm border-white/10 lg:col-span-3">
          <CardContent className="p-8 text-center text-white/70">
            No provider data available for comparison
          </CardContent>
        </Card>
      </div>
    )
  }

  // Sort providers for consistent ordering
  const sortedProviderStats = [...providerStats].sort((a, b) => a.provider.localeCompare(b.provider))
  
  // Find best and worst pricing  
  const bestPrice = sortedProviderStats.length > 0 ? Math.min(...sortedProviderStats.map(p => p.min_vm_price)) : 0
  const worstPrice = sortedProviderStats.length > 0 ? Math.max(...sortedProviderStats.map(p => p.max_vm_price)) : 0
  const bestProvider = sortedProviderStats.find(p => p.min_vm_price === bestPrice)
  
  // Calculate potential savings with fixed precision
  const avgPrices = sortedProviderStats.map(p => p.avg_vm_price)
  const maxAvgPrice = avgPrices.length > 0 ? Math.max(...avgPrices) : 0
  const minAvgPrice = avgPrices.length > 0 ? Math.min(...avgPrices) : 0
  const potentialSavings = Number((maxAvgPrice - minAvgPrice).toFixed(6))
  const savingsPercentage = maxAvgPrice > 0 ? ((potentialSavings / maxAvgPrice) * 100).toFixed(1) : '0.0'
  
  // Calculate monthly and yearly savings
  const hourlyDiff = potentialSavings
  const dailySavings = hourlyDiff * 24
  const monthlySavings = dailySavings * 30
  
  // Assumptions for savings calculations
  const assumedVMCount = 100
  const totalPotentialMonthly = monthlySavings * assumedVMCount

  // Performance metrics
  const totalVMs = sortedProviderStats.reduce((sum, p) => sum + p.vm_count, 0)
  const totalServices = sortedProviderStats.reduce((sum, p) => sum + p.storage_services, 0)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
      
      {/* Provider Head-to-Head Comparison */}
      <Card className="bg-card/80 backdrop-blur-sm border-white/10 lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-white text-lg font-medium flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Provider Cost Comparison
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {sortedProviderStats.map((provider, idx) => {
              const isLowest = provider.min_vm_price === bestPrice
              
              return (
                <div key={provider.provider} className="relative">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${
                        provider.provider === 'AWS' ? 'bg-orange-500' :
                        provider.provider === 'AZURE' ? 'bg-blue-500' : 'bg-green-500'
                      }`}></div>
                      <span className="text-white font-medium">{provider.provider}</span>
                      {isLowest && (
                        <span className="bg-green-500/20 text-green-400 px-2 py-1 rounded-full text-xs border border-green-500/30">
                          LOWEST COST
                        </span>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="text-white text-lg font-light">
                        ${provider.min_vm_price.toFixed(3)} - ${provider.max_vm_price.toFixed(3)}
                      </div>
                      <div className="text-white/50 text-xs">per hour range</div>
                    </div>
                  </div>
                  
                  {/* Cost breakdown bars */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-white/70">Average Cost</span>
                      <span className="text-white">${provider.avg_vm_price.toFixed(3)}/hr</span>
                    </div>
                    <div className="bg-white/10 rounded-full h-2 overflow-hidden">
                      <div 
                        className="h-full bg-white rounded-full transition-all duration-500"
                        style={{ width: `${(provider.avg_vm_price / worstPrice) * 100}%` }}
                      ></div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-xs text-white/60 mt-2">
                      <div>VM Count: {provider.vm_count.toLocaleString()}</div>
                      <div>Storage Services: {provider.storage_services}</div>
                    </div>
                  </div>
                  
                  {idx < sortedProviderStats.length - 1 && (
                    <div className="border-b border-white/10 mt-4"></div>
                  )}
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Cost Savings Opportunities */}
      <Card className="bg-card/80 backdrop-blur-sm border-white/10">
        <CardHeader>
          <CardTitle className="text-white text-lg font-medium flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-green-400" />
            Savings Opportunities
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="text-center">
            <div className="text-3xl font-light text-white mb-1">
              {savingsPercentage}%
            </div>
            <div className="text-white/50 text-sm">Potential Savings</div>
            <div className="text-green-400 text-sm mt-2">
              Up to ${potentialSavings.toFixed(3)}/hr difference
            </div>
          </div>
          
          <div className="space-y-3">
            <div className="bg-white/5 rounded-lg p-3">
              <div className="text-white/70 text-sm mb-1">Best Value Provider</div>
              <div className="text-white font-medium">{bestProvider?.provider}</div>
              <div className="text-green-400 text-xs">From ${bestPrice.toFixed(3)}/hr</div>
            </div>
            
            <div className="bg-white/5 rounded-lg p-3">
              <div className="text-white/70 text-sm mb-1">Savings Projection</div>
              <div className="text-white font-medium">
                ${totalPotentialMonthly.toLocaleString(undefined, {maximumFractionDigits: 2})} / month
              </div>
              <div className="text-white/50 text-xs">For 100 VMs running 24/7</div>
            </div>

            {/* New section with calculation details */}
            <div className="bg-white/5 rounded-lg p-3">
              <div className="flex items-center gap-1 text-white/70 text-sm mb-2">
                <Info className="h-3.5 w-3.5" />
                <div>Calculation Method</div>
              </div>
              <div className="text-white/60 text-xs space-y-1">
                <p>• Based on average price difference between highest and lowest cost providers</p>
                <p>• Hourly: ${hourlyDiff.toFixed(3)} per VM</p>
                <p>• Daily: ${dailySavings.toFixed(2)} per VM</p>
                <p>• Yearly: ${(dailySavings * 365).toFixed(2)} per VM</p>
              </div>
            </div>
          </div>

          {/* Assumptions section */}
          <div className="border-t border-white/10 pt-3">
            <div className="text-white/70 text-xs mb-2 font-medium">Key Assumptions</div>
            <div className="text-white/60 text-xs space-y-2">
              <div className="flex justify-between">
                <span>• Based on comparable VM specs across providers</span>
              </div>
              <div className="flex justify-between">
                <span>• Assumes constant usage (24/7)</span>
              </div>
              <div className="flex justify-between">
                <span>• Excludes data transfer costs</span>
              </div>
              <div className="flex justify-between">
                <span>• Doesn&apos;t account for spot/reserved pricing</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Performance Overview */}
      <Card className="bg-card/80 backdrop-blur-sm border-white/10 lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-white text-lg font-medium flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Performance vs Cost Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-6">
            {sortedProviderStats.map((provider) => {
              // Calculate performance score based on VM count and average specs
              const performanceScore = totalVMs > 0 ? (provider.vm_count / totalVMs) * 100 : 0
              const costEfficiency = provider.avg_vm_price > 0 ? (1 / provider.avg_vm_price) * 100 : 0
              
              return (
                <div key={provider.provider} className="text-center">
                  <div className={`w-4 h-4 rounded-full mx-auto mb-2 ${
                    provider.provider === 'AWS' ? 'bg-orange-500' :
                    provider.provider === 'AZURE' ? 'bg-blue-500' : 'bg-green-500'
                  }`}></div>
                  <div className="text-white font-medium mb-3">{provider.provider}</div>
                  
                  <div className="space-y-3">
                    <div>
                      <div className="text-white/70 text-xs mb-1">Market Coverage</div>
                      <div className="bg-white/10 rounded-full h-1.5 overflow-hidden">
                        <div 
                          className="h-full bg-white rounded-full"
                          style={{ width: `${performanceScore}%` }}
                        ></div>
                      </div>
                      <div className="text-white text-sm mt-1">{performanceScore.toFixed(1)}%</div>
                    </div>
                    
                    <div>
                      <div className="text-white/70 text-xs mb-1">Cost Efficiency</div>
                      <div className="bg-white/10 rounded-full h-1.5 overflow-hidden">
                        <div 
                          className="h-full bg-white rounded-full"
                          style={{ width: `${Math.min(costEfficiency, 100)}%` }}
                        ></div>
                      </div>
                      <div className="text-white text-sm mt-1">{costEfficiency.toFixed(0)}</div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <Card className="bg-card/80 backdrop-blur-sm border-white/10">
        <CardHeader>
          <CardTitle className="text-white text-lg font-medium flex items-center gap-2">
            <Server className="h-5 w-5" />
            Quick Stats
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="bg-white/5 rounded-lg p-3 text-center">
              <div className="text-white text-lg font-light">{totalVMs.toLocaleString()}</div>
              <div className="text-white/50">Total VMs</div>
            </div>
            <div className="bg-white/5 rounded-lg p-3 text-center">
              <div className="text-white text-lg font-light">{totalServices}</div>
              <div className="text-white/50">Storage Services</div>
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-white/70 text-sm">Price Range</span>
              <span className="text-white text-sm">${bestPrice.toFixed(3)} - ${worstPrice.toFixed(3)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/70 text-sm">Avg Difference</span>
              <span className="text-white text-sm">${potentialSavings.toFixed(3)}/hr</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
} 