import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import { 
  Sun, Moon, Bell, Settings, Network, Search, 
  ShieldCheck, CheckSquare, Library, BookOpen, 
  Gavel, ArrowRight, Cpu, ChevronRight 
} from 'lucide-react';

export default function LandingPage({ toggleTheme, isDark }) {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);
  const { scrollYProgress } = useScroll();
  const heroY = useTransform(scrollYProgress, [0, 1], ['0%', '10%']);
  const opacityProgress = useTransform(scrollYProgress, [0, 0.2], [1, 0]);

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
        delayChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] }
    }
  };

  return (
    <div 
      className="min-h-screen bg-surface font-body-md text-body-md antialiased selection:bg-primary/30 selection:text-primary relative overflow-x-hidden"
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {/* Dynamic Cursor Glow - more subtle and sharp */}
      <div 
        className="fixed top-0 left-0 w-[400px] h-[400px] rounded-none pointer-events-none z-0 transition-opacity duration-300 mix-blend-screen"
        style={{
          background: 'radial-gradient(circle, rgba(212, 175, 55, 0.05) 0%, rgba(15, 51, 37, 0.02) 40%, rgba(0, 0, 0, 0) 70%)',
          transform: `translate(${mousePosition.x - 200}px, ${mousePosition.y - 200}px)`,
          opacity: isHovering ? 1 : 0,
        }}
      />

      {/* Sharp Grid Pattern Background */}
      <div className="fixed inset-0 z-0 pointer-events-none opacity-[0.05] dark:opacity-[0.1]" 
           style={{ backgroundImage: 'linear-gradient(var(--color-outline-variant) 1px, transparent 1px), linear-gradient(90deg, var(--color-outline-variant) 1px, transparent 1px)', backgroundSize: '64px 64px' }} />

      {/* TopNavBar - Sharp Edges, Thin border */}
      <header className="bg-surface/90 backdrop-blur-md w-full top-0 sticky z-50 border-b border-on-surface transition-all duration-300">
        <div className="flex justify-between items-center px-margin-mobile md:px-margin-desktop py-md w-full max-w-[1440px] mx-auto">
          {/* Brand */}
          <div className="flex items-center gap-md cursor-pointer group">
            <span className="font-headline-md text-headline-md font-bold text-on-surface tracking-tight group-hover:text-primary transition-colors duration-300">CLAUSE.</span>
          </div>
          
          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-xl border-l border-on-surface pl-xl h-8">
            {['Acts & Rules', 'Precedents', 'Compliance', 'Settings'].map((item) => (
              <a key={item} className="font-mono text-label-md uppercase tracking-[0.2em] text-on-surface-variant hover:text-primary transition-colors duration-200 cursor-pointer relative group" href="#">
                {item}
                <span className="absolute -bottom-2 left-0 w-full h-[1px] bg-primary scale-x-0 group-hover:scale-x-100 transition-transform origin-left duration-300"></span>
              </a>
            ))}
          </nav>
          
          {/* Actions */}
          <div className="flex items-center gap-lg">
            <div className="hidden md:flex items-center gap-md text-on-surface border-r border-on-surface pr-lg h-8">
              <button onClick={toggleTheme} className="cursor-pointer hover:text-primary transition-colors duration-200 flex items-center justify-center">
                <span className="font-mono text-label-md uppercase tracking-widest">{isDark ? 'Light' : 'Dark'}</span>
              </button>
            </div>
            <Link to="/chat" className="relative group overflow-hidden bg-on-surface text-surface font-mono text-label-md uppercase tracking-widest px-lg py-sm transition-all duration-300 cursor-pointer border border-on-surface hover:bg-surface hover:text-on-surface flex items-center gap-3">
              <span className="relative z-10">Initialize</span>
              <ArrowRight className="w-4 h-4 relative z-10 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>
      </header>

      <main className="content-layer relative z-10 max-w-[1440px] mx-auto px-margin-mobile md:px-margin-desktop pb-xl">
        
        {/* Hero Section */}
        <section className="min-h-[85vh] flex flex-col justify-center items-center text-center pt-24 pb-xl gap-xl relative perspective-1000 border-x border-outline-variant/30 px-4 md:px-0">
          <div className="absolute top-0 w-full h-[1px] bg-outline-variant/30"></div>
          <div className="absolute bottom-0 w-full h-[1px] bg-outline-variant/30"></div>
          
          <motion.div 
            initial="hidden"
            animate="visible"
            variants={containerVariants}
            style={{ y: heroY, opacity: opacityProgress }}
            className="flex flex-col items-center gap-lg z-10 w-full max-w-5xl"
          >
            <motion.div variants={itemVariants} className="inline-flex items-center gap-4 px-4 py-1 border border-on-surface mb-8 bg-surface">
              <span className="font-mono text-label-sm text-on-surface uppercase tracking-[0.3em]">Clause AI // Institutional Grade</span>
            </motion.div>

            <motion.h1 variants={itemVariants} className="font-headline-xl text-[6rem] leading-[1] md:text-[10rem] text-on-surface tracking-tighter mb-2 relative uppercase">
              <span className="absolute -left-12 top-0 text-xl font-mono text-secondary">01.</span>
              Clause<span className="text-primary">.</span>
            </motion.h1>
            
            <motion.h2 variants={itemVariants} className="font-headline-md text-2xl md:text-4xl text-on-surface-variant font-light italic mb-8">
              Absolute Certainty.
            </motion.h2>
            
            <motion.p variants={itemVariants} className="font-body-lg text-body-lg md:text-xl text-on-surface-variant max-w-2xl font-light leading-relaxed border-l-2 border-primary pl-6 text-left self-center">
              Navigate intricate corporate law, extract hidden liabilities, and establish irrefutable factual timelines. Clause is your AI-powered legal assistant for the Companies Act, SEBI, and MCA Rules.
            </motion.p>
            
            <motion.div variants={itemVariants} className="flex flex-col sm:flex-row items-center gap-6 mt-12 w-full justify-center border-t border-outline-variant/30 pt-12">
              <Link to="/chat" className="group relative w-full sm:w-auto px-12 py-5 bg-transparent text-on-surface font-mono text-label-lg uppercase tracking-[0.2em] transition-all duration-300 border border-on-surface hover:bg-on-surface hover:text-surface overflow-hidden flex items-center justify-center gap-4">
                <span className="relative z-10">Access Terminal</span>
                <ArrowRight className="w-5 h-5 relative z-10 group-hover:translate-x-2 transition-transform duration-300" />
              </Link>
            </motion.div>
          </motion.div>
        </section>

        {/* Abstract Mockup / Visualizer - Brutalist style */}
        <motion.section 
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 1 }}
          className="w-full mt-24 border-y border-outline-variant/50 py-12"
        >
          <div className="w-full max-w-5xl mx-auto aspect-[21/9] relative border border-on-surface bg-surface overflow-hidden flex items-stretch group">
            {/* Terminal Header */}
            <div className="absolute top-0 w-full h-8 border-b border-on-surface flex items-center justify-between px-4 bg-surface z-20">
              <div className="font-mono text-[10px] uppercase tracking-widest text-on-surface">SYS.Terminal_01</div>
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-on-surface"></div>
                <div className="w-2 h-2 border border-on-surface"></div>
                <div className="w-2 h-2 border border-on-surface"></div>
              </div>
            </div>

            <div className="w-full h-full pt-8 flex">
              {/* Sidebar Mock */}
              <div className="w-[200px] h-full border-r border-on-surface flex flex-col p-4 gap-4 bg-surface-container-low">
                <div className="w-full h-4 bg-on-surface/20"></div>
                <div className="w-3/4 h-3 bg-on-surface/10"></div>
                <div className="w-5/6 h-3 bg-on-surface/10"></div>
                <div className="w-1/2 h-3 bg-on-surface/10"></div>
              </div>
              
              {/* Main Area Mock */}
              <div className="flex-1 h-full flex flex-col p-8 relative">
                {/* Data lines */}
                <div className="space-y-6 mt-4 w-full">
                  <div className="flex gap-4">
                    <div className="w-8 font-mono text-xs text-secondary">01</div>
                    <div className="w-[80%] h-4 bg-on-surface/80"></div>
                  </div>
                  <div className="flex gap-4">
                    <div className="w-8 font-mono text-xs text-secondary">02</div>
                    <div className="w-[90%] h-4 border border-on-surface/40 p-2">
                       <div className="w-full h-full bg-primary/20"></div>
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div className="w-8 font-mono text-xs text-secondary">03</div>
                    <div className="w-[60%] h-4 bg-on-surface/40"></div>
                  </div>
                </div>
                
                {/* Accent Block */}
                <div className="mt-auto self-end w-1/2 h-24 border border-secondary bg-surface p-4 flex flex-col justify-between">
                  <div className="w-1/3 h-2 bg-secondary"></div>
                  <div className="w-full h-8 border-t border-secondary/30 pt-2 flex justify-between">
                     <div className="w-1/4 h-full bg-on-surface/10"></div>
                     <div className="w-1/4 h-full bg-on-surface/10"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.section>

        {/* Stats Section */}
        <motion.section 
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={containerVariants}
          className="py-24 border-b border-outline-variant/30"
        >
          <div className="grid grid-cols-2 md:grid-cols-4 gap-0 border-y border-outline-variant/30">
            {[
              { label: 'Legal Chunks', value: '7,367', color: 'text-primary' },
              { label: 'Core Acts', value: '3', color: 'text-secondary' },
              { label: 'Faithfulness', value: '0.984', color: 'text-primary' },
              { label: 'Avg. Response', value: '24ms', color: 'text-secondary' },
            ].map((stat, i) => (
              <motion.div key={i} variants={itemVariants} className="border-x border-outline-variant/30 -ml-[1px] p-8 md:p-12 flex flex-col items-start gap-4 hover:bg-surface-container-low transition-colors duration-300">
                <span className={`font-mono text-label-sm uppercase tracking-[0.2em] ${stat.color}`}>{stat.label}</span>
                <span className="font-headline-lg text-4xl md:text-5xl font-light text-on-surface">{stat.value}</span>
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* Architecture Grid */}
        <motion.section 
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={containerVariants}
          className="py-24 flex flex-col gap-16"
        >
          <motion.div variants={itemVariants} className="flex flex-col items-start gap-6 border-l-4 border-primary pl-8">
            <span className="font-mono text-label-sm text-secondary uppercase tracking-[0.3em]">Capabilities</span>
            <h2 className="font-headline-lg text-4xl md:text-6xl text-on-surface font-light tracking-tight max-w-2xl leading-tight">Uncompromising<br/><span className="italic">Accuracy.</span></h2>
          </motion.div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0 border border-outline-variant/30 auto-rows-[350px]">
            {/* Card 1 */}
            <motion.div variants={itemVariants} className="md:col-span-2 relative group border-b md:border-b-0 md:border-r border-outline-variant/30 bg-surface p-12 flex flex-col justify-between hover:bg-surface-container-low transition-colors duration-500">
              <div className="w-16 h-16 border border-primary flex items-center justify-center">
                <Library className="w-8 h-8 text-primary" />
              </div>
              <div>
                <h3 className="font-headline-md text-3xl text-on-surface mb-4">Comprehensive Corpus</h3>
                <p className="font-body-md text-lg text-on-surface-variant max-w-md font-light">
                  Instantly search and analyze across the entire Companies Act 2013, SEBI Regulations, DPIIT Guidelines, and detailed MCA Rules.
                </p>
              </div>
            </motion.div>

            {/* Card 2 */}
            <motion.div variants={itemVariants} className="relative group bg-surface p-12 flex flex-col justify-between hover:bg-surface-container-low transition-colors duration-500">
              <div className="w-16 h-16 bg-secondary flex items-center justify-center">
                <CheckSquare className="w-8 h-8 text-surface" />
              </div>
              <div>
                <h3 className="font-headline-md text-2xl text-on-surface mb-3">Absolute Faithfulness</h3>
                <p className="font-body-sm text-on-surface-variant font-light">
                  Every response is rigorously verified against the source text to ensure zero hallucinations.
                </p>
              </div>
            </motion.div>

            {/* Card 3 */}
            <motion.div variants={itemVariants} className="relative group bg-surface border-t border-outline-variant/30 p-12 flex flex-col justify-between hover:bg-surface-container-low transition-colors duration-500">
              <div className="w-16 h-16 border-2 border-on-surface flex items-center justify-center">
                <BookOpen className="w-8 h-8 text-on-surface" />
              </div>
              <div>
                <h3 className="font-headline-md text-2xl text-on-surface mb-3">Verifiable Citations</h3>
                <p className="font-body-sm text-on-surface-variant font-light">
                  Every assertion is mathematically mapped to its precise legal source and section.
                </p>
              </div>
            </motion.div>

            {/* Card 4 */}
            <motion.div variants={itemVariants} className="md:col-span-2 relative group border-t border-l md:border-l-0 md:border-t border-outline-variant/30 bg-surface p-12 flex flex-col md:flex-row justify-between items-start md:items-end gap-8 hover:bg-surface-container-low transition-colors duration-500">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-6">
                  <ShieldCheck className="w-6 h-6 text-secondary" />
                  <span className="font-mono text-xs text-secondary uppercase tracking-widest">Security</span>
                </div>
                <h3 className="font-headline-md text-3xl text-on-surface mb-4">Enterprise Privacy</h3>
                <p className="font-body-md text-lg text-on-surface-variant max-w-sm font-light">
                  Built for institutional security. Clause runs securely without exposing your proprietary inquiries or data to public models.
                </p>
              </div>
              <div className="w-full md:w-auto font-mono text-5xl text-outline-variant/20 tracking-tighter self-end">
                [04]
              </div>
            </motion.div>
          </div>
        </motion.section>
      </main>

      {/* Footer */}
      <footer className="bg-surface w-full border-t border-on-surface z-40 relative mt-24">
        <div className="flex flex-col justify-center items-center px-margin-mobile md:px-margin-desktop py-16 w-full max-w-[1440px] mx-auto gap-8">
          <div className="flex items-center justify-between w-full border-b border-outline-variant/30 pb-8">
            <span className="font-headline-md text-2xl text-on-surface font-bold tracking-tight">CLAUSE.</span>
            <span className="font-mono text-xs uppercase tracking-widest text-on-surface-variant">System Offline</span>
          </div>
          <div className="flex flex-col md:flex-row justify-between w-full items-center gap-4">
            <span className="font-mono text-xs text-on-surface-variant">
              © 2026 Clause Legal Technologies.
            </span>
            <div className="flex gap-8">
              {['Privacy', 'Terms', 'Security', 'API'].map((link) => (
                <a key={link} className="font-mono text-xs uppercase tracking-widest text-on-surface hover:text-primary transition-colors" href="#">
                  {link}
                </a>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
