export type SchemeCategory = 
  | 'ALL' 
  | 'LAND_REVENUE' 
  | 'AGRICULTURE_DBT' 
  | 'INFRASTRUCTURE' 
  | 'HOUSING_WATER' 
  | 'DIGITAL_CITIZEN';

export interface GovScheme {
  id: string;
  code: string;
  name: string;
  nameHi: string;
  shortName: string;
  category: SchemeCategory;
  ministry: string;
  ministryHi: string;
  slogan: string;
  sloganHi: string;
  tagline: string;
  taglineHi: string;
  badge: string;
  theme: 'saffron' | 'navy' | 'emerald' | 'green' | 'blue' | 'purple' | 'amber';
  impactMetric: string;
  impactLabel: string;
  secondaryMetric: string;
  secondaryLabel: string;
  portalUrl: string;
  portalName: string;
  helpline: string;
  description: string;
  descriptionHi: string;
  keyBenefits: string[];
  keyBenefitsHi: string[];
  eligibility: string;
  eligibilityHi: string;
  flagshipInitiative: boolean;
  bannerCtaText?: string;
  circularRef?: string;
}

export const GOV_SCHEMES: GovScheme[] = [
  {
    id: 'SCHEME-SVAMITVA',
    code: 'SVAMITVA',
    name: 'SVAMITVA Scheme (Survey of Villages and Mapping with Improvised Technology in Village Areas)',
    nameHi: 'स्वामित्व योजना — ड्रोन सर्वेक्षण एवं डिजिटल संपत्ति पत्रक',
    shortName: 'SVAMITVA',
    category: 'LAND_REVENUE',
    ministry: 'Ministry of Panchayati Raj & Survey of India, Govt. of India',
    ministryHi: 'पंचायती राज मंत्रालय एवं भारतीय सर्वेक्षण विभाग, भारत सरकार',
    slogan: 'Meri Zameen, Mera Haq — Empowering Rural India',
    sloganHi: 'मेरी ज़मीन, मेरा हक़ — समृद्ध गाँव, समर्थ भारत',
    tagline: 'High-Resolution Drone Cadastral Mapping for Rural Inhabited (Abadi) Lands',
    taglineHi: 'ग्रामीण आबादी क्षेत्रों का आधुनिक ड्रोन सर्वेक्षण एवं कानूनी संपत्ति स्वामित्व',
    badge: 'FLAGSHIP DRONE SURVEY',
    theme: 'saffron',
    impactMetric: '1.65+ Crore',
    impactLabel: 'Sampatti Cards (Property Cards) Distributed',
    secondaryMetric: '3,15,000+ Villages',
    secondaryLabel: 'Drone Flying & Demarcation Completed',
    portalUrl: 'https://svamitva.nic.in',
    portalName: 'svamitva.nic.in',
    helpline: '1800-11-7788 (Toll Free)',
    description: 'A revolutionary central flagship initiative providing rural household owners with legal ownership documents (Property Cards / Sampatti Patra) through cutting-edge drone surveying technology and CORS network.',
    descriptionHi: 'ग्रामीण भारत के नागरिकों को उनकी आबादी भूमि का निर्विवाद कानूनी मालिकाना हक़ (प्रॉपर्टी कार्ड) प्रदान करने हेतु भारत सरकार की ऐतिहासिक ड्रोन आधारित राष्ट्रीय योजना।',
    keyBenefits: [
      'Statutory Property Cards with legal evidentiary value under state land revenue codes',
      'Enables villagers to access institutional bank loans, mortgages, and agricultural credit',
      'High-accuracy 5-cm resolution GIS cadastral boundary maps to prevent boundary disputes',
      'Pre-acquisition demarcation integrated seamlessly into BHUMISETU for fair compensation'
    ],
    keyBenefitsHi: [
      'राजस्व कानूनों के तहत मान्य कानूनी संपत्ति पत्रक (प्रॉपर्टी कार्ड) का वितरण',
      'ग्रामीणों को बैंक ऋण, होम लोन एवं वित्तीय साख की सुलभ सुविधा',
      '५ सेमी सटीकता वाले डिजिटल भू-नक्शे जिससे सीमा विवादों का स्थायी समाधान',
      'भूमि अधिग्रहण में पारदर्शी एवं त्वरित मुआवजा भुगतान हेतु भूमिसेतु से संबद्ध'
    ],
    eligibility: 'All rural residential property owners residing in surveyed village Abadi areas.',
    eligibilityHi: 'सर्वेक्षित ग्रामों के आबादी क्षेत्र में निवास करने वाले सभी ग्रामीण भूस्वामी।',
    flagshipInitiative: true,
    bannerCtaText: 'Download Sampatti Card',
    circularRef: 'MoPR/SVAMITVA/2026/CIR-14'
  },
  {
    id: 'SCHEME-PMKISAN',
    code: 'PM-KISAN',
    name: 'Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)',
    nameHi: 'प्रधानमंत्री किसान सम्मान निधि — प्रत्यक्ष बैंक अंतरण वित्तीय संबल',
    shortName: 'PM-KISAN',
    category: 'AGRICULTURE_DBT',
    ministry: 'Ministry of Agriculture and Farmers Welfare, Govt. of India',
    ministryHi: 'कृषि एवं किसान कल्याण मंत्रालय, भारत सरकार',
    slogan: 'Annadata Ka Samman — Direct Income Support to Farmers',
    sloganHi: 'अन्नदाता का सम्मान, आत्मनिर्भर किसान, समृद्ध राष्ट्र',
    tagline: '₹6,000 Annual Direct Benefit Transfer (DBT) directly into Aadhaar-Linked Bank Accounts',
    taglineHi: '₹६,००० प्रति वर्ष तीन समान किस्तों में सीधे किसानों के बैंक खातों में प्रत्यक्ष अंतरण',
    badge: 'DIRECT BENEFIT TRANSFER',
    theme: 'green',
    impactMetric: '₹3.24+ Lakh Cr',
    impactLabel: 'Direct Cash Transferred via PFMS Portal',
    secondaryMetric: '11.8+ Crore',
    secondaryLabel: 'Active Beneficiary Farmer Families',
    portalUrl: 'https://pmkisan.gov.in',
    portalName: 'pmkisan.gov.in',
    helpline: '155261 / 1800-11-5526',
    description: 'A 100% centrally funded welfare program providing guaranteed direct financial support of ₹6,000 per year in three 4-monthly installments of ₹2,000 directly to landholder farmer families.',
    descriptionHi: 'शत-प्रतिशत केंद्र सरकार द्वारा वित्तपोषित योजना जिसके तहत पात्र भूमिधारक कृषक परिवारों को प्रति वर्ष ₹६,००० की सुनिश्चित वित्तीय सहायता डीबीटी के माध्यम से बैंक खाते में दी जाती है।',
    keyBenefits: [
      'Transparent direct financial assistance credited without any middleman or deduction',
      'Aadhaar-seeded PFMS platform ensures instant verification and zero leakage',
      'Landholding verification linked with digital state land records (7/12, Khatauni, Patta)',
      'Synchronized with RFCTLARR 2013 compensation DBT disbursement in BHUMISETU'
    ],
    keyBenefitsHi: [
      'बिना किसी बिचौलिए या कटौती के सीधे बैंक खाते में शत-प्रतिशत पारदर्शी सहायता',
      'आधार-सीडेड पीएफएमएस पोर्टल द्वारा तुरंत बैंक खाते में राशि का अंतरण',
      'डिजिटल राज्य राजस्व अभिलेखों (७/१२, खतौनी, पट्टा) से स्वतः पात्रता सत्यापन',
      'भूमिसेतु पोर्टल के साथ एकीकृत जिससे अधिग्रहण मुआवजा राशि का भी निर्बाध अंतरण'
    ],
    eligibility: 'All landholding farmer families with cultivable land in valid state land records.',
    eligibilityHi: 'वे सभी कृषक परिवार जिनके नाम राज्य राजस्व अभिलेखों में कृषि योग्य भूमि दर्ज है।',
    flagshipInitiative: true,
    bannerCtaText: 'Check Beneficiary Status',
    circularRef: 'MoA&FW/PM-KISAN/2026/NOTIF-18'
  },
  {
    id: 'SCHEME-GATISHAKTI',
    code: 'PM-GATISHAKTI',
    name: 'PM GatiShakti National Master Plan for Multi-Modal Connectivity',
    nameHi: 'पीएम गति शक्ति — राष्ट्रीय बहु-मॉडल कनेक्टिविटी महायोजना',
    shortName: 'PM GatiShakti',
    category: 'INFRASTRUCTURE',
    ministry: 'DPIIT, Ministry of Commerce & Industry / MoRTH, Govt. of India',
    ministryHi: 'उद्योग संवर्धन विभाग एवं सड़क परिवहन मंत्रालय, भारत सरकार',
    slogan: 'Gati Se Pragati — Integrated Planning for National Infrastructure',
    sloganHi: 'गति से प्रगति — समग्र विकास, आत्मनिर्भर भारत का संकल्प',
    tagline: 'Single National Spatial GIS Engine for Zero-Delay Infrastructure Corridors',
    taglineHi: 'राष्ट्रीय बुनियादी ढांचा परियोजनाओं हेतु एकीकृत स्थानिक जीआईएस मास्टर प्लान',
    badge: 'NATIONAL MASTER PLAN',
    theme: 'navy',
    impactMetric: '1,450+ Layers',
    impactLabel: 'Spatial GIS Corridors & Land Alignments Synced',
    secondaryMetric: '₹100+ Lakh Cr',
    secondaryLabel: 'National Infrastructure Pipeline Monitored',
    portalUrl: 'https://gatishakti.gov.in',
    portalName: 'gatishakti.gov.in',
    helpline: '011-2306-1222',
    description: 'PM GatiShakti breaks departmental silos by bringing 16 Central Ministries together on a single geospatial portal for seamless multi-modal logistics, highway right-of-way planning, and fast-track land acquisitions.',
    descriptionHi: '१६ मंत्रालयों को एक एकीकृत भू-स्थानिक डिजिटल मंच पर लाकर सड़क, रेल, ऊर्जा एवं लॉजिस्टिक्स के बुनियादी ढांचे के निर्माण व भूमि अधिग्रहण को तीव्र गति देने वाली राष्ट्रीय महायोजना।',
    keyBenefits: [
      'Multi-layer PostGIS corridor intersection analysis preventing greenfield route clashes',
      'Single-window statutory clearances across Forest, Wildlife, Railways, and Defense RoW',
      'Eliminates duplicate surveying expenditure across Central & State agencies',
      'Real-time statutory timeline tracking synced directly with BHUMISETU early-warning model'
    ],
    keyBenefitsHi: [
      'मार्ग टकराव रोकने हेतु बहु-स्तरीय पोस्टजीआईएस गलियारा समन्वय विश्लेषण',
      'वन, पर्यावरण, रेलवे एवं रक्षा भूमि हेतु एकल-खिड़की त्वरित वैधानिक अनापत्ति',
      'केंद्र व राज्यों के बीच सर्वेक्षण में दोहरे खर्च की पूर्ण समाप्ति',
      'भूमिसेतु अर्ली-वार्निंग इंजन के साथ वास्तविक समय में मील का पत्थर अनुश्रवण'
    ],
    eligibility: 'Central & State infrastructure executing agencies, NHAI, Railways, and industrial corridors.',
    eligibilityHi: 'केंद्रीय व राज्य अवसंरचना कार्यान्वयन एजेंसियां, एनएचएआई, भारतीय रेल एवं औद्योगिक गलियारे।',
    flagshipInitiative: true,
    bannerCtaText: 'View National Spatial GIS',
    circularRef: 'DPIIT/GATISHAKTI/NMP-2026'
  },
  {
    id: 'SCHEME-BHUAADHAAR',
    code: 'BHU-AADHAAR',
    name: 'Bhu-Aadhaar (ULPIN) — 14-Digit Geo-Coded Unique Land Parcel Identification',
    nameHi: 'भू-आधार (ULPIN) — प्रत्येक भूखंड का १४-अंकीय विशिष्ट भू-पहचान क्रमांक',
    shortName: 'Bhu-Aadhaar',
    category: 'LAND_REVENUE',
    ministry: 'Department of Land Resources, Ministry of Rural Development, Govt. of India',
    ministryHi: 'भूमि संसाधन विभाग, ग्रामीण विकास मंत्रालय, भारत सरकार',
    slogan: 'One Land Parcel, One Digital Identity — Freedom from Land Litigation',
    sloganHi: 'एक भूखंड, एक पहचान — भूमि विवादों और धोखाधड़ी से संपूर्ण मुक्ति',
    tagline: '14-Digit Alphanumeric Universal Identity Derived from Geo-Coordinates',
    taglineHi: 'अक्षांश व देशांतर निर्देशांकों से निर्मित अंतरराष्ट्रीय मानक डिजिटल भू-पहचान',
    badge: 'DIGITAL INDIA LAND RECORD',
    theme: 'emerald',
    impactMetric: '29 States & UTs',
    impactLabel: 'Rolled Out across Revenue Sub-Divisions',
    secondaryMetric: '100% Geo-Coded',
    secondaryLabel: 'WGS-84 Centroid & Vertex Polygon Registration',
    portalUrl: 'https://dilrmp.gov.in',
    portalName: 'dilrmp.gov.in',
    helpline: '1800-11-2013 (Toll Free)',
    description: 'Bhu-Aadhaar provides a unique 14-digit alphanumeric identification code for every surveyed land parcel in India, based on the international open standard coordinates of its boundaries.',
    descriptionHi: 'प्रत्येक भूखंड के देशांतर एवं अक्षांश निर्देशांकों के आधार पर जारी १४-अंकीय विशिष्ट पहचान संख्या, जो भूमि स्वामित्व की प्रमाणिकता और त्वरित अभिलेख अद्यतन सुनिश्चित करती है।',
    keyBenefits: [
      'Eliminates fraudulent duplicate land sales, benami transfers, and forged revenue mutations',
      'Enables instant electronic title deed search and verifiable 7/12 / Jamabandi records',
      'Direct synchronization between Sub-Registrar registration offices and Revenue Records',
      'Automated boundary match in BHUMISETU prevents encroachment on Highway RoW reservations'
    ],
    keyBenefitsHi: [
      'फर्जी बिक्री, बेनामी लेन-देन एवं जाली फेरफार अभिलेखों पर पूर्ण रोकथाम',
      'सत्यापित ७/१२ व जमाबंदी अभिलेखों की तत्काल डिजिटल ऑनलाइन खोज',
      'पंजीयन कार्यालय (रजिस्ट्रार) एवं तहसील राजस्व अभिलेखों का स्वतः रीयल-टाइम मिलान',
      'भूमिसेतु में स्वतः सीमा मिलान जिससे महामार्ग आरक्षण पर अतिक्रमण की तत्काल पहचान'
    ],
    eligibility: 'All agricultural, commercial, industrial, and residential land title holders.',
    eligibilityHi: 'देश के समस्त कृषि, अकृषक, व्यावसायिक एवं आवासीय भूमिधारक।',
    flagshipInitiative: true,
    bannerCtaText: 'Verify 14-Digit ULPIN',
    circularRef: 'DoLR/DILRMP/ULPIN/2026-09'
  },
  {
    id: 'SCHEME-PMAYG',
    code: 'PMAY-G',
    name: 'Pradhan Mantri Awaas Yojana - Gramin (PMAY-G)',
    nameHi: 'प्रधानमंत्री आवास योजना - ग्रामीण — पक्के मकान की गारंटी',
    shortName: 'PMAY-Gramin',
    category: 'HOUSING_WATER',
    ministry: 'Ministry of Rural Development, Government of India',
    ministryHi: 'ग्रामीण विकास मंत्रालय, भारत सरकार',
    slogan: 'Har Parivar Ko Pakka Ghar — Dignity, Security & Prosperity',
    sloganHi: 'हर परिवार को पक्का घर — सम्मान, सुरक्षा और आत्मनिर्भरता',
    tagline: 'Financial Assistance of ₹1.20 Lakh to ₹1.30 Lakh + 90 Days MGNREGA Labor for Rural Housing',
    taglineHi: 'ग्रामीण परिवारों को पक्के घर निर्माण हेतु ₹१.२० से ₹१.३० लाख की प्रत्यक्ष आर्थिक सहायता',
    badge: 'HOUSING FOR ALL',
    theme: 'amber',
    impactMetric: '2.95+ Crore',
    impactLabel: 'Pucca Houses Sanctioned & Delivered',
    secondaryMetric: '100% DBT',
    secondaryLabel: 'Geo-Tagged Stage Payments through AwaasSoft',
    portalUrl: 'https://pmayg.nic.in',
    portalName: 'pmayg.nic.in',
    helpline: '1800-11-6446 (Toll Free)',
    description: 'Providing pucca houses with basic amenities (piped water, electricity, LPG) to all houseless households and those living in dilapidated houses in rural areas with direct geo-tagged bank transfer.',
    descriptionHi: 'ग्रामीण क्षेत्रों में कच्चे व जीर्ण-शीर्ण मकानों में रहने वाले सभी पात्र परिवारों को बुनियादी सुविधाओं (शौचालय, बिजली, एलपीजी एवं नल-जल) युक्त पक्का मकान उपलब्ध कराने का राष्ट्रीय अभियान।',
    keyBenefits: [
      'Direct DBT credit of ₹1,20,000 (Plains) / ₹1,30,000 (Hilly/NE/IAP districts) in 3 installments',
      'Additional 90-95 person-days of unskilled labor under MGNREGA (~₹25,000 cash)',
      '₹12,000 dedicated assistance for construction of household latrine under Swachh Bharat Mission',
      'Integration with BHUMISETU resettlement and rehabilitation (R&R) awards under First Schedule'
    ],
    keyBenefitsHi: [
      'मैदानी क्षेत्रों हेतु ₹१,२०,००० तथा दुर्गम/पहाड़ी क्षेत्रों हेतु ₹१,३०,००० की ३ किस्तों में सहायता',
      'मनरेगा के तहत ९०-९५ दिवस की अकुशल मजदूरी (लगभग ₹२५,०००) अतिरिक्त',
      'स्वच्छ भारत मिशन के तहत ₹१२,००० की पक्के शौचालय निर्माण सहायता',
      'भूमि अधिग्रहण पुनर्वास (R&R) के तहत विस्थापित परिवारों को प्राथमिकता आवंटन'
    ],
    eligibility: 'Socio-Economic Caste Census (SECC) deprivations and Awaas+ verified houseless families.',
    eligibilityHi: 'आवास प्लस सूची में सत्यापित ग्रामीण बेघर एवं कच्चे मकानों में निवास करने वाले परिवार।',
    flagshipInitiative: true,
    bannerCtaText: 'Check Awaas Beneficiary List',
    circularRef: 'MoRD/PMAY-G/2026/GUIDE-08'
  },
  {
    id: 'SCHEME-JJM',
    code: 'JAL-JEEVAN',
    name: 'Jal Jeevan Mission — Har Ghar Jal',
    nameHi: 'जल जीवन मिशन — हर घर नल से शुद्ध जल',
    shortName: 'Jal Jeevan Mission',
    category: 'HOUSING_WATER',
    ministry: 'Department of Drinking Water and Sanitation, Ministry of Jal Shakti, Govt. of India',
    ministryHi: 'पेयजल एवं स्वच्छता विभाग, जल शक्ति मंत्रालय, भारत सरकार',
    slogan: 'Har Ghar Jal, Har Ghar Khushhali — Clean Tap Water for Every Rural Household',
    sloganHi: 'हर घर नल से जल — स्वस्थ जीवन, समृद्ध भारत',
    tagline: '55 Litres per Capita per Day of Potable Drinking Water through Functional Household Tap Connections',
    taglineHi: 'प्रत्येक ग्रामीण परिवार को नियमित आधार पर प्रति व्यक्ति ५५ लीटर शुद्ध पेयजल की उपलब्धता',
    badge: 'HAR GHAR JAL',
    theme: 'blue',
    impactMetric: '15.2+ Crore',
    impactLabel: 'Rural Tap Water Connections Provided (78%+ Coverage)',
    secondaryMetric: '2.15+ Lakh',
    secondaryLabel: 'Har Ghar Jal Certified Gram Panchayats',
    portalUrl: 'https://ejalshakti.gov.in/jjmreport/',
    portalName: 'jaljeevanmission.gov.in',
    helpline: '1800-180-1551',
    description: 'A transformative national movement ensuring clean, safe and potable tap water connection to every rural household, primary school, Anganwadi centre, and community health facility across India.',
    descriptionHi: 'देश के प्रत्येक ग्रामीण घर, प्राथमिक विद्यालय एवं आंगनबाड़ी केंद्र में नल द्वारा पर्याप्त व सुरक्षित पेयजल की नियमित आपूर्ति सुनिश्चित करने वाला ऐतिहासिक मिशन।',
    keyBenefits: [
      'Standardized 55 litres per person per day of potable quality water meeting BIS 10500 standards',
      'Water quality monitoring with IoT digital sensors and 5 women trained in every village with Field Test Kits',
      'Free from fluoride, arsenic and chemical contamination in acquired and rehabilitated settlements',
      'RoW approvals fast-tracked via BHUMISETU for district pipeline easements'
    ],
    keyBenefitsHi: [
      'बीआईएस १०५०० मानकों के अनुरूप प्रति व्यक्ति प्रतिदिन ५५ लीटर शुद्ध व सुरक्षित पेयजल',
      'आईओटी सेंसर द्वारा रीयल-टाइम निगरानी व हर ग्राम की ५ महिलाओं को जल परीक्षण किट प्रशिक्षण',
      'फ्लोराइड, आर्सेनिक एवं रासायनिक अशुद्धियों से पूर्ण मुक्ति',
      'भूमिसेतु पोर्टल द्वारा पाइपलाइन गलियारों हेतु त्वरित भूमि अनापत्ति'
    ],
    eligibility: 'All rural households, schools, anganwadis, and community health centers.',
    eligibilityHi: 'देश के समस्त ग्रामीण परिवार, प्राथमिक विद्यालय, आंगनबाड़ी एवं सार्वजनिक स्वास्थ्य केंद्र।',
    flagshipInitiative: true,
    bannerCtaText: 'View JJM Dashboard',
    circularRef: 'MoJS/JJM/WATER/2026/CIRC-22'
  },
  {
    id: 'SCHEME-BHOOMIRASHI',
    code: 'BHOOMI-RASHI',
    name: 'Bhoomi Rashi Portal & Bharatmala Pariyojana',
    nameHi: 'भूमि राशि पोर्टल एवं भारतमाला परियोजना — पारदर्शी राजमार्ग भूसंपादन',
    shortName: 'Bhoomi Rashi',
    category: 'INFRASTRUCTURE',
    ministry: 'Ministry of Road Transport and Highways (MoRTH) & NHAI, Govt. of India',
    ministryHi: 'सड़क परिवहन एवं राजमार्ग मंत्रालय व एनएचएआई, भारत सरकार',
    slogan: 'World-Class Highway Corridors with Fair & Fast Compensation',
    sloganHi: 'विश्वस्तरीय एक्सप्रेसवे गलियारे — त्वरित एवं न्यायोचित मुआवजा',
    tagline: 'Digitized Land Acquisition Notifications & 100% Solatium Guarantee',
    taglineHi: 'ई-गजट अधिसूचनाएं एवं अधिनियम की धारा ३० तहत १००% सोलेशियम की गारंटी',
    badge: 'HIGHWAY ACQUISITION',
    theme: 'blue',
    impactMetric: '34,800 Km',
    impactLabel: 'Economic Highway Corridors & Expressways Built',
    secondaryMetric: '100% Solatium',
    secondaryLabel: 'Statutory 100% Equivalent Solatium Added to Award',
    portalUrl: 'https://bhoomirashi.gov.in',
    portalName: 'bhoomirashi.gov.in',
    helpline: '1033 (National Highway Helpline)',
    description: 'Bhoomi Rashi digitizes the entire land acquisition workflow for National Highways, expediting Gazette notifications under the NH Act and RFCTLARR 2013 with direct PFMS bank payouts to affected landowners.',
    descriptionHi: 'राष्ट्रीय राजमार्गों के भूसंपादन की संपूर्ण प्रक्रिया को डिजिटाइज़ कर ई-गजट प्रकाशन, समयबद्ध धारा १५ सुनवाई एवं पीएफएमएस द्वारा त्वरित मुआवजा भुगतान सुनिश्चित करने वाला पोर्टल।',
    keyBenefits: [
      'Gazette notification publishing time reduced from months to under 48 hours',
      'Mandated 100% Solatium plus 12% annual interest from Section 11 notice to award date',
      'Transparent compensation calculation matrix accessible to every affected citizen',
      'Integration with BHUMISETU for Cadastral GIS corridor overlap validation'
    ],
    keyBenefitsHi: [
      'राजपत्र (ई-गजट) अधिसूचना प्रकाशन की अवधि महीनों से घटकर मात्र ४८ घंटे',
      'धारा ३० के तहत १००% अनिवार्य सोलेशियम व अधिसूचना से अधिनिर्णय तक १२% वार्षिक ब्याज',
      'प्रत्येक नागरिक हेतु पारदर्शी मुआवजा गणना पत्रक की ऑनलाइन सुलभता',
      'भूखंडों के सटीक सीमांकन हेतु भूमिसेतु कैडस्ट्रल जीआईएस के साथ सीधा समन्वय'
    ],
    eligibility: 'All landowners whose parcels fall in notified National Highway Right-of-Way corridors.',
    eligibilityHi: 'वे सभी नागरिक जिनकी भूमि राष्ट्रीय राजमार्ग परियोजना के अधिसूचित क्षेत्र में आती है।',
    flagshipInitiative: false,
    bannerCtaText: 'Track Highway Notices',
    circularRef: 'MoRTH/BHOOMI-RASHI/2026/CORR-01'
  },
  {
    id: 'SCHEME-VIKSITBHARAT',
    code: 'VIKSIT-BHARAT',
    name: 'Viksit Bharat 2047 — Digital Governance & Citizen Rights Charter',
    nameHi: 'विकसित भारत २०४७ — डिजिटल सुशासन एवं नागरिक भू-अधिकार संकल्प',
    shortName: 'Viksit Bharat',
    category: 'DIGITAL_CITIZEN',
    ministry: 'NITI Aayog & MeitY, Government of India',
    ministryHi: 'नीति आयोग एवं इलेक्ट्रॉनिक्स व सूचना प्रौद्योगिकी मंत्रालय, भारत सरकार',
    slogan: 'Transparent Administration, Empowered Citizens, Developed India',
    sloganHi: 'पारदर्शी प्रशासन, सशक्त नागरिक, विकसित भारत संकल्प',
    tagline: 'Zero-Discretion Statutory Timeline Enforcement & Citizen First e-Governance',
    taglineHi: 'समयबद्ध वैधानिक निपटारा, शून्य भ्रष्टाचार एवं नागरिक-हितैषी ई-गवर्नेंस',
    badge: 'VISION 2047',
    theme: 'purple',
    impactMetric: '100% Digital',
    impactLabel: 'Paperless Section 15 Hearing Notices & Awards',
    secondaryMetric: '60-Day SLA',
    secondaryLabel: 'Strict Statutory Objection Disposal Guarantee',
    portalUrl: 'https://india.gov.in',
    portalName: 'india.gov.in',
    helpline: '1800-11-2047 (Toll Free)',
    description: 'The national mission towards transforming India into a developed nation by 2047 through transparent, citizen-centric digital governance, time-bound legal services, and absolute statutory fairness.',
    descriptionHi: 'वर्ष २०४७ तक भारत को पूर्ण विकसित राष्ट्र बनाने का राष्ट्रीय संकल्प, जहाँ प्रत्येक नागरिक को समयबद्ध न्याय, पारदर्शी डिजिटल सेवाएं एवं संपत्ति अधिकारों की पूर्ण सुरक्षा प्राप्त हो।',
    keyBenefits: [
      'Time-bound 60-day disposal of public objections under RFCTLARR Section 15',
      'Real-time SMS and DigiLocker delivery of statutory notices and PFMS DBT receipts',
      'AI early-warning engine detects statutory deadline breaches before legal lapsing occurs',
      'Comprehensive DPDP Act 2023 compliance safeguarding citizen biometric and land data'
    ],
    keyBenefitsHi: [
      'धारा १५ के तहत आपत्तियों का ६० दिवस में अनिवार्य समयबद्ध वैधानिक निराकरण',
      'डिजीलॉकर एवं एसएमएस द्वारा वैधानिक नोटिस व मुआवजा रसीदों की तत्काल डिलीवरी',
      'मुकदमेबाजी रोकने हेतु एआई अर्ली-वार्निंग तकनीक द्वारा समय-सीमा का स्वतः अनुश्रवण',
      'डीपीडीपी अधिनियम २०२३ के अनुसार नागरिकों के व्यक्तिगत व भू-अभिलेखों की पूर्ण सुरक्षा'
    ],
    eligibility: 'All Indian citizens, farmers, khatedars, and statutory stakeholders.',
    eligibilityHi: 'देश के समस्त नागरिक, कृषक, खातेदार एवं संबंधित हितधारक।',
    flagshipInitiative: true,
    bannerCtaText: 'Join Viksit Bharat Mission',
    circularRef: 'NITI/VB2047/CITIZEN-CHARTER'
  },
  {
    id: 'SCHEME-DIGILOCKER',
    code: 'DIGILOCKER',
    name: 'DigiLocker Land & Revenue Records (Digital India)',
    nameHi: 'डिजीलॉकर भू-अभिलेख — डिजिटल सशक्तिकरण एवं सुरक्षित दस्तावेज',
    shortName: 'DigiLocker Land',
    category: 'DIGITAL_CITIZEN',
    ministry: 'Ministry of Electronics & Information Technology (MeitY), Govt. of India',
    ministryHi: 'इलेक्ट्रॉनिक्स एवं सूचना प्रौद्योगिकी मंत्रालय, भारत सरकार',
    slogan: 'Meri Pehchan, Mera Digital Locker — Legally Valid Electronic Documents',
    sloganHi: 'मेरी पहचान, मेरा डिजीलॉकर — सुरक्षित, मान्य एवं कागज़रहित दस्तावेज़',
    tagline: 'Statutory 7/12 Extracts, Mutation Certificates & Land Acquisition Awards Stored Securely',
    taglineHi: '७/१२ उद्धरण, फेरफार एवं मुआवजा अधिनिर्णय की विधिमान्य डिजिटल प्रतियां',
    badge: 'PAPERLESS GOVERNANCE',
    theme: 'navy',
    impactMetric: '22.5+ Crore',
    impactLabel: 'Registered DigiLocker Citizens Across India',
    secondaryMetric: '6.7+ Billion',
    secondaryLabel: 'Legally Authentic Issued Documents in Vault',
    portalUrl: 'https://www.digilocker.gov.in',
    portalName: 'digilocker.gov.in',
    helpline: '1800-111-555',
    description: 'DigiLocker is a flagship initiative under Digital India aimed at empowering citizens electronically by providing authentic digital documents to citizen digital document wallets with legal validity under IT Act 2000.',
    descriptionHi: 'डिजिटल इंडिया के अंतर्गत नागरिकों को उनके भू-अभिलेख, खतौनी, ७/१२ एवं भूसंपादन मुआवजा प्रमाण पत्र सीधे उनके डिजिटल वॉल्ट में सुरक्षित और विधिमान्य रूप से उपलब्ध कराने वाली सेवा।',
    keyBenefits: [
      'Documents in DigiLocker are treated at par with original physical documents under Rule 9A of IT Rules 2016',
      'Instant access to digitally signed 7/12 extracts, Jamabandi, and mutation register extracts',
      'Automated receipt of Section 11/19 notifications and Section 23/30 DBT compensation awards',
      'Zero risk of losing physical paper deeds or fraudulent land records fabrication'
    ],
    keyBenefitsHi: [
      'आईटी नियम २०१६ के तहत डिजीलॉकर के दस्तावेज मूल भौतिक प्रमाण पत्रों के समतुल्य मान्य',
      'डिजिटल हस्ताक्षरित ७/१२, खतौनी व फेरफार प्रविष्टियों की तत्काल मोबाइल उपलब्धता',
      'धारा ११/१९ की अधिसूचनाएं एवं मुआवजा अधिनिर्णय सीधे डिजीलॉकर में स्वतः प्राप्त',
      'कागजी दस्तावेजों के खोने या जाली अभिलेख तैयार करने की संभावना शून्य'
    ],
    eligibility: 'All Indian citizens with an Aadhaar number and registered mobile.',
    eligibilityHi: 'आधार कार्ड धारक समस्त भारतीय नागरिक।',
    flagshipInitiative: false,
    bannerCtaText: 'Access DigiLocker Vault',
    circularRef: 'MeitY/DIGILOCKER/REV/2026'
  }
];

export const CAMPAIGN_TICKER_ITEMS = [
  {
    tag: 'SVAMITVA',
    tagHi: 'स्वामित्व',
    text: 'Drone survey completed in 3,15,000 villages — Download your Digital Property Card online on svamitva.nic.in',
    textHi: '३,१५,००० गाँवों में ड्रोन सर्वेक्षण पूर्ण — अपना डिजिटल प्रॉपर्टी कार्ड ऑनलाइन प्राप्त करें।',
    link: 'https://svamitva.nic.in'
  },
  {
    tag: 'PM-KISAN',
    tagHi: 'पीएम किसान',
    text: '17th Installment credited to 11.8 Crore farmers via PFMS DBT — Verify your e-KYC status now.',
    textHi: '११.८ करोड़ किसानों को १७वीं किस्त का अंतरण संपन्न — अपना ई-केवाईसी तुरंत सत्यापित करें।',
    link: 'https://pmkisan.gov.in'
  },
  {
    tag: 'BHU-AADHAAR',
    tagHi: 'भू-आधार',
    text: 'Link your 14-digit ULPIN with 7/12 land records for instant Aadhaar DBT compensation without delays.',
    textHi: 'त्वरित मुआवजा भुगतान हेतु अपने ७/१२ भू-अभिलेख को १४-अंकीय भू-आधार (ULPIN) से लिंक करें।',
    link: 'https://dilrmp.gov.in'
  },
  {
    tag: 'PMAY-G',
    tagHi: 'पीएम आवास',
    text: '2.95 Crore rural pucca houses delivered with piped water & electricity under PMAY-Gramin.',
    textHi: 'पीएम आवास ग्रामीण के तहत २.९५ करोड़ पक्के आवासों का निर्माण व गृह प्रवेश संपन्न।',
    link: 'https://pmayg.nic.in'
  },
  {
    tag: 'HAR GHAR JAL',
    tagHi: 'जल जीवन',
    text: 'Over 15.2 Crore rural households now connected with clean drinking tap water under Jal Jeevan Mission.',
    textHi: '१५.२ करोड़ से अधिक ग्रामीण परिवारों को नल से शुद्ध जल की आपूर्ति सुनिश्चित।',
    link: 'https://jaljeevanmission.gov.in'
  },
  {
    tag: 'RFCTLARR ACT',
    tagHi: 'अधिनियम २०१३',
    text: 'Mandatory 100% Solatium plus 12% statutory annual interest guaranteed for all notified land acquisitions.',
    textHi: 'अधिसूचित भूसंपादन पर १००% अनिवार्य सोलेशियम एवं १२% वार्षिक ब्याज की सांविधिक गारंटी।',
    link: '#notices'
  }
];
