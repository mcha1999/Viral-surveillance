'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { format, subDays, addDays, differenceInDays } from 'date-fns';
import { useUIStore } from '@/lib/store';

interface TimeScrubberProps {
  currentDate: Date;
  onDateChange: (date: Date) => void;
}

const HISTORY_DAYS = 30;
const FORECAST_DAYS = 7;
const TOTAL_DAYS = HISTORY_DAYS + FORECAST_DAYS;

export function TimeScrubber({ currentDate, onDateChange }: TimeScrubberProps) {
  const { isPlaying, setPlaying } = useUIStore();
  const [isDragging, setIsDragging] = useState(false);
  const sliderRef = useRef<HTMLDivElement>(null);

  const today = new Date();
  const minDate = subDays(today, HISTORY_DAYS);
  const maxDate = addDays(today, FORECAST_DAYS);

  // Calculate slider position (0-100)
  const position = ((differenceInDays(currentDate, minDate) / TOTAL_DAYS) * 100);

  // Handle slider interaction
  const updateDate = useCallback(
    (clientX: number) => {
      if (!sliderRef.current) return;

      const rect = sliderRef.current.getBoundingClientRect();
      const percent = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
      const daysFromMin = Math.round((percent / 100) * TOTAL_DAYS);
      const newDate = addDays(minDate, daysFromMin);

      onDateChange(newDate);
    },
    [minDate, onDateChange]
  );

  // Mouse handlers
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      setIsDragging(true);
      updateDate(e.clientX);
    },
    [updateDate]
  );

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      updateDate(e.clientX);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, updateDate]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        onDateChange(subDays(currentDate, 1));
      } else if (e.key === 'ArrowRight') {
        onDateChange(addDays(currentDate, 1));
      } else if (e.key === ' ') {
        e.preventDefault();
        setPlaying(!isPlaying);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentDate, onDateChange, isPlaying, setPlaying]);

  // Auto-play animation
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      onDateChange((prev) => {
        const next = addDays(prev, 1);
        if (next > maxDate) {
          setPlaying(false);
          return prev;
        }
        return next;
      });
    }, 500);

    return () => clearInterval(interval);
  }, [isPlaying, maxDate, onDateChange, setPlaying]);

  const isFuture = currentDate > today;

  return (
    <div className="flex items-center gap-4 h-full">
      {/* Play/Pause button */}
      <button
        onClick={() => setPlaying(!isPlaying)}
        className="p-2 hover:bg-white/10 rounded-lg transition-colors"
        aria-label={isPlaying ? 'Pause' : 'Play'}
      >
        {isPlaying ? (
          <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
          </svg>
        ) : (
          <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
      </button>

      {/* Current date display */}
      <div className="w-32 text-center">
        <div className="text-lg font-semibold">
          {format(currentDate, 'MMM d')}
        </div>
        <div className="text-xs text-dark-muted">
          {isFuture ? (
            <span className="text-blue-400">Forecast</span>
          ) : (
            format(currentDate, 'yyyy')
          )}
        </div>
      </div>

      {/* Slider */}
      <div
        ref={sliderRef}
        className="flex-1 h-2 bg-dark-surface rounded-full cursor-pointer relative"
        onMouseDown={handleMouseDown}
      >
        {/* Track */}
        <div className="absolute inset-0 rounded-full overflow-hidden">
          {/* Past section */}
          <div
            className="absolute left-0 top-0 bottom-0 bg-dark-border"
            style={{ width: `${(HISTORY_DAYS / TOTAL_DAYS) * 100}%` }}
          />
          {/* Today marker */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-white/50"
            style={{ left: `${(HISTORY_DAYS / TOTAL_DAYS) * 100}%` }}
          />
          {/* Future section */}
          <div
            className="absolute right-0 top-0 bottom-0 bg-blue-900/50"
            style={{ width: `${(FORECAST_DAYS / TOTAL_DAYS) * 100}%` }}
          />
        </div>

        {/* Thumb */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg transform -translate-x-1/2 transition-transform hover:scale-110"
          style={{ left: `${position}%` }}
        />
      </div>

      {/* Date labels */}
      <div className="flex gap-2 text-xs text-dark-muted">
        <span>{format(minDate, 'MMM d')}</span>
        <span>-</span>
        <span className="text-blue-400">{format(maxDate, 'MMM d')}</span>
      </div>
    </div>
  );
}
