/**
 * TouchToHearPanel — Zero-Literacy Visual Symptom Input for ASHA Tablet
 *
 * Replicates the clean clinical ASHA tablet interface:
 * Large illustrated symptom tiles with Hindi/regional text,
 * Web Speech Synthesis audio instructions, structured Yes/No inputs,
 * and instant on-device IMCI triage evaluation.
 */

import { useState, useCallback } from 'react';
import {
  Volume2,
  Check,
  X,
  RotateCcw,
  AlertTriangle,
  Wind,
  Droplets,
  Zap,
  Ban,
  ChevronRight,
  SunMedium,
} from 'lucide-react';
import { emptyPayload } from '@/types/api';
import { TriageResultCard } from './TriageResultCard';
import { useAppStore, type AppLanguage } from '@/store/useAppStore';
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
  | 'vomitingEverything'
  | 'unableToDrink'
  | 'snakeBite';

const AUDIO_PROMPTS: Record<AppLanguage, Record<TileId, string>> = {
  Hindi: {
    ageGroup: 'मरीज की आयु वर्ग चुनें — नवजात, शिशु, 1 से 5 वर्ष, 6 से 18 वर्ष, या वयस्क।',
    fever: 'क्या बच्चे को बुखार है? माथे या कांख को छूकर देखें।',
    feverDays: 'बुखार कितने दिनों से है? एक या दो दिन, या तीन से अधिक दिन।',
    chestIndrawing: 'क्या बच्चे की छाती सांस लेते समय अंदर धंस रही है? यह गंभीर संकेत है।',
    fastBreathing: 'क्या बच्चे की सांस तेज चल रही है? एक मिनट में चालीस से ज्यादा सांसें गिनें।',
    diarrhoea: 'क्या बच्चे को दस्त हो रहे हैं? दिन में तीन या उससे अधिक बार पानी जैसा मल।',
    convulsions: 'क्या बच्चे को दौरे पड़े हैं या शरीर में अकड़न आई है?',
    vomitingEverything: 'क्या बच्चा बार-बार उल्टी कर रहा है और कुछ भी रोक नहीं पा रहा?',
    unableToDrink: 'क्या बच्चा कुछ भी पी या स्तनपान नहीं कर पा रहा है?',
    snakeBite: 'क्या सांप ने काटा है, जहर का शक है, या कोई विषैला कीड़ा लगा है?',
  },
  Tamil: {
    ageGroup: 'நோயாளியின் வயதை தேர்வு செய்யுங்கள் — பிறந்த குழந்தை, 1-12 மாதம், 1-5 வருடம், 6-18 வருடம், அல்லது பெரியவர்.',
    fever: 'குழந்தைக்கு காய்ச்சல் உள்ளதா? நெற்றியை தொட்டு பாருங்கள்.',
    feverDays: 'காய்ச்சல் எத்தனை நாட்களாக இருக்கிறது? ஒன்று அல்லது இரண்டு நாட்கள், அல்லது மூன்றுக்கும் மேல்.',
    chestIndrawing: 'சுவாசிக்கும்போது குழந்தையின் மார்பு உள்ளே இழுக்கப்படுகிறதா? இது ஆபத்தான அறிகுறி.',
    fastBreathing: 'குழந்தை மிக வேகமாக மூச்சு விடுகிறதா? ஒரு நிமிடத்தில் நாற்பதுக்கும் அதிகமான மூச்சுகள்.',
    diarrhoea: 'குழந்தைக்கு வயிற்றுப்போக்கு உள்ளதா? நாளொன்றுக்கு மூன்று அல்லது அதிக முறை.',
    convulsions: 'குழந்தைக்கு வலிப்பு வந்ததா அல்லது உடல் விறைத்ததா?',
    vomitingEverything: 'குழந்தை சாப்பிடும் அனைத்தையும் தொடர்ந்து வாந்தி எடுக்கிறதா?',
    unableToDrink: 'குழந்தையால் தண்ணீர் அல்லது தாய்ப்பால் குடிக்கவே முடியவில்லையா?',
    snakeBite: 'பாம்பு கடித்ததா அல்லது விஷம் ஏறியதாக சந்தேகம் உள்ளதா?',
  },
  Bengali: {
    ageGroup: 'রোগীর বয়স বেছে নিন — নবজাতক, ১-১২ মাস, ১-৫ বছর, ৬-১৮ বছর, বা প্রাপ্তবয়স্ক।',
    fever: 'বাচ্চার কি জ্বর আছে? কপাল বা বগল ছুঁয়ে দেখুন।',
    feverDays: 'জ্বর কতদিন ধরে আছে? ১-২ দিন নাকি ৩ দিনের বেশি?',
    chestIndrawing: 'শ্বাস নেওয়ার সময় বাচ্চার বুক কি ভেতরে ঢুকে যাচ্ছে? এটি বিপদের লক্ষণ।',
    fastBreathing: 'বাচ্চা কি খুব দ্রুত শ্বাস নিচ্ছে? এক মিনিটে ৪০ বারের বেশি?',
    diarrhoea: 'বাচ্চার কি পাতলা পায়খানা হচ্ছে? দিনে তিনবার বা তার বেশি।',
    convulsions: 'বাচ্চার কি খিঁচুনি হয়েছে বা শরীর শক্ত হয়ে গেছে?',
    vomitingEverything: 'বাচ্চা কি বারবার বমি করছে এবং কিছুই পেটে রাখতে পারছে না?',
    unableToDrink: 'বাচ্চা কি জল বা দুধ একটুও পান করতে পারছে না?',
    snakeBite: 'সাপে কামড় দিয়েছে বা বিষের সন্দেহ আছে কি?',
  },
};

// -----------------------------------------------------------------
// Symptom Tile Config matching the exact screenshot layout
// -----------------------------------------------------------------
interface TileConfig {
  id: Exclude<TileId, 'ageGroup' | 'feverDays'>;
  iconType: 'thermometer' | 'lungs' | 'wind' | 'droplet' | 'lightning' | 'nausea' | 'prohibited' | 'snake';
  title: Record<AppLanguage, string>;
  subtitle: Record<AppLanguage, string>;
  payloadKey: keyof SymptomPayload;
  severity: 'yellow' | 'red';
}

const TILES: TileConfig[] = [
  {
    id: 'fever',
    iconType: 'thermometer',
    title: { Hindi: 'बुखार', Tamil: 'காய்ச்சல்', Bengali: 'জ্বর' },
    subtitle: { Hindi: 'क्या बच्चे को बुखार है?', Tamil: 'குழந்தைக்கு காய்ச்சல் உள்ளதா?', Bengali: 'বাচ্চার কি জ্বর আছে?' },
    payloadKey: 'has_fever',
    severity: 'yellow',
  },
  {
    id: 'chestIndrawing',
    iconType: 'lungs',
    title: { Hindi: 'छाती धंसना', Tamil: 'மார்பு உள்வாங்குதல்', Bengali: 'বুক ভেতরে ঢোকা' },
    subtitle: { Hindi: 'क्या बच्चे की छाती धंस रही है?', Tamil: 'மார்பு உள்வாங்குகிறதா?', Bengali: 'বুক কি ভেতরে ঢুকে যাচ্ছে?' },
    payloadKey: 'chest_indrawing',
    severity: 'red',
  },
  {
    id: 'fastBreathing',
    iconType: 'wind',
    title: { Hindi: 'तेज़ साँस चलना', Tamil: 'வேகமான மூச்சு', Bengali: 'দ্রুত শ্বাস চলা' },
    subtitle: { Hindi: 'क्या सांस तेज चल रही है?', Tamil: 'மூச்சு வேகமாக உள்ளதா?', Bengali: 'শ্বাস কি খুব দ্রুত চলছে?' },
    payloadKey: 'difficulty_breathing',
    severity: 'red',
  },
  {
    id: 'diarrhoea',
    iconType: 'droplet',
    title: { Hindi: 'दस्त', Tamil: 'வயிற்றுப்போக்கு', Bengali: 'পাতলা পায়খানা' },
    subtitle: { Hindi: 'क्या दस्त हो रहे हैं?', Tamil: 'வயிற்றுப்போக்கு உள்ளதா?', Bengali: 'পাতলা পায়খানা হচ্ছে কি?' },
    payloadKey: 'diarrhoea',
    severity: 'yellow',
  },
  {
    id: 'convulsions',
    iconType: 'lightning',
    title: { Hindi: 'दौरे (फिट आना)', Tamil: 'வலிப்பு (ஃபிட்ஸ்)', Bengali: 'খিঁচুনি (ফিট)' },
    subtitle: { Hindi: 'क्या दौरे पड़े हैं?', Tamil: 'வலிப்பு ஏற்பட்டதா?', Bengali: 'খিঁচুনি হয়েছে কি?' },
    payloadKey: 'convulsions',
    severity: 'red',
  },
  {
    id: 'vomitingEverything',
    iconType: 'nausea',
    title: { Hindi: 'लगातार उल्टी', Tamil: 'தொடர் வாந்தி', Bengali: 'বারবার বমি' },
    subtitle: { Hindi: 'क्या बार-बार उल्टी हो रही है?', Tamil: 'தொடர்ந்து வாந்தி வருகிறதா?', Bengali: 'বারবার বমি হচ্ছে কি?' },
    payloadKey: 'vomiting_everything',
    severity: 'red',
  },
  {
    id: 'unableToDrink',
    iconType: 'prohibited',
    title: { Hindi: 'कुछ नहीं पी पा रहा/रही', Tamil: 'குடிக்க முடியவில்லை', Bengali: 'কিছু পান করতে পারছে না' },
    subtitle: { Hindi: 'क्या बच्चा कुछ भी पी नहीं पा रहा/रही है?', Tamil: 'எதுவும் குடிக்க இயலவில்லையா?', Bengali: 'বাচ্চা কিছু পান করতে পারছে না?' },
    payloadKey: 'unable_to_drink_or_breastfeed',
    severity: 'red',
  },
  {
    id: 'snakeBite',
    iconType: 'snake',
    title: { Hindi: 'साँप काटा / जहर का शक', Tamil: 'பாம்பு கடி / விஷம்', Bengali: 'সাপের কামড় / বিষ' },
    subtitle: { Hindi: 'क्या साँप ने काटा या जहर का शक है?', Tamil: 'பாம்பு கடித்ததாக சந்தேகம் உள்ளதா?', Bengali: 'সাপে কামড় বা বিষের সন্দেহ?' },
    payloadKey: 'acute_poisoning_or_bite',
    severity: 'red',
  },
];

const AGE_OPTIONS: { value: AgeGroup; labelHindi: string; labelTamil: string; labelBengali: string }[] = [
  { value: 'neonate', labelHindi: '0–28 दिन', labelTamil: '0–28 நாள்', labelBengali: '০–২৮ দিন' },
  { value: 'infant', labelHindi: '1–12 माह', labelTamil: '1–12 மாதம்', labelBengali: '১–১২ মাস' },
  { value: 'child', labelHindi: '1–5 वर्ष', labelTamil: '1–5 வருடம்', labelBengali: '১–৫ বছর' },
  { value: 'adolescent', labelHindi: '6–18 वर्ष', labelTamil: '6–18 வருடம்', labelBengali: '৬–১৮ বছর' },
  { value: 'adult', labelHindi: '18+ वर्ष', labelTamil: '18+ வருடம்', labelBengali: '১৮+ বছর' },
];

function speak(text: string, lang: AppLanguage) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = lang === 'Hindi' ? 'hi-IN' : lang === 'Tamil' ? 'ta-IN' : 'bn-IN';
  utter.rate = 0.9;
  utter.pitch = 1.0;
  window.speechSynthesis.speak(utter);
}

// Custom rendered icons matching screenshot visual cues
function SymptomIcon({ type }: { type: TileConfig['iconType'] }) {
  switch (type) {
    case 'thermometer':
      return (
        <div className="w-9 h-9 rounded-full bg-rose-50 flex items-center justify-center text-rose-500 shrink-0">
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" fill="#fecdd3" />
            <circle cx="11.5" cy="17.5" r="2.5" fill="#e11d48" />
          </svg>
        </div>
      );
    case 'lungs':
      return (
        <div className="w-9 h-9 rounded-full bg-rose-50 flex items-center justify-center text-rose-500 shrink-0">
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M7.5 4C5.5 4 4 6 4 9c0 4.5 3 8 7 11v-9c0-1.5-1.5-2.5-3.5-2.5V4zm9 0c2 0 3.5 2 3.5 5 0 4.5-3 8-7 11v-9c0-1.5 1.5-2.5 3.5-2.5V4z" fill="#f43f5e" opacity="0.85" />
            <path d="M11 2h2v10h-2z" fill="#94a3b8" />
          </svg>
        </div>
      );
    case 'wind':
      return (
        <div className="w-9 h-9 rounded-full bg-cyan-50 flex items-center justify-center text-cyan-600 shrink-0">
          <Wind className="w-5 h-5 stroke-[2.2]" />
        </div>
      );
    case 'droplet':
      return (
        <div className="w-9 h-9 rounded-full bg-sky-50 flex items-center justify-center text-sky-500 shrink-0">
          <Droplets className="w-5 h-5 fill-sky-400 stroke-sky-600" />
        </div>
      );
    case 'lightning':
      return (
        <div className="w-9 h-9 rounded-full bg-purple-50 flex items-center justify-center text-purple-600 shrink-0">
          <Zap className="w-5 h-5 fill-purple-400 stroke-purple-600" />
        </div>
      );
    case 'nausea':
      return (
        <div className="w-9 h-9 rounded-full bg-amber-50 flex items-center justify-center text-amber-500 shrink-0">
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="#fef3c7" stroke="#f59e0b" strokeWidth="2" />
            <circle cx="9" cy="9" r="1.5" fill="#b45309" />
            <circle cx="15" cy="9" r="1.5" fill="#b45309" />
            <path d="M8 15h8" stroke="#b45309" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>
      );
    case 'prohibited':
      return (
        <div className="w-9 h-9 rounded-full bg-rose-50 flex items-center justify-center text-rose-600 shrink-0">
          <Ban className="w-5 h-5 stroke-[2.4]" />
        </div>
      );
    case 'snake':
      return (
        <div className="w-9 h-9 rounded-full bg-emerald-50 flex items-center justify-center text-emerald-600 shrink-0">
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3a3 3 0 0 0-3 3v2a3 3 0 0 1-3 3v1a4 4 0 0 0 8 0v-4a1 1 0 0 1 2 0v5a5 5 0 0 1-10 0" />
            <circle cx="17" cy="6" r="1" fill="#059669" />
          </svg>
        </div>
      );
  }
}

interface TouchToHearPanelProps {
  language: AppLanguage;
  onShowMap?: () => void;
}

type TileAnswer = boolean | null;

export function TouchToHearPanel({ language, onShowMap }: TouchToHearPanelProps) {
  const [answers, setAnswers] = useState<Record<string, TileAnswer>>(
    () => Object.fromEntries(TILES.map((t) => [t.id, null]))
  );
  const [feverDays, setFeverDays] = useState<'short' | 'long' | null>(null);
  const [ageGroup, setAgeGroup] = useState<AgeGroup>('child');
  const [speakingId, setSpeakingId] = useState<TileId | null>(null);
  const [result, setResult] = useState<TriageOutcome | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const evaluateCustomPayload = useAppStore((s) => s.evaluateCustomPayload);
  const addMessage = useAppStore((s) => s.addMessage);

  const handleSpeak = useCallback(
    (tileId: TileId) => {
      setSpeakingId(tileId);
      const text = AUDIO_PROMPTS[language]?.[tileId] || AUDIO_PROMPTS.Hindi[tileId];
      speak(text, language);
      setTimeout(() => setSpeakingId((prev) => (prev === tileId ? null : prev)), 3200);
    },
    [language]
  );

  const handleAnswer = (tileId: string, answer: boolean) => {
    setAnswers((prev) => ({ ...prev, [tileId]: answer }));
    setResult(null);
    setSubmitted(false);
  };

  const handleEvaluate = async () => {
    const langCode = language === 'Hindi' ? 'hi' : language === 'Tamil' ? 'ta' : 'bn';
    const payload: SymptomPayload = {
      ...emptyPayload(langCode),
      age_group: ageGroup,
    };
    const activeTiles: string[] = [];
    for (const tile of TILES) {
      if (answers[tile.id] === true) {
        (payload as unknown as Record<string, unknown>)[tile.payloadKey] = true;
        activeTiles.push(tile.title[language]);
      }
    }
    if (answers['fever'] === true) {
      payload.fever_days = feverDays === 'long' ? 4 : 1;
    }

    const summaryText = `Visual Check: ${activeTiles.length ? activeTiles.join(', ') : 'No danger signs'}`;
    addMessage({
      type: 'user_text',
      text: `📱 [Touch-to-Hear Assessment] Age: ${ageGroup}, Findings: ${
        activeTiles.length ? activeTiles.join(', ') : 'None marked'
      }`,
    });

    const activeEval = await evaluateCustomPayload(payload, summaryText);
    setResult(activeEval.outcome);
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
    <div className="flex flex-col h-full bg-white overflow-y-auto p-4 md:p-6 font-sans">
      {/* Top Header matching screenshot */}
      <div className="flex items-start justify-between pb-3 border-b border-slate-100">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-slate-900 tracking-tight">
            Touch-to-Hear Symptom Check
          </h2>
          <p className="text-slate-500 text-xs md:text-sm mt-0.5 font-normal">
            {language === 'Hindi'
              ? 'कार्ड को छुएं या हाँ/ना बोलकर उत्तर दें'
              : language === 'Tamil'
              ? 'கார்டைத் தொட்டு கேளுங்கள் அல்லது ஆம்/இல்லை என்று பதிலளியுங்கள்'
              : 'কার্ড স্পর্শ করে শুনুন অথবা হ্যাঁ/না উত্তর দিন'}
          </p>
        </div>
        <button
          onClick={handleReset}
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-900 transition-colors px-2.5 py-1.5 rounded-lg hover:bg-slate-100 font-medium"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset
        </button>
      </div>

      {/* Age Group Filter Section matching screenshot */}
      <div className="my-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold text-slate-800">
            {language === 'Hindi'
              ? 'आयु वर्ग (Age Group)'
              : language === 'Tamil'
              ? 'வயது பிரிவு (Age Group)'
              : 'বয়স গ্রুপ (Age Group)'}
          </span>
          <button
            onClick={() => handleSpeak('ageGroup')}
            className="flex items-center gap-1 text-xs text-emerald-800 hover:text-emerald-950 font-medium px-2 py-0.5 rounded-md hover:bg-emerald-50 transition-colors"
          >
            <Volume2 className="w-3.5 h-3.5 text-emerald-700" />
            {speakingId === 'ageGroup' ? 'Playing…' : 'Hear Instructions'}
          </button>
        </div>

        <div className="flex gap-2 flex-wrap">
          {AGE_OPTIONS.map((opt) => {
            const isSelected = ageGroup === opt.value;
            const label =
              language === 'Hindi'
                ? opt.labelHindi
                : language === 'Tamil'
                ? opt.labelTamil
                : opt.labelBengali;
            return (
              <button
                key={opt.value}
                onClick={() => setAgeGroup(opt.value)}
                className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all shadow-sm ${
                  isSelected
                    ? 'bg-[#0f4c42] text-white border border-[#0f4c42]'
                    : 'bg-white text-slate-700 border border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 2-Column Grid of 8 Symptom Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 my-2">
        {TILES.map((tile) => {
          const answered = answers[tile.id];
          const isSpeaking = speakingId === (tile.id as TileId);
          const title = tile.title[language] || tile.title.Hindi;
          const subtitle = tile.subtitle[language] || tile.subtitle.Hindi;

          return (
            <div
              key={tile.id}
              className={`rounded-xl p-3.5 border transition-all shadow-[0_1px_3px_rgba(0,0,0,0.03)] flex flex-col justify-between ${
                answered === true
                  ? 'border-emerald-500/60 bg-emerald-50/20'
                  : answered === false
                  ? 'border-slate-200 bg-slate-50/50 opacity-80'
                  : 'border-slate-200/90 bg-white hover:border-slate-300'
              }`}
            >
              {/* Top Row: Icon + Hindi Title & Question */}
              <div className="flex items-start gap-3 mb-2.5">
                <SymptomIcon type={tile.iconType} />
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-bold text-slate-900 leading-tight">
                    {title}
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5 leading-snug">
                    {subtitle}
                  </p>
                </div>
              </div>

              {/* Middle Row: Touch-to-Hear Audio Button */}
              <button
                onClick={() => handleSpeak(tile.id as TileId)}
                className={`w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-semibold mb-2.5 border transition-all ${
                  isSpeaking
                    ? 'bg-teal-100 text-teal-900 border-teal-300 shadow-inner'
                    : 'border-teal-200 bg-teal-50/40 hover:bg-teal-50 text-teal-800'
                }`}
              >
                <Volume2 className={`w-3.5 h-3.5 ${isSpeaking ? 'animate-pulse text-teal-900' : 'text-teal-700'}`} />
                {isSpeaking ? 'Playing Audio…' : 'Touch-to-Hear'}
              </button>

              {/* Bottom Row: Yes / No Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => handleAnswer(tile.id, true)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-bold border transition-all ${
                    answered === true
                      ? 'bg-emerald-600 border-emerald-600 text-white shadow-sm'
                      : 'bg-white border-slate-200 text-slate-800 hover:bg-emerald-50/60 hover:border-emerald-300'
                  }`}
                >
                  <Check className={`w-3.5 h-3.5 ${answered === true ? 'text-white' : 'text-emerald-600'}`} />
                  {language === 'Hindi' ? 'हाँ' : language === 'Tamil' ? 'ஆம்' : 'হ্যাঁ'}
                </button>
                <button
                  onClick={() => handleAnswer(tile.id, false)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-bold border transition-all ${
                    answered === false
                      ? 'bg-slate-700 border-slate-700 text-white shadow-sm'
                      : 'bg-white border-slate-200 text-slate-800 hover:bg-rose-50/60 hover:border-rose-300'
                  }`}
                >
                  <X className={`w-3.5 h-3.5 ${answered === false ? 'text-white' : 'text-rose-600'}`} />
                  {language === 'Hindi' ? 'नहीं' : language === 'Tamil' ? 'இல்லை' : 'না'}
                </button>
              </div>

              {/* Sub-selection for fever duration */}
              {tile.id === 'fever' && answered === true && (
                <div className="mt-2.5 pt-2 border-t border-amber-200/80 bg-amber-50/40 p-2 rounded-lg">
                  <div className="flex items-center gap-1 text-[11px] text-amber-800 font-semibold mb-1.5">
                    <SunMedium className="w-3 h-3 text-amber-600" /> कितने दिनों से बुखार है? (Duration)
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setFeverDays('short')}
                      className={`flex-1 text-xs py-1 rounded-md border font-semibold transition-all ${
                        feverDays === 'short'
                          ? 'bg-amber-600 text-white border-amber-600 shadow-sm'
                          : 'bg-white text-slate-700 border-slate-200 hover:bg-amber-50'
                      }`}
                    >
                      1–2 दिन
                    </button>
                    <button
                      onClick={() => setFeverDays('long')}
                      className={`flex-1 text-xs py-1 rounded-md border font-semibold transition-all ${
                        feverDays === 'long'
                          ? 'bg-rose-600 text-white border-rose-600 shadow-sm'
                          : 'bg-white text-slate-700 border-slate-200 hover:bg-rose-50'
                      }`}
                    >
                      3+ दिन (गंभीर)
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom Status Bar matching screenshot */}
      <div className="mt-3 pt-3 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-2.5">
        <span className="text-xs font-medium text-slate-600">
          {answeredCount} / {TILES.length}{' '}
          {language === 'Hindi'
            ? 'उत्तर दिए गए'
            : language === 'Tamil'
            ? 'பதில்கள் அளிக்கப்பட்டுள்ளன'
            : 'উত্তর দেওয়া হয়েছে'}
        </span>

        {!canEvaluate ? (
          <div className="text-xs font-semibold text-amber-700 bg-amber-50 px-3 py-1.5 rounded-lg border border-amber-200 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            {language === 'Hindi'
              ? 'कम से कम 3 लक्षणों के उत्तर आवश्यक'
              : language === 'Tamil'
              ? 'குறைந்தது 3 அறிகுறிகளுக்கு பதில் தேவை'
              : 'কমপক্ষে ৩টি লক্ষণের উত্তর প্রয়োজন'}
          </div>
        ) : (
          <button
            onClick={handleEvaluate}
            className="flex items-center gap-2 bg-[#0f4c42] hover:bg-[#0d3f37] text-white text-xs font-bold py-2 px-5 rounded-lg shadow-sm transition-all"
          >
            Run IMCI Triage Engine
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Result Card */}
      {submitted && result && (
        <div className="mt-4 pt-4 border-t border-slate-200">
          <TriageResultCard
            outcome={result}
            message={result.rationale_en}
            evaluatedOffline
            onShowMap={onShowMap || (() => {})}
          />
        </div>
      )}
    </div>
  );
}
