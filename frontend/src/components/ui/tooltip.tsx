"use client";

import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "@/lib/utils";

const TooltipProvider = TooltipPrimitive.Provider;

const Tooltip = TooltipPrimitive.Root;

const TooltipTrigger = TooltipPrimitive.Trigger;

const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Content
    ref={ref}
    sideOffset={sideOffset}
    className={cn(
      "z-50 overflow-hidden rounded-lg border border-border bg-background-elevated px-3 py-1.5 text-sm text-foreground shadow-lg",
      "animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
      "data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
      className
    )}
    {...props}
  />
));
TooltipContent.displayName = TooltipPrimitive.Content.displayName;

// Feature discovery tooltip with dismiss
interface FeatureTooltipProps {
  children: React.ReactNode;
  title: string;
  description: string;
  onDismiss?: () => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

function FeatureTooltip({
  children,
  title,
  description,
  onDismiss,
  open,
  onOpenChange,
}: FeatureTooltipProps) {
  return (
    <TooltipProvider>
      <Tooltip open={open} onOpenChange={onOpenChange}>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent className="max-w-xs p-4" side="bottom">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-lg">💡</span>
              <h4 className="font-semibold text-foreground">{title}</h4>
            </div>
            <p className="text-sm text-foreground-secondary">{description}</p>
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="text-xs text-primary hover:underline mt-2"
              >
                Got it
              </button>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider, FeatureTooltip };
