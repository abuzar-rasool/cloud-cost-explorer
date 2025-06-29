import { Suspense } from 'react'
import { notFound } from 'next/navigation'
import { getVMComparison, getStorageComparison, getPriceDistribution } from '@/services/dashboard'
import { ComparisonTable } from '@/components/dashboard/comparison-table'
import { CostChart } from '@/components/dashboard/cost-chart'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowLeft, TrendingUp, Server, Database } from 'lucide-react'
import Link from 'next/link'
import { Provider } from '@/types'

interface ProviderPageProps {
  params: Promise<{
    provider: string
  }>
}

async function ProviderContent({ provider }: { provider: Provider }) {
  const [vmData, storageData, priceDistribution] = await Promise.all([
    getVMComparison([provider], undefined, 100),
    getStorageComparison([provider], undefined, 50),
    getPriceDistribution(provider),
  ])

  const avgPrice = priceDistribution.reduce((sum, item) => sum + item.price_per_hour_usd, 0) / priceDistribution.length
  const minPrice = Math.min(...priceDistribution.map(item => item.price_per_hour_usd))
  const maxPrice = Math.max(...priceDistribution.map(item => item.price_per_hour_usd))

  const providerStats = [{
    provider,
    vm_count: priceDistribution.length,
    storage_services: storageData.length,
    avg_vm_price: avgPrice,
    min_vm_price: minPrice,
    max_vm_price: maxPrice,
    avg_storage_price: 0,
    regions: [...new Set(vmData.map(vm => vm.region))],
  }]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link href="/">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">{provider} Cloud Analysis</h1>
            <p className="text-muted-foreground">Detailed cost analysis and comparison for {provider}</p>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="flex items-center justify-center p-6">
            <div className="text-center">
              <Server className="h-8 w-8 mx-auto mb-2 text-blue-600" />
              <p className="text-2xl font-bold">{vmData.length}</p>
              <p className="text-sm text-muted-foreground">VM Instances</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-center p-6">
            <div className="text-center">
              <Database className="h-8 w-8 mx-auto mb-2 text-green-600" />
              <p className="text-2xl font-bold">{storageData.length}</p>
              <p className="text-sm text-muted-foreground">Storage Options</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-center p-6">
            <div className="text-center">
              <TrendingUp className="h-8 w-8 mx-auto mb-2 text-orange-600" />
              <p className="text-2xl font-bold">${avgPrice.toFixed(3)}</p>
              <p className="text-sm text-muted-foreground">Avg Price/Hr</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-center p-6">
            <div className="text-center">
              <TrendingUp className="h-8 w-8 mx-auto mb-2 text-purple-600" />
              <p className="text-2xl font-bold">{providerStats[0].regions.length}</p>
              <p className="text-sm text-muted-foreground">Regions</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <section>
        <h2 className="text-2xl font-semibold mb-6">Cost Analysis</h2>
        <CostChart data={providerStats} />
      </section>

      {/* Detailed Comparison */}
      <section>
        <h2 className="text-2xl font-semibold mb-6">Detailed Service Comparison</h2>
        <ComparisonTable 
          vmData={vmData}
          storageData={storageData}
          onFiltersChange={() => {
            // Provider-specific filtering logic
          }}
        />
      </section>
    </div>
  )
}

function LoadingFallback() {
  return (
    <div className="space-y-8">
      <div className="animate-pulse">
        <div className="h-10 bg-gray-200 rounded w-64 mb-4"></div>
        <div className="h-6 bg-gray-200 rounded w-96"></div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-16 bg-gray-200 rounded"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default async function ProviderPage({ params }: ProviderPageProps) {
  const resolvedParams = await params
  const provider = resolvedParams.provider.toUpperCase() as Provider
  
  if (!['AWS', 'AZURE', 'GCP'].includes(provider)) {
    notFound()
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <Suspense fallback={<LoadingFallback />}>
          <ProviderContent provider={provider} />
        </Suspense>
      </div>
    </div>
  )
} 