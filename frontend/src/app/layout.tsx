import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'Kairos | AI-Powered Micro-Feedback',
  description:
    'Kairos is an AI-powered EdTech platform that delivers instant, concept-level micro-feedback to students, identifying knowledge gaps and providing targeted hints.',
  keywords: ['AI', 'education', 'micro-feedback', 'EdTech', 'assessment'],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} dark`}>
      <body className="font-sans antialiased text-white min-h-screen">
        {children}
      </body>
    </html>
  );
}
