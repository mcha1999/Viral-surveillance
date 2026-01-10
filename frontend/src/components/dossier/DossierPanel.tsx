"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Star,
  Share2,
  ArrowLeft,
  Plane,
  Clock,
  ChevronDown,
} from "lucide-react";
import { cn, formatRelativeTime, formatCompactNumber, getRiskLevel } from "@/lib/utils";
import { useApp } from "@/store/app-context";
import { Button, RiskScore, Badge, SkeletonDossierPanel } from "@/components/ui";
import type { Location, Variant, FlightArc } from "@/types";

interface DossierPanelProps {
  location: Location | null;
  flightArcs?: FlightArc[];
  isLoading?: boolean;
  className?: string;
}

export function DossierPanel({
  location,
  flightArcs = [],
  isLoading = false,
  className,
}: DossierPanelProps) {
  const { state, dispatch, addToWatchlist, removeFromWatchlist, isInWatchlist } = useApp();
  const [isExpanded, setIsExpanded] = React.useState(false);

  const handleClose = () => {
    dispatch({ type: "SELECT_LOCATION", payload: null });
    dispatch({ type: "TOGGLE_DOSSIER", payload: false });
  };

  const inWatchlist = location ? isInWatchlist(location.id) : false;

  const handleWatchlistToggle = () => {
    if (!location) return;
    if (inWatchlist) {
      removeFromWatchlist(location.id);
    } else {
      addToWatchlist(location.id);
    }
  };

  // Desktop sidebar animation
  const sidebarVariants = {
    hidden: { x: "100%", opacity: 0 },
    visible: {
      x: 0,
      opacity: 1,
      transition: { type: "spring", damping: 25, stiffness: 300 },
    },
    exit: {
      x: "100%",
      opacity: 0,
      transition: { duration: 0.2 },
    },
  };

  // Mobile bottom sheet animation
  const bottomSheetVariants = {
    hidden: { y: "100%", opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { type: "spring", damping: 25, stiffness: 300 },
    },
    exit: {
      y: "100%",
      opacity: 0,
      transition: { duration: 0.2 },
    },
  };

  if (!state.isDossierOpen) return null;

  return (
    <>
      {/* Desktop Sidebar */}
      <AnimatePresence>
        {state.isDossierOpen && (
          <motion.div
            initial="hidden"
            animate="visible"
            exit="exit"
            variants={sidebarVariants}
            className={cn(
              "hidden md:block fixed right-0 top-0 h-full w-[400px] bg-background-panel shadow-panel-lg z-30 overflow-hidden",
              "panel-light",
              className
            )}
          >
            {isLoading || !location ? (
              <SkeletonDossierPanel />
            ) : (
              <DossierContent
                location={location}
                flightArcs={flightArcs}
                inWatchlist={inWatchlist}
                onClose={handleClose}
                onWatchlistToggle={handleWatchlistToggle}
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mobile Bottom Sheet */}
      <AnimatePresence>
        {state.isDossierOpen && (
          <motion.div
            initial="hidden"
            animate="visible"
            exit="exit"
            variants={bottomSheetVariants}
            className={cn(
              "md:hidden fixed bottom-0 left-0 right-0 bg-background-panel rounded-t-2xl shadow-panel-lg z-30",
              "panel-light safe-bottom",
              isExpanded ? "h-[85vh]" : "h-auto max-h-[40vh]"
            )}
          >
            {/* Drag handle */}
            <div
              className="flex justify-center py-2 cursor-grab"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              <div className="w-10 h-1 rounded-full bg-neutral-300" />
            </div>

            {isLoading || !location ? (
              <div className="px-4 pb-4">
                <SkeletonDossierPanel />
              </div>
            ) : (
              <MobileDossierContent
                location={location}
                isExpanded={isExpanded}
                inWatchlist={inWatchlist}
                onClose={handleClose}
                onWatchlistToggle={handleWatchlistToggle}
                onExpand={() => setIsExpanded(true)}
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

// Desktop dossier content
interface DossierContentProps {
  location: Location;
  flightArcs: FlightArc[];
  inWatchlist: boolean;
  onClose: () => void;
  onWatchlistToggle: () => void;
}

function DossierContent({
  location,
  flightArcs,
  inWatchlist,
  onClose,
  onWatchlistToggle,
}: DossierContentProps) {
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-200">
        <button
          onClick={onClose}
          className="p-2 hover:bg-neutral-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="h-5 w-5 text-neutral-600" />
        </button>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onWatchlistToggle}
            className={cn(inWatchlist && "text-risk-moderate")}
          >
            <Star className={cn("h-5 w-5", inWatchlist && "fill-current")} />
          </Button>
          <Button variant="ghost" size="icon-sm">
            <Share2 className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-6">
        {/* Location header */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">{getFlagEmoji(location.countryCode)}</span>
            <h2 className="text-xl font-semibold text-neutral-900">{location.name}</h2>
          </div>
          <p className="text-sm text-neutral-500">
            {location.country}
            {location.population && ` • Pop. ${formatCompactNumber(location.population)}`}
          </p>
        </div>

        {/* Risk Score */}
        <RiskScore
          score={location.riskScore}
          weeklyChange={location.weeklyChange}
          showDescription
        />

        {/* Wastewater Trend Chart Placeholder */}
        <div>
          <h3 className="text-sm font-semibold text-neutral-700 mb-3">
            Wastewater Trend (30 days)
          </h3>
          <div className="h-40 bg-neutral-50 rounded-lg border border-neutral-200 flex items-center justify-center">
            <span className="text-sm text-neutral-400">Chart coming soon</span>
          </div>
        </div>

        {/* Variants */}
        {location.variants && location.variants.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-neutral-700 mb-3">
              Dominant Variants
            </h3>
            <div className="flex flex-wrap gap-2">
              {location.variants.map((variant) => (
                <VariantCard key={variant.id} variant={variant} />
              ))}
            </div>
          </div>
        )}

        {/* Incoming Flight Routes */}
        {flightArcs.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-neutral-700 mb-3">
              Top Incoming Routes
            </h3>
            <div className="space-y-2">
              {flightArcs.slice(0, 5).map((arc) => (
                <FlightRouteItem key={arc.id} arc={arc} />
              ))}
            </div>
          </div>
        )}

        {/* Last updated */}
        <div className="flex items-center gap-2 text-xs text-neutral-500 pt-4 border-t border-neutral-200">
          <Clock className="h-3 w-3" />
          <span>Last updated: {formatRelativeTime(location.lastUpdated)}</span>
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              `bg-freshness-current`
            )}
          />
        </div>
      </div>
    </div>
  );
}

// Mobile dossier content (condensed)
interface MobileDossierContentProps {
  location: Location;
  isExpanded: boolean;
  inWatchlist: boolean;
  onClose: () => void;
  onWatchlistToggle: () => void;
  onExpand: () => void;
}

function MobileDossierContent({
  location,
  isExpanded,
  inWatchlist,
  onClose,
  onWatchlistToggle,
  onExpand,
}: MobileDossierContentProps) {
  const riskLevel = getRiskLevel(location.riskScore);
  // Using riskLevel for dynamic styling
  void riskLevel;

  return (
    <div className="px-4 pb-4">
      {/* Condensed header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xl">{getFlagEmoji(location.countryCode)}</span>
          <div>
            <h2 className="font-semibold text-neutral-900">{location.name}</h2>
            <p className="text-xs text-neutral-500">{location.country}</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-neutral-100 rounded-lg"
        >
          <X className="h-5 w-5 text-neutral-600" />
        </button>
      </div>

      {/* Risk summary */}
      <div
        className={cn(
          "flex items-center justify-between p-3 rounded-lg border-2 mb-4",
          `border-risk-${riskLevel}/50 bg-risk-${riskLevel}/10`
        )}
      >
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "text-2xl font-bold font-mono",
              `text-risk-${riskLevel}`
            )}
          >
            {location.riskScore}
          </span>
          <div>
            <p className={cn("text-sm font-medium", `text-risk-${riskLevel}`)}>
              {getRiskLevel(location.riskScore).toUpperCase()} RISK
            </p>
            <p className="text-xs text-neutral-500">
              {location.weeklyChange > 0 ? "+" : ""}
              {location.weeklyChange}% this week
            </p>
          </div>
        </div>
        {!isExpanded && (
          <button
            onClick={onExpand}
            className="p-2 hover:bg-neutral-100 rounded-lg"
          >
            <ChevronDown className="h-5 w-5 text-neutral-400" />
          </button>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <Button
          variant="secondary"
          className="flex-1"
          onClick={onWatchlistToggle}
        >
          <Star
            className={cn(
              "h-4 w-4 mr-2",
              inWatchlist && "fill-risk-moderate text-risk-moderate"
            )}
          />
          {inWatchlist ? "Watching" : "Add to Watchlist"}
        </Button>
        <Button variant="outline" size="icon">
          <Share2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="mt-4 space-y-4">
          {/* Variants */}
          {location.variants && location.variants.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-neutral-700 mb-2">
                Variants
              </h3>
              <div className="flex flex-wrap gap-2">
                {location.variants.map((variant) => (
                  <Badge key={variant.id} variant="secondary">
                    {variant.name} ({variant.prevalence}%)
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Variant card component
function VariantCard({ variant }: { variant: Variant }) {
  return (
    <div className="p-3 bg-neutral-50 rounded-lg border border-neutral-200 min-w-[120px]">
      <div className="flex items-center gap-1 mb-1">
        <span className="text-sm">🧬</span>
        <span className="font-semibold text-neutral-900">{variant.name}</span>
      </div>
      <p className="text-xs text-neutral-500 mb-2">{variant.prevalence}% prevalence</p>
      <div className="flex gap-1">
        <Badge size="sm" variant={variant.severity === "high" ? "high" : "secondary"}>
          {variant.severity}
        </Badge>
      </div>
    </div>
  );
}

// Flight route item
function FlightRouteItem({ arc }: { arc: FlightArc }) {
  const originRisk = getRiskLevel(arc.origin.riskScore);

  return (
    <div className="flex items-center justify-between p-2 hover:bg-neutral-50 rounded-lg transition-colors">
      <div className="flex items-center gap-2">
        <Plane className="h-4 w-4 text-neutral-400" />
        <span className="text-sm text-neutral-900">{arc.origin.name}</span>
        <Badge size="sm" variant={originRisk}>
          {arc.origin.riskScore}
        </Badge>
      </div>
      <span className="text-xs text-neutral-500">
        {formatCompactNumber(arc.dailyPassengers)}/day
      </span>
    </div>
  );
}

// Helper to get flag emoji
function getFlagEmoji(countryCode: string): string {
  if (!countryCode || countryCode.length !== 2) return "🌍";
  const codePoints = countryCode
    .toUpperCase()
    .split("")
    .map((char) => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
}

export default DossierPanel;
