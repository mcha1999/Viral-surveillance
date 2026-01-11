'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-white',
        secondary: 'border-transparent bg-background-secondary text-foreground',
        outline: 'border-border text-foreground',
        // Risk levels
        low: 'border-risk-low/30 bg-risk-low/20 text-risk-low',
        moderate: 'border-risk-moderate/30 bg-risk-moderate/20 text-risk-moderate',
        elevated: 'border-risk-elevated/30 bg-risk-elevated/20 text-risk-elevated',
        high: 'border-risk-high/30 bg-risk-high/20 text-risk-high',
        'very-high': 'border-risk-very-high/30 bg-risk-very-high/20 text-risk-very-high',
        // Freshness
        current: 'border-freshness-current/30 bg-freshness-current/20 text-freshness-current',
        stale: 'border-freshness-stale/30 bg-freshness-stale/20 text-freshness-stale',
        old: 'border-freshness-old/30 bg-freshness-old/20 text-freshness-old',
      },
      size: {
        default: 'px-2.5 py-0.5 text-xs',
        sm: 'px-2 py-0.5 text-[10px]',
        lg: 'px-3 py-1 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant, size }), className)} {...props} />;
}

export { Badge, badgeVariants };
