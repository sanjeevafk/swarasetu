import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Send, MoreVertical, Paperclip, ChevronLeft } from 'lucide-react';
import { useAppStore, type AppLanguage } from '@/store/useAppStore';
import { TriageResultCard } from './TriageResultCard';

export function DemoChat({ onShowMap }: { onShowMap: () => void }) {
  const { currentScenario, activeLanguage, setLanguage, demoProgress, setDemoProgress } = useAppStore();
  
  // Progress states: 0=init, 1=recording, 2=stt, 3=ner, 4=imci, 5=result
  const [messages, setMessages] = useState<any[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, demoProgress]);

  // Reset chat when language changes
  useEffect(() => {
    setMessages([{ type: 'bot', text: 'Namaste! Please tell me how your patient is feeling today using a voice note.' }]);
    setDemoProgress(0);
  }, [activeLanguage, setDemoProgress]);

  const handleMicClick = () => {
    if (demoProgress > 0) return;
    setDemoProgress(1); // Recording
    
    setTimeout(() => {
      setMessages(prev => [...prev, { type: 'audio', duration: currentScenario.audioDuration }]);
      setDemoProgress(2); // STT

      setTimeout(() => {
        setMessages(prev => [...prev, { type: 'stt', script: currentScenario.originalScript, english: currentScenario.englishTranslation }]);
        setDemoProgress(3); // NER

        setTimeout(() => {
          setDemoProgress(4); // IMCI

          setTimeout(() => {
            setDemoProgress(5); // Result
          }, 1500);
        }, 1500);
      }, 1500);
    }, 1500);
  };

  return (
    <div className="flex flex-col h-full bg-[#efeae2] dark:bg-[#0b141a] relative font-sans">
      {/* WhatsApp Header */}
      <div className="bg-[#008069] dark:bg-[#202c33] text-white px-3 py-2 flex items-center shadow-md z-10">
        <div className="flex items-center flex-1">
          <ChevronLeft className="w-6 h-6 mr-1" />
          <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center mr-3 font-bold text-lg">
            S
          </div>
          <div>
            <h2 className="font-semibold text-base leading-tight">SwaraSetu Triage</h2>
            <p className="text-xs text-white/80 font-medium tracking-wide">Sarvam AI Triage Engine</p>
          </div>
        </div>
        <div className="flex gap-4">
          <div className="text-xs flex flex-col items-center justify-center bg-white/10 hover:bg-white/20 px-2 rounded cursor-pointer transition-colors" onClick={() => {
             const langs: AppLanguage[] = ['Hindi','Tamil','Bengali'];
             const idx = langs.indexOf(activeLanguage);
             setLanguage(langs[(idx+1)%3]);
          }}>
            <span className="font-bold">{activeLanguage}</span>
            <span className="text-[9px] uppercase tracking-wider">Switch</span>
          </div>
          <MoreVertical className="w-5 h-5 mt-1" />
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3" ref={scrollRef}>
        <AnimatePresence initial={false}>
          {messages.map((m, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className={`flex ${m.type === 'bot' ? 'justify-start' : 'justify-end'}`}
            >
              <div className={`max-w-[85%] rounded-lg p-2.5 shadow-sm text-[15px] ${
                m.type === 'bot' 
                  ? 'bg-white dark:bg-[#202c33] text-slate-800 dark:text-slate-200 rounded-tl-none' 
                  : 'bg-[#d9fdd3] dark:bg-[#005c4b] text-slate-900 dark:text-[#e9edef] rounded-tr-none'
              }`}>
                {m.type === 'bot' && <p>{m.text}</p>}
                
                {m.type === 'audio' && (
                  <div className="flex items-center gap-3 w-48">
                    <div className="w-10 h-10 bg-emerald-500 rounded-full flex items-center justify-center">
                      <Mic className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1 flex items-center gap-1">
                      <div className="h-1.5 w-1.5 bg-slate-500 rounded-full animate-[bounce_1s_infinite]" />
                      <div className="h-2 w-1.5 bg-slate-500 rounded-full animate-[bounce_1s_infinite_100ms]" />
                      <div className="h-3 w-1.5 bg-slate-500 rounded-full animate-[bounce_1s_infinite_200ms]" />
                      <div className="h-1.5 w-1.5 bg-slate-500 rounded-full animate-[bounce_1s_infinite_300ms]" />
                    </div>
                    <span className="text-xs text-slate-500 font-medium">0:0{m.duration}</span>
                  </div>
                )}
                
                {m.type === 'stt' && (
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2 mb-1">
                      <Mic className="w-4 h-4 text-emerald-600" />
                      <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider">Voice Transcribed</span>
                    </div>
                    <p className="font-medium text-slate-800 dark:text-slate-100">{m.script}</p>
                    <p className="text-[13px] text-slate-600 dark:text-slate-300 italic mt-1 pt-1 border-t border-black/10 dark:border-white/10">"{m.english}"</p>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
          
          {demoProgress === 1 && (
            <motion.div initial={{ opacity:0 }} animate={{opacity:1}} exit={{opacity:0}} className="flex justify-end">
              <div className="bg-[#d9fdd3] dark:bg-[#005c4b] rounded-lg p-2 rounded-tr-none text-sm font-medium animate-pulse text-slate-700 dark:text-slate-200">
                Recording audio...
              </div>
            </motion.div>
          )}

          {demoProgress >= 3 && (
            <motion.div initial={{ opacity:0, y: 10 }} animate={{opacity:1, y: 0}} className="flex justify-start w-full my-4">
              <div className="bg-white dark:bg-[#202c33] rounded-lg p-3 w-full border-l-4 border-blue-500 shadow-sm">
                <div className="text-xs font-bold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-widest">Sarvam Extraction JSON</div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(currentScenario.nerExtraction).map(([k,v]) => {
                     if(!v || (Array.isArray(v) && v.length===0)) return null;
                     return (
                       <div key={k} className="bg-slate-50 dark:bg-slate-800 p-2 rounded border border-slate-100 dark:border-slate-700">
                          <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">{k}</div>
                          <div className="font-semibold text-slate-800 dark:text-slate-200 text-[13px] mt-0.5">
                            {Array.isArray(v) ? v.join(', ') : String(v)}
                          </div>
                       </div>
                     )
                  })}
                </div>
              </div>
            </motion.div>
          )}

          {demoProgress >= 4 && (
            <motion.div initial={{ opacity:0, scale:0.95 }} animate={{opacity:1, scale:1}} className="flex justify-start w-full my-4">
               <div className="w-full bg-[#1e1e1e] text-slate-300 rounded-lg p-3 font-mono text-[11px] shadow-lg border border-slate-800">
                  <div className="text-emerald-400 mb-1 font-bold"># IMCI Engine Running...</div>
                  <div className="opacity-80">&gt; evaluating symptoms against WHO guidelines...</div>
                  {demoProgress === 4 ? (
                    <div className="animate-pulse text-amber-400 font-bold">&gt; calculating risk...</div>
                  ) : (
                    <div className="text-emerald-400 font-bold">&gt; decision: {currentScenario.imciDecision}</div>
                  )}
               </div>
            </motion.div>
          )}

          {demoProgress === 5 && (
            <motion.div initial={{ opacity:0, y:20 }} animate={{opacity:1, y:0}} className="w-full mt-2 mb-4">
              <TriageResultCard 
                riskScore={currentScenario.riskScore} 
                message={currentScenario.responseMessageOriginal}
                onShowMap={onShowMap}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input Area */}
      <div className="bg-[#f0f2f5] dark:bg-[#202c33] p-2 md:p-3 flex items-center gap-2 z-10 border-t border-slate-200 dark:border-slate-800 border-opacity-50">
        <button className="p-2 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full transition-colors">
          <Paperclip className="w-6 h-6" />
        </button>
        <div className="flex-1 bg-white dark:bg-[#2a3942] rounded-full h-11 px-4 flex items-center shadow-sm">
          <span className="text-slate-400 text-[15px]">Message</span>
        </div>
        {demoProgress === 0 ? (
          <button 
            onClick={handleMicClick}
            className="w-12 h-12 bg-[#00a884] rounded-full flex items-center text-white justify-center shadow-md hover:scale-105 transition-transform"
          >
            <Mic className="w-6 h-6" />
          </button>
        ) : (
          <button className="w-12 h-12 bg-slate-300 dark:bg-slate-700 rounded-full flex items-center text-slate-500 dark:text-slate-400 justify-center">
            <Send className="w-5 h-5 ml-1" />
          </button>
        )}
      </div>
    </div>
  );
}
