'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { Button } from './button';
import { AlertCircle, Search, MapPin, RefreshCw } from 'lucide-react';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center p-8 text-center', className)}>
      {icon && (
        <div className="mb-4 rounded-full bg-background-secondary p-4 text-foreground-muted">
          {icon}
        </div>
      )}
      <h3 className="mb-1 text-lg font-semibold text-foreground">{title}</h3>
      {description && (
        <p className="mb-4 max-w-sm text-sm text-foreground-secondary">{description}</p>
      )}
      {action && (
        <Button variant="secondary" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}

function NoResults({ query, onClear }: { query?: string; onClear?: () => void }) {
  return (
    <EmptyState
      icon={<Search className="h-6 w-6" />}
      title="No results found"
      description={query ? `No locations matching "${query}"` : 'Try adjusting your search'}
      action={onClear ? { label: 'Clear search', onClick: onClear } : undefined}
    />
  );
}

function NoLocation({ onSelect }: { onSelect?: () => void }) {
  return (
    <EmptyState
      icon={<MapPin className="h-6 w-6" />}
      title="No location selected"
      description="Select a location on the globe to view detailed risk information"
      action={onSelect ? { label: 'Search locations', onClick: onSelect } : undefined}
    />
  );
}

function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <EmptyState
      icon={<AlertCircle className="h-6 w-6" />}
      title="Something went wrong"
      description={message || 'Unable to load data. Please try again.'}
      action={onRetry ? { label: 'Try again', onClick: onRetry } : undefined}
    />
  );
}

function LoadingState({ message }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <RefreshCw className="mb-4 h-8 w-8 animate-spin text-primary" />
      <p className="text-sm text-foreground-secondary">{message || 'Loading...'}</p>
    </div>
  );
}

export { EmptyState, NoResults, NoLocation, ErrorState, LoadingState };
