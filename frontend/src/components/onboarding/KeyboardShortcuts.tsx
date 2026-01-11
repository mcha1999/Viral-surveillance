'use client';

import { useEffect } from 'react';
import { useUIStore } from '@/lib/store';

const SHORTCUTS = [
  {
    category: 'Navigation',
    items: [
      { keys: ['/'], description: 'Focus search' },
      { keys: ['Esc'], description: 'Close panel / Clear selection' },
      { keys: ['H'], description: 'Go to home location' },
      { keys: ['W'], description: 'Toggle watchlist' },
    ],
  },
  {
    category: 'Time Controls',
    items: [
      { keys: ['←', '→'], description: 'Move 1 day back / forward' },
      { keys: ['Shift', '+', '←', '→'], description: 'Move 1 week back / forward' },
      { keys: ['Space'], description: 'Play / Pause timeline' },
    ],
  },
  {
    category: 'View Controls',
    items: [
      { keys: ['F'], description: 'Toggle flight routes' },
      { keys: ['G'], description: 'Toggle 2D / 3D view' },
      { keys: ['?'], description: 'Show keyboard shortcuts' },
    ],
  },
  {
    category: 'Watchlist',
    items: [
      { keys: ['1', '-', '5'], description: 'Jump to watchlist location' },
    ],
  },
];

export function KeyboardShortcuts() {
  const { isShortcutsOpen, setShortcutsOpen } = useUIStore();

  // Handle keyboard shortcut to open/close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
        // Don't trigger when typing in inputs
        if (document.activeElement?.tagName === 'INPUT' ||
            document.activeElement?.tagName === 'TEXTAREA') {
          return;
        }
        e.preventDefault();
        setShortcutsOpen(!isShortcutsOpen);
      }
      if (e.key === 'Escape' && isShortcutsOpen) {
        setShortcutsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isShortcutsOpen, setShortcutsOpen]);

  if (!isShortcutsOpen) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div
        className="bg-dark-surface border border-dark-border rounded-xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden animate-in fade-in zoom-in duration-200"
        role="dialog"
        aria-labelledby="shortcuts-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-dark-border">
          <h2 id="shortcuts-title" className="text-lg font-semibold text-white">
            Keyboard Shortcuts
          </h2>
          <button
            onClick={() => setShortcutsOpen(false)}
            className="p-1 hover:bg-white/10 rounded transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5 text-dark-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 max-h-[60vh] overflow-y-auto">
          <div className="space-y-6">
            {SHORTCUTS.map((category) => (
              <div key={category.category}>
                <h3 className="text-xs font-medium text-dark-muted uppercase tracking-wider mb-2">
                  {category.category}
                </h3>
                <div className="space-y-2">
                  {category.items.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-sm text-white">{item.description}</span>
                      <div className="flex items-center gap-1">
                        {item.keys.map((key, keyIdx) => (
                          <span key={keyIdx}>
                            {key === '+' ? (
                              <span className="text-dark-muted text-xs mx-1">+</span>
                            ) : key === '-' ? (
                              <span className="text-dark-muted text-xs mx-1">-</span>
                            ) : (
                              <kbd className="px-2 py-1 bg-dark-bg border border-dark-border rounded text-xs font-mono text-dark-muted">
                                {key}
                              </kbd>
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-dark-border bg-dark-bg/50">
          <p className="text-xs text-dark-muted text-center">
            Press <kbd className="px-1.5 py-0.5 bg-dark-surface border border-dark-border rounded text-xs font-mono">?</kbd> to toggle this panel
          </p>
        </div>
      </div>
    </div>
  );
}
