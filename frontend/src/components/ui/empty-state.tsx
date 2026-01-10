"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "./button";
import { MapPin, AlertTriangle, WifiOff, Search, Globe } from "lucide-react";

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

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-12 px-4 text-center", className)}>
      {icon && (
        <div className="mb-4 text-foreground-muted">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-foreground mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-foreground-secondary max-w-sm mb-6">{description}</p>
      )}
      {action && (
        <Button onClick={action.onClick} variant="secondary">
          {action.label}
        </Button>
      )}
    </div>
  );
}

// Pre-built empty states for common scenarios
export function NoDataEmptyState({ onBrowse }: { onBrowse?: () => void }) {
  return (
    <EmptyState
      icon={<MapPin className="h-12 w-12" />}
      title="No surveillance data available"
      description="Coverage is expanding! We're working to add more locations. Try browsing regions that have data."
      action={onBrowse ? { label: "Browse covered regions", onClick: onBrowse } : undefined}
    />
  );
}

export function NoSearchResultsEmptyState({ query, onClear }: { query: string; onClear?: () => void }) {
  return (
    <EmptyState
      icon={<Search className="h-12 w-12" />}
      title={`No results for "${query}"`}
      description="Try searching for a different city, country, or region."
      action={onClear ? { label: "Clear search", onClick: onClear } : undefined}
    />
  );
}

export function ErrorEmptyState({ onRetry }: { onRetry?: () => void }) {
  return (
    <EmptyState
      icon={<AlertTriangle className="h-12 w-12 text-risk-elevated" />}
      title="Something went wrong"
      description="We're having trouble loading this data. Please try again."
      action={onRetry ? { label: "Try again", onClick: onRetry } : undefined}
    />
  );
}

export function OfflineEmptyState({ onRetry }: { onRetry?: () => void }) {
  return (
    <EmptyState
      icon={<WifiOff className="h-12 w-12 text-risk-moderate" />}
      title="You're offline"
      description="Check your internet connection and try again."
      action={onRetry ? { label: "Retry", onClick: onRetry } : undefined}
    />
  );
}

export function WelcomeEmptyState({ onExplore }: { onExplore?: () => void }) {
  return (
    <EmptyState
      icon={<Globe className="h-12 w-12 text-primary" />}
      title="Welcome to Viral Weather"
      description="Click anywhere on the globe or search for a location to see viral activity data."
      action={onExplore ? { label: "Start exploring", onClick: onExplore } : undefined}
    />
  );
}

// Data freshness warning banner
interface FreshnessBannerProps {
  status: "stale" | "old" | "expired";
  lastUpdated: Date;
  className?: string;
}

export function FreshnessBanner({ status, lastUpdated, className }: FreshnessBannerProps) {
  const config = {
    stale: {
      bg: "bg-risk-moderate/10",
      border: "border-risk-moderate/30",
      text: "text-risk-moderate",
      message: "Data may be outdated",
    },
    old: {
      bg: "bg-risk-elevated/10",
      border: "border-risk-elevated/30",
      text: "text-risk-elevated",
      message: "Limited data availability",
    },
    expired: {
      bg: "bg-foreground-muted/10",
      border: "border-foreground-muted/30",
      text: "text-foreground-muted",
      message: "Data is no longer current",
    },
  };

  const { bg, border, text, message } = config[status];

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-lg border",
        bg,
        border,
        className
      )}
    >
      <AlertTriangle className={cn("h-4 w-4", text)} />
      <span className={cn("text-sm", text)}>{message}</span>
      <span className="text-xs text-foreground-muted">
        Last updated: {lastUpdated.toLocaleDateString()}
      </span>
    </div>
  );
}
