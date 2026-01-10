'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { autocomplete } from '@/lib/api';
import { useLocationStore, useUIStore } from '@/lib/store';

export function SearchBar() {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { setSelectedLocation } = useLocationStore();
  const { setSearchFocused } = useUIStore();

  // Debounced autocomplete
  const { data: suggestions = [] } = useQuery({
    queryKey: ['autocomplete', query],
    queryFn: () => autocomplete(query, 5),
    enabled: query.length >= 2,
    staleTime: 60 * 1000, // 1 minute
  });

  // Handle selection
  const handleSelect = useCallback(
    (id: string) => {
      setSelectedLocation(id);
      setQuery('');
      setIsOpen(false);
      inputRef.current?.blur();
    },
    [setSelectedLocation]
  );

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // "/" to focus search
      if (e.key === '/' && document.activeElement !== inputRef.current) {
        e.preventDefault();
        inputRef.current?.focus();
      }
      // Escape to close
      if (e.key === 'Escape') {
        setIsOpen(false);
        inputRef.current?.blur();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="relative">
      {/* Search input */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => {
            setIsOpen(true);
            setSearchFocused(true);
          }}
          onBlur={() => {
            // Delay to allow click on suggestions
            setTimeout(() => {
              setIsOpen(false);
              setSearchFocused(false);
            }, 200);
          }}
          placeholder="Search locations... (press /)"
          className="w-full px-4 py-3 pl-10 bg-dark-surface/90 backdrop-blur-md border border-dark-border rounded-lg text-white placeholder-dark-muted focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500"
        />
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-muted"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </div>

      {/* Suggestions dropdown */}
      {isOpen && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-dark-surface/95 backdrop-blur-md border border-dark-border rounded-lg overflow-hidden shadow-xl">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion.id}
              onClick={() => handleSelect(suggestion.id)}
              className="w-full px-4 py-3 text-left hover:bg-white/5 transition-colors border-b border-dark-border last:border-0"
            >
              <span className="text-white">{suggestion.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* No results */}
      {isOpen && query.length >= 2 && suggestions.length === 0 && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-dark-surface/95 backdrop-blur-md border border-dark-border rounded-lg p-4">
          <span className="text-dark-muted">No locations found</span>
        </div>
      )}
    </div>
  );
}
