import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Send, Activity, CloudOff, Sparkles, Volume2 } from 'lucide-react';
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
  const quickChips: Record<AppLanguage, { label: string; score: number; text: string }[]> = {
    Hindi: [
      { label: 'Mild Fever (Score 1)', score: 1, text: 'बच्चे को एक दिन से हल्का बुखार है' },
      { label: 'Cough & Fast Breathing (Score 2)', score: 2, text: 'बच्चे को खांसी है और तेज सांस चल रही है' },
      { label: 'Snake Bite 🐍 (Score 3)', score: 3, text: 'मरीज को सांप ने काट लिया है और चक्कर आ रहे हैं!' },
      { label: 'Chest Pain & Blood (Score 3)', score: 3, text: 'सीने में बहुत तेज दर्द है और खून की उल्टी हो रही है' },
    ],
    Tamil: [
      { label: 'Mild Fever (Score 1)', score: 1, text: 'என் குழந்தைக்கு ஒரு நாளாக லேசான காய்ச்சல் இருக்கு' },
      { label: 'Cough & Fast Breathing (Score 2)', score: 2, text: 'குழந்தைக்கு இருமல் மற்றும் மூச்சுத் திணறல் உள்ளது' },
      { label: 'Snake Bite 🐍 (Score 3)', score: 3, text: 'என் தம்பிக்கு பாம்பு கடித்துவிட்டது, உடனே உதவி தேவை!' },
      { label: 'Chest Pain & Blood (Score 3)', score: 3, text: 'நெஞ்சு வலி அதிகமாக உள்ளது மற்றும் ரத்த வாந்தி வருகிறது' },
    ],
    Bengali: [
      { label: 'Mild Fever (Score 1)', score: 1, text: 'বাচ্চার একদিন ধরে হালকা জ্বর আছে' },
      { label: 'Cough & Fast Breathing (Score 2)', score: 2, text: 'বাচ্চার কাশি এবং দ্রুত শ্বাস চলছে' },
      { label: 'Snake Bite 🐍 (Score 3)', score: 3, text: 'রোগীকে সাপে কামড়েছে, জলদি অ্যাম্বুলেন্স দরকার!' },
      { label: 'Chest Pain & Blood (Score 3)', score: 3, text: 'আমার বুকে খুব ব্যথা হচ্ছে এবং রক্তবমি হচ্ছে!' },
    ],
  };

  const currentChips = quickChips[activeLanguage] || quickChips.Hindi;

  return (
    <div className="flex flex-col h-full bg-[#f8fafc] relative font-sans text-slate-900">
      {/* Header matching ASHA Portal aesthetic */}
      <div className="bg-[#0f4c42] text-white px-4 py-3 flex items-center justify-between shadow-sm z-10">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center text-white">
            <Activity className="w-4 h-4 stroke-[2.5]" />
          </div>
          <div>
            <h2 className="font-bold text-sm leading-tight text-white">
              {titleOverride || 'SwaraSetu — Voice Triage'}
            </h2>
            <p className="text-[11px] text-emerald-200 font-medium">
              {isOfflineMode ? 'Edge Mode Active (Offline)' : 'Live Sarvam AI Clinical Engine'}
            </p>
          </div>
        </div>

        <button
          type="button"
          className="text-xs flex items-center gap-1.5 bg-white/10 hover:bg-white/20 px-2.5 py-1 rounded-lg transition-all border border-white/20 text-white font-medium shadow-sm"
          onClick={() => {
            const langs: AppLanguage[] = ['Hindi', 'Tamil', 'Bengali'];
            const idx = langs.indexOf(activeLanguage);
            setLanguage(langs[(idx + 1) % 3]);
          }}
          title="Cycle language"
        >
          <span>{activeLanguage}</span>
          <span className="text-[9px] uppercase tracking-wider bg-white/25 px-1 py-0.2 rounded font-bold">
            Change
          </span>
        </button>
      </div>

      {/* Chat Messages Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3" ref={scrollRef}>
        <AnimatePresence initial={false}>
          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className={`flex ${m.type === 'bot' ? 'justify-start' : 'justify-end'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl p-3 shadow-sm text-sm ${
                  m.type === 'bot'
                    ? 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm'
                    : 'bg-emerald-50 border border-emerald-200 text-slate-900 rounded-tr-sm'
                }`}
              >
                {m.type === 'bot' && <p className="leading-relaxed">{m.text}</p>}
                {m.type === 'user_text' && <p className="font-semibold leading-relaxed">{m.text}</p>}

                {m.type === 'audio' && (
                  <div className="flex items-center gap-3 w-52 py-1">
                    <div className="w-9 h-9 bg-emerald-600 rounded-full flex items-center justify-center text-white shadow-sm shrink-0">
                      <Volume2 className="w-4 h-4" />
                    </div>
                    <div className="flex-1 flex items-center gap-1">
                      <div className="h-2 w-1.5 bg-emerald-600 rounded-full animate-[bounce_1s_infinite]" />
                      <div className="h-4 w-1.5 bg-emerald-600 rounded-full animate-[bounce_1s_infinite_100ms]" />
                      <div className="h-6 w-1.5 bg-emerald-600 rounded-full animate-[bounce_1s_infinite_200ms]" />
                      <div className="h-3 w-1.5 bg-emerald-600 rounded-full animate-[bounce_1s_infinite_300ms]" />
                    </div>
                    <span className="text-xs text-slate-500 font-bold">0:0{m.duration || 3}</span>
                  </div>
                )}

                {m.type === 'stt' && (
                  <div className="flex flex-col">
                    <div className="flex items-center gap-1.5 mb-1">
                      <Mic className="w-3.5 h-3.5 text-emerald-700" />
                      <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">
                        Transcribed ({activeLanguage})
                      </span>
                    </div>
                    <p className="font-bold text-slate-900 text-sm">{m.script}</p>
                    <p className="text-xs text-slate-600 italic mt-1.5 pt-1.5 border-t border-emerald-100">
                      "{m.english}"
                    </p>
                  </div>
                )}
              </div>
            </motion.div>
          ))}

          {demoProgress === 1 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex justify-end">
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl rounded-tr-sm p-3 text-xs font-semibold animate-pulse flex items-center gap-2">
                <Mic className="w-3.5 h-3.5 text-emerald-600 animate-spin" /> Recording audio note…
              </div>
            </motion.div>
          )}

          {demoProgress >= 4 && (
            <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="flex justify-start w-full my-2">
              <div className="w-full bg-white text-slate-800 rounded-xl p-3 font-mono text-xs shadow-sm border border-slate-200 space-y-1">
                <div className="text-emerald-700 font-bold flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5" /> WHO IMCI Clinical Protocol
                </div>
                <div className="text-slate-500">&gt; Evaluating clinical danger signs...</div>
                {demoProgress === 4 || isEvaluating ? (
                  <div className="animate-pulse text-amber-600 font-bold">&gt; Calculating risk score &amp; action plan...</div>
                ) : activeRes ? (
                  <>
                    <div className="text-emerald-800 font-bold">
                      &gt; Decision: Risk Score {activeRes.outcome.risk_score} ({activeRes.outcome.primary_cluster})
                    </div>
                    {activeRes.evaluatedOffline && (
                      <div className="flex items-center gap-1 text-amber-700 text-[11px] font-semibold">
                        <CloudOff className="w-3 h-3 text-amber-600" /> On-Device IMCI Engine (Offline)
                      </div>
                    )}
                  </>
                ) : null}
              </div>
            </motion.div>
          )}

          {demoProgress === 5 && activeRes && (
            <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} className="w-full mt-2 mb-3">
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

      {/* Quick Suggestion Chips */}
      <div className="px-3 py-2 bg-white border-t border-slate-200 flex gap-2 overflow-x-auto no-scrollbar">
        {currentChips.map((chip, idx) => (
          <button
            key={idx}
            onClick={() => handleSendCustomText(chip.text)}
            className={`text-xs px-3 py-1.5 rounded-lg border flex-shrink-0 flex items-center gap-1.5 font-semibold transition-all shadow-sm ${
              chip.score === 1
                ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border-emerald-200'
                : chip.score === 2
                ? 'bg-amber-50 hover:bg-amber-100 text-amber-800 border-amber-200'
                : 'bg-rose-50 hover:bg-rose-100 text-rose-800 border-rose-200'
            }`}
          >
            <Sparkles className="w-3 h-3" /> {chip.label}
          </button>
        ))}
      </div>

      {/* Input Bottom Bar */}
      <div className="bg-white p-3 flex items-center gap-2 z-10 border-t border-slate-200">
        <div className="flex-1 bg-slate-50 border border-slate-200 rounded-xl h-10 px-3 flex items-center shadow-inner">
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
            className="w-full bg-transparent text-slate-900 placeholder:text-slate-400 text-xs md:text-sm focus:outline-none"
          />
        </div>

        {inputText.trim() ? (
          <button
            onClick={() => handleSendCustomText()}
            className="w-10 h-10 bg-[#0f4c42] hover:bg-[#0d3f37] rounded-xl flex items-center text-white justify-center shadow-sm transition-all"
          >
            <Send className="w-4 h-4 ml-0.5" />
          </button>
        ) : (
          <button
            onClick={handleMicClick}
            title="Click to simulate voice note input"
            className="w-10 h-10 bg-[#0f4c42] hover:bg-[#0d3f37] rounded-xl flex items-center text-white justify-center shadow-sm transition-all"
          >
            <Mic className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
