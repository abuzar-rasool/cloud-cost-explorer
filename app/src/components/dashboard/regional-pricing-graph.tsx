"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useEffect, useRef, useMemo } from "react";
import { Chart, registerables } from "chart.js";
import { useRegionalPricing, RegionPriceData } from "@/hooks/useRegionalPricing";

// Register Chart.js components
Chart.register(...registerables);

interface RegionalPricingGraphProps {
  data?: RegionPriceData[];
}

export function RegionalPricingGraph({ data }: RegionalPricingGraphProps) {
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstance = useRef<Chart | null>(null);
  const { data: regionalPricing, isLoading, error, isError } = useRegionalPricing();

  // Use the data from props if provided, otherwise use the data from the hook
  const chartData = useMemo(() => data || regionalPricing || [], [data, regionalPricing]);

  useEffect(() => {
    if (!chartRef.current || chartData.length === 0) return;
    
    // Destroy previous chart instance if it exists
    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = chartRef.current.getContext('2d');
    if (!ctx) return;

    // Prepare data for chart
    const regions = chartData.map(item => item.region);
    
    // Create new chart
    chartInstance.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: regions,
        datasets: [
          {
            label: 'AWS',
            data: chartData.map(item => item.aws_price),
            backgroundColor: 'rgba(255, 153, 0, 0.7)',
            borderColor: 'rgba(255, 153, 0, 1)',
            borderWidth: 1
          },
          {
            label: 'Azure',
            data: chartData.map(item => item.azure_price),
            backgroundColor: 'rgba(0, 120, 215, 0.7)',
            borderColor: 'rgba(0, 120, 215, 1)',
            borderWidth: 1
          },
          {
            label: 'GCP',
            data: chartData.map(item => item.gcp_price),
            backgroundColor: 'rgba(52, 168, 83, 0.7)',
            borderColor: 'rgba(52, 168, 83, 1)',
            borderWidth: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: 'rgba(255, 255, 255, 0.7)',
              font: {
                family: 'system-ui'
              }
            }
          },
          title: {
            display: false
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = context.dataset.label || '';
                const value = context.raw as number;
                return `${label}: $${value.toFixed(3)}/hour`;
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
              color: 'rgba(255, 255, 255, 0.7)',
              callback: function(value) {
                return '$' + value + '/hr';
              }
            }
          },
          x: {
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
              color: 'rgba(255, 255, 255, 0.7)'
            }
          }
        }
      }
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [chartData]);

  if (isLoading) {
    return (
      <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6">
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <CardTitle className="text-white text-lg font-medium">Regional VM Pricing</CardTitle>
          <div className="text-white/50 text-xs">Loading data...</div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="h-80 flex items-center justify-center">
            <div className="animate-pulse flex flex-col items-center">
              <div className="h-8 w-32 bg-white/20 rounded mb-4"></div>
              <div className="h-4 w-64 bg-white/10 rounded"></div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6">
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <CardTitle className="text-white text-lg font-medium">Regional VM Pricing</CardTitle>
          <div className="text-white/50 text-xs">Error loading data</div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="h-80 flex items-center justify-center flex-col">
            <div className="text-white/70 text-center">
              <p className="mb-2">Unable to load regional pricing data.</p>
              <p className="text-xs text-white/50">{error instanceof Error ? error.message : 'Unknown error'}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!chartData || chartData.length === 0) {
    return (
      <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6">
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <CardTitle className="text-white text-lg font-medium">Regional VM Pricing</CardTitle>
          <div className="text-white/50 text-xs">No data available</div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="h-80 flex items-center justify-center">
            <div className="text-white/70">
              No regional pricing data available.
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-white/5 backdrop-blur-sm border-white/10 p-6">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <CardTitle className="text-white text-lg font-medium">Regional VM Pricing</CardTitle>
        <div className="text-white/50 text-xs">Average price per hour</div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="text-white/70 text-sm mb-4">Compare VM pricing across regions</div>
        <div className="h-80">
          <canvas ref={chartRef}></canvas>
        </div>
      </CardContent>
    </Card>
  );
} 