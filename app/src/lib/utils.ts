import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(amount)
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num)
}

export function getProviderColor(provider: string): string {
  switch (provider.toUpperCase()) {
    case 'AWS':
      return '#FF9900'
    case 'AZURE':
      return '#0078D4'
    case 'GCP':
      return '#4285F4'
    default:
      return '#6B7280'
  }
}

export function getProviderBgColor(provider: string): string {
  switch (provider.toUpperCase()) {
    case 'AWS':
      return 'bg-orange-100 text-orange-800'
    case 'AZURE':
      return 'bg-blue-100 text-blue-800'
    case 'GCP':
      return 'bg-indigo-100 text-indigo-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
} 