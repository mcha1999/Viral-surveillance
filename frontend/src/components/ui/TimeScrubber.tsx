'use client';

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { format, subDays, addDays, differenceInDays, parseISO } from 'date-fns';
import { useQuery } from '@tanstack/react-query';
import { useUIStore, useLocationStore } from '@/lib/store';
import { getVariantWaves } from '@/lib/api';

interface TimeScrubberProps {
  currentDate: Date;
  onDateChange: (date: Date) => void;
}

const FORECAST_DAYS = 7;
const RANGE_OPTIONS = [30, 90, 180, 365] as const;

export function TimeScrubber({ currentDate, onDateChange }: TimeScrubberProps) {
  const { isPlaying, setPlaying } = useUIStore();
  const { historyDays, setHistoryDays, selectedLocation } = useLocationStore();
  const [isDragging, setIsDragging] = useState(false);
  const [showWaves, setShowWaves] = useState(true);
  const sliderRef = useRef<HTMLDivElement>(null);

  const totalDays = historyDays + FORECAST_DAYS;
  const today = new Date();
  const minDate = subDays(today, historyDays);
  const maxDate = addDays(today, FORECAST_DAYS);

  // Fetch variant waves
  const { data: wavesData } = useQuery({
    queryKey: ['variantWaves', selectedLocation, historyDays],
    queryFn: () => getVariantWaves({ locationId: selectedLocation || undefined, days: historyDays }),
    staleTime: 15 * 60 * 1000,
  });

  // Calculate wave positions for rendering
  const wavePositions = useMemo(() => {
    if (!wavesData?.waves) return [];

    return wavesData.waves.map((wave) => {
      const startDate = parseISO(wave.start_date);
      const peakDate = parseISO(wave.peak_date);
      const endDate = wave.end_date ? parseISO(wave.end_date) : maxDate;

      const startPos = Math.max(0, (differenceInDays(startDate, minDate) / totalDays) * 100);
      const peakPos = (differenceInDays(peakDate, minDate) / totalDays) * 100;
      const endPos = Math.min(100, (differenceInDays(endDate, minDate) / totalDays) * 100);

      return {
        ...wave,
        startPos,
        peakPos,
        endPos,
        width: Math.max(2, endPos - startPos),
      };
    });
  }, [wavesData, minDate, maxDate, totalDays]);

  // Calculate slider position (0-100)
  const position = (differenceInDays(currentDate, minDate) / totalDays) * 100;

  // Handle slider interaction
  const updateDate = useCallback(
    (clientX: number) => {
      if (!sliderRef.current) return;

      const rect = sliderRef.current.getBoundingClientRect();
      const percent = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
      const daysFromMin = Math.round((percent / 100) * totalDays);
      const newDate = addDays(minDate, daysFromMin);

      onDateChange(newDate);
    },
    [minDate, totalDays, onDateChange]
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

    const handleMouseMove = (e: MouseEvent) => updateDate(e.clientX);
    const handleMouseUp = () => setIsDragging(false);

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
      if (e.target instanceof HTMLInputElement) return;

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
      const next = addDays(currentDate, 1);
      if (next > maxDate) {
        setPlaying(false);
        return;
      }
      onDateChange(next);
    }, 500);

    return () => clearInterval(interval);
  }, [isPlaying, currentDate, maxDate, onDateChange, setPlaying]);

  const isFuture = currentDate > today;
  const todayPosition = (historyDays / totalDays) * 100;

  return (
    <div className="flex flex-col gap-2 h-full py-2">
      {/* Top row: Controls and range selector */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {/* Play/Pause button */}
          <button
            onClick={() => setPlaying(!isPlaying)}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>

          {/* Current date display */}
          <div className="w-28 text-center">
            <div className="text-sm font-semibold">{format(currentDate, 'MMM d, yyyy')}</div>
            {isFuture && <div className="text-[10px] text-blue-400">Forecast</div>}
          </div>
        </div>

        {/* Range selector */}
        <div className="flex items-center gap-1">
          <span className="text-xs text-dark-muted mr-1">Range:</span>
          {RANGE_OPTIONS.map((days) => (
            <button
              key={days}
              onClick={() => setHistoryDays(days)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                historyDays === days
                  ? 'bg-blue-600 text-white'
                  : 'bg-dark-surface text-dark-muted hover:bg-white/10'
              }`}
            >
              {days}d
            </button>
          ))}
        </div>

        {/* Wave toggle */}
        <button
          onClick={() => setShowWaves(!showWaves)}
          className={`p-1.5 rounded transition-colors ${
            showWaves ? 'text-purple-400' : 'text-dark-muted hover:text-white'
          }`}
          title={showWaves ? 'Hide variant waves' : 'Show variant waves'}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
        </button>
      </div>

      {/* Variant wave bars */}
      {showWaves && wavePositions.length > 0 && (
        <div className="relative h-6 flex items-center">
          {wavePositions.map((wave, i) => (
            <div
              key={wave.variant_id}
              className="absolute h-4 rounded-sm opacity-60 hover:opacity-100 transition-opacity cursor-pointer group"
              style={{
                left: `${wave.startPos}%`,
                width: `${wave.width}%`,
                backgroundColor: wave.color,
                top: `${(i % 2) * 8}px`,
              }}
              title={`${wave.display_name}: ${format(parseISO(wave.start_date), 'MMM d')} - ${
                wave.end_date ? format(parseISO(wave.end_date), 'MMM d') : 'ongoing'
              }`}
            >
              {wave.width > 10 && (
                <span className="absolute inset-0 flex items-center justify-center text-[9px] text-white font-medium truncate px-1">
                  {wave.display_name}
                </span>
              )}
              {/* Peak marker */}
              <div
                className="absolute top-0 w-0.5 h-full bg-white/50"
                style={{ left: `${((wave.peakPos - wave.startPos) / wave.width) * 100}%` }}
              />
            </div>
          ))}
        </div>
      )}

      {/* Timeline slider */}
      <div className="flex items-center gap-3">
        {/* Min date label */}
        <span className="text-[10px] text-dark-muted w-12">{format(minDate, 'MMM d')}</span>

        {/* Slider */}
        <div
          ref={sliderRef}
          className="flex-1 h-3 bg-dark-surface rounded-full cursor-pointer relative"
          onMouseDown={handleMouseDown}
        >
          {/* Track segments */}
          <div className="absolute inset-0 rounded-full overflow-hidden">
            {/* Past section */}
            <div
              className="absolute left-0 top-0 bottom-0 bg-dark-border"
              style={{ width: `${todayPosition}%` }}
            />
            {/* Future section */}
            <div
              className="absolute right-0 top-0 bottom-0 bg-blue-900/50"
              style={{ width: `${(FORECAST_DAYS / totalDays) * 100}%` }}
            />
          </div>

          {/* Today marker */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-white/60"
            style={{ left: `${todayPosition}%` }}
          />

          {/* Thumb */}
          <div
            className={`absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full shadow-lg transform -translate-x-1/2 transition-all ${
              isDragging ? 'scale-125' : 'hover:scale-110'
            } ${isFuture ? 'bg-blue-400' : 'bg-white'}`}
            style={{ left: `${Math.max(0, Math.min(100, position))}%` }}
          />

          {/* Tick marks for reference */}
          {historyDays > 60 && (
            <>
              {[0.25, 0.5, 0.75].map((frac) => (
                <div
                  key={frac}
                  className="absolute top-0 bottom-0 w-px bg-white/10"
                  style={{ left: `${frac * 100}%` }}
                />
              ))}
            </>
          )}
        </div>

        {/* Max date label */}
        <span className="text-[10px] text-blue-400 w-12 text-right">{format(maxDate, 'MMM d')}</span>
      </div>

      {/* Legend */}
      {showWaves && wavePositions.length > 0 && (
        <div className="flex flex-wrap gap-x-3 gap-y-1 justify-center">
          {wavePositions.slice(0, 5).map((wave) => (
            <div key={wave.variant_id} className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: wave.color }} />
              <span className="text-[10px] text-dark-muted">{wave.display_name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
