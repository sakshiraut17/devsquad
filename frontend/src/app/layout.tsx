import React from 'react';
import './globals.css';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';

export const metadata = {
  title: 'DevSquad — Autonomous AI Software Engineering Team',
  description: 'Multi-Agent Autonomous AI Engineering Platform powered by LangGraph, FastAPI, and Docker Sandbox.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-white min-h-screen antialiased">
        <Sidebar />
        <Header />
        <main className="pl-64 pt-16 min-h-screen">
          <div className="p-8 max-w-7xl mx-auto space-y-8">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
