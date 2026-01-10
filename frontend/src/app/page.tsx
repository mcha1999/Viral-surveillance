'use client';

import { useState } from 'react';
import { Globe } from '@/components/globe/Globe';
import { SearchBar } from '@/components/ui/SearchBar';
import { DossierPanel } from '@/components/dossier/DossierPanel';
import { TimeScrubber } from '@/components/ui/TimeScrubber';
import { useLocationStore } from '@/lib/store';

export default function Home() {
  const { selectedLocation } = useLocationStore();
  const [currentDate, setCurrentDate] = useState(new Date());

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-dark-bg">
      {/* Globe (background) */}
      <div className="globe-container">
        <Globe currentDate={currentDate} />
      </div>

      {/* Search bar (top center) */}
      <div className="search-bar">
        <SearchBar />
      </div>

      {/* Dossier panel (right side, shown when location selected) */}
      {selectedLocation && (
        <DossierPanel locationId={selectedLocation} />
      )}

      {/* Time scrubber (bottom) */}
      <div className="time-scrubber">
        <TimeScrubber
          currentDate={currentDate}
          onDateChange={setCurrentDate}
        />
      </div>

      {/* Attribution */}
      <div className="fixed bottom-16 left-4 text-xs text-dark-muted">
        Data: CDC NWSS, Nextstrain, AviationStack
      </div>
    </main>
  );
}
