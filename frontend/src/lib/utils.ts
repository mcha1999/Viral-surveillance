import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(num: number, decimals = 0): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num);
}

export function formatCompactNumber(num: number): string {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(num);
}

export function formatPercentage(num: number, showSign = false): string {
  const sign = showSign && num > 0 ? "+" : "";
  return `${sign}${num.toFixed(0)}%`;
}

export function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? "s" : ""} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;

  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function getRiskLevel(score: number): "low" | "moderate" | "elevated" | "high" | "very-high" {
  if (score <= 20) return "low";
  if (score <= 40) return "moderate";
  if (score <= 60) return "elevated";
  if (score <= 80) return "high";
  return "very-high";
}

export function getRiskLabel(score: number): string {
  const level = getRiskLevel(score);
  const labels: Record<string, string> = {
    low: "Low",
    moderate: "Moderate",
    elevated: "Elevated",
    high: "High",
    "very-high": "Very High",
  };
  return labels[level];
}

export function getRiskDescription(score: number): string {
  const level = getRiskLevel(score);
  const descriptions: Record<string, string> = {
    low: "Minimal viral activity detected",
    moderate: "Moderate levels, normal caution advised",
    elevated: "Above average activity",
    high: "Significant viral activity",
    "very-high": "Extreme levels detected",
  };
  return descriptions[level];
}

export function getFreshnessStatus(lastUpdated: Date): "current" | "stale" | "old" | "expired" {
  const diffDays = Math.floor((new Date().getTime() - lastUpdated.getTime()) / 86400000);

  if (diffDays <= 2) return "current";
  if (diffDays <= 14) return "stale";
  if (diffDays <= 30) return "old";
  return "expired";
}

export function getFreshnessLabel(status: "current" | "stale" | "old" | "expired"): string {
  const labels: Record<string, string> = {
    current: "Current",
    stale: "Data may be outdated",
    old: "Limited data",
    expired: "Data expired",
  };
  return labels[status];
}
