# UX, Onboarding & Visual Design Recommendations

> **Viral Weather MVP** - Enhancing the user experience for "The Waze for Viral Avoidance"

---

## Executive Summary

This document provides comprehensive recommendations to create an intuitive, engaging, and trustworthy experience for Viral Weather users. The recommendations are organized into three main areas:

1. **User Experience (UX)** - Information architecture, interaction patterns, and user flows
2. **Onboarding** - First-time user experience and progressive engagement
3. **Visual Design** - Design system, theming, and visual language

---

## Part 1: User Experience Recommendations

### 1.1 Information Hierarchy

The app presents complex data (wastewater surveillance, genomic variants, flight vectors). Users need a clear mental model.

#### Recommended Information Layers

```
Layer 1: Global Overview (Default View)
├── Globe with risk heatmap
├── Top 5 "hot zones" highlighted
└── Global trend indicator (↑ Rising / ↓ Falling / → Stable)

Layer 2: Regional Context (On Hover/Click)
├── Country/State name + flag
├── Risk score badge (0-100)
├── Dominant variant chip
└── Data freshness indicator

Layer 3: Location Dossier (Side Panel)
├── Full risk breakdown
├── Wastewater trend chart (30-day)
├── Variant composition pie chart
├── Incoming flight risk list
└── Historical context
```

#### Risk Score Communication

Instead of raw numbers, translate risk into human-understandable terms:

| Score Range | Label | Color | Description |
|-------------|-------|-------|-------------|
| 0-20 | Low | `#22C55E` (Green) | "Minimal viral activity detected" |
| 21-40 | Moderate | `#EAB308` (Yellow) | "Moderate levels, normal caution advised" |
| 41-60 | Elevated | `#F97316` (Orange) | "Above average activity" |
| 61-80 | High | `#EF4444` (Red) | "Significant viral activity" |
| 81-100 | Very High | `#991B1B` (Dark Red) | "Extreme levels detected" |

### 1.2 Core User Flows

#### Flow A: "Check My Area" (Primary Use Case)

```
1. User lands on globe
2. System prompts: "Where would you like to monitor?"
3. User searches/selects location
4. Globe zooms smoothly to location (1.5s animation)
5. Dossier panel slides in from right
6. User sees:
   - Current risk level (large, prominent)
   - 7-day trend sparkline
   - "Add to Watchlist" CTA
7. User can explore nearby areas or add to watchlist
```

**UX Enhancement**: Add a "Quick Glance" summary at the top of the dossier:
```
┌─────────────────────────────────┐
│  New York City                  │
│  Risk: ELEVATED (54/100)        │
│  ↑ 12% vs last week             │
│  Last updated: 2 hours ago ●    │
└─────────────────────────────────┘
```

#### Flow B: "Explore Transmission Routes"

```
1. User clicks location on globe
2. Flight arcs animate in (outgoing first, then incoming)
3. Arc thickness = passenger volume
4. Arc color = risk contribution
5. User hovers arc → tooltip shows:
   - Origin → Destination
   - Daily passengers estimate
   - Source risk level
6. User clicks arc → detailed modal with:
   - Flight frequency
   - Historical transmission correlation
   - "Monitor this route" option
```

#### Flow C: "Travel Planning" (Future Enhancement)

```
1. User enters: "Flying from NYC to London next week"
2. System shows:
   - NYC current risk
   - London current risk
   - Flight route risk factors
   - 7-day forecast for both locations
   - Suggested precautions based on risk
```

### 1.3 Interaction Patterns

#### Globe Interactions

| Action | Desktop | Mobile |
|--------|---------|--------|
| Pan | Click + drag | One finger drag |
| Zoom | Scroll wheel | Pinch |
| Rotate | Right-click + drag | Two finger rotate |
| Select location | Click | Tap |
| Hover preview | Mouse hover | Long press |
| Reset view | Double-click empty space | Double tap |

#### Gestures & Shortcuts

**Desktop Keyboard Shortcuts**:
```
/         → Focus search
Esc       → Close panel/modal, clear selection
← →       → Navigate time scrubber (1 day)
Shift+←/→ → Navigate time scrubber (1 week)
Space     → Play/pause time animation
H         → Return to home location
G         → Toggle globe/2D map
W         → Open watchlist
?         → Show keyboard shortcuts
1-5       → Quick jump to watchlist locations
```

**Mobile Gestures**:
- Swipe up on dossier → Expand to full screen
- Swipe down on dossier → Minimize to peek
- Swipe right on dossier → Close
- Pull down on globe → Refresh data

### 1.4 Feedback & System States

#### Loading States

```
Initial Load:
┌──────────────────────────────────────┐
│  ○ ○ ○                               │
│      Loading global viral data...    │
│      [████████░░░░░░░░] 65%          │
│                                      │
│  Fetching wastewater data            │
│  Calculating risk scores             │
│  Loading flight routes               │
└──────────────────────────────────────┘
```

**Progressive Loading Strategy**:
1. Show globe shell immediately (< 500ms)
2. Load risk heatmap tiles progressively
3. Show location markers as data arrives
4. Load flight arcs on demand (when zoomed in)

#### Empty States

```
No Data for Region:
┌──────────────────────────────────────┐
│        📡                            │
│                                      │
│  No surveillance data available      │
│  for this region yet                 │
│                                      │
│  Coverage is expanding! We're        │
│  working to add more locations.      │
│                                      │
│  [Browse covered regions]            │
└──────────────────────────────────────┘
```

#### Error States

| Error Type | User Message | Action |
|------------|--------------|--------|
| API timeout | "Taking longer than usual..." | Auto-retry with spinner |
| Data stale (7-14d) | Yellow badge: "Data from [date]" | Show cached data |
| Data very stale (14-30d) | Orange badge: "Limited data" | Warning + show anyway |
| Region offline | "Data temporarily unavailable" | Check back + notify option |
| All sources down | "Experiencing difficulties" | Status page link |

### 1.5 Accessibility Requirements

#### MVP Accessibility (Must Have)

- **Keyboard Navigation**: All interactive elements focusable
- **Focus Indicators**: Visible focus rings (3px solid, brand color)
- **Color Independence**: Don't rely on color alone (use patterns/icons)
- **Screen Reader**: Alt text for data visualizations
- **Reduced Motion**: Respect `prefers-reduced-motion`
- **Touch Targets**: Minimum 44x44px on mobile

#### Post-MVP Accessibility (Nice to Have)

- Full WCAG 2.1 AA compliance
- Voice navigation
- High contrast mode
- Screen reader optimized data tables

---

## Part 2: Onboarding Recommendations

### 2.1 First-Time User Experience

#### Onboarding Philosophy

- **Progressive disclosure**: Don't overwhelm with features
- **Value-first**: Show useful data before asking for anything
- **Low friction**: No registration required for MVP
- **Contextual learning**: Teach features when relevant

#### Welcome Flow

```
Step 1: Landing (0s)
┌──────────────────────────────────────┐
│                                      │
│         [Animated Globe]             │
│    Showing current hot zones         │
│                                      │
│    "See viral activity worldwide"    │
│                                      │
└──────────────────────────────────────┘
        ↓ (After 2s, subtle prompt)

Step 2: Location Prompt (2s)
┌──────────────────────────────────────┐
│  ┌─────────────────────────────┐     │
│  │ 📍 Set your home location   │     │
│  │                             │     │
│  │ Get personalized risk       │     │
│  │ updates for your area       │     │
│  │                             │     │
│  │ [Search for a city...]      │     │
│  │                             │     │
│  │ [Skip for now]              │     │
│  └─────────────────────────────┘     │
│         [Globe in background]        │
└──────────────────────────────────────┘

Step 3a: Location Set
┌──────────────────────────────────────┐
│  ✓ Home set to New York City        │
│                                      │
│  [Globe zooms to NYC]                │
│  [Dossier panel opens]               │
│                                      │
│  Tip: "Add up to 5 locations to      │
│       your watchlist"                │
└──────────────────────────────────────┘

Step 3b: Location Skipped
┌──────────────────────────────────────┐
│  [Globe stays on global view]        │
│                                      │
│  Tip: "Click any location to see     │
│       detailed risk information"     │
│                                      │
│  [Highlight a hot zone]              │
└──────────────────────────────────────┘
```

### 2.2 Feature Discovery

#### Contextual Tooltips (First-Time Only)

Show tooltips progressively as user explores:

```
Tooltip 1: After first location click
┌─────────────────────────────────────┐
│ 💡 This is the Dossier Panel        │
│                                     │
│ View detailed risk information,     │
│ trends, and variants for any        │
│ location.                           │
│                                     │
│ [Got it]                            │
└─────────────────────────────────────┘

Tooltip 2: After viewing 3 locations
┌─────────────────────────────────────┐
│ 💡 Add to your Watchlist            │
│                                     │
│ Track up to 5 locations and get     │
│ notified when risk levels change    │
│ significantly.                      │
│                                     │
│ [Show me how] [Dismiss]             │
└─────────────────────────────────────┘

Tooltip 3: First time using time scrubber
┌─────────────────────────────────────┐
│ 💡 Travel through time              │
│                                     │
│ Drag the scrubber to see how viral  │
│ activity has changed over the past  │
│ 30 days.                            │
│                                     │
│ [Got it]                            │
└─────────────────────────────────────┘
```

### 2.3 Watchlist Onboarding

```
First Watchlist Add:
┌──────────────────────────────────────┐
│  ⭐ Location added to Watchlist!    │
│                                      │
│  We'll highlight this location on    │
│  the globe and notify you of         │
│  significant changes.                │
│                                      │
│  Notification threshold: +50%        │
│  [Adjust sensitivity]                │
│                                      │
│  [Add more locations] [Done]         │
└──────────────────────────────────────┘
```

### 2.4 Return User Experience

#### Smart Welcome Back

```
For users with set home location:
┌──────────────────────────────────────┐
│  Welcome back!                       │
│                                      │
│  📍 New York City                    │
│  Risk: MODERATE (38) ↓ 5%            │
│                                      │
│  Your watchlist:                     │
│  • London: HIGH (67) ↑ 12%           │
│  • Tokyo: LOW (18) → stable          │
│                                      │
│  [View details]                      │
└──────────────────────────────────────┘
```

### 2.5 Onboarding Checklist (Gamification Lite)

Optional "Getting Started" panel for engaged users:

```
Getting Started with Viral Weather
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Set your home location
✓ Explore the globe
□ Add a location to watchlist
□ View a location's history
□ Explore flight routes
□ Learn about variants

Progress: 2/6 complete

[Show me what's next]
```

---

## Part 3: Visual Design Recommendations

### 3.1 Design Principles

1. **Trust through clarity**: Clean, scientific aesthetic that conveys accuracy
2. **Calm urgency**: Show risk without causing panic
3. **Data density done right**: Lot of information, zero clutter
4. **Consistency**: Unified visual language across all components

### 3.2 Color System

#### Primary Palette

```css
/* Brand Colors */
--color-primary: #3B82F6;      /* Blue - Trust, reliability */
--color-primary-dark: #1D4ED8;
--color-primary-light: #93C5FD;

/* Neutral Colors */
--color-neutral-900: #111827;  /* Near black */
--color-neutral-800: #1F2937;
--color-neutral-700: #374151;
--color-neutral-600: #4B5563;
--color-neutral-500: #6B7280;
--color-neutral-400: #9CA3AF;
--color-neutral-300: #D1D5DB;
--color-neutral-200: #E5E7EB;
--color-neutral-100: #F3F4F6;
--color-neutral-50: #F9FAFB;

/* Background */
--color-bg-primary: #0F172A;   /* Dark blue-gray for globe bg */
--color-bg-secondary: #1E293B;
--color-bg-panel: #FFFFFF;     /* Light panels for contrast */
```

#### Semantic Colors (Risk Levels)

```css
/* Risk Gradient - Inspired by weather radar */
--risk-low: #22C55E;           /* Green */
--risk-low-gradient: linear-gradient(135deg, #22C55E, #16A34A);

--risk-moderate: #EAB308;      /* Yellow */
--risk-moderate-gradient: linear-gradient(135deg, #EAB308, #CA8A04);

--risk-elevated: #F97316;      /* Orange */
--risk-elevated-gradient: linear-gradient(135deg, #F97316, #EA580C);

--risk-high: #EF4444;          /* Red */
--risk-high-gradient: linear-gradient(135deg, #EF4444, #DC2626);

--risk-very-high: #991B1B;     /* Dark Red */
--risk-very-high-gradient: linear-gradient(135deg, #991B1B, #7F1D1D);
```

#### Data Freshness Colors

```css
--freshness-current: #22C55E;  /* Green - Data < 48 hours */
--freshness-stale: #EAB308;    /* Yellow - 7-14 days */
--freshness-old: #F97316;      /* Orange - 14-30 days */
--freshness-expired: #6B7280;  /* Gray - > 30 days (hidden) */
```

### 3.3 Typography

#### Font Stack

```css
/* Primary - Clean, modern, highly legible */
--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

/* Mono - For data/numbers */
--font-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;

/* Alternative: IBM Plex Sans for more scientific feel */
```

#### Type Scale

```css
--text-xs: 0.75rem;    /* 12px - Labels, captions */
--text-sm: 0.875rem;   /* 14px - Secondary text */
--text-base: 1rem;     /* 16px - Body text */
--text-lg: 1.125rem;   /* 18px - Emphasized text */
--text-xl: 1.25rem;    /* 20px - Section headers */
--text-2xl: 1.5rem;    /* 24px - Page titles */
--text-3xl: 1.875rem;  /* 30px - Hero numbers */
--text-4xl: 2.25rem;   /* 36px - Large displays */

--font-weight-normal: 400;
--font-weight-medium: 500;
--font-weight-semibold: 600;
--font-weight-bold: 700;
```

### 3.4 Component Design

#### Risk Score Badge

```
┌─────────────────────────────────────────────┐
│  ELEVATED RISK                              │
│                                             │
│     ┌───────────────────────┐               │
│     │         54            │  ← Large,     │
│     │        /100           │    prominent  │
│     │   ▲ 12% this week     │               │
│     └───────────────────────┘               │
│                                             │
│  Background: Subtle orange gradient         │
│  Border: 2px solid orange                   │
│  Border-radius: 12px                        │
└─────────────────────────────────────────────┘
```

#### Dossier Panel

```
Desktop (Right side panel, 400px width):
┌────────────────────────────────────────┐
│ ← Back                    [★] [Share]  │
├────────────────────────────────────────┤
│                                        │
│  New York City, USA       🇺🇸          │
│  Population: 8.4M                      │
│                                        │
├────────────────────────────────────────┤
│  ┌──────────────────────────────────┐  │
│  │  ELEVATED    54/100   ▲ 12%     │  │
│  │              ████████░░░         │  │
│  └──────────────────────────────────┘  │
│                                        │
├────────────────────────────────────────┤
│  Wastewater Trend (30 days)            │
│  ┌──────────────────────────────────┐  │
│  │     ╱╲    ╱╲                     │  │
│  │    ╱  ╲  ╱  ╲ ╱╲                 │  │
│  │   ╱    ╲╱    ╳  ╲                │  │
│  │  ╱            ╲  ╲───            │  │
│  └──────────────────────────────────┘  │
│                                        │
├────────────────────────────────────────┤
│  Dominant Variants                     │
│  ┌─────────────┐ ┌─────────────┐       │
│  │ JN.1 (68%)  │ │ BA.2.86(22%)│       │
│  └─────────────┘ └─────────────┘       │
│                                        │
├────────────────────────────────────────┤
│  Top Incoming Routes                   │
│  ✈ London (HIGH)     →  1,200/day      │
│  ✈ Los Angeles (MOD) →  3,400/day      │
│  ✈ Miami (LOW)       →  2,100/day      │
│                                        │
├────────────────────────────────────────┤
│  Last updated: 2 hours ago ● Current   │
└────────────────────────────────────────┘
```

#### Mobile Bottom Sheet

```
┌─────────────────────────────────────────────┐
│                 ━━━━━                       │ ← Drag handle
│  New York City, USA                  🇺🇸    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  ELEVATED  54/100           ▲ 12%  │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  [View Details]  [Add to Watchlist]         │
└─────────────────────────────────────────────┘
        ↓ (Swipe up to expand)
```

#### Time Scrubber

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  30 days ago                    Today        +7 day forecast │
│  │                                │                     │    │
│  ├──────────────────────────────●━━━━━━━━━━━░░░░░░░░░░░░│    │
│  │                              ▲                       │    │
│  │                          Current                     │    │
│                                                              │
│  [◄◄]  [◄]  [▶ Play]  [►]  [►►]              Speed: 1x  ▼   │
│                                                              │
└──────────────────────────────────────────────────────────────┘

Legend:
●━━━━ = Historical data (solid)
░░░░░ = Forecast projection (dashed/semi-transparent)
```

#### Variant Card

```
┌─────────────────────────────────┐
│  🧬 JN.1                        │
│  "Pirola offspring"             │
│                                 │
│  Prevalence: 68%  ▲             │
│  Severity: Moderate             │
│  Transmissibility: High         │
│                                 │
│  Key mutations: L455S, F456L    │
│                                 │
│  [Learn more ↗]                 │
└─────────────────────────────────┘
```

### 3.5 Globe Visualization

#### Visual Treatments

```
Base Globe:
- Background: Deep blue gradient (#0F172A → #1E293B)
- Land: Dark gray (#374151) with subtle border
- Ocean: Transparent or very dark blue
- Country borders: Subtle white (#FFFFFF at 20% opacity)

Risk Overlay:
- Heatmap using risk gradient colors
- Smooth interpolation between data points
- Opacity: 60-80% for visibility

Location Markers:
- Circle with pulsing animation
- Size: Proportional to catchment population
- Color: Risk level color
- Glow effect for "hot zones"

Flight Arcs:
- Curved great circle paths
- Color: Source location risk color
- Width: Log scale of passenger volume
- Animation: Particles flowing along arc
- Opacity: 50% base, 80% on hover
```

#### Visual Hierarchy on Globe

```
Layer Order (bottom to top):
1. Ocean/background
2. Land masses (dark, recede)
3. Country borders (subtle)
4. Risk heatmap (semi-transparent)
5. Flight arcs (on demand)
6. Location markers (always visible)
7. Labels (on hover/zoom)
8. User's home location (highlighted)
```

### 3.6 Spacing & Layout

#### Spacing Scale

```css
--space-0: 0;
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
```

#### Border Radius

```css
--radius-sm: 4px;
--radius-md: 8px;
--radius-lg: 12px;
--radius-xl: 16px;
--radius-full: 9999px;  /* Circles, pills */
```

### 3.7 Motion & Animation

#### Animation Principles

- **Purposeful**: Every animation serves a function
- **Quick**: Most transitions 150-300ms
- **Eased**: Use ease-out for entrances, ease-in for exits
- **Respectful**: Honor `prefers-reduced-motion`

#### Key Animations

```css
/* Standard transition */
--transition-fast: 150ms ease-out;
--transition-base: 200ms ease-out;
--transition-slow: 300ms ease-out;

/* Globe animations */
--globe-zoom-duration: 1500ms;
--globe-zoom-easing: cubic-bezier(0.4, 0, 0.2, 1);

/* Panel animations */
--panel-slide-duration: 250ms;
--panel-slide-easing: cubic-bezier(0.4, 0, 0.2, 1);

/* Pulse animation for markers */
@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.5); opacity: 0.5; }
}

/* Arc particle flow */
@keyframes arcFlow {
  0% { offset-distance: 0%; }
  100% { offset-distance: 100%; }
}
```

### 3.8 Responsive Design

#### Breakpoints

```css
--breakpoint-mobile: 320px;   /* Small phones */
--breakpoint-mobile-lg: 480px; /* Large phones */
--breakpoint-tablet: 768px;    /* Tablets */
--breakpoint-desktop: 1024px;  /* Small desktop */
--breakpoint-desktop-lg: 1280px; /* Large desktop */
--breakpoint-desktop-xl: 1536px; /* Extra large */
```

#### Layout Adaptations

| Component | Desktop | Tablet | Mobile |
|-----------|---------|--------|--------|
| Globe | 3D, full viewport | 3D, full viewport | 2D map fallback |
| Dossier Panel | Right sidebar (400px) | Right sidebar (350px) | Bottom sheet |
| Search | Top center overlay | Top center | Full width |
| Time Scrubber | Bottom, full width | Bottom, full width | Simplified (dates only) |
| Watchlist | Left sidebar | Dropdown | Full screen overlay |
| Navigation | Hidden (minimal) | Top bar | Bottom bar |

### 3.9 Dark Mode (Post-MVP)

```css
/* Dark mode palette */
--dark-bg-primary: #0F172A;
--dark-bg-secondary: #1E293B;
--dark-bg-tertiary: #334155;
--dark-text-primary: #F8FAFC;
--dark-text-secondary: #CBD5E1;
--dark-border: #475569;

/* Light mode (inverted panels) */
--light-bg-primary: #FFFFFF;
--light-bg-secondary: #F8FAFC;
--light-text-primary: #1E293B;
--light-text-secondary: #64748B;
--light-border: #E2E8F0;
```

---

## Part 4: Implementation Priorities

### Phase 1 (MVP Foundation)

**Must Have**:
- [ ] Basic color system with risk gradient
- [ ] Typography scale with Inter font
- [ ] Globe with risk heatmap visualization
- [ ] Location markers with risk colors
- [ ] Dossier panel (desktop + mobile bottom sheet)
- [ ] Simple onboarding (location prompt)
- [ ] Loading states (skeleton + progress)
- [ ] Error states (basic)
- [ ] Keyboard navigation (/, Esc, arrows)

### Phase 2 (Enhanced Experience)

**Should Have**:
- [ ] Time scrubber with animation
- [ ] Flight arc visualization
- [ ] Watchlist with alerts
- [ ] Contextual tooltips (first-time)
- [ ] Empty states with coverage info
- [ ] Data freshness indicators
- [ ] Variant cards

### Phase 3 (Polish)

**Nice to Have**:
- [ ] Getting started checklist
- [ ] Return user welcome
- [ ] Full keyboard shortcuts
- [ ] Micro-interactions and animations
- [ ] Dark mode
- [ ] Advanced accessibility

---

## Part 5: Design Assets Needed

### Design Deliverables Checklist

- [ ] **Figma/Design file** with component library
- [ ] **Color palette** exported as CSS variables
- [ ] **Typography specimen** with all styles
- [ ] **Icon set** (risk levels, navigation, actions)
- [ ] **Globe visualization mockups** (all states)
- [ ] **Dossier panel layouts** (desktop, tablet, mobile)
- [ ] **Empty/Error state illustrations**
- [ ] **Onboarding flow screens**
- [ ] **Animation specifications** (timing, easing)
- [ ] **Responsive breakpoint examples**

### Recommended Tools

- **Design**: Figma (collaborative, component-based)
- **Prototyping**: Figma or Framer
- **Icons**: Lucide React (open source, consistent)
- **Illustrations**: Consider custom or undraw.co
- **Animation**: Framer Motion (React)

---

## Appendix A: Competitive Analysis

### Similar Products to Study

1. **Windy.com** - Weather radar with layers
   - Excellent globe visualization
   - Time scrubber implementation
   - Layer toggling UX

2. **FlightRadar24** - Flight tracking
   - Arc visualization
   - Real-time updates
   - Mobile experience

3. **COVID-19 Dashboards** (JHU, NYT)
   - Risk communication
   - Data density handling
   - Trust/credibility signals

4. **Waze** - Crowdsourced risk
   - Onboarding simplicity
   - Personalization
   - Alert design

---

## Appendix B: User Research Recommendations

### Suggested Research Activities

1. **Usability testing** (5-8 participants)
   - First-time onboarding flow
   - Finding a specific location
   - Understanding risk scores
   - Using time scrubber

2. **Card sorting** (10-15 participants)
   - Information architecture validation
   - Menu/navigation labeling

3. **A/B testing** (post-launch)
   - Onboarding with/without location prompt
   - Risk score display (number vs. label)
   - Dossier panel position

---

*Document Version: 1.0*
*Last Updated: January 2026*
*Author: UX Enhancement Analysis*
