import { Link } from 'react-router-dom';
import { Moon, Sun, ArrowRight, Gavel } from 'lucide-react';

export default function TopNav({ toggleTheme, isDark }) {
  return (
    <header className="bg-surface dark:bg-surface w-full top-0 sticky z-50 border-b border-outline-variant transition-colors duration-300">
      <div className="flex justify-between items-center px-margin-mobile md:px-margin-desktop py-md w-full max-w-[1440px] mx-auto">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-md cursor-pointer group">
          <Gavel className="text-primary w-6 h-6 group-hover:scale-110 transition-transform" />
          <span className="font-headline-md text-headline-md font-bold text-primary tracking-tight">Clause</span>
        </Link>
        
        {/* Navigation Links (Desktop) */}
        <nav className="hidden md:flex items-center gap-lg">
          <a href="#" className="font-label-md text-label-md text-on-surface-variant hover:text-primary transition-colors">Products</a>
          <a href="#" className="font-label-md text-label-md text-on-surface-variant hover:text-primary transition-colors">Solutions</a>
          <a href="#" className="font-label-md text-label-md text-on-surface-variant hover:text-primary transition-colors">Pricing</a>
          <a href="#" className="font-label-md text-label-md text-on-surface-variant hover:text-primary transition-colors">Resources</a>
        </nav>
        
        {/* Actions */}
        <div className="flex items-center gap-md">
          <button 
            onClick={toggleTheme}
            className="w-10 h-10 rounded-full hover:bg-surface-variant flex items-center justify-center text-on-surface-variant hover:text-primary transition-colors"
            aria-label="Toggle dark mode"
          >
            {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
          <div className="hidden md:block w-[1px] h-6 bg-outline-variant"></div>
          <Link to="/chat" className="hidden md:flex items-center gap-sm font-label-md text-label-md text-primary hover:text-inverse-primary transition-colors">
            Sign In
          </Link>
          <Link to="/chat" className="bg-primary hover:bg-inverse-primary text-on-primary font-label-md text-label-md px-lg py-sm rounded transition-all duration-200 hover:shadow-lg flex items-center gap-sm group">
            Get Started
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </div>
    </header>
  );
}
