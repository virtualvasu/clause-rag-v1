import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Search, Shield, Zap, Database, ChevronRight, FileText, Gavel } from 'lucide-react';
import TopNav from '../components/TopNav';

export default function LandingPage({ toggleTheme, isDark }) {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { type: 'spring', stiffness: 100, damping: 15 },
    },
  };

  return (
    <div 
      className="min-h-screen relative overflow-hidden"
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {/* Dynamic Cursor Glow */}
      <div 
        className="fixed top-0 left-0 w-[400px] h-[400px] rounded-full pointer-events-none z-0 transition-opacity duration-300"
        style={{
          background: 'radial-gradient(circle, rgba(149, 211, 186, 0.1) 0%, rgba(12, 19, 36, 0) 70%)',
          transform: `translate(${mousePosition.x - 200}px, ${mousePosition.y - 200}px)`,
          opacity: isHovering ? 1 : 0,
        }}
      />

      <div className="content-layer relative z-10">
        <TopNav toggleTheme={toggleTheme} isDark={isDark} />

        {/* Hero Section */}
        <section className="px-margin-mobile md:px-margin-desktop pt-[80px] pb-[120px] max-w-[1440px] mx-auto flex flex-col items-center text-center">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="max-w-[800px] flex flex-col items-center"
          >
            <motion.div variants={itemVariants} className="inline-flex items-center gap-xs px-sm py-xs border border-outline-variant rounded-full mb-lg bg-surface-container-low backdrop-blur-sm">
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest">Clause 2.0 is now live</span>
            </motion.div>
            
            <motion.h1 variants={itemVariants} className="font-headline-xl text-headline-xl text-on-surface mb-lg tracking-tight">
              Institutional Intelligence for<br/>
              <span className="text-primary italic">Complex Legal Workflows</span>
            </motion.h1>
            
            <motion.p variants={itemVariants} className="font-body-lg text-body-lg text-on-surface-variant mb-xl max-w-[600px]">
              Deploy specialized RAG pipelines to navigate intricate merger agreements, extract hidden liabilities, and establish irrefutable factual timelines with source-of-truth grounding.
            </motion.p>
            
            <motion.div variants={itemVariants} className="flex flex-col sm:flex-row items-center gap-md">
              <Link to="/chat" className="w-full sm:w-auto bg-primary hover:bg-inverse-primary text-on-primary font-label-md text-label-md px-[32px] py-[16px] rounded transition-colors flex items-center justify-center gap-sm group">
                Deploy Pipeline
                <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <button className="w-full sm:w-auto border border-outline hover:border-primary text-on-surface hover:text-primary font-label-md text-label-md px-[32px] py-[16px] rounded transition-colors flex items-center justify-center gap-sm">
                <FileText className="w-4 h-4" />
                Read the Whitepaper
              </button>
            </motion.div>
          </motion.div>

          {/* Hero Image/Abstract UI */}
          <motion.div 
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.8, type: 'spring' }}
            className="mt-[80px] w-full max-w-[1000px] h-[400px] rounded-xl border border-outline-variant bg-surface-container-low shadow-[0_20px_40px_-15px_rgba(0,0,0,0.1)] dark:shadow-[0_20px_40px_-15px_rgba(0,0,0,0.5)] overflow-hidden relative"
          >
            <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-5 mix-blend-overlay"></div>
            
            {/* Mock Interface Elements */}
            <div className="absolute top-0 left-0 w-full h-[40px] border-b border-outline-variant bg-surface flex items-center px-md gap-sm">
              <div className="w-3 h-3 rounded-full bg-error"></div>
              <div className="w-3 h-3 rounded-full bg-secondary"></div>
              <div className="w-3 h-3 rounded-full bg-primary"></div>
            </div>
            
            <div className="absolute top-[80px] left-[40px] right-[40px] bottom-[40px] border border-outline-variant rounded flex gap-md p-md backdrop-blur-md bg-surface/50">
              <div className="w-1/3 border border-outline-variant rounded bg-surface-container flex flex-col gap-sm p-sm opacity-80">
                <div className="w-full h-8 bg-surface-variant rounded"></div>
                <div className="w-3/4 h-4 bg-surface-variant rounded"></div>
                <div className="w-5/6 h-4 bg-surface-variant rounded"></div>
              </div>
              <div className="w-2/3 border border-outline-variant border-l-2 border-l-primary rounded bg-surface-container flex flex-col gap-md p-lg">
                <div className="flex gap-sm items-center">
                  <Shield className="w-5 h-5 text-primary" />
                  <div className="w-48 h-6 bg-surface-variant rounded"></div>
                </div>
                <div className="w-full h-3 bg-surface-variant rounded"></div>
                <div className="w-full h-3 bg-surface-variant rounded"></div>
                <div className="w-2/3 h-3 bg-surface-variant rounded"></div>
              </div>
            </div>
          </motion.div>
        </section>

        {/* Feature Grid */}
        <section className="px-margin-mobile md:px-margin-desktop py-[100px] bg-surface-container-low border-y border-outline-variant">
          <div className="max-w-[1440px] mx-auto">
            <div className="mb-xl text-center md:text-left">
              <span className="font-label-md text-label-md text-secondary uppercase tracking-widest mb-sm block">System Capabilities</span>
              <h2 className="font-headline-lg text-headline-lg text-on-surface max-w-[600px]">Architected for uncompromising accuracy and verifiable execution.</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-lg">
              {/* Feature 1 */}
              <div className="p-xl border border-outline-variant rounded bg-surface hover:border-primary transition-colors group">
                <div className="w-12 h-12 rounded bg-primary-container flex items-center justify-center mb-lg group-hover:scale-110 transition-transform">
                  <Database className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-headline-md text-headline-md text-on-surface mb-md">Graph-Augmented Retrieval</h3>
                <p className="font-body-md text-body-md text-on-surface-variant">
                  We don't just match keywords. Clause constructs a dynamic knowledge graph of your precedents, mapping explicit entities and implicit obligations across thousands of documents.
                </p>
              </div>
              
              {/* Feature 2 */}
              <div className="p-xl border border-outline-variant rounded bg-surface hover:border-secondary transition-colors group">
                <div className="w-12 h-12 rounded bg-surface-container flex items-center justify-center mb-lg group-hover:scale-110 transition-transform">
                  <Search className="w-6 h-6 text-secondary" />
                </div>
                <h3 className="font-headline-md text-headline-md text-on-surface mb-md">Deterministic Citations</h3>
                <p className="font-body-md text-body-md text-on-surface-variant">
                  Every assertion is mathematically tied back to the source text. Click any generated insight to view the exact excerpt, page number, and surrounding context.
                </p>
              </div>
              
              {/* Feature 3 */}
              <div className="p-xl border border-outline-variant rounded bg-surface hover:border-primary transition-colors group">
                <div className="w-12 h-12 rounded bg-surface-container flex items-center justify-center mb-lg group-hover:scale-110 transition-transform">
                  <Zap className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-headline-md text-headline-md text-on-surface mb-md">Zero-Data Retention</h3>
                <p className="font-body-md text-body-md text-on-surface-variant">
                  Built for enterprise security. Your data is processed in isolated, ephemeral environments. Models are never trained on your proprietary legal corpus.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="px-margin-mobile md:px-margin-desktop py-xl bg-surface">
          <div className="max-w-[1440px] mx-auto flex flex-col md:flex-row justify-between items-center gap-lg">
            <div className="flex items-center gap-sm">
              <Gavel className="w-5 h-5 text-on-surface-variant" />
              <span className="font-label-md text-label-md text-on-surface-variant font-bold tracking-tight">Clause Systems Inc.</span>
            </div>
            
            <div className="flex gap-lg">
              <a href="#" className="font-label-sm text-label-sm text-on-surface-variant hover:text-primary transition-colors">Privacy Policy</a>
              <a href="#" className="font-label-sm text-label-sm text-on-surface-variant hover:text-primary transition-colors">Terms of Service</a>
              <a href="#" className="font-label-sm text-label-sm text-on-surface-variant hover:text-primary transition-colors">Security Architecture</a>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
