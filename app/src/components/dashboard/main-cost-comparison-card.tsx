'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ProviderStats } from '@/types'
import { BarChart } from 'lucide-react'

interface MainCostComparisonCardProps {
  providerStats: ProviderStats[]
}

export function MainCostComparisonCard({ providerStats }: MainCostComparisonCardProps) {
  // Early return if no data
  if (!providerStats || providerStats.length === 0) {
    return (
      <Card className="bg-card/80 backdrop-blur-sm border-white/10 h-full">
        <CardContent className="p-8 text-center text-white/70">
          No provider data available for comparison
        </CardContent>
      </Card>
    );
  }
  
  // Find min/max prices across all providers
  const minPrices = providerStats.map(p => p.min_vm_price);
  const maxPrices = providerStats.map(p => p.max_vm_price);
  const avgPrices = providerStats.map(p => p.avg_vm_price);
  
  const lowestPrice = Math.min(...minPrices);
  const highestPrice = Math.max(...maxPrices);
  const priceRange = highestPrice - lowestPrice;
  
  // Calculate savings
  const maxAvgPrice = Math.max(...avgPrices);
  const minAvgPrice = Math.min(...avgPrices);
  const potentialSavings = maxAvgPrice - minAvgPrice;

  // Find provider with lowest average price
  const bestProvider = providerStats.find(p => p.avg_vm_price === minAvgPrice);

  // Sort providers by average price (low to high)
  const sortedProviders = [...providerStats].sort((a, b) => a.avg_vm_price - b.avg_vm_price);

  // Get some stats about the comparison
  const totalVMs = providerStats.reduce((sum, p) => sum + p.vm_count, 0);
  
  return (
    <Card className="bg-card/80 backdrop-blur-sm border-white/10">
      <CardHeader>
        <CardTitle className="text-white text-lg font-medium flex items-center gap-2">
          <BarChart className="h-5 w-5" />
          Cloud Cost Comparison
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Main price comparison */}
        <div className="space-y-4">
          {sortedProviders.map((provider) => {
            // Calculate width of the price bars relative to the global price range
            const minWidth = ((provider.min_vm_price - lowestPrice) / priceRange) * 100;
            const rangeWidth = ((provider.max_vm_price - provider.min_vm_price) / priceRange) * 100;
            const avgPosition = ((provider.avg_vm_price - lowestPrice) / priceRange) * 100;
            
            return (
              <div key={provider.provider} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${
                      provider.provider === 'AWS' ? 'bg-orange-500' :
                      provider.provider === 'AZURE' ? 'bg-blue-500' : 'bg-green-500'
                    }`}></div>
                    <span className="text-white font-medium">{provider.provider}</span>
                    {provider === bestProvider && (
                      <span className="bg-green-500/20 text-green-400 px-2 py-0.5 text-xs rounded-full">
                        Best Value
                      </span>
                    )}
                  </div>
                  <span className="text-white">
                    ${provider.min_vm_price.toFixed(3)} - ${provider.max_vm_price.toFixed(3)}
                  </span>
                </div>
                
                {/* Price range bars */}
                <div className="relative h-4 bg-white/5 rounded-full overflow-hidden">
                  {/* Minimum price marker */}
                  <div className="absolute top-0 bottom-0 left-0 bg-white/10 h-full"
                    style={{ width: `${minWidth}%` }}></div>
                  
                  {/* Price range bar */}
                  <div className="absolute top-0 bottom-0 h-full bg-white/20"
                    style={{ 
                      left: `${minWidth}%`, 
                      width: `${rangeWidth}%` 
                    }}></div>
                  
                  {/* Average price marker */}
                  <div className="absolute top-0 bottom-0 w-1 bg-white"
                    style={{ 
                      left: `${avgPosition}%`,
                      transform: 'translateX(-50%)',
                      height: '100%'
                    }}></div>
                </div>
                
                <div className="flex justify-between text-xs text-white/50">
                  <span>Min: ${provider.min_vm_price.toFixed(3)}/hr</span>
                  <span>Avg: ${provider.avg_vm_price.toFixed(3)}/hr</span>
                  <span>Max: ${provider.max_vm_price.toFixed(3)}/hr</span>
                </div>
              </div>
            );
          })}
        </div>
        
        {/* Additional metrics */}
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="bg-white/5 rounded-lg p-4">
            <div className="text-white/70 text-xs mb-2">Price Range</div>
            <div className="text-white font-light">
              ${lowestPrice.toFixed(3)} - ${highestPrice.toFixed(3)}
            </div>
            <div className="text-white/50 text-xs">per hour</div>
          </div>
          
          <div className="bg-white/5 rounded-lg p-4">
            <div className="text-white/70 text-xs mb-2">Avg Difference</div>
            <div className="text-white font-light">
              ${potentialSavings.toFixed(3)}
            </div>
            <div className="text-white/50 text-xs">per VM hour</div>
          </div>
          
          <div className="bg-white/5 rounded-lg p-4">
            <div className="text-white/70 text-xs mb-2">Analyzed VMs</div>
            <div className="text-white font-light">
              {totalVMs.toLocaleString()}
            </div>
            <div className="text-white/50 text-xs">instances</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
} 