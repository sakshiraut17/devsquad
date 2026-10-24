import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { AmbientBackground } from "@/components/layout/AmbientBackground";

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
    <html lang="en" className="dark" style={{ backgroundColor: "#07090E", color: "#F1F4ED" }}>
      <body
        className="bg-background text-foreground min-h-screen flex antialiased relative"
        style={{ backgroundColor: "#07090E", color: "#F1F4ED", margin: 0 }}
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
