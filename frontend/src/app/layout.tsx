import type { Metadata } from "next";
import Sidebar from '@/components/Sidebar';
import LogTerminal from '@/components/LogTerminal';
import "./globals.css";

export const metadata: Metadata = {
  title: "OpenClaw Mission Control",
  description: "Centralized command-and-control dashboard for AI agents",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6 pb-[60px] scrollbar-thin">
          {children}
        </main>
        <LogTerminal />
      </body>
    </html>
  );
}
