'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { getProviderColor } from '@/lib/utils'
import { ProviderStats } from '@/types'

interface CostChartProps {
  data: ProviderStats[]
}

export function CostChart({ data }: CostChartProps) {
  const chartData = data.map(stat => ({
    name: stat.provider,
    avgPrice: stat.avg_vm_price,
    minPrice: stat.min_vm_price,
    maxPrice: stat.max_vm_price,
    vmCount: stat.vm_count,
    storageServices: stat.storage_services,
  }))

  const pieData = data.map(stat => ({
    name: stat.provider,
    value: stat.vm_count,
    color: getProviderColor(stat.provider),
  }))

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card>
        <CardHeader>
          <CardTitle>VM Pricing Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis 
                tickFormatter={(value) => `$${value.toFixed(2)}`}
              />
              <Tooltip 
                formatter={(value: number) => [`$${value.toFixed(4)}`, 'Price/Hour']}
              />
              <Legend />
              <Bar dataKey="minPrice" fill="#10B981" name="Min Price" />
              <Bar dataKey="avgPrice" fill="#3B82F6" name="Avg Price" />
              <Bar dataKey="maxPrice" fill="#EF4444" name="Max Price" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>VM Distribution by Provider</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => [value.toLocaleString(), 'VM Instances']} />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
} 