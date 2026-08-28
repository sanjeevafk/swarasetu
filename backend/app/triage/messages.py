"""Plain-language message catalog for triage rationales and actions.

Every rationale key produced by the engine resolves to:
  - English text (audit + supervisor dashboard)
  - Native-language strings for the supported Indic languages
    (hi = Hindi, ta = Tamil, bn = Bengali) used for TTS/voice responses.

Adding a language only requires extending LANG_TEXT; engine logic is untouched.
"""

from __future__ import annotations

SUPPORTED_LANGUAGES = ("en", "hi", "ta", "bn")

# key -> {lang: text}
RATIONALE: dict[str, dict[str, str]] = {
    "general_danger_sign": {
        "en": "A general danger sign was detected. This needs emergency care now.",
        "hi": "एक सामान्य खतरे का संकेत पाया गया है। इसे अभी आपातकालीन देखभाल की आवश्यकता है।",
        "ta": "ஒரு பொது ஆபத்து அறிகுறி கண்டறியப்பட்டது. உடனடி அவசர சிகிச்சை தேவை.",
        "bn": "একটি সাধারণ বিপদচিহ্ন শনাক্ত হয়েছে। এখনই জরুরি যত্ন প্রয়োজন।",
    },
    "snake_bite_emergency": {
        "en": "Snake bite or acute envenomation is a critical life-threatening emergency. Immediate anti-venom at nearest PHC is required.",
        "hi": "सांप का काटना / विषैला दंश एक गंभीर आपातकालीन स्थिति है। नजदीकी प्राथमिक स्वास्थ्य केंद्र पर तुरंत एंटी-वेनम की आवश्यकता है।",
        "ta": "பாம்பு கடி / விஷக்கடி என்பது உயிருக்கு ஆபத்தான அவசர நிலை. அருகிலுள்ள ஆரம்ப சுகாதார நிலையத்தில் உடனடியாக ஆன்டி-வெனம் (விஷ முறிவு) சிகிச்சை பெற வேண்டும்.",
        "bn": "সাপের কামড় একটি মারাত্মক জরুরি অবস্থা। অবিলম্বে নিকটস্থ স্বাস্থ্যকেন্দ্রে অ্যান্টি-ভেনম চিকিৎসা প্রয়োজন।",
    },
    "severe_trauma_burn": {
        "en": "Severe injury, major burn, or trauma requires immediate emergency medical care and hospital stabilization.",
        "hi": "गंभीर चोट या जलना एक आपातकालीन स्थिति है। तुरंत अस्पताल में आपातकालीन उपचार की आवश्यकता है।",
        "ta": "கடுமையான தீக்காயம் அல்லது தீவிர காயம் ஏற்பட்டால் உடனடியாக அவசர மருத்துவ சிகிச்சை பெற வேண்டும்.",
        "bn": "গুরুতর আঘাত বা মারাত্মক পোড়া অবিলম্বে জরুরি চিকিৎসা প্রয়োজন।",
    },
    "severe_chest_pain": {

        "en": "Severe chest pain with vomiting blood can indicate a medical emergency.",
        "hi": "गंभीर सीने में दर्द के साथ खून की उल्टी आपातकालीन स्थिति का संकेत हो सकती है।",
        "ta": "கடுமையான நெஞ்சு வலி மற்றும் ரத்த வாந்தி மருத்துவ அவசரநிலையைக் குறிக்கலாம்.",
        "bn": "তীব্র বুকে ব্যথা এবং রক্তবমি একটি মেডিকেল ইমার্জেন্সির লক্ষণ হতে পারে।",
    },
    "fever_neck_stiffness_meningitis": {
        "en": "Fever with neck stiffness suggests possible meningitis and must be referred immediately.",
        "hi": "बुखार के साथ गर्दन में अकड़न मस्तिष्क ज्वर (मेनिन्जाइटिस) का संकेत है, तुरंत रेफर करें।",
        "ta": "காய்ச்சலுடன் கழுத்து விறைப்பு மூளைக்காய்ச்சல் (மெனிங்கைடிஸ்) அச்சத்தைக் குறிக்கிறது; உடனே பரிசோதனை தேவை.",
        "bn": "জ্বরের সঙ্গে ঘাড় শক্ত হওয়া মস্তিষ্কঝিল্লির প্রদাহ (মেনিনজাইটিস) নির্দেশ করতে পারে, তাৎক্ষণিক রেফার করুন।",
    },
    "fever_convulsions": {
        "en": "Convulsions with fever are a danger sign requiring immediate referral.",
        "hi": "बुखार के साथ झटके आना खतरे का संकेत है, तुरंत रेफर करें।",
        "ta": "காய்ச்சலுடன் வலிப்பு ஏற்படுவது ஆபத்தான அறிகுறி, உடனடியாக குறிப்பிட்ட மருத்துவமனைக்கு அனுப்பவும்.",
        "bn": "জ্বরের সঙ্গে খিঁচুনি একটি বিপদচিহ্ন, তাৎক্ষণিক রেফার প্রয়োজন।",
    },
    "fever_rash_urgent": {
        "en": "Fever with rash may signal dengue or another urgent infection needing assessment.",
        "hi": "बुखार के साथ चकत्ते डेंगू या किसी गंभीर संक्रमण का संकेत हो सकते हैं।",
        "ta": "காய்ச்சலுடன் சிவப்புத் தடிப்பு டெங்கு அல்லது வேறு தீவிர தொற்றின் அறிகுறியாக இருக்கலாம்.",
        "bn": "জ্বরের সঙ্গে র‍্যাশ ডেঙ্গু বা অন্য জরুরি সংক্রমণের লক্ষণ হতে পারে।",
    },
    "neonatal_fever": {
        "en": "Fever in a baby under 2 months is always treated as serious; refer now.",
        "hi": "2 महीने से छोटे शिशु में बुखार हमेशा गंभीर माना जाता है; तुरंत रेफर करें।",
        "ta": "2 மாதத்திற்குக் குறைவான குழந்தைக்கு காய்ச்சல் என்றால் அது தீவிரமானதாகவே கருதப்படும்; உடனே பரிசோதனை தேவை.",
        "bn": "২ মাসের কম শিশুর জ্বরকে সবসময় গুরুতর ধরা হয়; এখনই রেফার করুন।",
    },
    "fever_high_or_prolonged": {
        "en": "High or prolonged fever needs assessment within 24 hours by a health worker.",
        "hi": "तेज़ या लंबे बुखार की 24 घंटे के भीतर स्वास्थ्य कर्मी से जाँच आवश्यक है।",
        "ta": "அதிக அல்லது நீடித்த காய்ச்சலுக்கு 24 மணி நேரத்திற்குள் சுகாதார பணியாளர் பரிசோதனை தேவை.",
        "bn": "উচ্চ বা দীর্ঘস্থায়ী জ্বরের ২৪ ঘণ্টার মধ্যে স্বাস্থ্যকর্মীর মূল্যায়ন প্রয়োজন।",
    },
    "malaria_risk_fever": {
        "en": "In a malaria-prone area this fever needs testing and ASHA follow-up today.",
        "hi": "मलेरिया प्रवण क्षेत्र में इस बुखार की आज ही जाँच और आशा फॉलो-अप आवश्यक है।",
        "ta": "மலேரியா அதிகமுள்ள பகுதியில் இந்த காய்ச்சலுக்கு இன்றே பரிசோதனை மற்றும் ஆஷா பின்தொடர்தல் தேவை.",
        "bn": "ম্যালেরিয়াপ্রবণ এলাকায় এই জ্বরের আজই পরীক্ষা ও আশা ফলোআপ দরকার।",
    },
    "fever_self_care": {
        "en": "Mild fever without danger signs can be managed safely at home.",
        "hi": "खतरे के संकेत के बिना हल्का बुखार घर पर ही सुरक्षित रूप से देखभाल किया जा सकता है।",
        "ta": "ஆபத்து அறிகுறிகள் இல்லாத லேசான காய்ச்சலை வீட்டிலேயே பாதுகாப்பாக கவனிக்கலாம்.",
        "bn": "বিপদচিহ্ন ছাড়া হালকা জ্বর ঘরেই নিরাপদে সামলানো যায়।",
    },
    "resp_severe_distress": {
        "en": "Chest indrawing or noisy breathing (stridor) means severe respiratory distress — refer immediately.",
        "hi": "छाती का धँसना या सांस में घरघराहट (स्ट्राइडर) गंभीर सांस की तकलीफ है — तुरंत रेफर करें।",
        "ta": "நெஞ்சு உள்ளிழுத்தல் அல்லது மூச்சுக்குழல் சத்தம் (ஸ்ட்ரைடர்) கடுமையான மூச்சுத்திணறல் — உடனடி மருத்துவமனை தேவை.",
        "bn": "বুক খাঁকারি বা শ্বাসে শব্দ (স্ট্রাইডর) মারাত্মক শ্বাসকষ্ট নির্দেশ করে — তাৎক্ষণিক রেফার করুন।",
    },
    "resp_fast_breathing_pneumonia": {
        "en": "Fast breathing indicates possible pneumonia; an ASHA worker should assess within 24 hours.",
        "hi": "तेज़ सांस लेना निमोनिया का संकेत हो सकता है; आशा कर्मी को 24 घंटे में जाँच करनी चाहिए।",
        "ta": "வேகமான மூச்சு நிமோனியாவின் அறிகுறியாக இருக்கலாம்; ஆஷா பணியாளர் 24 மணி நேரத்திற்குள் பரிசோதிக்க வேண்டும்.",
        "bn": "দ্রুত শ্বাস নিউমোনিয়ার লক্ষণ হতে পারে; আশা কর্মীর ২৪ ঘণ্টার মধ্যে পরীক্ষা করা উচিত।",
    },
    "resp_uri_self_care": {
        "en": "Short cough without fast breathing looks like a common cold; home care suffices.",
        "hi": "तेज़ सांस के बिना छोटी खांसी सामान्य सर्दी-जुकाम जैसी है; घर की देखभाल पर्याप्त है।",
        "ta": "வேகமான மூச்சு இல்லாத சிறு இருமல் சாதாரண சளி போல தெரிகிறது; வீட்டு கவனிப்பு போதும்.",
        "bn": "দ্রুত শ্বাস ছাড়া অল্প কাশি সাধারণ ঠান্ডার মতো মনে হচ্ছে; ঘরোয়া যত্নই যথেষ্ট।",
    },
    "diarrhoea_severe_dehydration": {
        "en": "Signs of severe dehydration from diarrhoea detected — immediate referral needed.",
        "hi": "दस्त से गंभीर निर्जलीकरण के लक्षण मिले — तुरंत रेफर करें।",
        "ta": "வயிற்றுப்போக்கால் கடுமையான நீரிழப்பு அறிகுறிகள் கண்டறியப்பட்டன — உடனடி மருத்துவமனை தேவை.",
        "bn": "ডায়রিয়া থেকে মারাত্মক পানিশূন্যতার লক্ষণ পাওয়া গেছে — তাৎক্ষণিক রেফার প্রয়োজন।",
    },
    "diarrhoea_some_dehydration_or_dysentery": {
        "en": "Some dehydration or blood in stool detected; ASHA assessment needed within 24 hours with ORS guidance.",
        "hi": "कुछ निर्जलीकरण या मल में खून मिला; 24 घंटे में आशा जाँच और ORS मार्गदर्शन आवश्यक है।",
        "ta": "சில நீரிழப்பு அல்லது மலத்தில் ரத்தம் கண்டறியப்பட்டது; 24 மணி நேரத்திற்குள் ஆஷா பரிசோதனை மற்றும் ORS வழிகாட்டுதல் தேவை.",
        "bn": "কিছুটা পানিশূন্যতা বা মলে রক্ত পাওয়া গেছে; ২৪ ঘণ্টার মধ্যে আশা মূল্যায়ন ও ORS নির্দেশনা দরকার।",
    },
    "diarrhoea_no_dehydration": {
        "en": "Diarrhoea without dehydration signs; continue ORS and feeding at home.",
        "hi": "बिना निर्जलीकरण वाले दस्त; घर पर ORS और भोजन जारी रखें।",
        "ta": "நீரிழப்பு அறிகுறிகள் இல்லாத வயிற்றுப்போக்கு; வீட்டில் ORS மற்றும் உணவு தொடரவும்.",
        "bn": "পানিশূন্যতার লক্ষণ ছাড়া ডায়রিয়া; ঘরে ORS ও খাওয়া চালিয়ে যান।",
    },
    "maternal_emergency": {
        "en": "Maternal danger sign detected — this is an obstetric emergency requiring immediate referral.",
        "hi": "मातृ खतरे का संकेत मिला — यह प्रसूति आपातकाल है, तुरंत रेफर करें।",
        "ta": "தாய் தொடர்பான ஆபத்து அறிகுறி — இது உடனடி மகப்பேறு அவசரநிலை, உடனே மருத்துவமனைக்கு அனுப்பவும்.",
        "bn": "মাতৃ বিপদচিহ্ন শনাক্ত — এটি প্রসূতি জরুরি অবস্থা, তাৎক্ষণিক রেফার প্রয়োজন।",
    },
    "adhoc_supply_request": {
        "en": "This looks like a supply, medicine or schedule question; an ASHA worker will follow up and help.",
        "hi": "यह दवा या सूची/समय-सारणी से जुड़ा सवाल लगता है; आशा कर्मी फॉलो-अप करके मदद करेंगे।",
        "ta": "இது மருந்து அல்லது நடைமுறை தொடர்பான கேள்வி போல் தோன்றுகிறது; ஆஷா பணியாளர் தொடர்பு கொண்டு உதவுவார்.",
        "bn": "এটি ওষুধ বা সময়সূচি সংক্রান্ত প্রশ্ন মনে হচ্ছে; আশা কর্মী ফলোআপ করে সাহায্য করবেন।",
    },
    "no_symptoms_matched": {
        "en": "No concerning symptoms matched the IMCI protocol; monitor at home and return if things worsen.",
        "hi": "IMCI प्रोटोकॉल में कोई चिंताजनक लक्षण नहीं मिला; घर पर निगरानी करें और बिगड़ने पर वापस आएं।",
        "ta": "IMCI நெறிமுறையில் கவலை தரும் அறிகுறிகள் எதுவும் இல்லை; வீட்டில் கண்காணித்து, மோசமானால் திரும்பி வாருங்கள்.",
        "bn": "IMCI প্রোটোকলে কোনো উদ্বেগজনক লক্ষণ মেলেনি; ঘরে পর্যবেক্ষণ করুন, খারাপ হলে ফিরে আসুন।",
    },
}

# key -> {lang: action instruction}
ACTIONS: dict[str, dict[str, str]] = {
    "act_refer_phc_now": {
        "en": "Go to the nearest PHC/hospital immediately; share coordinates and contact number.",
        "hi": "निकटतम PHC/अस्पताल तुरंत जाएं; निर्देशांक और संपर्क नंबर साझा करें।",
        "ta": "நெருங்கிய PHC/மருத்துவமனைக்கு உடனே செல்லுங்கள்; இட ஒத்துழைப்பு மற்றும் தொடர்பு எண் வழங்கப்படும்.",
        "bn": "নিকটস্থ PHC/হাসপাতালে এখনই যান; স্থানাঙ্ক ও যোগাযোগ নম্বর দেওয়া হবে।",
    },
    "act_call_ambulance": {
        "en": "Call the 108 ambulance service right away.",
        "hi": "तुरंत 108 एम्बुलेंस सेवा को कॉल करें।",
        "ta": "உடனே 108 ஆம்புலன்ஸ் சேவையை அழைக்கவும்.",
        "bn": "এখনই 108 অ্যাম্বুলেন্স সার্ভিসে কল করুন।",
    },
    "act_notify_asha": {
        "en": "ASHA worker alerted for a visit within 24 hours.",
        "hi": "24 घंटे के भीतर आशा कार्यकर्ता को सूचित किया गया।",
        "ta": "24 மணி நேரத்திற்குள் பரிசோதிக்க ஆஷா பணியாளருக்கு தெரிவிக்கப்பட்டது.",
        "bn": "২৪ ঘণ্টার মধ্যে পরিদর্শনের জন্য আশা কর্মীকে জানানো হয়েছে।",
    },
    "act_paracetamol_home_care": {
        "en": "Give paracetamol as per weight, plenty of fluids, and monitor temperature twice daily.",
        "hi": "वजन के अनुसार पैरासिटामोल दें, खूब तरल दें, और दिन में दो बार बुखार जांचें।",
        "ta": "உடல் எடைக்கேற்ப பாராசிட்டமால் கொடுங்கள், நிறைய தண்ணீர் கொடுங்கள், தினமும் இருமுறை காய்ச்சல் பரிசோதிக்கவும்.",
        "bn": "ওজন অনুযায়ী প্যারাসিটামল দিন, প্রচুর তরল দিন, দিনে দু'বার জ্বর মাপুন।",
    },
    "act_return_if_worse": {
        "en": "Return immediately if breathing worsens, fever rises, or new danger signs appear.",
        "hi": "यदि सांस बिगड़े, बुखार बढ़े या नए खतरे के लक्षण दिखें तो तुरंत वापस आएं।",
        "ta": "மூச்சு சிக்கல் அதிகரித்தால், காய்ச்சல் அதிகரித்தால் அல்லது புதிய ஆபத்து அறிகுறிகள் தோன்றினால் உடனடியாக திரும்பவும்.",
        "bn": "শ্বাসকষ্ট বাড়লে, জ্বর বাড়লে বা নতুন বিপদচিহ্ন দেখা দিলে সাথে সাথে ফিরে আসুন।",
    },
    "act_ors_fluids": {
        "en": "Start ORS solution and continue frequent small feeds/breastfeeding.",
        "hi": "ORS घोल शुरू करें और बार-बार थोड़ा-थोड़ा भोजन/स्तनपान जारी रखें।",
        "ta": "ORS கரைசலைத் தொடங்கவும், அடிக்கடி சிறு அளவில் உணவு/தாய்ப்பால் தொடரவும்.",
        "bn": "ORS দ্রবণ শুরু করুন এবং ঘন ঘন অল্প অল্প খাওয়া/বুকের দুধ চালিয়ে যান।",
    },
    "act_monitor_home": {
        "en": "Monitor at home; no referral needed at this time.",
        "hi": "घर पर निगरानी करें; इस समय रेफरल की आवश्यकता नहीं है।",
        "ta": "வீட்டில் கண்காணிக்கவும்; இப்போது மருத்துவமனை அனுப்பத் தேவையில்லை.",
        "bn": "ঘরে পর্যবেক্ষণ করুন; এই মুহূর্তে রেফারেল প্রয়োজন নেই।",
    },
    "act_zinc_supplement": {
        "en": "Give zinc supplement for 14 days as advised by the health worker.",
        "hi": "स्वास्थ्य कर्मी की सलाह अनुसार 14 दिन ज़िंक पूरक दें।",
        "ta": "சுகாதார பணியாளர் ஆலோசனைப்படி 14 நாட்களுக்கு துத்தநாக சப்ளிமென்ட் கொடுங்கள்.",
        "bn": "স্বাস্থ্যকর্মীর পরামর্শ অনুযায়ী ১৪ দিন জিঙ্ক সাপ্লিমেন্ট দিন।",
    },
    "act_cough_warm_fluids": {
        "en": "Drink warm fluids (warm water, ginger/tulsi tea), take steam inhalation, and keep chest warm.",
        "hi": "गुनगुना पानी और तुलसी-अदरक चाय पिएं, भाप लें और छाती को गर्म रखें।",
        "ta": "சூடான திரவங்கள் (வெந்நீர், துளசி-இஞ்சி தேநீர்) குடிக்கவும், நீராவி பிடிக்கவும் மற்றும் உடலை கதகதப்பாக வைக்கவும்.",
        "bn": "উষ্ণ তরল (গরম জল, আদা-তুলসী চা) পান করুন, গরম জলের ভাপ নিন এবং শরীর উষ্ণ রাখুন।",
    },
    "act_hydration_rest": {
        "en": "Maintain adequate rest, drink clean boiled water and electrolytes, and eat light nutritious food.",
        "hi": "पर्याप्त आराम करें, साफ उबला पानी और तरल लें, तथा हल्का पौष्टिक भोजन करें।",
        "ta": "போதுமான ஓய்வு எடுக்கவும், சுத்தமான காய்ச்சிய நீர் குடிக்கவும் மற்றும் எளிதில் செரிக்கும் உணவு உட்கொள்ளவும்.",
        "bn": "পর্যাপ্ত বিশ্রাম নিন, ফুটানো জল ও তরল পান করুন এবং হালকা পুষ্টিকর খাবার গ্রহণ করুন।",
    },
}


def resolve(catalog: dict[str, dict[str, str]], keys, language: str) -> list[str]:
    """Deterministically resolve ordered keys into localized text lines."""
    lang = language.lower()
    lines: list[str] = []
    for k in keys:
        entry = catalog.get(k)
        if not entry:
            continue
        lines.append(entry.get(lang) or entry["en"])
    return lines
