"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn, getRiskLevel, getRiskLabel, getRiskDescription, formatPercentage } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
// RiskLevel type is inferred from getRiskLevel return type

const riskScoreVariants = cva("rounded-lg border-2 p-4 transition-all duration-200", {
  variants: {
    level: {
      low: "border-risk-low/50 bg-risk-low/10",
      moderate: "border-risk-moderate/50 bg-risk-moderate/10",
      elevated: "border-risk-elevated/50 bg-risk-elevated/10",
      high: "border-risk-high/50 bg-risk-high/10",
      "very-high": "border-risk-very-high/50 bg-risk-very-high/10",
    },
    size: {
      sm: "p-3",
      default: "p-4",
      lg: "p-6",
    },
  },
  defaultVariants: {
    level: "moderate",
    size: "default",
  },
});

const scoreTextVariants = cva("font-bold font-mono", {
  variants: {
    level: {
      low: "text-risk-low",
      moderate: "text-risk-moderate",
      elevated: "text-risk-elevated",
      high: "text-risk-high",
      "very-high": "text-risk-very-high",
    },
    size: {
      sm: "text-2xl",
      default: "text-4xl",
      lg: "text-5xl",
    },
  },
  defaultVariants: {
    level: "moderate",
    size: "default",
  },
});

interface RiskScoreProps extends VariantProps<typeof riskScoreVariants> {
  score: number;
  weeklyChange?: number;
  showDescription?: boolean;
  showTrend?: boolean;
  className?: string;
}

export function RiskScore({
  score,
  weeklyChange,
  showDescription = false,
  showTrend = true,
  size = "default",
  className,
}: RiskScoreProps) {
  const level = getRiskLevel(score);
  const label = getRiskLabel(score);
  const description = getRiskDescription(score);

  const TrendIcon =
    weeklyChange && weeklyChange > 0
      ? TrendingUp
      : weeklyChange && weeklyChange < 0
      ? TrendingDown
      : Minus;

  const trendColor =
    weeklyChange && weeklyChange > 0
      ? "text-risk-high"
      : weeklyChange && weeklyChange < 0
      ? "text-risk-low"
      : "text-foreground-muted";

  return (
    <div className={cn(riskScoreVariants({ level, size }), className)}>
      <div className="flex items-baseline justify-between">
        <div>
          <p
            className={cn(
              "text-xs font-semibold uppercase tracking-wider mb-1",
              `text-risk-${level}`
            )}
          >
            {label} Risk
          </p>
          <div className="flex items-baseline gap-1">
            <span className={cn(scoreTextVariants({ level, size }))}>{score}</span>
            <span className="text-foreground-muted text-sm">/100</span>
          </div>
        </div>

        {showTrend && weeklyChange !== undefined && (
          <div className={cn("flex items-center gap-1", trendColor)}>
            <TrendIcon className="h-4 w-4" />
            <span className="text-sm font-medium">
              {formatPercentage(Math.abs(weeklyChange), weeklyChange !== 0)}
            </span>
            <span className="text-xs text-foreground-muted">vs last week</span>
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div className="mt-3 h-2 bg-background-secondary rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500", `gradient-risk-${level}`)}
          style={{ width: `${score}%` }}
        />
      </div>

      {showDescription && (
        <p className="mt-2 text-sm text-foreground-secondary">{description}</p>
      )}
    </div>
  );
}

// Compact version for lists and hover states
interface RiskScoreCompactProps {
  score: number;
  weeklyChange?: number;
  className?: string;
}

export function RiskScoreCompact({ score, weeklyChange, className }: RiskScoreCompactProps) {
  const level = getRiskLevel(score);
  const label = getRiskLabel(score);

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span
        className={cn(
          "inline-flex items-center justify-center w-10 h-10 rounded-lg font-bold font-mono text-lg",
          `bg-risk-${level}/20 text-risk-${level}`
        )}
      >
        {score}
      </span>
      <div className="flex flex-col">
        <span className={cn("text-sm font-medium", `text-risk-${level}`)}>{label}</span>
        {weeklyChange !== undefined && (
          <span className="text-xs text-foreground-muted">
            {weeklyChange > 0 ? "+" : ""}
            {weeklyChange}% this week
          </span>
        )}
      </div>
    </div>
  );
}

// Mini badge for markers and compact displays
interface RiskScoreBadgeProps {
  score: number;
  size?: "sm" | "default";
  className?: string;
}

export function RiskScoreBadge({ score, size = "default", className }: RiskScoreBadgeProps) {
  const level = getRiskLevel(score);

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-full font-bold font-mono",
        `bg-risk-${level} text-white`,
        size === "sm" ? "w-6 h-6 text-xs" : "w-8 h-8 text-sm",
        className
      )}
    >
      {score}
    </span>
  );
}
