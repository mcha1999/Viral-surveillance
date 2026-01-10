import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Viral Weather - Real-time Viral Activity Radar",
  description:
    "Track viral activity worldwide with real-time wastewater surveillance data, genomic variants, and flight transmission routes.",
  keywords: [
    "viral surveillance",
    "wastewater monitoring",
    "disease tracking",
    "pandemic preparedness",
    "viral variants",
  ],
  authors: [{ name: "Viral Weather Team" }],
  openGraph: {
    title: "Viral Weather",
    description: "The Waze for Viral Avoidance",
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#0F172A",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased overflow-hidden">
        {children}
      </body>
    </html>
  );
}
