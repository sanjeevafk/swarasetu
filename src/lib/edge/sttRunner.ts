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

/** Multilingual keyword lexicon mirrored from ml/edge_runner.py LEXICON. */
const LEXICON: Record<string, Record<LanguageCode, string[]>> = {
  has_fever: {
    en: ['fever', 'temperature'],
    hi: ['बुखार', 'तापमान'],
    ta: ['காய்ச்சல்'],
    bn: ['জ্বর'],
  },
  cough_days_marker: {
    en: ['cough'],
    hi: ['खांसी', 'खाँसी'],
    ta: ['இருமல்'],
    bn: ['কাশি'],
  },
  difficulty_breathing: {
    en: ['breathing difficulty', 'shortness of breath'],
    hi: ['सांस लेने में दिक्कत', 'सांस की तकलीफ'],
    ta: ['மூச்சு வாங்க', 'மூச்சுத் திணறல்'],
    bn: ['শ্বাসকষ্ট', 'শ্বাস কষ্ট'],
  },
  chest_pain_severe: {
    en: ['chest pain'],
    hi: ['सीने में दर्द'],
    ta: ['நெஞ்சு வலி'],
    bn: ['বুকে ব্যথা'],
  },
  vomiting_blood: {
    en: ['vomiting blood'],
    hi: ['खून की उल्टी'],
    ta: ['ரத்த வாந்தி'],
    bn: ['রক্তবমি'],
  },
};

function decodeWavToFloat32(buffer: ArrayBuffer): Float32Array {
  const view = new DataView(buffer);
  // Minimal RIFF parser — field tablets always record 16-bit PCM mono WAV.
  const numChannels = view.getUint16(22, true);
  const dataOffset = 44;
  const samples = new Float32Array((buffer.byteLength - dataOffset) / 2 / numChannels);
  let idx = 0;
  for (let i = dataOffset; i + 1 < buffer.byteLength && idx < samples.length; i += 2 * numChannels) {
    samples[idx++] = view.getInt16(i, true) / 32768;
  }
  return samples;
}

async function loadSession(modelUrl: string): Promise<unknown | null> {
  try {
    // Dynamic runtime import keeps ORT out of the main bundle; resolved lazily
    // only on devices where weights are provisioned. The dependency is added
    // to package.json at provisioning time (`npm i onnxruntime-web`) — until
    // then this resolves to null and the mock path is used.
    const ORT_MODULE = 'onnxruntime-web'; // hidden from static type resolution
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

  const session = options.modelUrl ? await loadSession(options.modelUrl) : null;

  if (session === null) {
    // Documented degradation path: no weights available on-device.
    // Return the fixture transcript for the language so downstream stages
    // remain exercised (identical contract to ml/edge_runner.py mock mode).
    const fixtures: Record<LanguageCode, string> = {
      en: 'my child has a mild fever since yesterday',
      hi: 'बच्चे को खांसी है और सांस लेने में थोड़ी दिक्कत हो रही है दो दिन से',
      ta: 'என் குழந்தைக்கு லேசான காய்ச்சல் இருக்கு நேற்றிலிருந்து',
      bn: 'আমার স্বামীর বুকে খুব ব্যথা হচ্ছে আর রক্তবমি হচ্ছে',
    };
    const transcript = fixtures[options.language];
    const payload = normalizeTranscript(transcript, options.language);
    return {
      transcript,
      engine: 'mock',
      latencyMs: performance.now() - started,
      outcome: evaluateLocal(payload),
    };
  }

  // --- Real inference path (activated once weights are provisioned) ---
  // 1. Compute log-mel features from `samples` (see ml/edge_runner.py::_log_mel).
  // 2. Run encoder session -> cross-attention cache.
  // 3. Greedy-decode with the decoder session until <|endoftranscript|.
  // 4. Normalize + evaluate exactly like the mock branch below.
  void samples; // consumed by the feature extractor above once wired
  throw new Error('ONNX decoding loop not yet wired: provision model weights first.');
}

/** Deterministic transcript -> canonical payload normalization (edge mirror). */
export function normalizeTranscript(text: string, language: LanguageCode): SymptomPayload {
  const lowered = text.toLowerCase();
  const payload: SymptomPayload = {
    ...emptyPayloadFor(language),
  };

  const matches = (group: string): boolean => {
    const terms = LEXICON[group]?.[language] ?? LEXICON[group]?.en ?? [];
    return terms.some((t) =>
      t.includes(' ')
        ? t.split(' ').every((w) => lowered.includes(w))
        : lowered.includes(t),
    );
  };

  if (matches('has_fever')) {
    payload.has_fever = true;
    payload.fever_days = extractDays(lowered) ?? 1;
  }
  if (matches('cough_days_marker')) {
    payload.cough_days = extractDays(lowered) ?? 2;
  }
  if (matches('difficulty_breathing')) payload.difficulty_breathing = true;
  if (matches('chest_pain_severe')) payload.chest_pain_severe = true;
  if (matches('vomiting_blood')) payload.vomiting_blood = true;

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
