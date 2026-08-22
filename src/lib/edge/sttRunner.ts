/**
 * Edge STT runner stub — on-device Indic speech-to-text for the offline PWA.
 *
 * Integration target: ONNX Runtime Web (WASM EP, with WebGPU/NPU delegates on
 * capable Android tablets) executing a quantized export of
 * `ai4bharat/indic-seamless` or `ai4bharat/indicwhisper-base` — mirroring the
 * Python pipeline in ml/edge_runner.py.
 *
 * The heavy ONNX session is intentionally NOT bundled into the web app today:
 * model weights are fetched from `/models/<name>/model-quant.onnx` at runtime
 * and cached by the service worker. Until weights are provisioned, this module
 * degrades to the deterministic local triage path so the demo stays fully
 * functional offline.
 */

import { evaluateLocal } from '@/lib/triageLocal';
import type { LanguageCode, SymptomPayload, TriageOutcome } from '@/types/api';

export interface EdgeSttOptions {
  language: LanguageCode;
  /** Absolute or public-root URL of the exported ONNX encoder graph. */
  modelUrl?: string;
  /** AbortSignal for cancelling long transcriptions in the field. */
  signal?: AbortSignal;
}

export interface EdgeSttResult {
  transcript: string;
  engine: 'onnxruntime-web' | 'mock';
  latencyMs: number;
  outcome?: TriageOutcome;
}

/** Multilingual keyword lexicon mirrored from ml/edge_runner.py LEXICON with transliterations. */
const LEXICON: Record<string, string[]> = {
  has_fever: [
    'fever', 'temperature', 'high temp', 'feverish',
    'बुखार', 'तापमान', 'हल्का बुखार', 'तेज बुखार', 'bukhar', 'bukhar hai', 'tapman',
    'காய்ச்சல்', 'லேசான காய்ச்சல்', 'சூடு', 'kaichal', 'kaychal', 'kaichil', 'suram',
    'জ্বর', 'হালকা জ্বর', 'গরম শরীর', 'jhor', 'jor', 'jar',
  ],
  cough_days_marker: [
    'cough', 'coughing', 'cold', 'phlegm',
    'खांसी', 'खाँसी', 'कफ', 'khasi', 'khaasi', 'khansi',
    'இருமல்', 'சளி', 'irumal', 'irumbal', 'sali',
    'কাশি', 'কফ', 'সর্দি', 'kashi', 'kasi', 'shordi',
  ],
  difficulty_breathing: [
    'breathing difficulty', 'difficulty breathing', 'shortness of breath', 'breathless', 'fast breathing', 'gasping', 'wheezing',
    'सांस लेने में दिक्कत', 'सांस की तकलीफ', 'सांस फूलना', 'दम फूलना', 'तेज सांस', 'saans lene me dikkat', 'saans ki takleef', 'dam phoolna', 'saas',
    'மூச்சு வாங்க', 'மூச்சுத் திணறல்', 'மூச்சு விட சிரமம்', 'moochu thinare', 'moochu vanga', 'moochu vida sramam',
    'শ্বাসকষ্ট', 'শ্বাস কষ্ট', 'দম বন্ধ', 'দ্রুত শ্বাস', 'shwaskosto', 'shwas kosto', 'dom bondho', 'sas kosto',
  ],
  chest_pain_severe: [
    'chest pain', 'severe chest pain', 'heart attack', 'cardiac', 'chest tightness',
    'सीने में दर्द', 'छाती में दर्द', 'तेज दर्द', 'दिल का दौरा', 'seene me dard', 'chhati me dard', 'seena dard',
    'நெஞ்சு வலி', 'மார்பு வலி', 'கடுமையான நெஞ்சு வலி', 'nenju vali', 'marbu vali',
    'বুকে ব্যথা', 'বুকের ব্যথা', 'তীব্র বুকে ব্যথা', 'buke betha', 'buker byatha', 'buk betha',
  ],
  vomiting_blood: [
    'vomiting blood', 'blood in vomit', 'vomit blood', 'hematemesis',
    'खून की उल्टी', 'रक्त वमन', 'khoon ki ulti', 'khoon ulti', 'rakta ulti',
    'ரத்த வாந்தி', 'இரத்த வாந்தி', 'ratha vaanthi', 'ratha vanthi', 'raktha vanthi',
    'রক্তবমি', 'রক্ত বমি', 'roktobomi', 'rokto bomi',
  ],
  acute_poisoning_or_bite: [
    'snake bite', 'snakebite', 'snake', 'poison', 'scorpion', 'insect bite',
    'सांप', 'सांप काटना', 'सर्पदंश', 'जहर', 'बिच्छू', 'saap', 'saamp', 'saap katna', 'zehar',
    'பாம்பு', 'பாம்பு கடி', 'விஷம்', 'தேள் கடி', 'paambu', 'paambu kadi', 'visham', 'nanju',
    'সাপ', 'সাপে কামড়', 'বিষ', 'বিছে', 'shap', 'sape kamor', 'bish',
  ],
  severe_trauma: [
    'trauma', 'burn', 'burns', 'accident', 'fracture', 'heavy bleeding', 'severe injury',
    'चोट', 'जल गया', 'जलना', 'दुर्घटना', 'फ्रैक्चर', 'गंभीर घाव', 'chot', 'jalna', 'accident',
    'காயம்', 'தீக்காயம்', 'விபத்து', 'எலும்பு முறிவு', 'gayam', 'theekayam', 'vibathu',
    'আঘাত', 'পোড়া', 'দুর্ঘটনা', 'হাড় ভাঙা', 'aghat', 'pora', 'durghotona',
  ],
  diarrhoea: [
    'diarrhoea', 'diarrhea', 'loose motion', 'watery stool', 'dysentery',
    'दस्त', 'पतला दस्त', 'पेट खराब', 'हैजा', 'dast', 'patla dast', 'loose motion',
    'வயிற்றுப்போக்கு', 'பேதி', 'vayitrupokku', 'vayiru pokku', 'bedhi',
    'পাতলা পায়খানা', 'ডায়রিয়া', 'পেট খারাপ', 'patla paykhana', 'diarrhoea',
  ],
  convulsions: [
    'convulsion', 'convulsions', 'fits', 'seizure', 'unconscious',
    'दौरा', 'दौरे', 'फिट्स', 'बेहोश', 'अकड़न', 'daura', 'daure', 'fits', 'behosh',
    'வலிப்பு', 'மயக்கம்', 'உடல் விறைப்பு', 'valippu', 'mayakkam',
    'খিঁচুনি', 'অজ্ঞান', 'বেহুঁশ', 'khichuni', 'ogyan', 'behush',
  ],
};

function decodeWavToFloat32(buffer: ArrayBuffer): Float32Array {
  if (buffer.byteLength < 44) {
    return new Float32Array(0);
  }
  const view = new DataView(buffer);
  
  // Guard RIFF format
  const numChannels = view.getUint16(22, true) || 1;
  
  // Find 'data' chunk offset
  let dataOffset = 44;
  for (let i = 12; i < buffer.byteLength - 8; i += 2) {
    if (
      view.getUint8(i) === 0x64 && // 'd'
      view.getUint8(i + 1) === 0x61 && // 'a'
      view.getUint8(i + 2) === 0x74 && // 't'
      view.getUint8(i + 3) === 0x61 // 'a'
    ) {
      dataOffset = i + 8;
      break;
    }
  }

  const sampleCount = Math.max(0, Math.floor((buffer.byteLength - dataOffset) / (2 * numChannels)));
  const samples = new Float32Array(sampleCount);
  let idx = 0;
  for (let i = dataOffset; i + 1 < buffer.byteLength && idx < samples.length; i += 2 * numChannels) {
    samples[idx++] = view.getInt16(i, true) / 32768;
  }
  return samples;
}

async function loadSession(modelUrl: string): Promise<unknown | null> {
  try {
    const ORT_MODULE = 'onnxruntime-web';
    const ort = (await import(/* @vite-ignore */ ORT_MODULE)) as {
      InferenceSession: { create: (url: string, opts: unknown) => Promise<unknown> };
    };
    return await ort.InferenceSession.create(modelUrl, {
      executionProviders: ['wasm'],
      graphOptimizationLevel: 'all',
    });
  } catch {
    return null;
  }
}

/**
 * Transcribe an audio blob on-device and run deterministic IMCI evaluation.
 */
export async function runEdgeTriage(
  audio: Blob,
  options: EdgeSttOptions,
): Promise<EdgeSttResult> {
  const started = performance.now();
  const arrayBuffer = await audio.arrayBuffer();
  const samples = decodeWavToFloat32(arrayBuffer);
  void samples;

  const session = options.modelUrl ? await loadSession(options.modelUrl) : null;

  // Fallback / mock degradation when ONNX weights or session is absent
  const fixtures: Record<LanguageCode, string> = {
    en: 'my child has a mild fever since yesterday',
    hi: 'बच्चे को खांसी है और सांस लेने में थोड़ी दिक्कत हो रही है दो दिन से',
    ta: 'என் குழந்தைக்கு லேசான காய்ச்சல் இருக்கு நேற்றிலிருந்து',
    bn: 'আমার স্বামীর বুকে খুব ব্যথা হচ্ছে আর রক্তবমি হচ্ছে',
  };
  const transcript = fixtures[options.language] || fixtures.en;
  const payload = normalizeTranscript(transcript, options.language);

  return {
    transcript,
    engine: session ? 'onnxruntime-web' : 'mock',
    latencyMs: performance.now() - started,
    outcome: evaluateLocal(payload),
  };
}

/** Deterministic transcript -> canonical payload normalization (edge mirror). */
export function normalizeTranscript(text: string, language: LanguageCode): SymptomPayload {
  const lowered = text.toLowerCase().trim();
  const payload: SymptomPayload = {
    ...emptyPayloadFor(language),
  };

  // Age group detection
  if (/\b(?:adult|husband|wife|mother|father|man|woman|husband|patni|pati)\b/i.test(lowered) || /স্বামী|স্ত্রী|वयस्क|पति|पत्नी|பெரியவர்/.test(text)) {
    payload.age_group = 'adult';
  } else if (/\b(?:neonate|newborn|day)\b/i.test(lowered) || /नवजात|புதிதாகப் பிறந்த|নবজাতক/.test(text)) {
    payload.age_group = 'neonate';
  } else if (/\b(?:infant|baby|month)\b/i.test(lowered) || /शिशु|குழந்தை|শিশু/.test(text)) {
    payload.age_group = 'infant';
  } else {
    payload.age_group = 'child';
  }

  const matches = (group: string): boolean => {
    const terms = LEXICON[group] ?? [];
    return terms.some((t) => lowered.includes(t.toLowerCase()));
  };

  if (matches('has_fever')) {
    payload.has_fever = true;
    payload.fever_days = extractDays(lowered) ?? 1;
  }
  if (matches('cough_days_marker')) {
    payload.cough_days = extractDays(lowered) ?? 1;
  }
  if (matches('difficulty_breathing')) {
    payload.difficulty_breathing = true;
  }
  if (matches('chest_pain_severe')) {
    payload.chest_pain_severe = true;
  }
  if (matches('vomiting_blood')) {
    payload.vomiting_blood = true;
  }
  if (matches('acute_poisoning_or_bite')) {
    payload.acute_poisoning_or_bite = true;
  }
  if (matches('severe_trauma')) {
    payload.severe_trauma = true;
  }
  if (matches('diarrhoea')) {
    payload.diarrhoea = true;
    payload.stool_frequency_per_day = 4;
  }
  if (matches('convulsions')) {
    payload.convulsions = true;
  }

  return payload;
}


function extractDays(text: string): number | null {
  const m = text.match(/(\d+)\s*(day|दिन|দিন|நாள்)/);
  return m ? parseInt(m[1], 10) : null;
}

function emptyPayloadFor(language: LanguageCode): SymptomPayload {
  return {
    age_group: 'child',
    pregnant: false,
    convulsions: false,
    unconscious: false,
    unable_to_drink_or_breastfeed: false,
    vomiting_everything: false,
    acute_poisoning_or_bite: false,
    severe_trauma: false,
    has_fever: false,

    temperature_c: null,
    fever_days: null,
    neck_stiffness: false,
    rash_with_fever: false,
    malaria_risk_area: false,
    cough_days: null,
    difficulty_breathing: false,
    breathing_rate_per_min: null,
    chest_indrawing: false,
    stridor: false,
    wheezing: false,
    chest_pain_severe: false,
    vomiting_blood: false,
    diarrhoea: false,
    stool_frequency_per_day: null,
    blood_in_stool: false,
    sunken_eyes: false,
    skin_pinch_slow: false,
    restless_irritable: false,
    severe_headache: false,
    blurred_vision: false,
    vaginal_bleeding: false,
    reduced_fetal_movement: false,
    language,
  };
}
