import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Newsreader } from "next/font/google";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"], display: "swap" });
const newsreader = Newsreader({ variable: "--font-newsreader", subsets: ["latin"], display: "swap", style: ["normal", "italic"] });
const jetbrains = JetBrains_Mono({ variable: "--font-jetbrains", subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "Valuo - The long-term case for NEAR, measured",
  description:
    "Reproducible investment-committee research on $NEAR: live NEAR Intents execution benchmarks, on-chain supply accounting, and a fixed-seed sum-of-the-parts Monte Carlo with a falsifiable bear case.",
  applicationName: "Valuo",
  // Absolute base for the Open Graph / Twitter image URLs (app/opengraph-image.png, app/twitter-image.png).
  metadataBase: new URL(
    process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : "https://usevaluo.vercel.app",
  ),
  openGraph: { title: "Valuo", description: "The long-term case for NEAR, made falsifiable.", siteName: "Valuo", type: "website" },
  twitter: { card: "summary_large_image", title: "Valuo", description: "The long-term case for NEAR, made falsifiable." },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${newsreader.variable} ${jetbrains.variable} min-h-screen bg-canvas font-sans text-ink antialiased`}>{children}</body>
    </html>
  );
}
