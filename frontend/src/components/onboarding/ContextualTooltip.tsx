'use client';

import { useState, useEffect } from 'react';

interface ContextualTooltipProps {
  id: string;
  title: string;
  description: string;
  position?: 'top' | 'bottom' | 'left' | 'right';
  show: boolean;
  onDismiss: () => void;
  showAction?: boolean;
  actionLabel?: string;
  onAction?: () => void;
}

export function ContextualTooltip({
  id,
  title,
  description,
  position = 'bottom',
  show,
  onDismiss,
  showAction = false,
  actionLabel = 'Show me',
  onAction,
}: ContextualTooltipProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (show) {
      // Small delay to trigger animation
      const timer = setTimeout(() => setIsVisible(true), 100);
      return () => clearTimeout(timer);
    } else {
      setIsVisible(false);
    }
  }, [show]);

  if (!show) return null;

  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  const arrowClasses = {
    top: 'top-full left-1/2 -translate-x-1/2 border-t-dark-surface border-x-transparent border-b-transparent',
    bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-dark-surface border-x-transparent border-t-transparent',
    left: 'left-full top-1/2 -translate-y-1/2 border-l-dark-surface border-y-transparent border-r-transparent',
    right: 'right-full top-1/2 -translate-y-1/2 border-r-dark-surface border-y-transparent border-l-transparent',
  };

  return (
    <div
      className={`absolute z-[150] ${positionClasses[position]} transition-all duration-200 ${
        isVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-95'
      }`}
    >
      <div className="bg-dark-surface border border-dark-border rounded-lg shadow-xl p-4 max-w-xs">
        {/* Lightbulb icon */}
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-amber-500/20 flex items-center justify-center flex-shrink-0">
            <svg className="w-4 h-4 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
              <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.476.859h4.002z" />
            </svg>
          </div>
          <div className="flex-1">
            <h4 className="text-white font-medium text-sm mb-1">{title}</h4>
            <p className="text-dark-muted text-xs leading-relaxed">{description}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-dark-border">
          {showAction && onAction && (
            <button
              onClick={() => {
                onAction();
                onDismiss();
              }}
              className="flex-1 py-1.5 text-xs font-medium text-blue-400 hover:text-blue-300 transition-colors"
            >
              {actionLabel}
            </button>
          )}
          <button
            onClick={onDismiss}
            className={`${showAction ? '' : 'flex-1'} py-1.5 text-xs font-medium text-dark-muted hover:text-white transition-colors`}
          >
            Got it
          </button>
        </div>
      </div>

      {/* Arrow */}
      <div
        className={`absolute w-0 h-0 border-[6px] ${arrowClasses[position]}`}
      />
    </div>
  );
}

// Wrapper component that handles showing tooltips relative to an element
interface TooltipTriggerProps {
  children: React.ReactNode;
  tooltip: Omit<ContextualTooltipProps, 'show'>;
  show: boolean;
}

export function TooltipTrigger({ children, tooltip, show }: TooltipTriggerProps) {
  return (
    <div className="relative">
      {children}
      <ContextualTooltip {...tooltip} show={show} />
    </div>
  );
}
