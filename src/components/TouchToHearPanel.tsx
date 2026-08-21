/**
 * TouchToHearPanel — Zero-Literacy Visual Symptom Input for ASHA Tablet
 *
 * Replaces free-form text entry with large, illustrated symptom tiles.
 * Tapping the speaker button on any tile reads aloud a 2-second clinical
 * instruction using the Web Speech Synthesis API (pre-cached, fully offline).
 * Tapping Yes/No fills the structured SymptomPayload directly — no text
 * parsing, no AI extraction needed. The filled payload is then evaluated
 * by the on-device triageLocal engine in < 1 ms.
 */

import { useState, useCallback } from 'react';
import { Volume2, CheckCircle2, XCircle, ChevronRight, RotateCcw, AlertTriangle } from 'lucide-react';
import { evaluateLocal } from '@/lib/triageLocal';
import { emptyPayload } from '@/types/api';
import { TriageResultCard } from './TriageResultCard';
import type { AppLanguage } from '@/store/useAppStore';
import type { SymptomPayload, AgeGroup, TriageOutcome } from '@/types/api';

// -----------------------------------------------------------------
// Audio Tooltip Prompts — Pre-authored per language per symptom tile
// -----------------------------------------------------------------
type TileId =
  | 'ageGroup'
  | 'fever'
  | 'feverDays'
  | 'chestIndrawing'
  | 'fastBreathing'
  | 'diarrhoea'
  | 'convulsions'
  | 'snakeBite'
  | 'vomitingEverything'
  | 'unableToDrink';

const AUDIO_PROMPTS: Record<AppLanguage, Record<TileId, string>> = {
  Hindi: {
    ageGroup: 'मरीज की उम्र चुनें — नवजात, शिशु, बच्चा, किशोर, या वयस्क।',
    fever: 'क्या मरीज को बुखार है? माथे या कांख को छूकर देखें।',
    feverDays: 'बुखार कितने दिनों से है? एक सूरज मतलब एक दिन।',
    chestIndrawing: 'क्या बच्चे की छाती सांस लेते समय अंदर धंसती है? यह खतरे का संकेत है।',
    fastBreathing: 'क्या बच्चा बहुत तेज सांस ले रहा है? एक मिनट में 40 से ज्यादा सांसें गिनें।',
    diarrhoea: 'क्या मरीज को दस्त है? दिन में तीन या उससे ज्यादा बार पानी जैसा मल।',
    convulsions: 'क्या मरीज को दौरा पड़ा है या शरीर अकड़ा है? यह आपातकाल है।',
    snakeBite: 'क्या मरीज को सांप ने काटा है, जहर निगला है, या गंभीर चोट लगी है?',
    vomitingEverything: 'क्या मरीज जो भी खाता-पीता है सब उल्टी कर देता है?',
    unableToDrink: 'क्या मरीज पानी या दूध बिल्कुल नहीं पी पा रहा है?',
  },
  Tamil: {
    ageGroup: 'நோயாளியின் வயதை தேர்வு செய்யுங்கள் — பிறந்த குழந்தை, குழந்தை, அல்லது பெரியவர்.',
    fever: 'நோயாளிக்கு காய்ச்சல் உள்ளதா? நெற்றியை தொட்டு பாருங்கள்.',
    feverDays: 'காய்ச்சல் எத்தனை நாட்களாக இருக்கிறது? ஒரு சூரியன் ஒரு நாள்.',
    chestIndrawing: 'சுவாசிக்கும்போது குழந்தையின் மார்பு உள்ளே இழுக்கப்படுகிறதா? இது ஆபத்தான அறிகுறி.',
    fastBreathing: 'குழந்தை மிக வேகமாக மூச்சு விடுகிறதா? ஒரு நிமிடத்தில் 40 க்கும் அதிகமான மூச்சுகள்.',
    diarrhoea: 'நோயாளிக்கு வயிற்றுப்போக்கு உள்ளதா? நாளொன்றுக்கு மூன்று அல்லது அதிக முறை.',
    convulsions: 'நோயாளிக்கு வலிப்பு வந்ததா? உடல் வலைக்கட்டியதா? இது அவசரநிலை.',
    snakeBite: 'நோயாளியை பாம்பு கடித்ததா, விஷம் விழுங்கியதா, அல்லது கடுமையான காயம் உள்ளதா?',
    vomitingEverything: 'நோயாளி சாப்பிடுவது குடிப்பது அனைத்தையும் வாந்தி எடுக்கிறார்களா?',
    unableToDrink: 'நோயாளியால் தண்ணீரோ பாலோ குடிக்கவே முடியவில்லையா?',
  },
  Bengali: {
    ageGroup: 'রোগীর বয়স বেছে নিন — নবজাতক, শিশু, বাচ্চা, কিশোর, বা প্রাপ্তবয়স্ক।',
    fever: 'রোগীর কি জ্বর আছে? কপাল বা বগল ছুঁয়ে দেখুন।',
    feverDays: 'জ্বর কতদিন ধরে আছে? একটা সূর্য মানে একটা দিন।',
    chestIndrawing: 'শ্বাস নেওয়ার সময় বাচ্চার বুক কি ভেতরে ঢুকে যাচ্ছে? এটি বিপদের লক্ষণ।',
    fastBreathing: 'বাচ্চা কি খুব দ্রুত শ্বাস নিচ্ছে? এক মিনিটে ৪০ বারের বেশি গণনা করুন।',
    diarrhoea: 'রোগীর কি পাতলা পায়খানা হচ্ছে? দিনে তিনবার বা তার বেশি।',
    convulsions: 'রোগীর কি খিঁচুনি হয়েছে বা শরীর শক্ত হয়ে গেছে? এটি জরুরি অবস্থা।',
    snakeBite: 'রোগীকে কি সাপে কামড় দিয়েছে, বিষ গিলেছে, বা গুরুতর আঘাত লেগেছে?',
    vomitingEverything: 'রোগী কি খাওয়া-দাওয়া সব বমি করে দিচ্ছেন?',
    unableToDrink: 'রোগী কি জল বা দুধ একটুও পান করতে পারছেন না?',
  },
};

// -----------------------------------------------------------------
// Symptom Tile Config
// -----------------------------------------------------------------
interface TileConfig {
  id: Exclude<TileId, 'ageGroup' | 'feverDays'>;
  emoji: string;
  label: string;
  description: Record<AppLanguage, string>;
  payloadKey: keyof SymptomPayload;
  severity: 'yellow' | 'red';
}

const TILES: TileConfig[] = [
  {
    id: 'fever',
    emoji: '🌡️',
    label: 'Fever',
    description: { Hindi: 'बुखार — माथे को छूकर देखें', Tamil: 'காய்ச்சல் — நெற்றியை தொட்டு பாருங்கள்', Bengali: 'জ্বর — কপাল ছুঁয়ে দেখুন' },
    payloadKey: 'has_fever',
    severity: 'yellow',
  },
  {
    id: 'chestIndrawing',
    emoji: '🫁',
    label: 'Chest Indrawing',
    description: { Hindi: 'छाती का धंसना (गंभीर)', Tamil: 'மார்பு இழுக்கப்படுதல் (அபாயகரமானது)', Bengali: 'বুক ভেতরে ঢোকা (গুরুতর)' },
    payloadKey: 'chest_indrawing',
    severity: 'red',
  },
  {
    id: 'fastBreathing',
    emoji: '💨',
    label: 'Fast Breathing',
    description: { Hindi: 'तेज सांस — 40+ प्रति मिनट', Tamil: 'வேகமான மூச்சு — நிமிடத்திற்கு 40+', Bengali: 'দ্রুত শ্বাস — মিনিটে ৪০+' },
    payloadKey: 'difficulty_breathing',
    severity: 'red',
  },
  {
    id: 'diarrhoea',
    emoji: '💧',
    label: 'Diarrhoea',
    description: { Hindi: 'दस्त — 3+ बार पानी जैसा मल', Tamil: 'வயிற்றுப்போக்கு — நாளொன்றுக்கு 3+ முறை', Bengali: 'পাতলা পায়খানা — দিনে ৩+ বার' },
    payloadKey: 'diarrhoea',
    severity: 'yellow',
  },
  {
    id: 'convulsions',
    emoji: '⚡',
    label: 'Convulsions',
    description: { Hindi: 'दौरे / अकड़न (आपातकाल)', Tamil: 'வலிப்பு (அவசரநிலை)', Bengali: 'খিঁচুনি (জরুরি অবস্থা)' },
    payloadKey: 'convulsions',
    severity: 'red',
  },
  {
    id: 'vomitingEverything',
    emoji: '🤢',
    label: 'Vomiting Everything',
    description: { Hindi: 'सब कुछ उल्टी', Tamil: 'எல்லாவற்றையும் வாந்தி', Bengali: 'সব বমি হচ্ছে' },
    payloadKey: 'vomiting_everything',
    severity: 'red',
  },
  {
    id: 'unableToDrink',
    emoji: '🚫',
    label: 'Cannot Drink',
    description: { Hindi: 'पानी/दूध नहीं पी पाता', Tamil: 'தண்ணீர்/பால் குடிக்க முடியவில்லை', Bengali: 'পানি/দুধ পান করতে পারছে না' },
    payloadKey: 'unable_to_drink_or_breastfeed',
    severity: 'red',
  },
  {
    id: 'snakeBite',
    emoji: '🐍',
    label: 'Snake Bite / Poisoning',
    description: { Hindi: 'सांप काटना / जहर (आपातकाल)', Tamil: 'பாம்பு கடி / நஞ்சு (அவசரநிலை)', Bengali: 'সাপে কামড় / বিষ (জরুরি অবস্থা)' },
    payloadKey: 'acute_poisoning_or_bite',
    severity: 'red',
  },
];

const AGE_OPTIONS: { value: AgeGroup; label: string }[] = [
  { value: 'neonate', label: '0–28 days' },
  { value: 'infant', label: '1–12 mo' },
  { value: 'child', label: '1–5 yrs' },
  { value: 'adolescent', label: '6–18 yrs' },
  { value: 'adult', label: '18+ yrs' },
];

// -----------------------------------------------------------------
// Web Speech API helper — fully offline, no network needed
// -----------------------------------------------------------------
function speak(text: string, lang: AppLanguage) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = lang === 'Hindi' ? 'hi-IN' : lang === 'Tamil' ? 'ta-IN' : 'bn-IN';
  utter.rate = 0.9;
  utter.pitch = 1.0;
  window.speechSynthesis.speak(utter);
}

// -----------------------------------------------------------------
// Main Component
// -----------------------------------------------------------------
interface TouchToHearPanelProps {
  language: AppLanguage;
}

type TileAnswer = boolean | null;

export function TouchToHearPanel({ language }: TouchToHearPanelProps) {
  const [answers, setAnswers] = useState<Record<string, TileAnswer>>(
    () => Object.fromEntries(TILES.map((t) => [t.id, null]))
  );
  const [feverDays, setFeverDays] = useState<'short' | 'long' | null>(null);
  const [ageGroup, setAgeGroup] = useState<AgeGroup>('child');
  const [speakingId, setSpeakingId] = useState<TileId | null>(null);
  const [result, setResult] = useState<TriageOutcome | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const handleSpeak = useCallback(
    (tileId: TileId) => {
      setSpeakingId(tileId);
      speak(AUDIO_PROMPTS[language][tileId], language);
      setTimeout(() => setSpeakingId((prev) => (prev === tileId ? null : prev)), 3000);
    },
    [language]
  );

  const handleAnswer = (tileId: string, answer: boolean) => {
    setAnswers((prev) => ({ ...prev, [tileId]: answer }));
    setResult(null);
    setSubmitted(false);
  };

  const handleEvaluate = () => {
    const payload: SymptomPayload = {
      ...emptyPayload(language === 'Hindi' ? 'hi' : language === 'Tamil' ? 'ta' : 'bn'),
      age_group: ageGroup,
    };
    for (const tile of TILES) {
      if (answers[tile.id] === true) {
        (payload as unknown as Record<string, unknown>)[tile.payloadKey] = true;
      }
    }
    if (answers['fever'] === true) {
      payload.fever_days = feverDays === 'long' ? 4 : 1;
    }
    const outcome = evaluateLocal(payload);
    setResult(outcome);
    setSubmitted(true);
  };

  const handleReset = () => {
    setAnswers(Object.fromEntries(TILES.map((t) => [t.id, null])));
    setFeverDays(null);
    setAgeGroup('child');
    setResult(null);
    setSubmitted(false);
  };

  const answeredCount = Object.values(answers).filter((v) => v !== null).length;
  const canEvaluate = answeredCount >= 3;

  return (
    <div className="flex flex-col gap-3 p-3 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-bold text-white text-sm leading-tight">Touch-to-Hear Symptom Check</h2>
          <p className="text-slate-400 text-[10px] mt-0.5">
            {language === 'Hindi'
              ? 'टाइल सुनें और Yes/No बताएं'
              : language === 'Tamil'
              ? 'கார்டு கேட்டு Yes/No தேர்வு செய்யுங்கள்'
              : 'কার্ড শুনুন এবং Yes/No বেছে নিন'}
          </p>
        </div>
        <button
          onClick={handleReset}
          className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-white transition-colors px-2 py-1 rounded-lg hover:bg-slate-700/50"
        >
          <RotateCcw className="w-3 h-3" />
          Reset
        </button>
      </div>

      {/* Age Group */}
      <div className="bg-slate-800/50 rounded-xl p-2.5 border border-slate-700/50">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-semibold text-slate-300">
            {language === 'Hindi' ? '👤 मरीज की उम्र' : language === 'Tamil' ? '👤 நோயாளி வயது' : '👤 রোগীর বয়স'}
          </span>
          <button
            onClick={() => handleSpeak('ageGroup')}
            className={`flex items-center gap-1 text-[9px] px-2 py-0.5 rounded-md transition-colors ${
              speakingId === 'ageGroup' ? 'bg-teal-500/40 text-teal-200' : 'bg-teal-500/20 text-teal-300 hover:bg-teal-500/30'
            }`}
          >
            <Volume2 className="w-2.5 h-2.5" />
            {speakingId === 'ageGroup' ? '▶ Playing…' : 'Hear'}
          </button>
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {AGE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setAgeGroup(opt.value)}
              className={`text-[10px] px-2 py-0.5 rounded-lg border transition-all ${
                ageGroup === opt.value
                  ? 'bg-teal-600 border-teal-500 text-white font-bold'
                  : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-white'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tiles */}
      <div className="grid grid-cols-2 gap-2">
        {TILES.map((tile) => {
          const answered = answers[tile.id];
          const isSpeaking = speakingId === tile.id as TileId;
          return (
            <div
              key={tile.id}
              className={`rounded-xl p-2.5 border transition-all ${
                answered === true
                  ? tile.severity === 'red'
                    ? 'border-red-500/50 bg-red-950/25'
                    : 'border-amber-500/40 bg-amber-950/20'
                  : answered === false
                  ? 'border-slate-700/40 bg-slate-800/20 opacity-60'
                  : 'border-slate-700/50 bg-slate-800/50'
              }`}
            >
              {/* Header row */}
              <div className="flex items-center gap-1.5 mb-1.5">
                <span className="text-lg leading-none">{tile.emoji}</span>
                <div className="min-w-0">
                  <div className="text-[11px] font-bold text-white truncate">{tile.label}</div>
                  <div className="text-[9px] text-slate-400 leading-tight">{tile.description[language]}</div>
                </div>
              </div>

              {/* Touch-to-Hear button */}
              <button
                onClick={() => handleSpeak(tile.id as TileId)}
                className={`w-full flex items-center justify-center gap-1 text-[9px] py-1 rounded-lg mb-1.5 transition-all ${
                  isSpeaking ? 'bg-teal-500/40 text-teal-200' : 'bg-teal-500/15 text-teal-300 hover:bg-teal-500/25'
                }`}
              >
                <Volume2 className="w-2.5 h-2.5" />
                {isSpeaking ? '▶ Playing…' : 'Touch-to-Hear'}
              </button>

              {/* Yes / No */}
              <div className="flex gap-1">
                <button
                  onClick={() => handleAnswer(tile.id, true)}
                  className={`flex-1 flex items-center justify-center gap-0.5 py-1 rounded-lg text-[9px] font-bold border transition-all ${
                    answered === true
                      ? 'bg-rose-600 border-rose-500 text-white'
                      : 'bg-slate-900 border-slate-700 text-slate-300 hover:border-rose-500/50 hover:text-rose-300'
                  }`}
                >
                  <CheckCircle2 className="w-2.5 h-2.5" /> Yes
                </button>
                <button
                  onClick={() => handleAnswer(tile.id, false)}
                  className={`flex-1 flex items-center justify-center gap-0.5 py-1 rounded-lg text-[9px] font-bold border transition-all ${
                    answered === false
                      ? 'bg-slate-600 border-slate-500 text-white'
                      : 'bg-slate-900 border-slate-700 text-slate-300 hover:border-slate-500'
                  }`}
                >
                  <XCircle className="w-2.5 h-2.5" /> No
                </button>
              </div>

              {/* Fever days sub-question */}
              {tile.id === 'fever' && answered === true && (
                <div className="mt-1.5 pt-1.5 border-t border-slate-700/50">
                  <p className="text-[9px] text-amber-300 mb-1 font-semibold">☀️ Duration?</p>
                  <div className="flex gap-1">
                    {(['short', 'long'] as const).map((v) => (
                      <button
                        key={v}
                        onClick={() => setFeverDays(v)}
                        className={`flex-1 text-[9px] py-0.5 rounded-lg border transition-all ${
                          feverDays === v
                            ? 'bg-amber-600 border-amber-500 text-white font-bold'
                            : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-amber-300'
                        }`}
                      >
                        {v === 'short' ? '1–2 days' : '3+ days'}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Progress */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 px-1">
        <span>{answeredCount}/{TILES.length} answered</span>
        {!canEvaluate && (
          <span className="text-amber-400 flex items-center gap-1">
            <AlertTriangle className="w-2.5 h-2.5" /> Need 3+ answers
          </span>
        )}
      </div>

      {/* Evaluate */}
      <button
        onClick={handleEvaluate}
        disabled={!canEvaluate}
        className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold text-xs transition-all ${
          canEvaluate
            ? 'bg-teal-600 hover:bg-teal-500 text-white shadow-lg shadow-teal-900/40'
            : 'bg-slate-800 text-slate-600 cursor-not-allowed border border-slate-700'
        }`}
      >
        Run WHO IMCI Triage
        <ChevronRight className="w-3.5 h-3.5" />
      </button>

      {/* Result */}
      {submitted && result && (
        <div className="rounded-xl overflow-hidden border border-slate-700/50">
          <TriageResultCard outcome={result} message={result.rationale_en} evaluatedOffline onShowMap={() => {}} />
        </div>
      )}
    </div>
  );
}
