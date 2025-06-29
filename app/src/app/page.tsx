import { Suspense } from 'react'
import { getProviderStats, getVMComparison, getStorageComparison } from '@/services/dashboard'
import { ComparisonOverview } from '@/components/dashboard/comparison-overview'
import { RegionalCostComparison } from '@/components/dashboard/regional-cost-comparison'
import { BestValueMatrix } from '@/components/dashboard/best-value-matrix'
import { MainCostComparisonCard } from '@/components/dashboard/main-cost-comparison-card'
import { Navigation } from '@/components/dashboard/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Server } from 'lucide-react'

async function DashboardContent() {
  const [providerStats, vmData, storageData] = await Promise.all([
    getProviderStats(),
    getVMComparison(undefined, undefined, 50),
    getStorageComparison(undefined, undefined, 30),
  ])

  const totalVMs = providerStats.reduce((sum, provider) => sum + provider.vm_count, 0)
  const totalStorageServices = providerStats.reduce((sum, provider) => sum + provider.storage_services, 0)

  return (
    <div className="space-y-8">
      {/* Overview Header */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-medium text-white">Overview</h1>
        <div className="text-white/70 text-right">
          <div className="text-2xl font-medium text-white">{new Date().toLocaleDateString('en-US', { day: 'numeric', month: 'long' })}</div>
        </div>
      </div>

      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        
        {/* Main Cost Comparison Card */}
        <div className="lg:col-span-2">
          <MainCostComparisonCard providerStats={providerStats} />
        </div>

        {/* Right Column - Provider Connections & Recommendations */}
        <div className="space-y-6">
          {/* Provider Connections */}
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
                {providerStats.map((stat) => (
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

          {/* Recommendations */}
          <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <CardTitle className="text-white text-lg font-medium">Recommendations</CardTitle>
              <Button variant="ghost" size="sm" className="text-white/50 hover:text-white p-1">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                </svg>
              </Button>
            </CardHeader>
            <CardContent className="p-0 space-y-4">
              <div className="text-white/70 text-sm">Cost optimization insights</div>
              
              <div className="bg-white/5 rounded-lg p-4">
                <div className="text-white text-sm mb-2">
                  Cheapest option: ${Math.min(...providerStats.map(p => p.min_vm_price)).toFixed(3)}/hour
                </div>
                <div className="text-white/50 text-xs mb-3">
                  {providerStats.find(p => p.min_vm_price === Math.min(...providerStats.map(s => s.min_vm_price)))?.provider} offers lowest VM pricing
                </div>
              </div>
              
              <div className="text-white/70 text-sm">
                <div className="mb-1">
                  Avg cost difference: ${(Math.max(...providerStats.map(p => p.avg_vm_price)) - Math.min(...providerStats.map(p => p.avg_vm_price))).toFixed(3)}/hour
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/50 text-xs">Analysis</span>
                  <span className="text-white/50 text-xs">Live</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Bottom Grid - Tracking, Detailed Report, Cost Optimization */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Workload Analysis Card */}
        <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6">
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <CardTitle className="text-white text-lg font-medium">Workload Analysis</CardTitle>
            <Button variant="ghost" size="sm" className="text-white/50 hover:text-white p-1">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
              </svg>
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <div className="text-white/70 text-sm mb-4">High-cost instances (&gt;$10/hr)</div>
            <div className="text-white text-4xl font-light mb-2">
              188,179
            </div>
            <div className="text-white/50 text-sm mb-4">VM instances</div>
            
            <div className="bg-white/5 rounded-lg p-3 mb-4">
              <div className="text-white/70 text-xs mb-1">Monthly impact</div>
              <div className="text-white text-lg font-medium">$4.31B</div>
              <div className="text-white/50 text-xs">potential optimization target</div>
            </div>
            
            <div className="text-white/70 text-xs">
              21.3% of total instances are high-cost workloads requiring optimization review
            </div>
          </CardContent>
        </Card>

        {/* Regional Cost Analysis */}
        <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6">
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <CardTitle className="text-white text-lg font-medium">Regional Cost Analysis</CardTitle>
            <Button variant="outline" size="sm" className="text-white/70 border-white/20 hover:bg-white/10">
              Regions ↓
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <div className="text-white/70 text-sm mb-4">Best value regions by provider</div>
            
            <div className="space-y-3 mb-4">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                  <span className="text-white text-sm">AZURE Asia</span>
                </div>
                <div className="text-right">
                  <div className="text-white text-sm">$5.59/hr</div>
                  <div className="text-white/50 text-xs">avg cost</div>
                </div>
              </div>
              
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                  <span className="text-white text-sm">AWS Asia</span>
                </div>
                <div className="text-right">
                  <div className="text-white text-sm">$8.67/hr</div>
                  <div className="text-white/50 text-xs">avg cost</div>
                </div>
              </div>
            </div>
            
            <div className="bg-white/5 rounded-lg p-3">
              <div className="text-white/70 text-xs mb-1">Savings opportunity</div>
              <div className="text-white text-sm">Move 35% workloads to Asia</div>
              <div className="text-white/50 text-xs">~$2.2K monthly savings per 100 instances</div>
            </div>
          </CardContent>
        </Card>

        {/* Storage Optimization Insights */}
        <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6">
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <CardTitle className="text-white text-lg font-medium">Storage Optimization</CardTitle>
            <Button variant="outline" size="sm" className="text-white/70 border-white/20 hover:bg-white/10">
              Analyze
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <div className="text-white/70 text-sm mb-4">Archive storage potential</div>
            <div className="text-white text-4xl font-light mb-4">
              92%
            </div>
            <div className="text-white/50 text-xs mb-4">
              cost reduction using archive tiers
            </div>
            
            <div className="space-y-2 mb-4">
              <div className="flex justify-between">
                <span className="text-white/70 text-xs">AWS Archive Instant</span>
                <span className="text-white text-xs">$0.005/GB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/70 text-xs">Standard Storage</span>
                <span className="text-white text-xs">$0.025/GB</span>
              </div>
            </div>
            
            <div className="bg-white/5 rounded-lg p-3">
              <div className="text-white/70 text-xs mb-1">Smart tiering available</div>
              <div className="text-white text-sm">649 storage services</div>
              <div className="text-white/50 text-xs">ready for optimization</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Comparisons Overview Section */}
      <div className="mt-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-medium text-white">Comparisons Overview</h2>
          <div className="text-white/50 text-sm">Real-time analysis</div>
        </div>
        
        <ComparisonOverview providerStats={providerStats} />
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <RegionalCostComparison vmData={vmData} />
          <BestValueMatrix vmData={vmData} />
        </div>
      </div>

      {/* Data Insights Section */}
      <div className="mt-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-medium text-white">Data Insights</h2>
          <Button variant="outline" size="sm" className="text-white/70 border-white/20 hover:bg-white/10">
            View detailed comparison
          </Button>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top VM Instances */}
          <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <CardTitle className="text-white text-lg font-medium">Most economical VMs</CardTitle>
              <span className="text-white/50 text-sm">{vmData.length} instances</span>
            </CardHeader>
            <CardContent className="p-0">
              <div className="space-y-3">
                {vmData.slice(0, 5).map((vm, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="w-2 h-2 rounded-full bg-white/70"></div>
                      <div>
                        <div className="text-white text-sm font-medium">{vm.vm_name}</div>
                        <div className="text-white/50 text-xs">
                          {vm.virtual_cpu_count} CPU • {vm.memory_gb}GB RAM • {vm.provider}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-white font-medium">${vm.price_per_hour_usd.toFixed(3)}</div>
                      <div className="text-white/50 text-xs">per hour</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Storage Comparison */}
          <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <CardTitle className="text-white text-lg font-medium">Storage pricing</CardTitle>
              <span className="text-white/50 text-sm">{storageData.length} services</span>
            </CardHeader>
            <CardContent className="p-0">
              <div className="space-y-3">
                {storageData.slice(0, 5).map((storage, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className="w-2 h-2 rounded-full bg-white/70"></div>
                      <div>
                        <div className="text-white text-sm font-medium">{storage.service_name}</div>
                        <div className="text-white/50 text-xs">
                          {storage.storage_class} • {storage.access_tier} • {storage.provider}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-white font-medium">${storage.capacity_price.toFixed(4)}</div>
                      <div className="text-white/50 text-xs">per GB</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
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
  return (
    <div className="min-h-screen bg-black">
      {/* Floating Navigation */}
      <Navigation />
      
      {/* Main Content with Padding */}
      <div className="px-6 pb-8">
        <Suspense fallback={<LoadingFallback />}>
          <DashboardContent />
        </Suspense>
      </div>
    </div>
  )
}
