import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Research Paper Summarizer | AI-Powered Discovery",
  description: "Autonomous pipeline that discovers, curates, and summarizes the latest research papers tailored to your interests.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://higxlckrcpqxhodibmax.supabase.co" />
        <link rel="dns-prefetch" href="https://higxlckrcpqxhodibmax.supabase.co" />
      </head>
      <body className={`${inter.variable} antialiased min-h-screen flex flex-col`}>
        {/* Ambient gradients are now in globals.css as body::before — zero JS, zero animation cost */}
        <main className="flex-grow flex flex-col">
          {children}
        </main>
      </body>
    </html>
  );
}
