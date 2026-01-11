'use client';

import { useMemo } from 'react';

interface ForecastPoint {
  date: string;
  risk_score: number;
  confidence_low: number;
  confidence_high: number;
}

interface ForecastChartProps {
  forecast: ForecastPoint[];
  currentScore: number;
  height?: number;
}

export function ForecastChart({
  forecast,
  currentScore,
  height = 120,
}: ForecastChartProps) {
  const padding = { top: 20, right: 10, bottom: 25, left: 35 };
  const width = 280;

  const chartData = useMemo(() => {
    // Add current score as first point
    const allPoints = [
      {
        date: 'Today',
        risk_score: currentScore,
        confidence_low: currentScore,
        confidence_high: currentScore,
      },
      ...forecast,
    ];

    // Calculate scales
    const minY = Math.min(...allPoints.map((p) => p.confidence_low)) - 5;
    const maxY = Math.max(...allPoints.map((p) => p.confidence_high)) + 5;
    const yRange = maxY - minY || 1;

    const innerWidth = width - padding.left - padding.right;
    const innerHeight = height - padding.top - padding.bottom;

    const xScale = (i: number) =>
      padding.left + (i / (allPoints.length - 1)) * innerWidth;
    const yScale = (value: number) =>
      padding.top + innerHeight - ((value - minY) / yRange) * innerHeight;

    // Build path data
    const linePath = allPoints
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p.risk_score)}`)
      .join(' ');

    // Build confidence band path
    const confidencePath =
      allPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p.confidence_high)}`).join(' ') +
      ' ' +
      [...allPoints]
        .reverse()
        .map((p, i) => `L ${xScale(allPoints.length - 1 - i)} ${yScale(p.confidence_low)}`)
        .join(' ') +
      ' Z';

    return {
      allPoints,
      linePath,
      confidencePath,
      xScale,
      yScale,
      minY,
      maxY,
      innerWidth,
      innerHeight,
    };
  }, [forecast, currentScore, height]);

  // Format date for x-axis labels
  const formatDate = (dateStr: string, index: number) => {
    if (dateStr === 'Today') return 'Today';
    if (index === chartData.allPoints.length - 1) return `+${forecast.length}d`;
    if (index === Math.floor(forecast.length / 2)) return `+${Math.floor(forecast.length / 2)}d`;
    return '';
  };

  return (
    <svg width={width} height={height} className="overflow-visible">
      {/* Grid lines */}
      {[0, 25, 50, 75, 100].map((value) => {
        if (value < chartData.minY || value > chartData.maxY) return null;
        const y = chartData.yScale(value);
        return (
          <g key={value}>
            <line
              x1={padding.left}
              y1={y}
              x2={width - padding.right}
              y2={y}
              stroke="rgba(255,255,255,0.1)"
              strokeDasharray="2,2"
            />
            <text
              x={padding.left - 5}
              y={y}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-dark-muted text-[10px]"
            >
              {value}
            </text>
          </g>
        );
      })}

      {/* Confidence band */}
      <path
        d={chartData.confidencePath}
        fill="rgba(59, 130, 246, 0.15)"
        stroke="none"
      />

      {/* Main line */}
      <path
        d={chartData.linePath}
        fill="none"
        stroke="#3b82f6"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Current score reference line */}
      <line
        x1={padding.left}
        y1={chartData.yScale(currentScore)}
        x2={width - padding.right}
        y2={chartData.yScale(currentScore)}
        stroke="rgba(255,255,255,0.3)"
        strokeDasharray="4,4"
      />

      {/* Data points */}
      {chartData.allPoints.map((point, i) => (
        <g key={i}>
          <circle
            cx={chartData.xScale(i)}
            cy={chartData.yScale(point.risk_score)}
            r={i === 0 ? 5 : 3}
            fill={i === 0 ? '#fff' : '#3b82f6'}
            stroke={i === 0 ? '#3b82f6' : 'none'}
            strokeWidth={2}
          />
          {/* Confidence bars */}
          {i > 0 && (
            <line
              x1={chartData.xScale(i)}
              y1={chartData.yScale(point.confidence_low)}
              x2={chartData.xScale(i)}
              y2={chartData.yScale(point.confidence_high)}
              stroke="rgba(59, 130, 246, 0.4)"
              strokeWidth={2}
              strokeLinecap="round"
            />
          )}
        </g>
      ))}

      {/* X-axis labels */}
      {chartData.allPoints.map((point, i) => {
        const label = formatDate(point.date, i);
        if (!label) return null;
        return (
          <text
            key={i}
            x={chartData.xScale(i)}
            y={height - 5}
            textAnchor="middle"
            className="fill-dark-muted text-[10px]"
          >
            {label}
          </text>
        );
      })}
    </svg>
  );
}
