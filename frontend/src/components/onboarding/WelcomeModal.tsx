'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLocationStore, useOnboardingStore } from '@/lib/store';
import { useQuery } from '@tanstack/react-query';
import { autocomplete } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { getRiskLevel } from '@/lib/utils';
import { Globe, MapPin, Clock, Bell, Search, ArrowRight, Check } from 'lucide-react';

interface WelcomeModalProps {
  onComplete: () => void;
}

export function WelcomeModal({ onComplete }: WelcomeModalProps) {
  const [step, setStep] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const { setHomeLocation, setSelectedLocation } = useLocationStore();
  const { setHasSeenWelcome, markStepComplete } = useOnboardingStore();

  // Autocomplete for location search
  const { data: suggestions = [] } = useQuery({
    queryKey: ['autocomplete', searchQuery],
    queryFn: () => autocomplete(searchQuery, 5),
    enabled: searchQuery.length >= 2,
    staleTime: 60 * 1000,
  });

  const handleLocationSelect = useCallback((id: string, name: string) => {
    setHomeLocation(id);
    setSelectedLocation(id);
    markStepComplete('set_home');
    setStep(3);
  }, [setHomeLocation, setSelectedLocation, markStepComplete]);

  const handleSkip = useCallback(() => {
    setStep(3);
  }, []);

  const handleComplete = useCallback(() => {
    setHasSeenWelcome(true);
    markStepComplete('completed_welcome');
    onComplete();
  }, [setHasSeenWelcome, markStepComplete, onComplete]);

  const backdropVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
  };

  const modalVariants = {
    hidden: { opacity: 0, scale: 0.95, y: 20 },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      transition: { type: 'spring' as const, damping: 25, stiffness: 300 },
    },
    exit: {
      opacity: 0,
      scale: 0.95,
      y: 20,
      transition: { duration: 0.15 },
    },
  };

  const stepVariants = {
    enter: { opacity: 0, x: 20 },
    center: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -20 },
  };

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      exit="hidden"
      variants={backdropVariants}
      className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
    >
      <motion.div
        variants={modalVariants}
        className="bg-background-panel border border-border rounded-2xl shadow-2xl max-w-md w-full overflow-hidden"
      >
        {/* Progress indicator */}
        <div className="flex gap-1 p-4 pb-0">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
                s <= step ? 'bg-primary' : 'bg-border'
              }`}
            />
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* Step 1: Welcome */}
          {step === 1 && (
            <motion.div
              key="step1"
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.2 }}
              className="p-6 text-center"
            >
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center">
                <Globe className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-foreground mb-2">
                Welcome to Viral Weather
              </h2>
              <p className="text-foreground-muted mb-6">
                Track viral activity worldwide with real-time wastewater surveillance, genomic data, and flight transmission routes.
              </p>
              <div className="space-y-3">
                <FeatureItem
                  icon={<Globe className="w-4 h-4 text-risk-low" />}
                  iconBg="bg-risk-low/20"
                  title="Explore the Globe"
                  description="Click any location to see risk details"
                />
                <FeatureItem
                  icon={<Bell className="w-4 h-4 text-risk-moderate" />}
                  iconBg="bg-risk-moderate/20"
                  title="Build Your Watchlist"
                  description="Track up to 5 locations you care about"
                />
                <FeatureItem
                  icon={<Clock className="w-4 h-4 text-primary" />}
                  iconBg="bg-primary/20"
                  title="Travel Through Time"
                  description="See 30 days of history and 7-day forecasts"
                />
              </div>
              <Button className="w-full mt-6" onClick={() => setStep(2)}>
                Get Started
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </motion.div>
          )}

          {/* Step 2: Set Home Location */}
          {step === 2 && (
            <motion.div
              key="step2"
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.2 }}
              className="p-6"
            >
              <div className="text-center mb-6">
                <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-primary/20 flex items-center justify-center">
                  <MapPin className="w-6 h-6 text-primary" />
                </div>
                <h2 className="text-xl font-bold text-foreground mb-1">
                  Set Your Home Location
                </h2>
                <p className="text-foreground-muted text-sm">
                  Get personalized risk updates for your area
                </p>
              </div>

              {/* Search input */}
              <Input
                icon={<Search className="w-4 h-4" />}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search for a city..."
                className="mb-4"
                autoFocus
              />

              {/* Suggestions */}
              {suggestions.length > 0 && (
                <div className="bg-background-secondary border border-border rounded-lg overflow-hidden mb-4 max-h-48 overflow-y-auto custom-scrollbar">
                  {suggestions.map((suggestion) => (
                    <button
                      key={suggestion.id}
                      onClick={() => handleLocationSelect(suggestion.id, suggestion.label)}
                      className="w-full px-4 py-3 text-left hover:bg-background-elevated transition-colors border-b border-border last:border-0 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        <MapPin className="w-4 h-4 text-foreground-muted flex-shrink-0" />
                        <span className="text-foreground">{suggestion.label}</span>
                      </div>
                      {suggestion.risk_score !== undefined && (
                        <Badge variant={getRiskLevel(suggestion.risk_score)} size="sm">
                          {Math.round(suggestion.risk_score)}
                        </Badge>
                      )}
                    </button>
                  ))}
                </div>
              )}

              {searchQuery.length >= 2 && suggestions.length === 0 && (
                <div className="text-center text-foreground-muted py-4 mb-4">
                  No locations found
                </div>
              )}

              <Button variant="ghost" className="w-full" onClick={handleSkip}>
                Skip for now
              </Button>
            </motion.div>
          )}

          {/* Step 3: Ready to Go */}
          {step === 3 && (
            <motion.div
              key="step3"
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.2 }}
              className="p-6 text-center"
            >
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-risk-low to-emerald-600 flex items-center justify-center">
                <Check className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-foreground mb-2">
                You&apos;re All Set!
              </h2>
              <p className="text-foreground-muted mb-6">
                Start exploring viral activity around the world. Click any location on the globe to see detailed risk information.
              </p>
              <div className="bg-background-secondary rounded-lg p-4 mb-6 text-left">
                <h3 className="text-sm font-medium text-foreground mb-2">Quick Tips</h3>
                <ul className="space-y-2 text-sm text-foreground-muted">
                  <li className="flex items-center gap-2">
                    <kbd className="px-1.5 py-0.5 bg-background-elevated rounded text-xs font-mono">/</kbd>
                    <span>Quick search</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <kbd className="px-1.5 py-0.5 bg-background-elevated rounded text-xs font-mono">?</kbd>
                    <span>View all shortcuts</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <kbd className="px-1.5 py-0.5 bg-background-elevated rounded text-xs font-mono">Space</kbd>
                    <span>Play/pause timeline</span>
                  </li>
                </ul>
              </div>
              <Button className="w-full" onClick={handleComplete}>
                Start Exploring
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  );
}

function FeatureItem({
  icon,
  iconBg,
  title,
  description,
}: {
  icon: React.ReactNode;
  iconBg: string;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-center gap-3 text-left p-3 bg-background-secondary rounded-lg">
      <div className={`w-8 h-8 rounded-full ${iconBg} flex items-center justify-center flex-shrink-0`}>
        {icon}
      </div>
      <div>
        <div className="text-foreground text-sm font-medium">{title}</div>
        <div className="text-foreground-muted text-xs">{description}</div>
      </div>
    </div>
  );
}
