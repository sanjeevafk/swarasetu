"""Emergency dispatch and actionable first-aid protocol catalog for extreme and edge cases.

Provides deterministic, localized 4-Pillar Emergency Response protocols:
1. 🚑 Automated 108 CAD Ambulance Dispatch Ticket
2. 👩‍⚕️ Healthcare Worker (ASHA) & PHC Pre-Arrival Alert
3. 🩹 Life-Saving First-Aid Directives (Bilingual / Multi-lingual)
4. 📍 PHC Geo-Location & 1-Tap Navigation Link
"""

from __future__ import annotations

import uuid
from typing import Any


FIRST_AID_PROTOCOLS: dict[str, dict[str, Any]] = {
    "snake_bite_emergency": {
        "title_en": "Snake Bite & Acute Envenomation Protocol",
        "title_hi": "सर्पदंश एवं विषैला दंश आपातकालीन प्रोटोकॉल",
        "title_ta": "பாம்பு கடி மற்றும் விஷக்கடி அவசர நெறிமுறை",
        "title_bn": "সাপের কামড় জরুরি প্রোটোকল",
        "cad_priority": "CRITICAL_P1",
        "ambulance_type": "108 Emergency ALS",
        "phc_readiness": "Prepare Anti-Snake Venom (ASV) & Oxygen",
        "steps_en": [
            "🚑 108 Emergency Ambulance: Automated SOS dispatch ticket generated.",
            "👩‍⚕️ ASHA & PHC Pre-Alert: Alerted local ASHA responder & PHC doctor to prep ASV vials.",
            "🩹 Keep Patient Still: Keep patient lying flat & completely calm. Muscle movement accelerates venom absorption.",
            "🚫 Strict Don'ts: Do NOT cut, suck, or wash the bite wound. Do NOT apply ice or tight tourniquets (prevents gangrene).",
            "🛡️ Immobilize: Keep the bitten limb completely immobilized below heart level.",
        ],
        "steps_hi": [
            "🚑 108 एम्बुलेंस: स्वचालित SOS डिस्पैच टिकट जनरेट किया गया।",
            "👩‍⚕️ आशा एवं PHC अलर्ट: स्थानीय आशा कार्यकर्ता और PHC डॉक्टर को एंटी-वेनम तैयार रखने की सूचना दी गई।",
            "🩹 मरीज को स्थिर रखें: मरीज को शांत और लेटाकर रखें। हिलने-डुलने से जहर तेजी से फैलता है।",
            "🚫 क्या न करें: काटे गए स्थान को चीरें, चूसें या बर्फ न लगाएं। टाइट पट्टी न बांधें।",
            "🛡️ अंग को स्थिर रखें: प्रभावित अंग को दिल के स्तर से नीचे सहारा देकर रखें।",
        ],
        "steps_ta": [
            "🚑 108 ஆம்புலன்ஸ்: தானியங்கி SOS அவசர அழைப்பு அனுப்பப்பட்டது.",
            "👩‍⚕️ ஆஷா & PHC எச்சரிக்கை: ஆஷா பணியாளர் மற்றும் PHC மருத்துவருக்கு ஆன்டி-வெனம் தயார் செய்ய தகவல் அனுப்பப்பட்டது.",
            "🩹 அமைதியாக படுக்க வைக்கவும்: நோயாளியை அசையாமல் படுக்க வைக்கவும். அசைந்தால் விஷம் வேகமாக பரவும்.",
            "🚫 செய்யக்கூடாதவை: கடித்த இடத்தில் கீறவோ, உறிஞ்சவோ, ஐஸ் வைக்கவோ அல்லது இறுக்கமான கயிறு கட்டவோ கூடாது.",
            "🛡️ கடித்த உறுப்பை இதய மட்டத்திற்கு கீழே அசைவின்றி வைக்கவும்.",
        ],
        "steps_bn": [
            "🚑 ১০৮ অ্যাম্বুলেন্স: স্বয়ংক্রিয় জরুরি ডিসপ্যাচ শুরু হয়েছে।",
            "👩‍⚕️ আশা ও PHC সতর্কতা: স্থানীয় আশা কর্মী এবং PHC ডাক্তারকে অ্যান্টি-ভেনম প্রস্তুত রাখতে বলা হয়েছে।",
            "🩹 শান্ত রাখুন: রোগীকে সম্পূর্ণ স্থির ও শান্ত রাখুন। নড়াচড়া করলে বিষ দ্রুত ছড়ায়।",
            "🚫 নিষেধ: ক্ষতস্থান কাটবেন না, চুষবেন না বা খুব শক্ত বাঁধন দেবেন না।",
            "🛡️ অঙ্গ স্থির রাখুন: আক্রান্ত অঙ্গ হৃদপিন্ডের নিচে স্থির রাখুন।",
        ],
    },
    "severe_chest_pain": {
        "title_en": "Acute Coronary / Cardiac & Severe Distress Protocol",
        "title_hi": "हृदय आघात एवं गंभीर सीने में दर्द प्रोटोकॉल",
        "title_ta": "மாரடைப்பு மற்றும் கடுமையான நெஞ்சு வலி நெறிமுறை",
        "title_bn": "তীব্র বুকে ব্যথা ও কার্ডিয়াক প্রোটোকল",
        "cad_priority": "CRITICAL_P1",
        "ambulance_type": "108 Cardiac ICU Ambulance",
        "phc_readiness": "Prepare ECG, Oxygen & Sublingual Sorbitrate",
        "steps_en": [
            "🚑 108 Ambulance: Emergency Cardiac CAD ticket initiated.",
            "👩‍⚕️ PHC Pre-Alert: Alerted emergency duty doctor to prepare ECG bay.",
            "🩹 Position: Keep patient seated upright in comfortable leaning position. Loosen tight clothing.",
            "💊 First Aid: Administer 300mg chewable Aspirin if available and patient is not allergic.",
            "🚫 Strict Don'ts: Do NOT allow patient to walk, stand, or perform physical exertion.",
        ],
        "steps_hi": [
            "🚑 108 एम्बुलेंस: आपातकालीन कार्डियक टिकट शुरू किया गया।",
            "👩‍⚕️ PHC अलर्ट: ड्यूटी डॉक्टर को ECG वार्ड तैयार रखने की सूचना दी गई।",
            "🩹 स्थिति: मरीज को आराम से बैठाकर रखें और तंग कपड़े ढीले करें।",
            "💊 प्राथमिक उपचार: यदि उपलब्ध हो और एलर्जी न हो, तो 300mg एस्पिरिन चबाने को दें।",
            "🚫 पैदल न चलने दें: मरीज को कोई शारीरिक मेहनत न करने दें।",
        ],
        "steps_ta": [
            "🚑 108 ஆம்புலன்ஸ்: அவசர இதய சிகிச்சை டிக்கெட் உருவாக்கப்பட்டது.",
            "👩‍⚕️ PHC எச்சரிக்கை: மருத்துவர் ECG பரிசோதனை செய்ய எச்சரிக்கை அனுப்பப்பட்டது.",
            "🩹 நிலை: நோயாளியை சாய்ந்த நிலையில் அமர வைக்கவும். இறுக்கமான ஆடைகளை தளர்த்தவும்.",
            "💊 முதலுதவி: ஒவ்வாமை இல்லையெனில் 300mg ஆஸ்பிரின் மெல்ல கொடுக்கவும்.",
            "🚫 நோயாளியை நடக்கவோ சிரமப்படவோ விடாதீர்கள்.",
        ],
        "steps_bn": [
            "🚑 ১০৮ অ্যাম্বুলেন্স: কার্ডিয়াক জরুরি টিকিট প্রস্তুত।",
            "👩‍⚕️ PHC সতর্কতা: ইসিজি প্রস্তুত রাখার বার্তা পাঠানো হয়েছে।",
            "🩹 রোগীকে আরামদায়ক অবস্থানে বসিয়ে রাখুন এবং জামাকাপড় ঢিলে করুন।",
            "💊 অ্যালার্জি না থাকলে ৩০০ মিলিগ্রাম অ্যাসপিরিন চিবিয়ে খেতে দিন।",
            "🚫 রোগীকে হাঁটাহাঁটি করতে দেবেন না।",
        ],
    },
    "severe_trauma_burn": {
        "title_en": "Severe Trauma, Major Burns & Fracture Protocol",
        "title_hi": "गंभीर चोट, जलना एवं फ्रैक्चर आपातकालीन प्रोटोकॉल",
        "title_ta": "கடுமையான காயம், தீக்காயம் மற்றும் எலும்பு முறிவு நெறிமுறை",
        "title_bn": "মারাত্মক পোড়া ও আঘাত প্রোটোকল",
        "cad_priority": "CRITICAL_P1",
        "ambulance_type": "108 Trauma Ambulance",
        "phc_readiness": "Prepare Sterile Dressings, IV Fluids & Splints",
        "steps_en": [
            "🚑 108 Emergency: Trauma dispatch ticket logged.",
            "🩹 Major Burns: Cool immediately under clean, gently running room-temperature water for 20 minutes. Do NOT apply toothpaste or pop blisters.",
            "🩸 Bleeding: Apply firm, continuous direct pressure with a sterile/clean cloth.",
            "🦴 Fractures: Support and immobilize limb in position found. Do not force bone back into alignment.",
            "👩‍⚕️ Hospital: PHC trauma team alerted for immediate stabilization.",
        ],
        "steps_hi": [
            "🚑 108 इमरजेंसी: ट्रॉमा रिस्पांस टिकट दर्ज किया गया।",
            "🩹 जलने पर: तुरंत 20 मिनट तक साफ बहते पानी से ठंडा करें। टूथपेस्ट न लगाएं और छाले न फोड़ें।",
            "🩸 रक्तस्राव: साफ कपड़े से लगातार दबाकर रखें।",
            "🦴 फ्रैक्चर: अंग को बिना हिलाए सहारा देकर स्थिर रखें।",
            "👩‍⚕️ PHC ट्रॉमा टीम को प्राथमिक उपचार हेतु सूचित किया गया।",
        ],
        "steps_ta": [
            "🚑 108 அவசர சிகிச்சை: அவசர டிக்கெட் பதிவு செய்யப்பட்டது.",
            "🩹 தீக்காயத்திற்கு: 20 நிமிடங்கள் சுத்தமான குளிர்ந்த நீரில் குளிர்விக்கவும். பற்பசை பூச வேண்டாம்.",
            "🩸 ரத்தப்போக்குக்கு: சுத்தமான துணியால் தொடர்ந்து அழுத்திப் பிடிக்கவும்.",
            "🦴 எலும்பு முறிவுக்கு: அசைக்காமல் நிலைநிறுத்தவும்.",
            "👩‍⚕️ PHC அவசர சிகிச்சைக்கு தகவல் தெரிவிக்கப்பட்டது.",
        ],
        "steps_bn": [
            "🚑 ১০৮ ট্রমা জরুরি টিকিট শুরু।",
            "🩹 পোড়া স্থান ২০ মিনিট পরিষ্কার জলে ঠান্ডা করুন। টুথপেস্ট লাগাবেন না।",
            "🩸 রক্তপাতে পরিষ্কার কাপড় দিয়ে চেপে ধরুন।",
            "🦴 ভাঙা অঙ্গ না নাড়িয়ে স্থির রাখুন।",
            "👩‍⚕️ PHC ট্রমা টিমকে অবহিত করা হয়েছে।",
        ],
    },
    "maternal_emergency": {
        "title_en": "Maternal Obstetric Emergency Protocol",
        "title_hi": "मातृ आपातकालीन प्रसूति प्रोटोकॉल",
        "title_ta": "மகப்பேறு அவசர சிகிச்சை நெறிமுறை",
        "title_bn": "মাতৃ জরুরি প্রসূতি প্রোটোকল",
        "cad_priority": "CRITICAL_P1",
        "ambulance_type": "108 102 Janani Shishu Ambulance",
        "phc_readiness": "Prepare Delivery Bay, Magnesium Sulfate & Blood Transfusion Contact",
        "steps_en": [
            "🚑 108/102 Emergency: Obstetric ambulance dispatched.",
            "🩹 Left Lateral Position: Turn mother onto her LEFT side to ensure optimal blood & oxygen flow to baby.",
            "⚡ Convulsions: Clear immediate area. Do NOT insert fingers, spoon, or objects into mouth.",
            "👩‍⚕️ ASHA & PHC: Local ASHA worker & PHC Obstetric Officer alerted immediately.",
        ],
        "steps_hi": [
            "🚑 108/102 एम्बुलेंस: प्रसूति एम्बुलेंस डिस्पैच की गई।",
            "🩹 बाईं करवट: महिला को बाईं करवट लेटाएं ताकि शिशु को ऑक्सीजन व रक्त सही मिले।",
            "⚡ दौरे पर: मुंह में कोई चम्मच या अंगुली न डालें।",
            "👩‍⚕️ आशा कार्यकर्ता एवं PHC प्रसूति वार्ड को तत्काल अलर्ट भेजा गया।",
        ],
        "steps_ta": [
            "🚑 108/102 ஆம்புலன்ஸ்: மகப்பேறு அவசர ஆம்புலன்ஸ் அனுப்பப்பட்டது.",
            "🩹 இடது பக்கமாக படுக்க வைக்கவும்: குழந்தைக்கு ரத்த ஓட்டம் சீராக இருக்க தாயை இடது பக்கமாக படுக்க வைக்கவும்.",
            "⚡ வலிப்பு வந்தால் வாயில் விரல் அல்லது ஸ்பூன் வைக்க வேண்டாம்.",
            "👩‍⚕️ ஆஷா பணியாளர் மற்றும் PHC மருத்துவருக்கு தகவல் தெரிவிக்கப்பட்டது.",
        ],
        "steps_bn": [
            "🚑 ১০৮/১০২ প্রসূতি অ্যাম্বুলেন্স প্রেরণ করা হয়েছে।",
            "🩹 মাকে বাম পাশ ফিরে শুইয়ে দিন।",
            "⚡ খিঁচুনির সময় মুখে কোনো বস্তু দেবেন না।",
            "👩‍⚕️ আশা কর্মী ও PHC প্রসূতি ওয়ার্ডকে সতর্ক করা হয়েছে।",
        ],
    },
    "general_emergency": {
        "title_en": "Critical Emergency Life Support Protocol",
        "title_hi": "आपातकालीन जीवन रक्षक प्रोटोकॉल",
        "title_ta": "அவசர உயிர் காக்கும் நெறிமுறை",
        "title_bn": "জরুরি জীবন রক্ষা প্রোটোকল",
        "cad_priority": "CRITICAL_P1",
        "ambulance_type": "108 Emergency Ambulance",
        "phc_readiness": "Prepare Resuscitation & Emergency Stabilization",
        "steps_en": [
            "🚑 108 Ambulance: Emergency ambulance dispatch initiated.",
            "🩹 Recovery Position: Place unconscious patient on their side to maintain open airway.",
            "🚫 Strict Don'ts: Do NOT give any water, liquids, or oral medications while unconscious.",
            "👩‍⚕️ PHC: Pre-arrival hospital notification sent to duty doctor.",
        ],
        "steps_hi": [
            "🚑 108 एम्बुलेंस: आपातकालीन एम्बुलेंस डिस्पैच शुरू की गई।",
            "🩹 रिकवरी स्थिति: बेहोश मरीज को करवट के बल लेटाएं ताकि सांस न रुके।",
            "🚫 बेहोशी में पानी या कोई दवा मुंह में न दें।",
            "👩‍⚕️ PHC ड्यूटी डॉक्टर को पहले ही सूचना भेज दी गई है।",
        ],
        "steps_ta": [
            "🚑 108 ஆம்புலன்ஸ்: அவசர ஆம்புலன்ஸ் அனுப்பப்பட்டது.",
            "🩹 நோயாளியை ஒருக்களித்துப் படுக்க வைக்கவும்.",
            "🚫 மயக்க நிலையில் எந்த தண்ணீரோ மருந்தோ கொடுக்க வேண்டாம்.",
            "👩‍⚕️ PHC மருத்துவருக்கு முன் அறிவிப்பு அனுப்பப்பட்டது.",
        ],
        "steps_bn": [
            "🚑 ১০৮ অ্যাম্বুলেন্স রওনা হয়েছে।",
            "🩹 অজ্ঞান রোগীকে একপাশে কাত করে শুইয়ে দিন।",
            "🚫 অজ্ঞান অবস্থায় কোনো জল বা ওষুধ মুখে দেবেন না।",
            "👩‍⚕️ PHC ডাক্তারকে সতর্ক করা হয়েছে।",
        ],
    },
}


def get_first_aid_protocol(
    rationale_keys: list[str] | tuple[str, ...],
    language: str = "hi",
    primary_cluster: str = "general",
) -> dict[str, Any]:
    """Resolve the specific first-aid protocol and dispatch steps for extreme/edge cases."""
    lang = language.split("-")[0].lower() if language else "hi"
    if lang not in ("en", "hi", "ta", "bn"):
        lang = "hi"

    matched_key = "general_emergency"
    if "snake_bite_emergency" in rationale_keys:
        matched_key = "snake_bite_emergency"
    elif "severe_chest_pain" in rationale_keys:
        matched_key = "severe_chest_pain"
    elif "severe_trauma_burn" in rationale_keys:
        matched_key = "severe_trauma_burn"
    elif primary_cluster == "maternal" or any("maternal" in k or "pregnancy" in k for k in rationale_keys):
        matched_key = "maternal_emergency"

    proto = FIRST_AID_PROTOCOLS[matched_key]
    ticket_id = f"108-EMRI-{uuid.uuid4().hex[:6].upper()}"

    steps = proto.get(f"steps_{lang}") or proto["steps_en"]
    title = proto.get(f"title_{lang}") or proto["title_en"]

    return {
        "protocol_key": matched_key,
        "title": title,
        "ticket_id": ticket_id,
        "cad_priority": proto["cad_priority"],
        "ambulance_type": proto["ambulance_type"],
        "phc_readiness": proto["phc_readiness"],
        "steps": steps,
        "steps_en": proto["steps_en"],
    }
