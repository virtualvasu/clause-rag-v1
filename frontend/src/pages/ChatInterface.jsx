import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Moon, Sun, ArrowUp, Paperclip, Lock, 
  Cpu, Search, Network, FileText, Scale, ChevronRight, 
  AlertTriangle, Copy, Flag, Landmark, BookOpen,
  RotateCw, Layers, Server
} from 'lucide-react';
import Sidebar from '../components/Sidebar';

export default function ChatInterface({ toggleTheme, isDark }) {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userQuery = inputValue.trim();
    
    // Add User Message to State
    const newUserMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: userQuery,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    
    setMessages(prev => [...prev, newUserMsg]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userQuery,
          use_crag: true,
          use_graph: true
        })
      });

      if (!response.ok) {
        throw new Error(`API returned status: ${response.status}`);
      }

      const data = await response.json();

      const newAssistantMsg = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.answer,
        citations: data.citations || [],
        crag_score: data.crag_score || 0,
        iterations: data.iterations || 0,
        chunks_used: data.chunks_used || 0,
        provider: data.provider || 'unknown',
        retrieval: data.retrieval || { vector_hits: 0, bm25_hits: 0, graph_hits: 0, candidates: 0 },
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, newAssistantMsg]);
    } catch (error) {
      console.error("Failed to fetch query:", error);
      const errorMsg = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "An error occurred while connecting to the Clause API. Please check if the backend is running.",
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Get the latest assistant message to drive the metadata panel
  const latestAssistantMessage = [...messages].reverse().find(m => m.role === 'assistant' && !m.isError);

  return (
    <div className="bg-background text-on-surface h-screen overflow-hidden flex font-body-md transition-colors duration-300">
      <Sidebar />
      
      {/* Main Layout Workspace */}
      <div className="flex-1 flex ml-64 h-full bg-surface transition-colors duration-300">
        
        {/* Center Column: Chat Canvas */}
        <main className="flex-1 flex flex-col h-full border-r border-outline-variant relative">
          
          {/* Context Header */}
          <header className="h-[60px] min-h-[60px] border-b border-outline-variant flex items-center justify-between px-lg bg-surface/90 backdrop-blur-sm sticky top-0 z-10 transition-colors duration-300">
            <div className="flex flex-col">
              <span className="font-label-sm text-label-sm text-secondary uppercase tracking-widest">Active Inquiry</span>
              <h2 className="font-headline-md text-headline-md text-on-surface truncate">
                {messages.length > 0 ? "Legal Analysis Session" : "New Inquiry"}
              </h2>
            </div>
            <div className="flex items-center gap-sm">
              <button onClick={toggleTheme} className="w-8 h-8 rounded flex items-center justify-center text-on-surface-variant hover:text-primary transition-colors">
                {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </button>
            </div>
          </header>
          
          {/* Scrollable Chat History */}
          <div className="flex-1 overflow-y-auto px-lg py-xl flex flex-col gap-xl">
            {messages.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center opacity-50">
                <Scale className="w-16 h-16 text-primary mb-md" />
                <h3 className="font-headline-lg text-headline-lg text-on-surface mb-sm">What can I help you analyze?</h3>
                <p className="font-body-md text-body-md text-on-surface-variant text-center max-w-md">
                  Query the legal corpus, analyze contracts, or search for precedents.
                </p>
              </div>
            ) : (
              messages.map((msg) => (
                <MessageBubble key={msg.id} msg={msg} />
              ))
            )}
            
            {/* Typing Indicator */}
            {isLoading && (
              <div className="flex justify-start opacity-70">
                <div className="max-w-[85%] flex gap-md items-center">
                  <div className="w-8 h-8 rounded bg-surface-container border border-outline-variant flex-shrink-0 flex items-center justify-center">
                    <Landmark className="text-primary w-[18px] h-[18px]" />
                  </div>
                  <div className="bg-surface-container rounded-lg rounded-tl-none p-md border border-outline-variant border-l-2 border-l-secondary flex items-center gap-1 h-[42px]">
                    <motion.div animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }} transition={{ duration: 1.4, repeat: Infinity, delay: 0 }} className="w-1.5 h-1.5 rounded-full bg-primary" />
                    <motion.div animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }} transition={{ duration: 1.4, repeat: Infinity, delay: 0.16 }} className="w-1.5 h-1.5 rounded-full bg-primary" />
                    <motion.div animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }} transition={{ duration: 1.4, repeat: Infinity, delay: 0.32 }} className="w-1.5 h-1.5 rounded-full bg-primary" />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          
          {/* Input Area */}
          <div className="p-lg bg-surface border-t border-outline-variant z-10 transition-colors duration-300">
            <div className="relative flex items-end gap-sm bg-surface-container-low border border-outline-variant rounded focus-within:border-secondary transition-colors p-sm shadow-[2px_2px_0px_0px_var(--color-surface-container-lowest)]">
              <button className="p-sm text-on-surface-variant hover:text-primary transition-colors flex-shrink-0">
                <Paperclip className="w-5 h-5" />
              </button>
              <textarea 
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                className="flex-1 bg-transparent border-none focus:ring-0 text-on-surface font-body-md resize-none max-h-[120px] min-h-[44px] py-sm px-xs outline-none" 
                placeholder="Ask a question about the Companies Act, SEBI, or DPIIT..." 
                rows={1}
                disabled={isLoading}
              />
              <button 
                onClick={handleSubmit}
                disabled={!inputValue.trim() || isLoading}
                className="p-sm bg-primary text-on-primary rounded hover:bg-inverse-primary disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0 flex items-center justify-center h-10 w-10"
              >
                <ArrowUp className="w-5 h-5" />
              </button>
            </div>
            <div className="mt-sm flex justify-between items-center px-xs">
              <span className="font-label-sm text-label-sm text-on-surface-variant">Clause AI can make mistakes. Verify critical citations.</span>
              <span className="font-label-sm text-label-sm text-secondary flex items-center gap-xs">
                <Lock className="w-[12px] h-[12px]" />
                End-to-End Encrypted
              </span>
            </div>
          </div>
        </main>
        
        {/* Right Column: Metadata Panel (Execution Trace) */}
        <aside className="w-[320px] bg-surface-container-lowest flex flex-col h-full border-l border-outline-variant overflow-y-auto transition-colors duration-300">
          <header className="h-[60px] min-h-[60px] border-b border-outline-variant flex items-center px-md sticky top-0 bg-surface-container-lowest/90 backdrop-blur-sm z-10 transition-colors duration-300">
            <h3 className="font-headline-md text-headline-md text-on-surface flex items-center gap-sm">
              <Cpu className="text-secondary w-5 h-5" />
              Execution Trace
            </h3>
          </header>
          
          {latestAssistantMessage ? (
            <div className="p-md flex flex-col gap-lg">
              {/* CRAG Score Instrumentation */}
              <div className="border border-outline-variant bg-surface-container-low rounded p-md">
                <div className="flex justify-between items-end mb-sm">
                  <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-widest">CRAG Confidence</span>
                  <span className="font-headline-lg text-headline-lg text-primary leading-none">
                    {Math.round(latestAssistantMessage.crag_score * 100)}<span className="text-body-sm">%</span>
                  </span>
                </div>
                <div className="h-2 w-full bg-surface-variant rounded-full overflow-hidden border border-outline-variant">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.round(latestAssistantMessage.crag_score * 100)}%` }}
                    transition={{ duration: 1 }}
                    className="h-full bg-primary relative"
                  />
                </div>
                <div className="mt-xs flex justify-between font-label-sm text-label-sm text-on-surface-variant">
                  <span>Threshold: 85%</span>
                  <span className={latestAssistantMessage.crag_score >= 0.85 ? "text-primary" : "text-error"}>
                    {latestAssistantMessage.crag_score >= 0.85 ? "Validated" : "Low Confidence"}
                  </span>
                </div>
              </div>
              
              {/* Instrumental Metrics Grid */}
              <div className="grid grid-cols-2 gap-sm">
                <div className="border border-outline-variant bg-surface-container-low rounded p-sm flex flex-col justify-between aspect-square">
                  <span className="font-label-sm text-label-sm text-secondary uppercase flex items-center gap-xs">
                    <Search className="w-[14px] h-[14px]" /> Vector Hits
                  </span>
                  <div className="text-right">
                    <span className="font-headline-lg text-headline-lg text-on-surface">
                      {latestAssistantMessage.retrieval?.vector_hits || 0}
                    </span>
                  </div>
                </div>
                <div className="border border-outline-variant bg-surface-container-low rounded p-sm flex flex-col justify-between aspect-square">
                  <span className="font-label-sm text-label-sm text-secondary uppercase flex items-center gap-xs">
                    <Network className="w-[14px] h-[14px]" /> Graph Nodes
                  </span>
                  <div className="text-right">
                    <span className="font-headline-lg text-headline-lg text-on-surface">
                      {latestAssistantMessage.retrieval?.graph_hits || 0}
                    </span>
                  </div>
                </div>
                <div className="border border-outline-variant bg-surface-container-low rounded p-sm flex flex-col justify-between aspect-square">
                  <span className="font-label-sm text-label-sm text-secondary uppercase flex items-center gap-xs">
                    <RotateCw className="w-[14px] h-[14px]" /> Iterations
                  </span>
                  <div className="text-right">
                    <span className="font-headline-lg text-headline-lg text-on-surface">
                      {latestAssistantMessage.iterations || 0}
                    </span>
                  </div>
                </div>
                <div className="border border-outline-variant bg-surface-container-low rounded p-sm flex flex-col justify-between aspect-square">
                  <span className="font-label-sm text-label-sm text-secondary uppercase flex items-center gap-xs">
                    <Layers className="w-[14px] h-[14px]" /> Chunks Used
                  </span>
                  <div className="text-right">
                    <span className="font-headline-lg text-headline-lg text-on-surface">
                      {latestAssistantMessage.chunks_used || 0}
                    </span>
                  </div>
                </div>
              </div>

              {/* Provider Info */}
              <div className="border border-outline-variant bg-surface-container-low rounded p-md flex items-center justify-between">
                <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-widest flex items-center gap-xs">
                  <Server className="w-[16px] h-[16px] text-secondary" /> Provider
                </span>
                <span className="font-headline-sm text-headline-sm text-on-surface capitalize">
                  {latestAssistantMessage.provider || 'unknown'}
                </span>
              </div>
              
              {/* Document Context Analyzed */}
              {latestAssistantMessage.citations && latestAssistantMessage.citations.length > 0 && (
                <div>
                  <h4 className="font-label-md text-label-md text-on-surface-variant uppercase tracking-widest mb-sm border-b border-outline-variant pb-xs">Context Sources</h4>
                  <ul className="flex flex-col gap-sm">
                    {/* Dedup acts for display */}
                    {Array.from(new Set(latestAssistantMessage.citations.map(c => c.act))).map((act, idx) => (
                      <li key={idx} className="flex items-start gap-sm p-sm border border-outline-variant rounded bg-surface-container hover:border-secondary transition-colors cursor-default">
                        <FileText className="text-secondary w-[18px] h-[18px] mt-[2px] flex-shrink-0" />
                        <div className="flex flex-col overflow-hidden">
                          <span className="font-label-md text-label-md text-on-surface truncate">{act}</span>
                          <span className="font-label-sm text-label-sm text-on-surface-variant">
                            {latestAssistantMessage.citations.filter(c => c.act === act).length} citations
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
             <div className="p-md flex flex-col items-center justify-center h-full opacity-50 text-center">
               <Cpu className="w-12 h-12 text-on-surface-variant mb-md" />
               <p className="font-body-md text-body-md text-on-surface-variant">Trace data will appear here once an inquiry is processed.</p>
             </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function MessageBubble({ msg }) {
  const [isCitationOpen, setIsCitationOpen] = useState(false);
  const isUser = msg.role === 'user';

  if (isUser) {
    return (
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
        <div className="max-w-[75%] flex gap-md">
          <div className="bg-primary-container text-on-primary-container rounded-lg rounded-tr-none p-md border border-outline-variant shadow-[2px_2px_0px_0px_rgba(6,78,59,0.5)]">
            <p className="font-body-md text-body-md whitespace-pre-wrap">{msg.content}</p>
          </div>
          <div className="w-8 h-8 rounded-full bg-surface-variant border border-outline-variant flex-shrink-0 flex items-center justify-center overflow-hidden">
            <span className="font-label-md text-label-md text-on-surface">US</span>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex justify-start">
      <div className="max-w-[85%] flex gap-md">
        <div className="w-8 h-8 rounded bg-surface-container border border-outline-variant flex-shrink-0 flex items-center justify-center">
          <Landmark className={`w-[18px] h-[18px] ${msg.isError ? 'text-error' : 'text-primary'}`} />
        </div>
        <div className="flex flex-col gap-sm">
          <div className={`bg-surface-container text-on-surface rounded-lg rounded-tl-none p-md border border-outline-variant border-l-2 ${msg.isError ? 'border-l-error' : 'border-l-secondary'}`}>
            {msg.isError ? (
              <div className="font-body-md text-body-md mb-md whitespace-pre-wrap text-error">
                {msg.content}
              </div>
            ) : (
              <div className="font-body-md text-body-md mb-md prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed prose-headings:font-headline-sm prose-headings:text-primary prose-a:text-secondary prose-code:text-primary prose-code:bg-surface-variant prose-code:px-1 prose-code:rounded prose-strong:text-on-surface prose-strong:font-bold">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>
            )}
            
            {/* Citations Showcase */}
            {!msg.isError && msg.citations && msg.citations.length > 0 && (
              <div className="mt-xl pt-md border-t border-outline-variant">
                <div className="font-label-sm text-label-sm text-secondary uppercase tracking-widest flex items-center gap-xs mb-md">
                  <BookOpen className="w-[14px] h-[14px]" /> Cited Legal Authorities
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-sm">
                  {msg.citations.map((cit, idx) => (
                    <div key={idx} className="bg-surface border border-outline-variant rounded p-sm flex flex-col gap-xs hover:border-secondary transition-colors group shadow-[2px_2px_0px_0px_var(--color-surface-container-lowest)]">
                      <div className="flex justify-between items-start gap-sm">
                        <span className="font-label-md text-label-md text-primary flex items-center gap-xs truncate">
                          <FileText className="w-3 h-3 flex-shrink-0" />
                          <span className="truncate" title={cit.act}>{cit.act}</span>
                        </span>
                        <span className="bg-primary-container text-on-primary-container font-label-sm text-[10px] px-1.5 py-0.5 rounded whitespace-nowrap">
                          {cit.section_type} {cit.section_number}
                        </span>
                      </div>
                      <p className="font-body-sm text-body-sm text-on-surface-variant line-clamp-3 mt-xs" title={cit.section_title || cit.text_excerpt}>
                        {cit.section_title || cit.text_excerpt?.substring(0, 150) + '...'}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          {/* Action Bar below bubble */}
          {!msg.isError && (
            <div className="flex items-center gap-sm px-unit">
              <button className="font-label-sm text-label-sm text-on-surface-variant hover:text-primary transition-colors flex items-center gap-xs">
                <Copy className="w-[14px] h-[14px]" /> Copy
              </button>
              <div className="w-[1px] h-3 bg-outline-variant"></div>
              <button className="font-label-sm text-label-sm text-on-surface-variant hover:text-secondary transition-colors flex items-center gap-xs">
                <Flag className="w-[14px] h-[14px]" /> Flag for Review
              </button>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
