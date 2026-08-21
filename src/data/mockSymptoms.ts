export type RiskLevel = 1 | 2 | 3;

export interface SymptomScenario {
  id: string;
  language: 'Tamil' | 'Hindi' | 'Bengali';
  riskScore: RiskLevel;
  audioDuration: number;
  originalScript: string;
  englishTranslation: string;
  nerExtraction: {
    symptoms: string[];
    duration?: string;
    patientAge?: string;
    redFlags?: string[];
  };
  imciDecision: string;
  responseMessageOriginal: string;
  responseMessageEnglish: string;
}

export const defaultScenarios: Record<'Tamil' | 'Hindi' | 'Bengali', SymptomScenario> = {
  Tamil: {
    id: 'sc-1',
    language: 'Tamil',
    riskScore: 1,
    audioDuration: 3,
    originalScript: "என் குழந்தைக்கு லேசான காய்ச்சல் இருக்கு. நேற்றிலிருந்து...",
    englishTranslation: "My child has a mild fever. Since yesterday...",
    nerExtraction: {
      symptoms: ["Mild fever"],
      duration: "1 day",
      patientAge: "child",
      redFlags: [],
    },
    imciDecision: "No danger signs. Manage at home with paracetamol.",
    responseMessageOriginal: "லேசான காய்ச்சல் மட்டும். கவலைப்பட வேண்டாம், பாராசிட்டமால் கொடுக்கவும்.",
    responseMessageEnglish: "Only mild fever. Do not worry, give Paracetamol.",
  },
  Hindi: {
    id: 'sc-2',
    language: 'Hindi',
    riskScore: 2,
    audioDuration: 4,
    originalScript: "बच्चे को खांसी है और सांस लेने में थोड़ी दिक्कत हो रही है। दो दिन से।",
    englishTranslation: "The child has a cough and slight difficulty breathing. Since two days.",
    nerExtraction: {
      symptoms: ["Cough", "Difficulty breathing"],
      duration: "2 days",
      patientAge: "child",
      redFlags: ["Breathing difficulty"],
    },
    imciDecision: "Possible pneumonia. Refer to ASHA/CHW for assessment.",
    responseMessageOriginal: "आशा दीदी को बता दिया गया है, वो जल्द ही घर आएंगी।",
    responseMessageEnglish: "ASHA worker has been notified, she will come home soon.",
  },
  Bengali: {
    id: 'sc-3',
    language: 'Bengali',
    riskScore: 3,
    audioDuration: 5,
    originalScript: "আমার স্বামীর বুকে খুব ব্যথা হচ্ছে আর রক্তবমি হচ্ছে! জলদি কিছু করুন!",
    englishTranslation: "My husband is having severe chest pain and vomiting blood! Do something quickly!",
    nerExtraction: {
      symptoms: ["Chest pain", "Vomiting blood"],
      duration: "Immediate",
      patientAge: "adult male",
      redFlags: ["Severe chest pain", "Vomiting blood"],
    },
    imciDecision: "SEVERE EMERGENCY. Immediate referral to nearest PHC/Hospital.",
    responseMessageOriginal: "অবিলম্বে নিকটস্থ স্বাস্থ্য কেন্দ্রে যান। অ্যাম্বুলেন্স ডাকা হচ্ছে।",
    responseMessageEnglish: "Go to the nearest health center immediately. Ambulance has been called.",
  }
};
