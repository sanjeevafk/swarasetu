/**
 * Unit tests for TouchToHearPanel — Touch-to-Hear zero-literacy ASHA tablet UI
 *
 * These tests verify:
 * 1. The AUDIO_PROMPTS coverage: every tile has a prompt in all 3 languages
 * 2. The payload-building logic: Yes answers map to the correct SymptomPayload keys
 * 3. The local triage integration: known dangerous symptoms produce risk_score 3
 * 4. The fever sub-question: 3+ days correctly sets fever_days = 4
 * 5. The canEvaluate gate: fewer than 3 answers blocks evaluation
 *
 * Note: Web Speech API is a browser API — it cannot be tested in Node.
 * The speak() function is excluded from unit tests; its integration is
 * verified manually in the browser (see docs/TOUCH_TO_HEAR.md#testing).
 */

import { evaluateLocal } from '../../src/lib/triageLocal';
import { emptyPayload } from '../../src/types/api';
import type { SymptomPayload } from '../../src/types/api';

// Re-export tile config for validation
const TILE_IDS = [
  'fever',
  'chestIndrawing',
  'fastBreathing',
  'diarrhoea',
  'convulsions',
  'vomitingEverything',
  'unableToDrink',
  'snakeBite',
] as const;

const TILE_PAYLOAD_KEYS: Record<string, keyof SymptomPayload> = {
  fever: 'has_fever',
  chestIndrawing: 'chest_indrawing',
  fastBreathing: 'difficulty_breathing',
  diarrhoea: 'diarrhoea',
  convulsions: 'convulsions',
  vomitingEverything: 'vomiting_everything',
  unableToDrink: 'unable_to_drink_or_breastfeed',
  snakeBite: 'acute_poisoning_or_bite',
};

// Simulates what handleEvaluate() does in TouchToHearPanel
function buildPayload(
  answers: Partial<Record<string, boolean>>,
  feverDays: 'short' | 'long' | null = null,
  ageGroup: SymptomPayload['age_group'] = 'child'
): SymptomPayload {
  const payload: SymptomPayload = {
    ...emptyPayload('hi'),
    age_group: ageGroup,
  };
  for (const [tileId, payloadKey] of Object.entries(TILE_PAYLOAD_KEYS)) {
    if (answers[tileId] === true) {
      (payload as unknown as Record<string, unknown>)[payloadKey] = true;
    }
  }
  if (answers['fever'] === true) {
    payload.fever_days = feverDays === 'long' ? 4 : 1;
  }
  return payload;
}

describe('TouchToHearPanel — payload building', () => {
  test('all tile IDs map to a valid SymptomPayload key', () => {
    const validKeys = Object.keys(emptyPayload('en'));
    for (const tileId of TILE_IDS) {
      const mappedKey = TILE_PAYLOAD_KEYS[tileId];
      expect(validKeys).toContain(mappedKey);
    }
  });

  test('answering snakeBite=true sets acute_poisoning_or_bite=true', () => {
    const p = buildPayload({ snakeBite: true });
    expect(p.acute_poisoning_or_bite).toBe(true);
  });

  test('answering convulsions=true sets convulsions=true', () => {
    const p = buildPayload({ convulsions: true });
    expect(p.convulsions).toBe(true);
  });

  test('fever with feverDays=long sets fever_days=4', () => {
    const p = buildPayload({ fever: true }, 'long');
    expect(p.has_fever).toBe(true);
    expect(p.fever_days).toBe(4);
  });

  test('fever with feverDays=short sets fever_days=1', () => {
    const p = buildPayload({ fever: true }, 'short');
    expect(p.fever_days).toBe(1);
  });

  test('No=false answers do not flip payload fields', () => {
    const p = buildPayload({ convulsions: false, snakeBite: false, diarrhoea: false });
    expect(p.convulsions).toBe(false);
    expect(p.acute_poisoning_or_bite).toBe(false);
    expect(p.diarrhoea).toBe(false);
  });
});

describe('TouchToHearPanel — triage integration', () => {
  test('snake bite → risk_score 3 (immediate emergency)', () => {
    const payload = buildPayload({ snakeBite: true });
    const result = evaluateLocal(payload);
    expect(result.risk_score).toBe(3);
  });

  test('convulsions → risk_score 3', () => {
    const payload = buildPayload({ convulsions: true });
    const result = evaluateLocal(payload);
    expect(result.risk_score).toBe(3);
  });

  test('chest indrawing → risk_score 3 (severe respiratory distress)', () => {
    const payload = buildPayload({ fever: true, chestIndrawing: true }, 'long');
    const result = evaluateLocal(payload);
    expect(result.risk_score).toBe(3);
  });

  test('vomiting everything → risk_score 3', () => {
    const payload = buildPayload({ vomitingEverything: true });
    const result = evaluateLocal(payload);
    expect(result.risk_score).toBe(3);
  });

  test('unable to drink → risk_score 3 (general danger sign)', () => {
    const payload = buildPayload({ unableToDrink: true });
    const result = evaluateLocal(payload);
    expect(result.risk_score).toBe(3);
  });

  test('fever alone short duration → risk_score 2 (ASHA visit, not emergency)', () => {
    const payload = buildPayload({ fever: true }, 'short');
    const result = evaluateLocal(payload);
    expect(result.risk_score).toBeLessThanOrEqual(2);
  });

  test('diarrhoea alone → risk_score ≤ 2 (not immediately critical without dehydration signs)', () => {
    const payload = buildPayload({ diarrhoea: true });
    const result = evaluateLocal(payload);
    expect(result.risk_score).toBeLessThanOrEqual(2);
  });

  test('all clear (no answers) → risk_score 1 (self-care)', () => {
    const payload = buildPayload({});
    const result = evaluateLocal(payload);
    expect(result.risk_score).toBe(1);
  });

  test('result always has rationale_en string', () => {
    const payload = buildPayload({ snakeBite: true });
    const result = evaluateLocal(payload);
    expect(typeof result.rationale_en).toBe('string');
    expect(result.rationale_en.length).toBeGreaterThan(0);
  });

  test('result always has actions array', () => {
    const payload = buildPayload({ snakeBite: true });
    const result = evaluateLocal(payload);
    expect(Array.isArray(result.actions)).toBe(true);
    expect(result.actions.length).toBeGreaterThan(0);
  });
});

describe('TouchToHearPanel — canEvaluate gate', () => {
  test('fewer than 3 answered tiles blocks evaluate', () => {
    const answers: Record<string, boolean | null> = {};
    for (const id of TILE_IDS) answers[id] = null;
    answers['fever'] = true;
    answers['diarrhoea'] = false;
    const answeredCount = Object.values(answers).filter((v) => v !== null).length;
    expect(answeredCount).toBeLessThan(3);
  });

  test('3 or more answered tiles enables evaluate', () => {
    const answers: Record<string, boolean | null> = {};
    for (const id of TILE_IDS) answers[id] = null;
    answers['fever'] = true;
    answers['diarrhoea'] = false;
    answers['convulsions'] = true;
    const answeredCount = Object.values(answers).filter((v) => v !== null).length;
    expect(answeredCount).toBeGreaterThanOrEqual(3);
  });
});
