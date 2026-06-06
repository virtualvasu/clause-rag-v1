import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Gavel,
  Plus,
  MessageSquare,
  Bookmark,
  Scale,
  BookOpen,
  Network,
  HelpCircle,
  LogOut
} from 'lucide-react';
import { cn } from '../lib/utils';

export default function Sidebar() {
  const [activeItem, setActiveItem] = useState('chat');

  const navItems = [
    { id: 'chat', label: 'Analysis: Indemnification...', icon: MessageSquare },
    { id: 'saved', label: 'Saved Clauses', icon: Bookmark },
    { id: 'caselaw', label: 'Case Law', icon: Scale },
    { id: 'statutes', label: 'Legal Statutes', icon: BookOpen },
    { id: 'traces', label: 'Execution Traces', icon: Network },
  ];

  return (
    <nav className="h-screen w-64 fixed left-0 top-0 bg-surface-container-low border-r border-outline-variant flex flex-col py-lg z-50 transition-colors duration-300">
      {/* Header */}
      <div className="px-md mb-lg">
        <Link to="/" className="flex items-center gap-sm mb-xs cursor-pointer group">
          <div className="w-8 h-8 rounded bg-primary-container flex items-center justify-center group-hover:bg-primary transition-colors">
            <Gavel className="text-primary group-hover:text-on-primary w-4 h-4 transition-colors" />
          </div>
          <div>
            <h1 className="font-headline-md text-headline-md text-primary">Clause</h1>
            <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Institutional Grade</p>
          </div>
        </Link>
      </div>

      {/* New Conversation Button */}
      <div className="px-md mb-md">
        <button 
          onClick={() => window.location.reload()}
          className="w-full bg-primary hover:bg-inverse-primary text-on-primary font-label-md text-label-md rounded flex items-center justify-center gap-sm py-sm transition-colors duration-200"
        >
          <Plus className="w-4 h-4" />
          New Inquiry
        </button>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto mt-sm">
        <ul className="flex flex-col gap-unit px-unit">
          {navItems.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => setActiveItem(item.id)}
                className={cn(
                  "w-full flex items-center gap-sm py-sm rounded-r-DEFAULT pl-4 transition-all duration-150 ease-in-out font-label-md text-label-md hover:bg-surface-bright hover:text-on-surface",
                  activeItem === item.id
                    ? "text-primary font-bold border-l-2 border-secondary bg-surface-bright/20 pl-3"
                    : "text-on-surface-variant"
                )}
              >
                <item.icon className="w-[18px] h-[18px]" />
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Footer Actions */}
      <div className="px-md mt-auto pt-md border-t border-outline-variant">
        <button className="w-full mb-md py-sm border border-secondary text-secondary rounded font-label-md text-label-md hover:bg-secondary/10 transition-colors">
          Upgrade to Pro
        </button>
        <ul className="flex flex-col gap-unit">
          <li>
            <button className="w-full flex items-center gap-sm py-sm text-on-surface-variant hover:text-primary transition-colors font-label-md text-label-md">
              <HelpCircle className="w-4 h-4" />
              Help Center
            </button>
          </li>
          <li>
            <button className="w-full flex items-center gap-sm py-sm text-on-surface-variant hover:text-primary transition-colors font-label-md text-label-md">
              <LogOut className="w-4 h-4" />
              Log Out
            </button>
          </li>
        </ul>
      </div>
    </nav>
  );
}
