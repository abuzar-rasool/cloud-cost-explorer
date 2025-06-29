'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { VMComparisonData } from '@/types'
import { Award, Cpu, HardDrive, DollarSign } from 'lucide-react'

interface BestValueMatrixProps {
  vmData: VMComparisonData[]
}

interface ValueCategory {
  label: string
  icon: React.ReactNode
  vm: VMComparisonData
  value: string
}

export function BestValueMatrix({ vmData }: BestValueMatrixProps) {
  // Early return if no data
  if (!vmData || vmData.length === 0) {
    return (
      <Card className="bg-card/80 backdrop-blur-sm border-white/10">
        <CardHeader>
          <CardTitle className="text-white text-lg font-medium flex items-center gap-2">
            <Award className="h-5 w-5" />
            Best Value Matrix
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-white/70 py-8">
            No data available for value analysis
          </div>
        </CardContent>
      </Card>
    )
  }

  // Find best values in different categories with stable sorting
  const findBestValue = (sortFn: (a: VMComparisonData, b: VMComparisonData) => number, label: string, icon: React.ReactNode, valueFormatter: (vm: VMComparisonData) => string): ValueCategory | null => {
    const sorted = [...vmData].sort((a, b) => {
      const result = sortFn(a, b)
      // Add secondary sort for stability
      return result !== 0 ? result : a.vm_name.localeCompare(b.vm_name)
    })
    
    if (sorted.length === 0) return null
    
    return {
      label,
      icon,
      vm: sorted[0],
      value: valueFormatter(sorted[0])
    }
  }

  const categories = [
    findBestValue(
      (a, b) => a.price_per_hour_usd - b.price_per_hour_usd, 
      'Lowest Cost', 
      <DollarSign className="h-4 w-4" />,
      (vm) => `$${vm.price_per_hour_usd.toFixed(3)}/hr`
    ),
    findBestValue(
      (a, b) => (b.virtual_cpu_count / b.price_per_hour_usd) - (a.virtual_cpu_count / a.price_per_hour_usd), 
      'Best CPU Value', 
      <Cpu className="h-4 w-4" />,
      (vm) => `${(vm.virtual_cpu_count / vm.price_per_hour_usd).toFixed(1)} CPU/$`
    ),
    findBestValue(
      (a, b) => (b.memory_gb / b.price_per_hour_usd) - (a.memory_gb / a.price_per_hour_usd), 
      'Best Memory Value', 
      <HardDrive className="h-4 w-4" />,
      (vm) => `${(vm.memory_gb / vm.price_per_hour_usd).toFixed(1)} GB/$`
    ),
  ].filter((category): category is ValueCategory => category !== null) // Remove null entries if no data

  return (
    <Card className="bg-card/80 backdrop-blur-sm border-white/10">
      <CardHeader>
        <CardTitle className="text-white text-lg font-medium flex items-center gap-2">
          <Award className="h-5 w-5" />
          Best Value Matrix
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {categories.map((category, idx) => (
            <div key={idx} className="relative">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 text-white/70">
                  {category.icon}
                  <span className="text-sm font-medium">{category.label}</span>
                </div>
                <div className="text-green-400 text-sm font-medium">
                  {category.value}
                </div>
              </div>
              
              <div className="bg-white/5 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      category.vm.provider === 'AWS' ? 'bg-orange-500' :
                      category.vm.provider === 'AZURE' ? 'bg-blue-500' : 'bg-green-500'
                    }`}></div>
                    <span className="text-white font-medium text-sm">{category.vm.provider}</span>
                  </div>
                  <span className="text-white/70 text-xs capitalize">
                    {category.vm.region.replace('_', ' ')}
                  </span>
                </div>
                
                <div className="text-white text-sm mb-1">{category.vm.vm_name}</div>
                <div className="flex items-center gap-4 text-xs text-white/60">
                  <span>{category.vm.virtual_cpu_count} CPU</span>
                  <span>{category.vm.memory_gb} GB RAM</span>
                  <span>{category.vm.os_type}</span>
                </div>
              </div>
              
              {idx < categories.length - 1 && (
                <div className="border-b border-white/10 mt-4"></div>
              )}
            </div>
          ))}
        </div>
        
        <div className="mt-6 pt-4 border-t border-white/10 text-center">
          <div className="text-white/70 text-sm mb-2">Total VMs Analyzed</div>
          <div className="text-white text-2xl font-light">{vmData.length.toLocaleString()}</div>
          <div className="text-white/50 text-xs">Across all providers and regions</div>
        </div>
      </CardContent>
    </Card>
  )
} 