import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Viral Weather - Predictive Viral Risk Intelligence',
  description: 'The Waze for viral avoidance. Real-time viral risk forecasts powered by wastewater surveillance, genomic data, and flight patterns.',
  keywords: ['viral', 'surveillance', 'wastewater', 'COVID', 'health', 'travel'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-dark-bg text-white antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
