import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Send, MoreVertical, Paperclip, ChevronLeft, CloudOff, Sparkles } from 'lucide-react';
import { useAppStore, type AppLanguage } from '@/store/useAppStore';
import { TriageResultCard } from './TriageResultCard';

interface DemoChatProps {
  onShowMap: () => void;
  titleOverride?: string;
}

export function DemoChat({ onShowMap, titleOverride }: DemoChatProps) {
  const {
    currentScenario,
    activeLanguage,
    setLanguage,
    demoProgress,
    setDemoProgress,
    isEvaluating,
    activeEvaluation,
    isOfflineMode,
    evaluateCurrentScenario,
    evaluateCustomText,
    messages,
    addMessage,
    inputText,
    setInputText,
  } = useAppStore();

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, demoProgress, activeEvaluation]);

  const handleMicClick = async () => {
    if (demoProgress > 0) return;
    setDemoProgress(1); // Recording

    setTimeout(() => {
      addMessage({ type: 'audio', duration: currentScenario.audioDuration });
      setDemoProgress(2); // STT

      setTimeout(() => {
        addMessage({
          type: 'stt',
          script: currentScenario.originalScript,
          english: currentScenario.englishTranslation,
        });
        setDemoProgress(3); // NER

        setTimeout(() => {
          setDemoProgress(4); // IMCI engine running
          void evaluateCurrentScenario().then(() => {
            setTimeout(() => {
              setDemoProgress(5); // Result
            }, 800);
          });
        }, 1000);
      }, 1200);
    }, 1200);
  };

  const handleSendCustomText = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text) return;

    addMessage({ type: 'user_text', text });
    setInputText('');
    setDemoProgress(3); // Analyzing

    try {
      setTimeout(() => {
        setDemoProgress(4); // IMCI running
        void evaluateCustomText(text).then(() => {
          setTimeout(() => {
            setDemoProgress(5);
          }, 800);
        });
      }, 500);
    } catch (err) {
      console.error('Triage failed:', err);
      setDemoProgress(0);
    }
  };

  const activeRes = activeEvaluation;

  // Language-specific quick suggestion chips
  const quickChips: Record<AppLanguage, { label: string; score: number; text: string; color: string }[]> = {
    Hindi: [
      { label: 'Mild Fever (Score 1)', score: 1, text: 'बच्चे को एक दिन से हल्का बुखार है', color: 'emerald' },
      { label: 'Cough & Breathing (Score 2)', score: 2, text: 'बच्चे को खांसी है और सांस लेने में तकलीफ हो रही है', color: 'amber' },
      { label: 'Snake Bite 🐍 (Score 3)', score: 3, text: 'मरीज को सांप ने काट लिया है और चक्कर आ रहे हैं!', color: 'red' },
      { label: 'Chest Pain & Blood (Score 3)', score: 3, text: 'सीने में बहुत तेज दर्द है और खून की उल्टी हो रही है', color: 'rose' },
    ],
    Tamil: [
      { label: 'Mild Fever (Score 1)', score: 1, text: 'என் குழந்தைக்கு ஒரு நாளாக லேசான காய்ச்சல் இருக்கு', color: 'emerald' },
      { label: 'Cough & Breathing (Score 2)', score: 2, text: 'குழந்தைக்கு இருமல் மற்றும் மூச்சுத் திணறல் உள்ளது', color: 'amber' },
      { label: 'Snake Bite 🐍 (Score 3)', score: 3, text: 'என் தம்பிக்கு பாம்பு கடித்துவிட்டது, உடனே உதவி தேவை!', color: 'red' },
      { label: 'Chest Pain & Blood (Score 3)', score: 3, text: 'நெஞ்சு வலி அதிகமாக உள்ளது மற்றும் ரத்த வாந்தி வருகிறது', color: 'rose' },
    ],
    Bengali: [
      { label: 'Mild Fever (Score 1)', score: 1, text: 'বাচ্চার একদিন ধরে হালকা জ্বর আছে', color: 'emerald' },
      { label: 'Cough & Breathing (Score 2)', score: 2, text: 'বাচ্চার কাশি এবং শ্বাস নিতে খুব কষ্ট হচ্ছে', color: 'amber' },
      { label: 'Snake Bite 🐍 (Score 3)', score: 3, text: 'রোগীকে সাপে কামড়েছে, জলদি অ্যাম্বুলেন্স দরকার!', color: 'red' },
      { label: 'Chest Pain & Blood (Score 3)', score: 3, text: 'আমার বুকে খুব ব্যথা হচ্ছে এবং রক্তবমি হচ্ছে!', color: 'rose' },
    ],
  };

  const currentChips = quickChips[activeLanguage] || quickChips.Hindi;

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
            <h2 className="font-semibold text-base leading-tight">
              {titleOverride || 'SwaraSetu Triage'}
            </h2>
            <p className="text-xs text-white/80 font-medium tracking-wide">
              {isOfflineMode ? 'On-Device Edge Engine (Offline)' : 'Sarvam AI Clinical Engine'}
            </p>
          </div>
        </div>
        <div className="flex gap-2 items-center">
          <button
            type="button"
            className="text-xs flex items-center gap-1 bg-white/10 hover:bg-white/20 px-2.5 py-1.5 rounded-full cursor-pointer transition-colors border border-white/20"
            onClick={() => {
              const langs: AppLanguage[] = ['Hindi', 'Tamil', 'Bengali'];
              const idx = langs.indexOf(activeLanguage);
              setLanguage(langs[(idx + 1) % 3]);
            }}
            title="Cycle language"
          >
            <span className="font-bold">{activeLanguage}</span>
            <span className="text-[9px] uppercase tracking-wider bg-white/20 px-1 py-0.2 rounded">Switch</span>
          </button>
          <MoreVertical className="w-5 h-5 text-white/80" />
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
              <div
                className={`max-w-[85%] rounded-lg p-2.5 shadow-sm text-[15px] ${
                  m.type === 'bot'
                    ? 'bg-white dark:bg-[#202c33] text-slate-800 dark:text-slate-200 rounded-tl-none'
                    : 'bg-[#d9fdd3] dark:bg-[#005c4b] text-slate-900 dark:text-[#e9edef] rounded-tr-none'
                }`}
              >
                {m.type === 'bot' && <p>{m.text}</p>}
                {m.type === 'user_text' && <p className="font-medium">{m.text}</p>}

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
                    <span className="text-xs text-slate-500 font-medium">0:0{m.duration || 3}</span>
                  </div>
                )}

                {m.type === 'stt' && (
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2 mb-1">
                      <Mic className="w-4 h-4 text-emerald-600" />
                      <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider">
                        Voice Transcribed ({activeLanguage})
                      </span>
                    </div>
                    <p className="font-medium text-slate-800 dark:text-slate-100">{m.script}</p>
                    <p className="text-[13px] text-slate-600 dark:text-slate-300 italic mt-1 pt-1 border-t border-black/10 dark:border-white/10">
                      "{m.english}"
                    </p>
                  </div>
                )}
              </div>
            </motion.div>
          ))}

          {demoProgress === 1 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex justify-end">
              <div className="bg-[#d9fdd3] dark:bg-[#005c4b] rounded-lg p-2 rounded-tr-none text-sm font-medium animate-pulse text-slate-700 dark:text-slate-200">
                Recording audio note…
              </div>
            </motion.div>
          )}

          {demoProgress >= 4 && (
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="flex justify-start w-full my-4">
              <div className="w-full bg-[#1e1e1e] text-slate-300 rounded-lg p-3 font-mono text-[11px] shadow-lg border border-slate-800">
                <div className="text-emerald-400 mb-1 font-bold"># IMCI Clinical Engine Running...</div>
                <div className="opacity-80">&gt; evaluating symptoms against WHO triage protocols...</div>
                {demoProgress === 4 || isEvaluating ? (
                  <div className="animate-pulse text-amber-400 font-bold">&gt; calculating clinical risk score...</div>
                ) : activeRes ? (
                  <>
                    <div className="text-emerald-400 font-bold">
                      &gt; decision: risk score {activeRes.outcome.risk_score} ({activeRes.outcome.primary_cluster})
                    </div>
                    {activeRes.evaluatedOffline && (
                      <div className="mt-1 flex items-center gap-1 text-amber-400">
                        <CloudOff className="w-3 h-3" /> on-device IMCI engine (offline)
                      </div>
                    )}
                  </>
                ) : null}
              </div>
            </motion.div>
          )}

          {demoProgress === 5 && activeRes && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full mt-2 mb-4">
              <TriageResultCard
                outcome={activeRes.outcome}
                evaluatedOffline={activeRes.evaluatedOffline}
                emergencyDispatch={activeRes.emergency_dispatch}
                message={activeRes.directive?.message_en ?? activeRes.outcome.rationale_en}
                onShowMap={onShowMap}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Quick Suggestion Symptom Chips - Language Aware */}
      <div className="px-3 py-1.5 bg-[#f0f2f5]/90 dark:bg-[#1a2329]/90 border-t border-slate-200 dark:border-slate-800 flex gap-2 overflow-x-auto no-scrollbar">
        {currentChips.map((chip, idx) => (
          <button
            key={idx}
            onClick={() => handleSendCustomText(chip.text)}
            className={`text-xs px-2.5 py-1 rounded-full border flex-shrink-0 flex items-center gap-1 transition-all ${
              chip.score === 1
                ? 'bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800'
                : chip.score === 2
                ? 'bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800'
                : 'bg-red-50 hover:bg-red-100 dark:bg-red-950/40 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800'
            }`}
          >
            <Sparkles className="w-3 h-3" /> {chip.label}
          </button>
        ))}
      </div>

      {/* Input Area */}
      <div className="bg-[#f0f2f5] dark:bg-[#202c33] p-2 md:p-3 flex items-center gap-2 z-10 border-t border-slate-200 dark:border-slate-800">
        <button className="p-2 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full transition-colors">
          <Paperclip className="w-5 h-5" />
        </button>
        <div className="flex-1 bg-white dark:bg-[#2a3942] rounded-full h-11 px-4 flex items-center shadow-sm">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSendCustomText();
              }
            }}
            placeholder={`Type symptoms in ${activeLanguage} or English...`}
            className="w-full bg-transparent text-slate-900 dark:text-slate-100 placeholder:text-slate-400 text-sm focus:outline-none"
          />
        </div>

        {inputText.trim() ? (
          <button
            onClick={() => handleSendCustomText()}
            className="w-11 h-11 bg-[#00a884] rounded-full flex items-center text-white justify-center shadow-md hover:scale-105 transition-transform"
          >
            <Send className="w-5 h-5 ml-0.5" />
          </button>
        ) : (
          <button
            onClick={handleMicClick}
            title="Click to simulate voice note input"
            className="w-11 h-11 bg-[#00a884] rounded-full flex items-center text-white justify-center shadow-md hover:scale-105 transition-transform"
          >
            <Mic className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
}
