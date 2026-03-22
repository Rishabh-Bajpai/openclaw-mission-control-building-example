'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: '📊' },
  { href: '/orgchart', label: 'Org Chart', icon: '🏢' },
  { href: '/kanban', label: 'Kanban', icon: '📋' },
  { href: '/agents', label: 'Agent Studio', icon: '🤖' },
  { href: '/chat', label: 'Chat', icon: '💬' },
  { href: '/standup', label: 'Standup', icon: '🎙️' },
  { href: '/terminal', label: 'Terminal', icon: '💻' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 h-screen bg-[#0a0a0a] border-r border-[#222] flex flex-col">
      <div className="p-6 border-b border-[#222]">
        <h1 className="text-xl font-bold gold-text">OpenClaw</h1>
        <p className="text-xs text-[#888] mt-1">Mission Control</p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`sidebar-link ${pathname === item.href ? 'active' : ''}`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      <div className="p-4 border-t border-[#222]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[#FBC02D] flex items-center justify-center text-black font-bold">
            CEO
          </div>
          <div>
            <p className="text-sm font-medium">The Boss</p>
            <p className="text-xs text-[#888]">Human CEO</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
