"use client";

import { useState, useEffect } from 'react'
import { ComparisonOverview } from '@/components/dashboard/comparison-overview'
import { MainCostComparisonCard } from '@/components/dashboard/main-cost-comparison-card'
import { Navigation } from '@/components/dashboard/navigation'
import { RegionalPricingGraph } from '@/components/dashboard/regional-pricing-graph'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Server, RefreshCw } from 'lucide-react'
import { useProviderStats, useVMComparisonData, useStorageComparisonData } from '@/hooks/useDashboard'
import { useRegionalPricing } from '@/hooks/useRegionalPricing'
import { ProviderStats } from '@/types'

function DashboardContent({ refreshInterval }: { refreshInterval: number }) {
  // Use React Query hooks for data fetching
  const { data: providerStats, isLoading: isLoadingStats, refetch: refetchStats } = useProviderStats();
  const { data: vmData, isLoading: isLoadingVMs, refetch: refetchVMs } = useVMComparisonData(undefined, undefined, 50);
  const { data: storageData, isLoading: isLoadingStorage, refetch: refetchStorage } = useStorageComparisonData(undefined, undefined, 30);
  const { data: regionalPricing, isLoading: isLoadingRegionalPricing, refetch: refetchRegionalPricing } = useRegionalPricing();

  // Set up refresh interval
  useEffect(() => {
    if (!refreshInterval) return;

    // Set up interval for data refetching
    const intervalId = setInterval(() => {
      refetchStats();
      refetchVMs();
      refetchStorage();
      refetchRegionalPricing();
      console.log('Dashboard data refreshed at', new Date().toLocaleTimeString());
    }, refreshInterval);

    // Clean up interval on unmount or when refreshInterval changes
    return () => clearInterval(intervalId);
  }, [refreshInterval, refetchStats, refetchVMs, refetchStorage, refetchRegionalPricing]);

  // If any data is loading, show loading state
  if (isLoadingStats || isLoadingVMs || isLoadingStorage || isLoadingRegionalPricing || 
      !providerStats || !vmData || !storageData) {
    return <LoadingFallback />;
  }

  const totalVMs = providerStats.reduce((sum: number, provider: ProviderStats) => sum + provider.vm_count, 0)
  const totalStorageServices = providerStats.reduce((sum: number, provider: ProviderStats) => sum + provider.storage_services, 0)

  return (
    <div className="space-y-8">
      {/* Overview Header */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-medium text-white">Overview</h1>
        <div className="text-white/70 text-right">
          <div className="text-2xl font-medium text-white">{new Date().toLocaleDateString('en-US', { day: 'numeric', month: 'long' })}</div>
          {refreshInterval > 0 && (
            <div className="text-white/50 text-sm flex items-center justify-end gap-1">
              <RefreshCw size={12} className="animate-spin" />
              Auto-refreshing every {refreshInterval / 1000}s
            </div>
          )}
        </div>
      </div>

      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        
        {/* Main Cost Comparison Card */}
        <div className="lg:col-span-2">
          <MainCostComparisonCard providerStats={providerStats} />
        </div>

        {/* Provider Connections */}
        <div className="space-y-6">
          <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <CardTitle className="text-white text-lg font-medium">Provider connections</CardTitle>
              <Button variant="ghost" size="sm" className="text-white/50 hover:text-white p-1">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                </svg>
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="space-y-4">
                {providerStats.map((stat: ProviderStats) => (
                  <div key={stat.provider} className="flex items-center justify-between">
                    <span className="text-white/70 text-sm">{stat.provider}</span>
                    <span className="text-white text-sm">
                      {stat.vm_count > 0 ? 'Connected' : 'Disconnected'}
                    </span>
                  </div>
                ))}
              </div>
              
              {/* Provider Visualization */}
              <div className="bg-white/5 rounded-lg p-4 my-4 h-32 flex items-center justify-center border border-white/10">
                <div className="text-white/70 text-xs text-center">
                  <Server className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <div>{totalVMs.toLocaleString()} VM Instances</div>
                  <div>{totalStorageServices} Storage Services</div>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-white/70 text-sm">Total coverage</span>
                <div className="flex items-center gap-2">
                  <div className="bg-white/20 rounded-full h-1 w-16">
                    <div className="bg-white rounded-full h-1" style={{ width: `${Math.min((totalVMs / 1000) * 100, 100)}%` }}></div>
                  </div>
                  <span className="text-white text-sm font-medium">
                    {Math.min(Math.floor((totalVMs / 1000) * 100), 100)}%
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Comparisons Overview Section */}
      <div className="mt-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-medium text-white">Comparisons Overview</h2>
          <div className="text-white/50 text-sm">Real-time analysis</div>
        </div>
        
        <ComparisonOverview providerStats={providerStats} />
      </div>
      
      {/* Regional Pricing Graph */}
      <div className="mt-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-medium text-white">Regional Pricing Analysis</h2>
          <div className="text-white/50 text-sm">Average hourly rates</div>
        </div>
        
        <RegionalPricingGraph data={regionalPricing} />
      </div>
    </div>
  )
}

function LoadingFallback() {
  return (
    <div className="space-y-8">
      <div className="text-center py-8">
        <div className="animate-pulse">
          <div className="h-10 bg-white/20 rounded w-64 mx-auto mb-4"></div>
          <div className="h-6 bg-white/20 rounded w-96 mx-auto mb-6"></div>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="animate-pulse bg-white/5 border-white/10">
            <CardHeader>
              <div className="h-6 bg-white/20 rounded w-20"></div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="h-4 bg-white/20 rounded"></div>
                <div className="h-4 bg-white/20 rounded w-3/4"></div>
                <div className="h-4 bg-white/20 rounded w-1/2"></div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default function Home() {
  // Add refresh interval state - 0 means no refresh, 60000 means refresh every 60 seconds
  const [refreshInterval] = useState(0);
  
  return (
    <div className="min-h-screen bg-black">
      {/* Floating Navigation */}
      <Navigation />
      
      {/* Main Content with Padding */}
      <div className="px-6 pb-8">
        <DashboardContent refreshInterval={refreshInterval} />
      
      </div>
    </div>
  )
}
