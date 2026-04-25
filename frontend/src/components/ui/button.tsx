import { type ButtonHTMLAttributes, forwardRef } from 'react'
import { cn } from '../../lib/utils'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'destructive'
  size?: 'sm' | 'default' | 'icon'
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    const base =
      'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-gray-400 disabled:pointer-events-none disabled:opacity-50'
    const variants: Record<string, string> = {
      default: 'bg-gray-900 text-white hover:bg-gray-800',
      outline: 'border border-gray-300 bg-white hover:bg-gray-50',
      ghost: 'hover:bg-gray-100',
      destructive: 'bg-red-600 text-white hover:bg-red-700',
    }
    const sizes: Record<string, string> = {
      sm: 'h-8 px-3 text-xs',
      default: 'h-9 px-4',
      icon: 'h-9 w-9',
    }
    return (
      <button ref={ref} className={cn(base, variants[variant], sizes[size], className)} {...props} />
    )
  },
)
Button.displayName = 'Button'
export { Button }
export type { ButtonProps }
