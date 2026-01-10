"use client";

import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Play,
  Pause,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui";

interface TimeScrubberProps {
  startDate: Date;
  endDate: Date;
  currentDate: Date;
  onDateChange: (date: Date) => void;
  forecastDays?: number;
  className?: string;
}

export function TimeScrubber({
  startDate,
  endDate,
  currentDate,
  onDateChange,
  forecastDays = 7,
  className,
}: TimeScrubberProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(1);

  // Calculate total days and current position
  const totalDays = Math.ceil((endDate.getTime() - startDate.getTime()) / 86400000);
  const currentPosition = Math.ceil((currentDate.getTime() - startDate.getTime()) / 86400000);
  const historyDays = totalDays - forecastDays;

  // Calculate percentage for slider
  const percentage = (currentPosition / totalDays) * 100;
  const forecastStartPercentage = ((totalDays - forecastDays) / totalDays) * 100;

  // Navigate functions
  const goToDay = useCallback(
    (days: number) => {
      const newDate = new Date(startDate.getTime() + days * 86400000);
      if (newDate >= startDate && newDate <= endDate) {
        onDateChange(newDate);
      }
    },
    [startDate, endDate, onDateChange]
  );

  const stepBack = () => goToDay(currentPosition - 1);
  const stepForward = () => goToDay(currentPosition + 1);
  const jumpBack = () => goToDay(currentPosition - 7);
  const jumpForward = () => goToDay(currentPosition + 7);

  // Handle slider change
  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    goToDay(value);
  };

  // Toggle play/pause
  const togglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  // Cycle through speeds
  const cycleSpeed = () => {
    const speeds = [1, 2, 4];
    const currentIndex = speeds.indexOf(playSpeed);
    setPlaySpeed(speeds[(currentIndex + 1) % speeds.length]);
  };

  // Auto-advance when playing
  React.useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      const nextPosition = currentPosition + 1;
      if (nextPosition > totalDays) {
        setIsPlaying(false);
        goToDay(0); // Reset to start
      } else {
        goToDay(nextPosition);
      }
    }, 1000 / playSpeed);

    return () => clearInterval(interval);
  }, [isPlaying, currentPosition, totalDays, playSpeed, goToDay]);

  // Format date for display
  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

  const isInForecast = currentPosition > historyDays;

  return (
    <div
      className={cn(
        "glass-dark rounded-xl p-4 mx-4 mb-4",
        className
      )}
    >
      {/* Date display */}
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs text-foreground-muted">{formatDate(startDate)}</div>
        <div className="text-center">
          <div className="text-lg font-semibold text-foreground">
            {formatDate(currentDate)}
          </div>
          {isInForecast && (
            <div className="text-xs text-risk-moderate">Forecast</div>
          )}
        </div>
        <div className="text-xs text-foreground-muted">
          {formatDate(endDate)}
          <span className="ml-1 text-risk-moderate/70">(+{forecastDays}d)</span>
        </div>
      </div>

      {/* Slider */}
      <div className="relative mb-3">
        {/* Background track */}
        <div className="h-2 bg-background-secondary rounded-full overflow-hidden">
          {/* Historical data section */}
          <div
            className="absolute h-full bg-primary/30"
            style={{ width: `${forecastStartPercentage}%` }}
          />
          {/* Forecast section */}
          <div
            className="absolute h-full bg-risk-moderate/20"
            style={{
              left: `${forecastStartPercentage}%`,
              width: `${100 - forecastStartPercentage}%`,
            }}
          />
          {/* Progress */}
          <div
            className={cn(
              "absolute h-full transition-all duration-100",
              isInForecast ? "bg-risk-moderate" : "bg-primary"
            )}
            style={{ width: `${percentage}%` }}
          />
        </div>

        {/* Input range */}
        <input
          type="range"
          min={0}
          max={totalDays}
          value={currentPosition}
          onChange={handleSliderChange}
          className="absolute inset-0 w-full h-2 opacity-0 cursor-pointer"
        />

        {/* Thumb indicator */}
        <motion.div
          className={cn(
            "absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 border-white shadow-lg",
            isInForecast ? "bg-risk-moderate" : "bg-primary"
          )}
          style={{ left: `calc(${percentage}% - 8px)` }}
          animate={{ scale: isPlaying ? [1, 1.1, 1] : 1 }}
          transition={{ repeat: isPlaying ? Infinity : 0, duration: 0.5 }}
        />
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={jumpBack}
            disabled={currentPosition <= 0}
            className="text-foreground-secondary hover:text-foreground"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={stepBack}
            disabled={currentPosition <= 0}
            className="text-foreground-secondary hover:text-foreground"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>

        <Button
          variant={isPlaying ? "secondary" : "default"}
          size="sm"
          onClick={togglePlay}
          className="px-4"
        >
          {isPlaying ? (
            <>
              <Pause className="h-4 w-4 mr-1" />
              Pause
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-1" />
              Play
            </>
          )}
        </Button>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={stepForward}
            disabled={currentPosition >= totalDays}
            className="text-foreground-secondary hover:text-foreground"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={jumpForward}
            disabled={currentPosition >= totalDays}
            className="text-foreground-secondary hover:text-foreground"
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Speed control */}
      <div className="flex justify-center mt-2">
        <button
          onClick={cycleSpeed}
          className="text-xs text-foreground-muted hover:text-foreground transition-colors"
        >
          Speed: {playSpeed}x
        </button>
      </div>
    </div>
  );
}

export default TimeScrubber;
