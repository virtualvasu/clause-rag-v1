import { Link } from 'react-router-dom';
import { Gavel, Plus } from 'lucide-react';

export default function Sidebar() {
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

    </nav>
  );
}
