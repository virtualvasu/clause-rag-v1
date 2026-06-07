import { Link } from 'react-router-dom';
import { Gavel, Plus } from 'lucide-react';

export default function Sidebar() {
  return (
    <nav className="h-screen w-64 fixed left-0 top-0 bg-surface-container-low border-r border-on-surface flex flex-col py-8 z-50 transition-colors duration-300">
      {/* Header */}
      <div className="px-6 mb-12">
        <Link to="/" className="flex items-center gap-4 mb-2 cursor-pointer group">
          <div className="w-8 h-8 bg-on-surface flex items-center justify-center group-hover:bg-primary transition-colors border border-on-surface">
            <Gavel className="text-surface group-hover:text-surface w-4 h-4 transition-colors" />
          </div>
          <div>
            <h1 className="font-headline-md text-2xl text-on-surface uppercase font-bold tracking-tight">Clause</h1>
            <p className="font-mono text-[10px] text-on-surface-variant uppercase tracking-widest">Institutional Grade</p>
          </div>
        </Link>
      </div>

      {/* New Conversation Button */}
      <div className="px-6 mb-8">
        <button 
          onClick={() => window.location.reload()}
          className="w-full bg-surface hover:bg-primary text-on-surface hover:text-surface border border-on-surface font-mono text-xs uppercase tracking-widest flex items-center justify-center gap-3 py-3 transition-colors duration-200"
        >
          <Plus className="w-4 h-4" />
          New Inquiry
        </button>
      </div>

    </nav>
  );
}
