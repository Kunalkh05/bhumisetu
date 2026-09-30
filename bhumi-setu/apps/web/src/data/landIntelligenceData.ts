/**
 * BHUMISETU - Unified AI-Powered Land Intelligence & Verification Platform
 * Central Demonstration & Knowledge Dataset
 * 
 * DISCLAIMER:
 * This dataset is for academic/prototype demonstration purposes only.
 * Fictional names, masked identifiers, and simulated cadastral references are used
 * in compliance with data privacy standards and do not represent legally binding records.
 */

export interface DemoProperty {
  id: string;
  ulpin: string;
  surveyNumber: string;
  subdivision: string;
  oldSurveyNumber: string;
  state: string;
  district: string;
  tehsil: string;
  village: string;
  areaHectares: number;
  areaAcres: number;
  areaSqMeters: number;
  landType: string;
  soilClassification: string;
  recordStatus: 'Digitized & Verified' | 'Mutation Pending' | 'Under Resurvey';
  lastUpdated: string;
  sourceDepartment: string;
  sourcePortal: string;
  sourcePortalUrl: string;
  cadastralSheetNo: string;
  khasraNo: string;
  khatauniNo: string;
  assessmentTaxAnnual: number;
  encumbranceStatus: 'Clear / No Mortgage' | 'Institutional Hypothecation' | 'Statutory Lien';
  panchayatWard: string;
  owners: {
    name: string;
    shareRatio: string;
    fatherName: string;
    holdingType: string;
    entryDate: string;
    mutationNumber: string;
  }[];
  registration: {
    registrationNumber: string;
    registrationDate: string;
    subRegistrarOffice: string;
    transactionType: string;
    stampDutyPaidINR: number;
    marketValueINR: number;
    considerationINR: number;
    status: string;
  };
  activeMutation: {
    applicationId: string;
    currentStage: string;
    currentStatus: 'In Progress' | 'Action Required' | 'Completed' | 'Pending';
    applicationDate: string;
    lastUpdate: string;
    applicant: string;
    purpose: string;
    revenueOfficer: string;
    remarks: string;
  };
}

export const SAMPLE_PROPERTY_DEMO: DemoProperty = {
  id: 'MH-NGP-00012345',
  ulpin: '27712049001234',
  surveyNumber: '123/4',
  subdivision: '4',
  oldSurveyNumber: '123 (Part)',
  state: 'Maharashtra',
  district: 'Nagpur',
  tehsil: 'Nagpur (Rural)',
  village: 'Demo Village (Besa-Ghogli)',
  areaHectares: 2.50,
  areaAcres: 6.18,
  areaSqMeters: 25000,
  landType: 'Agricultural (Jirayat / Seasonal Crop)',
  soilClassification: 'Medium Black Cotton (Kali Mitti - Grade II)',
  recordStatus: 'Digitized & Verified',
  lastUpdated: '29 September 2026',
  sourceDepartment: 'Revenue and Forest Department, Government of Maharashtra',
  sourcePortal: 'Mahabhulekh (Maharashtra Bhumi Abhilekh)',
  sourcePortalUrl: 'https://bhulekh.mahabhumi.gov.in',
  cadastralSheetNo: 'NGP-RUR-SHT-42',
  khasraNo: '123/4',
  khatauniNo: 'KH-8842',
  assessmentTaxAnnual: 420,
  encumbranceStatus: 'Clear / No Mortgage',
  panchayatWard: 'Gram Panchayat Besa Ward No. 3',
  owners: [
    {
      name: 'Rameshwar K. Sharma (Masked Demo)',
      shareRatio: '50% (1.25 Ha)',
      fatherName: 'Late Kisanrao Sharma',
      holdingType: 'Ancestral Co-parcener',
      entryDate: '14 March 2018',
      mutationNumber: 'MUT-892'
    },
    {
      name: 'Sunita R. Sharma (Masked Demo)',
      shareRatio: '25% (0.625 Ha)',
      fatherName: 'W/o Rameshwar Sharma',
      holdingType: 'Joint Holder',
      entryDate: '14 March 2018',
      mutationNumber: 'MUT-892'
    },
    {
      name: 'Devendra R. Sharma (Masked Demo)',
      shareRatio: '25% (0.625 Ha)',
      fatherName: 'S/o Rameshwar Sharma',
      holdingType: 'Co-owner / Legal Heir',
      entryDate: '10 June 2023',
      mutationNumber: 'MUT-1042'
    }
  ],
  registration: {
    registrationNumber: 'REG-NGP-2018-88492',
    registrationDate: '14 March 2018',
    subRegistrarOffice: 'Sub-Registrar Office Nagpur Rural - II',
    transactionType: 'Registered Partition & Settlement Deed',
    stampDutyPaidINR: 185000,
    marketValueINR: 4200000,
    considerationINR: 4200000,
    status: 'Duly Registered & Indexed (Index-II Certified)'
  },
  activeMutation: {
    applicationId: 'MUT-MH-2026-001245',
    currentStage: 'Revenue Officer Field Review & Public Notice under Sec 149',
    currentStatus: 'In Progress',
    applicationDate: '18 January 2026',
    lastUpdate: '15 February 2026',
    applicant: 'Devendra R. Sharma (Demo)',
    purpose: 'Partition Demarcation & Boundary Correction following SVAMITVA Resurvey',
    revenueOfficer: 'Circle Officer, Hingna-Nagpur Circle',
    remarks: 'Notice issued to contiguous survey boundary holders (Surveys 123/3 and 123/5). No objections received within 30-day statutory window. Final endorsement pending verification of GIS map polygon.'
  }
};

export interface RiskAnalysisCheck {
  id: string;
  category: string;
  title: string;
  titleHi: string;
  status: 'LOW DISCREPANCY' | 'MEDIUM DISCREPANCY' | 'HIGH DISCREPANCY';
  severityLevel: 'low' | 'medium' | 'high';
  issue: string;
  evidence: string;
  source: string;
  recommendedStep: string;
  recommendedStepHi: string;
}

export const PRELIMINARY_RISK_CHECKS: RiskAnalysisCheck[] = [
  {
    id: 'CHK-01',
    category: 'Ownership Identity',
    title: 'Owner Name Spelling & Aadhaar Concordance',
    titleHi: 'भूस्वामी नाम वर्तनी एवं आधार सामंजस्य',
    status: 'LOW DISCREPANCY',
    severityLevel: 'low',
    issue: 'Minor phonetic transliteration difference between Devanagari 7/12 extract and English Sale Deed index.',
    evidence: '7/12 reads "रामेश्वर किसनराव शर्मा" whereas registered deed shows "Rameshwar K. Sharma". All patronymics and co-sharer signatures match.',
    source: 'Mahabhulekh RoR vs SRO Registration Index-II',
    recommendedStep: 'Submit a self-declaration affidavit or obtain minor name rectification endorsement (Tadruk) during next mutation cycle.',
    recommendedStepHi: 'तलाठी कार्यालय में नाम वर्तनी सामंजस्य हेतु तदुक आवेदन प्रस्तुत करें।'
  },
  {
    id: 'CHK-02',
    category: 'Parcel Cadastre',
    title: 'Survey Number & Sub-division Hierarchy',
    titleHi: 'सर्वे/गट क्रमांक एवं उप-विभाग अनुक्रम',
    status: 'LOW DISCREPANCY',
    severityLevel: 'low',
    issue: 'No discrepancies detected. Survey number 123/4 corresponds to historic parental parcel 123 in village settlement record.',
    evidence: 'Revenue village map cadastral sheet NGP-RUR-SHT-42 correctly indexes 123/4 with clear boundary pegs.',
    source: 'State Directorate of Land Records & Settlement Office',
    recommendedStep: 'No action required. Boundary demarcation matches settlement record.',
    recommendedStepHi: 'कोई कार्रवाई आवश्यक नहीं। भू-नक्शा एवं अभिलेख सुसंगत हैं।'
  },
  {
    id: 'CHK-03',
    category: 'Spatial Geometry',
    title: 'Area Comparison (Sale Deed vs 7/12 vs GIS Polygon)',
    titleHi: 'क्षेत्रफल तुलना (दस्तावेज बनाम ७/१२ बनाम डिजिटल नक्शा)',
    status: 'MEDIUM DISCREPANCY',
    severityLevel: 'medium',
    issue: 'Marginal area variance (0.05 Ha / 2.0%) identified between Registered Deed (2.45 Ha) and Digital Cadastral Polygon (2.50 Ha).',
    evidence: 'Sale Deed specifies 2.45 Hectares whereas PostGIS computed polygon area from 2025 drone resurvey totals 2.50 Hectares (delta +500 sq.m along northern nullah boundary).',
    source: 'PostGIS GIS Engine vs SRO Registered Deed REG-2018-88492',
    recommendedStep: 'Order a joint physical measurement (Mojani) through Taluka Inspector of Land Records (TILR) to certify precise natural boundaries.',
    recommendedStepHi: 'तालुका भूमि अभिलेख निरीक्षक (TILR) से संयुक्त मोजणी कराकर सीमा स्पष्ट करें।'
  },
  {
    id: 'CHK-04',
    category: 'Bhu-Aadhaar Standard',
    title: 'ULPIN 14-Digit Geo-Coordinate Check',
    titleHi: '१४-अंकीय यूएलपीआईएन (भू-आधार) सत्यापन',
    status: 'LOW DISCREPANCY',
    severityLevel: 'low',
    issue: 'Valid 14-digit ULPIN generated based on longitudinal and latitudinal centroid standards under DILRMP.',
    evidence: 'ULPIN 27712049001234 resolves precisely to centroid coordinates: 21.0764° N, 79.0832° E.',
    source: 'National Bhu-Aadhaar Directory & Survey of India CORS Network',
    recommendedStep: 'Ensure ULPIN is printed on all prospective bank mortgages and revenue challans.',
    recommendedStepHi: 'भविष्य के सभी राजस्व दस्तावेजों एवं बैंक ऋणों में यूएलपीआईएन अंकित रखें।'
  },
  {
    id: 'CHK-05',
    category: 'Jurisdiction Concordance',
    title: 'Village, Tehsil & District Hierarchy',
    titleHi: 'ग्राम, तहसील एवं जिला क्षेत्राधिकार सामंजस्य',
    status: 'LOW DISCREPANCY',
    severityLevel: 'low',
    issue: 'Complete structural match across local governance bodies, sub-district revenue hierarchy, and Gram Panchayat.',
    evidence: 'State: 27 (MH), District: 712 (Nagpur), Tehsil: 049 (Nagpur Rural), Village Code: 534921 (LGD Code).',
    source: 'Local Government Directory (LGD) - Ministry of Panchayati Raj',
    recommendedStep: 'No action required. Jurisdictional codes match central directory.',
    recommendedStepHi: 'स्थानिक निकाय एवं राजस्व क्षेत्राधिकार पूर्णतः मेल खाते हैं।'
  },
  {
    id: 'CHK-06',
    category: 'Encumbrance & Liens',
    title: 'Sub-Registrar Encumbrance & Mortgage Status',
    titleHi: 'उप-पंजीयक भार/बंधक स्थिति (Encumbrance Certificate)',
    status: 'LOW DISCREPANCY',
    severityLevel: 'low',
    issue: 'No institutional mortgages, agricultural crop hypothecations, or judicial attachments recorded on Form 15.',
    evidence: '30-year search from 1996 to 2026 yielded nil adverse encumbrance entries at SRO Nagpur Rural - II.',
    source: 'IGR Maharashtra e-Search & CERSAI Portal',
    recommendedStep: 'Obtain an updated Form 16 (Nil Encumbrance Certificate) prior to entering any title transaction.',
    recommendedStepHi: 'किसी भी हस्तांतरण से पूर्व अद्यतन निरंक भार प्रमाणपत्र (Form 16) प्राप्त करें।'
  },
  {
    id: 'CHK-07',
    category: 'Workflow Integrity',
    title: 'Mutation Pipeline Continuity (Ferfar Patrak)',
    titleHi: 'नामांतरण निरंतरता एवं फेरफार पत्रिका प्रवाह',
    status: 'MEDIUM DISCREPANCY',
    severityLevel: 'medium',
    issue: 'Application MUT-MH-2026-001245 has been open for 42 days (standard Citizen Charter timeline is 30 days).',
    evidence: 'Application submitted on 18 Jan 2026; public notice issued 15 Feb 2026; pending final Talathi certification.',
    source: 'Maharashtra E-Ferfar Tracking System',
    recommendedStep: 'Follow up with Circle Officer / Talathi with reference to Sec 149 MLRC statutory compliance timeline.',
    recommendedStepHi: 'सर्कल अधिकारी से संपर्क कर महाराष्ट्र भूमि राजस्व संहिता धारा १४९ तहत प्रक्रिया पूर्ण कराएं।'
  },
  {
    id: 'CHK-08',
    category: 'Statutory Acquisition',
    title: 'RFCTLARR Act 2013 Gazette Overlay',
    titleHi: 'भूमि अधिग्रहण राजपत्र अधिसूचना मिलान',
    status: 'LOW DISCREPANCY',
    severityLevel: 'low',
    issue: 'Parcel is adjacent to Nagpur-Hyderabad Industrial Corridor alignment (Chainage 42+200) but falls outside statutory Right-of-Way (RoW).',
    evidence: 'Buffer distance from nearest Sec 11 preliminary notification alignment polygon is 185 meters.',
    source: 'BHUMISETU National Acquisition GIS Corridor Database',
    recommendedStep: 'Periodically monitor Section 11 & Section 19 notifications on BHUMISETU for corridor expansion updates.',
    recommendedStepHi: 'औद्योगिक गलियारे के समीप होने के कारण नए राजपत्र अधिसूचनाओं पर नजर रखें।'
  },
  {
    id: 'CHK-09',
    category: 'Title History',
    title: 'Chronological Chain of Title (1970 - 2026)',
    titleHi: 'ऐतिहासिक स्वामित्व श्रृंखला (१९७० - २०२६)',
    status: 'LOW DISCREPANCY',
    severityLevel: 'low',
    issue: 'Continuous historical chain of title verified through 4 succession mutations without broken links.',
    evidence: '1970 original settlement -> 1998 family partition -> 2018 registered deed -> 2023 legal heir partition.',
    source: 'Archived Revenue Bandobast Records & Record of Rights',
    recommendedStep: 'Maintain physical certified copies of all mutation notes (Ferfar 412, 892, 1042) for property archive.',
    recommendedStepHi: 'सभी ऐतिहासिक फेरफार प्रविष्टियों की प्रमाणित प्रतियां सुरक्षित रखें।'
  },
  {
    id: 'CHK-10',
    category: 'Cartographic Alignment',
    title: 'BhuNaksha Vector vs Drone Orthorectified Map',
    titleHi: 'भू-नक्शा वेक्टर बनाम ड्रोन ऑर्थोफोटो संरेखण',
    status: 'LOW DISCREPANCY',
    severityLevel: 'low',
    issue: 'Spatial overlap concordance is 98.4% between legacy settlement map and modern SVAMITVA drone imagery.',
    evidence: 'Survey boundaries exhibit less than 15 cm positional drift on North-East triangulation markers.',
    source: 'Survey of India Drone Orthorectified Tiles (2025)',
    recommendedStep: 'No action required. Cartographic alignment meets national cadastral standards.',
    recommendedStepHi: 'डिजिटल नक्शा एवं ड्रोन फोटो में ९८.४% संरेखण है।'
  },
  {
    id: 'CHK-11',
    category: 'Tenure & Restrictions',
    title: 'Class of Tenure & Tribal Land Restrictions',
    titleHi: 'भोगवटादार वर्ग एवं आदिवासी भूमि निर्बंधन',
    status: 'LOW DISCREPANCY',
    severityLevel: 'low',
    issue: 'Holding is classified as Occupant Class 1 (Bhogwatdar Varg 1) with unrestricted transferability.',
    evidence: 'No Section 36/36A tribal alienation restrictions or ceiling surplus tenures noted in other rights column.',
    source: '7/12 Extract Other Rights (Itar Hakka) Column',
    recommendedStep: 'Verify that any prospective agricultural-to-non-agricultural conversion follows standard Sec 44 process.',
    recommendedStepHi: 'भूमि भोगवटादार वर्ग १ है, जिस पर कोई विशेष कानूनी निर्बंधन नहीं है।'
  },
  {
    id: 'CHK-12',
    category: 'Public Infrastructure',
    title: 'Easementary Rights & Road Access Check',
    titleHi: 'सुखाधिकार एवं सार्वजनिक सड़क पहुंच मार्ग',
    status: 'LOW DISCREPANCY',
    severityLevel: 'low',
    issue: 'Dedicated 6-meter public access cart track (Vahiwat Rasta) recorded on the Southern parcel border.',
    evidence: 'Field inspection confirmed all-weather approach connecting to Major District Road (MDR-14).',
    source: 'Cadastral Village Map & Village Panchayat Asset Register',
    recommendedStep: 'Ensure cart track demarcation is preserved during boundary fencing.',
    recommendedStepHi: 'दक्षिण दिशा में ६ मीटर का सार्वजनिक रास्ता राजस्व अभिलेखों में दर्ज है।'
  }
];

export interface StatePortalInfo {
  stateName: string;
  stateCode: string;
  category: 'State' | 'Union Territory';
  capital: string;
  landRecordsPortal: string;
  landRecordsUrl: string;
  rorName: string;
  cadastralMapPortal: string;
  cadastralMapUrl: string;
  registrationPortal: string;
  registrationUrl: string;
  mutationPortal: string;
  departmentName: string;
  tollFree: string;
  digitizationStatus: string;
}

export const STATE_LAND_DIRECTORY: StatePortalInfo[] = [
  {
    stateName: 'Maharashtra',
    stateCode: 'MH',
    category: 'State',
    capital: 'Mumbai',
    landRecordsPortal: 'Mahabhulekh',
    landRecordsUrl: 'https://bhulekh.mahabhumi.gov.in',
    rorName: '7/12 Extract (Saat Bara) & 8-A',
    cadastralMapPortal: 'MahaBhuNaksha',
    cadastralMapUrl: 'https://mahabhunakasha.mahabhumi.gov.in',
    registrationPortal: 'IGR Maharashtra (e-Registration & e-Step-in)',
    registrationUrl: 'https://igrmaharashtra.gov.in',
    mutationPortal: 'E-Ferfar Digital Mutation Service',
    departmentName: 'Revenue & Forest Department',
    tollFree: '1800-120-8040',
    digitizationStatus: '99.8% Digitized with ULPIN Integration'
  },
  {
    stateName: 'Uttar Pradesh',
    stateCode: 'UP',
    category: 'State',
    capital: 'Lucknow',
    landRecordsPortal: 'Bhulekh UP',
    landRecordsUrl: 'https://upbhulekh.gov.in',
    rorName: 'Khatauni & Khasra Extract',
    cadastralMapPortal: 'UP BhuNaksha',
    cadastralMapUrl: 'https://upbhunaksha.gov.in',
    registrationPortal: 'IGRSUP (Stamp & Registration Dept)',
    registrationUrl: 'https://igrsup.gov.in',
    mutationPortal: 'UP Revenue Court Computerized System (RCCMS)',
    departmentName: 'Board of Revenue, Uttar Pradesh',
    tollFree: '0522-221714',
    digitizationStatus: '100% Digitized with 16-Digit Unique Code'
  },
  {
    stateName: 'Karnataka',
    stateCode: 'KA',
    category: 'State',
    capital: 'Bengaluru',
    landRecordsPortal: 'Bhoomi RTC Portal',
    landRecordsUrl: 'https://landrecords.karnataka.gov.in',
    rorName: 'RTC (Pahani / Form 16)',
    cadastralMapPortal: 'Dishaank & Karnataka BhuNaksha',
    cadastralMapUrl: 'https://revenueassam.nic.in/bhunaksha',
    registrationPortal: 'KAVERI 2.0 (Valuation & Registration)',
    registrationUrl: 'https://kaveri.karnataka.gov.in',
    mutationPortal: 'Bhoomi Mutation Online System',
    departmentName: 'Revenue Department, Govt. of Karnataka',
    tollFree: '080-22113251',
    digitizationStatus: '100% Integrated with Kaveri-Bhoomi Sync'
  },
  {
    stateName: 'Madhya Pradesh',
    stateCode: 'MP',
    category: 'State',
    capital: 'Bhopal',
    landRecordsPortal: 'MP Bhulekh',
    landRecordsUrl: 'https://mpbhulekh.gov.in',
    rorName: 'Khasra, Khatauni & Naksha Copy',
    cadastralMapPortal: 'MP BhuNaksha GIS Portal',
    cadastralMapUrl: 'https://mpbhulekh.gov.in/mpbhunaksha',
    registrationPortal: 'MPIGRS (Cyber Tehsildar & Sampada 2.0)',
    registrationUrl: 'https://mpigr.gov.in',
    mutationPortal: 'Cyber Tehsil Instant Mutation Service',
    departmentName: 'Revenue Department & Land Records HQ Gwalior',
    tollFree: '1800-233-1456',
    digitizationStatus: 'Real-time Cyber Tehsil Automated Mutation'
  },
  {
    stateName: 'Gujarat',
    stateCode: 'GJ',
    category: 'State',
    capital: 'Gandhinagar',
    landRecordsPortal: 'AnyRoR Anywhere Gujarat',
    landRecordsUrl: 'https://anyror.gujarat.gov.in',
    rorName: 'VF-7/12, VF-8A & VF-6 Hakrakh Patrak',
    cadastralMapPortal: 'Gujarat BhuNaksha GIS',
    cadastralMapUrl: 'https://anyror.gujarat.gov.in',
    registrationPortal: 'Garvi Gujarat (Inspector General of Registration)',
    registrationUrl: 'https://garvi.gujarat.gov.in',
    mutationPortal: 'e-Dhara Online Mutation Workflow',
    departmentName: 'Revenue Department, Government of Gujarat',
    tollFree: '1800-233-5500',
    digitizationStatus: 'Integrated e-Dhara and RoR Everywhere'
  },
  {
    stateName: 'Rajasthan',
    stateCode: 'RJ',
    category: 'State',
    capital: 'Jaipur',
    landRecordsPortal: 'Apna Khata (E-Dharti)',
    landRecordsUrl: 'https://apnakhata.rajasthan.gov.in',
    rorName: 'Jamabandi & Khasra Girdawari',
    cadastralMapPortal: 'BhuNaksha Rajasthan',
    cadastralMapUrl: 'https://bhunaksha.rajasthan.gov.in',
    registrationPortal: 'E-Panjiyan Rajasthan',
    registrationUrl: 'https://epanjiyan.nic.in',
    mutationPortal: 'Namantaran Online Revenue Portal',
    departmentName: 'Board of Revenue for Rajasthan, Ajmer',
    tollFree: '0145-2627719',
    digitizationStatus: 'Digitized with Digital Signatures'
  },
  {
    stateName: 'Tamil Nadu',
    stateCode: 'TN',
    category: 'State',
    capital: 'Chennai',
    landRecordsPortal: 'Anytime Anywhere e-Services (Patta Chitta)',
    landRecordsUrl: 'https://eservices.tn.gov.in',
    rorName: 'Patta Copy & Chitta Extract',
    cadastralMapPortal: 'CollabLand TN Cadastral FMB Maps',
    cadastralMapUrl: 'https://eservices.tn.gov.in/eservicesnew',
    registrationPortal: 'TNREGINET (Registration Department)',
    registrationUrl: 'https://tnreginet.gov.in',
    mutationPortal: 'Tamil Nilam Online Patta Transfer',
    departmentName: 'Survey and Settlement Department',
    tollFree: '1800-425-1333',
    digitizationStatus: 'Unified Tamil Nilam Land Registry'
  },
  {
    stateName: 'Telangana',
    stateCode: 'TG',
    category: 'State',
    capital: 'Hyderabad',
    landRecordsPortal: 'Dharani Integrated Land Records Management',
    landRecordsUrl: 'https://dharani.telangana.gov.in',
    rorName: 'Pattadar Passbook-cum-Title Deed',
    cadastralMapPortal: 'Dharani Cadastral Maps GIS',
    cadastralMapUrl: 'https://dharani.telangana.gov.in',
    registrationPortal: 'Dharani Slot Booking & Instant Registration',
    registrationUrl: 'https://dharani.telangana.gov.in',
    mutationPortal: 'Instant Combined Registration-cum-Mutation',
    departmentName: 'Revenue (Disaster Management) Department',
    tollFree: '1800-599-8288',
    digitizationStatus: 'Single-Window Instant Registry Mutation'
  },
  {
    stateName: 'Andhra Pradesh',
    stateCode: 'AP',
    category: 'State',
    capital: 'Amaravati',
    landRecordsPortal: 'Meebhoomi',
    landRecordsUrl: 'https://meebhoomi.ap.gov.in',
    rorName: 'Adangal (Pahani) & 1-B Record of Rights',
    cadastralMapPortal: 'BhuNaksha AP & Village FMBs',
    cadastralMapUrl: 'https://meebhoomi.ap.gov.in',
    registrationPortal: 'CARD (Registration & Stamps Department)',
    registrationUrl: 'https://registration.ap.gov.in',
    mutationPortal: 'Webland Integrated Mutation',
    departmentName: 'Revenue Department (Survey & Land Records)',
    tollFree: '1800-425-4440',
    digitizationStatus: 'YSR Jagananna Saswatha Bhu Hakku Resurvey'
  },
  {
    stateName: 'Odisha',
    stateCode: 'OD',
    category: 'State',
    capital: 'Bhubaneswar',
    landRecordsPortal: 'Bhulekh Odisha',
    landRecordsUrl: 'https://bhulekh.ori.nic.in',
    rorName: 'Khatian & RoR Web Copy',
    cadastralMapPortal: 'Bhunaksha Odisha',
    cadastralMapUrl: 'https://bhunakshaodisha.nic.in',
    registrationPortal: 'e-Registration Odisha (IGR)',
    registrationUrl: 'https://igrodisha.gov.in',
    mutationPortal: 'e-Mutation Tahsil Workflow',
    departmentName: 'Revenue & Disaster Management Department',
    tollFree: '1800-345-6770',
    digitizationStatus: '100% High-Accuracy Cadastral Records'
  },
  {
    stateName: 'Bihar',
    stateCode: 'BR',
    category: 'State',
    capital: 'Patna',
    landRecordsPortal: 'Biharbhumi Portal',
    landRecordsUrl: 'https://biharbhumi.bihar.gov.in',
    rorName: 'Jamabandi Panji-II & Dakhil Kharij',
    cadastralMapPortal: 'BhuNaksha Bihar GIS',
    cadastralMapUrl: 'https://bhunaksha.bihar.gov.in',
    registrationPortal: 'e-Nibandhan Bihar',
    registrationUrl: 'https://enibandhan.bihar.gov.in',
    mutationPortal: 'Dakhil Kharij Online Application',
    departmentName: 'Department of Revenue & Land Reforms',
    tollFree: '1800-345-6215',
    digitizationStatus: 'Special Land Survey & Settlement Active'
  },
  {
    stateName: 'West Bengal',
    stateCode: 'WB',
    category: 'State',
    capital: 'Kolkata',
    landRecordsPortal: 'BanglarBhumi',
    landRecordsUrl: 'https://banglarbhumi.gov.in',
    rorName: 'Khatian & Plot Information (RoR)',
    cadastralMapPortal: 'BanglarBhumi Mouza Map GIS',
    cadastralMapUrl: 'https://banglarbhumi.gov.in',
    registrationPortal: 'e-Nathikaran West Bengal',
    registrationUrl: 'https://wbregistration.gov.in',
    mutationPortal: 'Mutation Online Application (e-Bhumi)',
    departmentName: 'Land & Land Reforms and Refugee Relief Dept',
    tollFree: '1800-345-6600',
    digitizationStatus: 'Digitized Mouza Maps and Integrated Mutation'
  },
  {
    stateName: 'Punjab',
    stateCode: 'PB',
    category: 'State',
    capital: 'Chandigarh',
    landRecordsPortal: 'PLRS (Punjab Land Records Society)',
    landRecordsUrl: 'https://plrs.org.in',
    rorName: 'Fard Jamabandi',
    cadastralMapPortal: 'Punjab BhuNaksha',
    cadastralMapUrl: 'https://plrs.org.in',
    registrationPortal: 'NGDRS Punjab (National Generic Document Registration)',
    registrationUrl: 'https://igr.punjab.gov.in',
    mutationPortal: 'Intqal (Mutation) Verification Module',
    departmentName: 'Department of Revenue, Rehabilitation & Disaster Management',
    tollFree: '1800-180-2468',
    digitizationStatus: 'NGDRS Unified Digital Registration'
  },
  {
    stateName: 'Haryana',
    stateCode: 'HR',
    category: 'State',
    capital: 'Chandigarh',
    landRecordsPortal: 'Jamabandi Haryana',
    landRecordsUrl: 'https://jamabandi.nic.in',
    rorName: 'Nakal Jamabandi & Khasra Girdawari',
    cadastralMapPortal: 'Cadastral Maps Haryana',
    cadastralMapUrl: 'https://jamabandi.nic.in',
    registrationPortal: 'Web-HALRIS Online Deed Registration',
    registrationUrl: 'https://jamabandi.nic.in',
    mutationPortal: 'Automatic Mutation on Registry (HALRIS)',
    departmentName: 'Revenue and Disaster Management Department',
    tollFree: '1800-180-2117',
    digitizationStatus: 'Integrated HALRIS Automatic Intqal'
  },
  {
    stateName: 'Kerala',
    stateCode: 'KL',
    category: 'State',
    capital: 'Thiruvananthapuram',
    landRecordsPortal: 'E-Rekha Kerala',
    landRecordsUrl: 'https://erekha.kerala.gov.in',
    rorName: 'Thandaper & Field Measurement Book (FMB)',
    cadastralMapPortal: 'BhuNaksha Kerala',
    cadastralMapUrl: 'https://erekha.kerala.gov.in',
    registrationPortal: 'PEARL (Registration Department)',
    registrationUrl: 'https://keralaregistration.gov.in',
    mutationPortal: 'RELIS (Revenue Land Information System) Pokkuvaravu',
    departmentName: 'Survey and Land Records Department',
    tollFree: '1800-425-4933',
    digitizationStatus: 'Digital Resurvey (Ente Bhoomi) Active'
  },
  {
    stateName: 'Delhi (NCT)',
    stateCode: 'DL',
    category: 'Union Territory',
    capital: 'New Delhi',
    landRecordsPortal: 'Delhi Bhulekh / DLRC Portal',
    landRecordsUrl: 'https://dlrc.delhigovt.nic.in',
    rorName: 'Khasra Girdawari & Khatoni',
    cadastralMapPortal: 'Official link not configured',
    cadastralMapUrl: '',
    registrationPortal: 'DORIS (Delhi Online Registration Information System)',
    registrationUrl: 'https://esearch.delhigovt.nic.in',
    mutationPortal: 'e-District Delhi Revenue Mutation',
    departmentName: 'Revenue Department, GNCT of Delhi',
    tollFree: '1077 (Central Helpdesk)',
    digitizationStatus: 'Urban-Rural Hybrid Digital Records'
  }
];

export interface ChronologicalEvent {
  year: string;
  date: string;
  title: string;
  titleHi: string;
  category: 'Registration' | 'Mutation' | 'Survey' | 'Tax' | 'Active';
  source: string;
  status: 'Completed' | 'In Progress' | 'Certified';
  description: string;
  referenceId: string;
}

export const PROPERTY_TIMELINE_SAMPLE: ChronologicalEvent[] = [
  {
    year: '2018',
    date: '14 March 2018',
    title: 'Registered Partition & Settlement Deed',
    titleHi: 'पंजीकृत पारिवारिक विभाजन एवं समझौता विलेख',
    category: 'Registration',
    source: 'Sub-Registrar Office Nagpur Rural - II',
    status: 'Completed',
    description: 'Registered formal partition deed distributing ancestral parcel 123 among co-sharers. Stamp duty of ₹1,85,000 paid. Index-II issued.',
    referenceId: 'REG-NGP-2018-88492'
  },
  {
    year: '2020',
    date: '10 October 2020',
    title: 'Mutation Application under MLRC Section 149',
    titleHi: 'महाराष्ट्र भूमि राजस्व संहिता धारा १४९ तहत नामांतरण आवेदन',
    category: 'Mutation',
    source: 'Talathi Office, Besa Saja, Nagpur Rural',
    status: 'Completed',
    description: 'Talathi recorded entry in Register of Mutations (Ferfar Patrak No. 892) following registered deed execution.',
    referenceId: 'FERFAR-892'
  },
  {
    year: '2021',
    date: '15 January 2021',
    title: 'Mutation Approval & 7/12 Digital Certification',
    titleHi: 'नामांतरण प्रमाणन एवं डिजिटल ७/१२ निर्गमन',
    category: 'Mutation',
    source: 'Circle Officer, Hingna-Nagpur Circle',
    status: 'Certified',
    description: 'Statutory 30-day notice completed without boundary disputes. Circle Officer certified Ferfar 892. Digitally signed 7/12 extract generated.',
    referenceId: 'CERT-CO-2021-049'
  },
  {
    year: '2023',
    date: '10 June 2023',
    title: 'Ownership Partition Entry of Legal Heir',
    titleHi: 'कानूनी वारिस सह-स्वामित्व प्रविष्टि',
    category: 'Mutation',
    source: 'E-Ferfar Digital Revenue Portal',
    status: 'Completed',
    description: 'Added Devendra R. Sharma as co-sharer (25% undivided share) in ancestral agricultural holding. Ferfar entry 1042 certified.',
    referenceId: 'FERFAR-1042'
  },
  {
    year: '2025',
    date: '22 August 2025',
    title: 'SVAMITVA Drone Resurvey & High-Res Cadastral Polygonization',
    titleHi: 'स्वामित्व ड्रोन पुनर्सर्वेक्षण एवं डिजिटल भू-नक्शा निर्माण',
    category: 'Survey',
    source: 'Survey of India & Department of Land Records',
    status: 'Completed',
    description: '5-centimeter drone orthorectified imagery mapped boundary pegs. Computed parcel area: 2.50 Hectares. 14-digit ULPIN 27712049001234 assigned.',
    referenceId: 'SVAMITVA-SHT-42'
  },
  {
    year: '2026',
    date: '18 January 2026',
    title: 'Current Mutation Notice & Demarcation Review',
    titleHi: 'वर्तमान नामांतरण सूचना एवं सीमा समीक्षा',
    category: 'Active',
    source: 'Revenue Court & Circle Office',
    status: 'In Progress',
    description: 'Application for boundary demarcation endorsement following drone survey. Statutory public notice published under Sec 149.',
    referenceId: 'MUT-MH-2026-001245'
  }
];

export interface MutationStep {
  stepNumber: number;
  title: string;
  titleHi: string;
  status: 'Completed' | 'In Progress' | 'Pending' | 'Action Required';
  date: string;
  responsibleOfficer: string;
  details: string;
}

export const MUTATION_TRACKING_SAMPLE: {
  applicationId: string;
  propertyId: string;
  ulpin: string;
  steps: MutationStep[];
} = {
  applicationId: 'MUT-MH-2026-001245',
  propertyId: 'MH-NGP-00012345',
  ulpin: '27712049001234',
  steps: [
    {
      stepNumber: 1,
      title: 'Application Submission & Token Generation',
      titleHi: 'ऑनलाइन आवेदन प्रस्तुति एवं टोकन जनरेशन',
      status: 'Completed',
      date: '18 Jan 2026 • 11:24 AM',
      responsibleOfficer: 'Citizen Portal / Maha E-Seva Kendra',
      details: 'Application submitted with supporting registered sale deed and current 7/12 extract. Acknowledgment token MUT-MH-2026-001245 generated.'
    },
    {
      stepNumber: 2,
      title: 'Talathi Scrutiny & Ferfar Diary Entry',
      titleHi: 'तलाठी संवीक्षा एवं कच्ची फेरफार नोंद',
      status: 'Completed',
      date: '25 Jan 2026 • 03:40 PM',
      responsibleOfficer: 'Talathi, Besa Saja, Nagpur Rural',
      details: 'Talathi inspected title documents and entered provisional Ferfar note in village mutation diary. No prima facie document deficiency.'
    },
    {
      stepNumber: 3,
      title: 'Statutory Notice under MLRC Section 149',
      titleHi: 'धारा १४९ के अधीन १५-दिवसीय सार्वजनिक सूचना',
      status: 'Completed',
      date: '02 Feb 2026 • 10:15 AM',
      responsibleOfficer: 'Circle Officer, Hingna-Nagpur Circle',
      details: 'Statutory 15-day notice published on Gram Panchayat notice board and served to adjacent survey holders (123/3, 123/5). No objections filed.'
    },
    {
      stepNumber: 4,
      title: 'Revenue Officer Field Verification & Hearing',
      titleHi: 'राजस्व अधिकारी स्थल निरीक्षण एवं सुनवाई',
      status: 'In Progress',
      date: '15 Feb 2026 • 02:00 PM',
      responsibleOfficer: 'Circle Officer & Naib Tehsildar',
      details: 'Field report received confirming peaceful physical possession. Circle officer reviewing marginal 0.05 Ha spatial polygon delta with TILR surveyor.'
    },
    {
      stepNumber: 5,
      title: 'Final Mutation Certification & RoR 7/12 Update',
      titleHi: 'अंतिम फेरफार प्रमाणन एवं नवीन ७/१२ निर्गमन',
      status: 'Pending',
      date: 'Expected: 15 Oct 2026',
      responsibleOfficer: 'Tehsildar & Sub-Divisional Officer (SDO)',
      details: 'Pending final digital signature endorsement. Upon approval, new digitally signed 7/12 and 8-A extracts will be available on Mahabhulekh.'
    }
  ]
};

export interface ExtractedDocumentData {
  documentType: string;
  sourceFile: string;
  confidenceScore: number;
  extractedFields: {
    label: string;
    value: string;
    status: 'Matched' | 'Discrepancy' | 'Verified';
  }[];
  discrepancies: {
    field: string;
    valueInDoc: string;
    valueInRegistry: string;
    severity: 'LOW' | 'MEDIUM' | 'HIGH';
    comment: string;
  }[];
}

export const SAMPLE_EXTRACTED_DOCUMENTS: Record<string, ExtractedDocumentData> = {
  '7_12_EXTRACT': {
    documentType: 'Maharashtra Record of Rights (7/12 Extract)',
    sourceFile: 'sample_7_12_extract_besa_123_4.pdf',
    confidenceScore: 98.7,
    extractedFields: [
      { label: 'State', value: 'Maharashtra', status: 'Matched' },
      { label: 'District', value: 'Nagpur', status: 'Matched' },
      { label: 'Taluka', value: 'Nagpur (Rural)', status: 'Matched' },
      { label: 'Village', value: 'Demo Village (Besa)', status: 'Matched' },
      { label: 'Survey / Gat No.', value: '123/4', status: 'Matched' },
      { label: 'Recorded Area', value: '2.50 Hectares', status: 'Discrepancy' },
      { label: 'Recorded Owner', value: 'Rameshwar K. Sharma & 2 others', status: 'Matched' },
      { label: 'Land Tenure', value: 'Bhogwatdar Varg 1 (Freehold)', status: 'Matched' },
      { label: 'Assessment Tax', value: '₹420.00 / year', status: 'Verified' },
      { label: 'Active Mutation Note', value: 'Ferfar 1042 / Pending Notice 1245', status: 'Verified' },
      { label: 'Other Rights (Itar Hakka)', value: 'Nil Encumbrance / No Bank Charge', status: 'Verified' }
    ],
    discrepancies: [
      {
        field: 'Area Discrepancy',
        valueInDoc: '2.50 Hectares (in 7/12 Extract)',
        valueInRegistry: '2.45 Hectares (in 2018 Sale Deed)',
        severity: 'MEDIUM',
        comment: 'Variance of 0.05 Ha between historic sale deed and 2025 drone orthorectified survey. Verification recommended via TILR mojani.'
      }
    ]
  },
  'SALE_DEED': {
    documentType: 'Registered Sale / Partition Deed (Index-II)',
    sourceFile: 'registered_sale_deed_nagpur_2018.pdf',
    confidenceScore: 96.4,
    extractedFields: [
      { label: 'Registration No.', value: 'REG-NGP-2018-88492', status: 'Matched' },
      { label: 'Registration Date', value: '14 March 2018', status: 'Matched' },
      { label: 'SRO Office', value: 'Sub-Registrar Nagpur Rural - II', status: 'Matched' },
      { label: 'Purchaser / Beneficiary', value: 'Rameshwar K. Sharma', status: 'Matched' },
      { label: 'Transferred Area', value: '2.45 Hectares', status: 'Discrepancy' },
      { label: 'Stamp Duty Paid', value: '₹1,85,000', status: 'Verified' },
      { label: 'Market Valuation', value: '₹42,00,000', status: 'Verified' },
      { label: 'Encumbrance Certificate', value: 'Form 15 Attached (Nil Encumbrance)', status: 'Verified' }
    ],
    discrepancies: [
      {
        field: 'Transliteration in Owner Name',
        valueInDoc: 'Rameshwar K. Sharma',
        valueInRegistry: 'रामेश्वर किसनराव शर्मा (7/12)',
        severity: 'LOW',
        comment: 'Phonetic English abbreviation vs Devanagari full name. Non-critical; standard identity affidavit acceptable.'
      }
    ]
  }
};
