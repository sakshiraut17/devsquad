import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { AmbientBackground } from "@/components/layout/AmbientBackground";

const sansFont = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const monoFont = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DevSquad — AI Software Engineering Platform",
  description: "Autonomous multi-agent platform converting GitHub issues into verified code changes.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" style={{ backgroundColor: "#08090D", color: "#F8FAFC" }}>
      <body
        className={`${sansFont.variable} ${monoFont.variable} font-sans bg-background text-foreground min-h-screen flex antialiased relative`}
        style={{ backgroundColor: "#08090D", color: "#F8FAFC", margin: 0 }}
      >
        <AmbientBackground />
        <Sidebar />
        <div
          className="flex-1 flex flex-col min-w-0 min-h-screen relative z-10"
        >
          {children}
        </div>
      </body>
    </html>
  );
}
