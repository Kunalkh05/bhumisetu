import { 
  HistoricalCadastralParcel, 
  EncroachmentDetectionRecord, 
  HistoricalSurveyMetadata 
} from '../types/cadastralHistory';

export const HISTORICAL_SURVEY_METADATA: HistoricalSurveyMetadata = {
  surveyYear: 1974,
  surveyTitle: '1974 Revision Cadastral Settlement & Village Boundary Survey',
  surveyTitleHi: '१९७४ सुधारित जमाबंदी भूमापन व ग्राम सीमा अभिलेख',
  surveyAgency: 'Office of the Settlement Commissioner and Director of Land Records, Maharashtra',
  surveyAgencyHi: 'जमाबंदी आयुक्त आणि भूमि अभिलेख संचालक कार्यालय, महाराष्ट्र शासन',
  sheetNumber: 'Settlement Cadastral Sheet No. 14 / Haveli Sub-Division',
  tehsil: 'Haveli',
  district: 'Pune',
  geodeticDatum: 'Everest 1956 (Transformed to WGS 84 / UTM Zone 43N)',
  digitizationStandard: 'DILRMP Stage-II Cadastral GIS Vector Modernization (Scale 1:2,500)',
  totalParcelsAudited: 12,
  encroachmentsFoundCount: 4,
  totalEncroachedAreaSqM: 1133
};

/**
 * Historical Cadastral Parcels digitized from 1974 settlement village maps
 */
export const HISTORICAL_CADASTRAL_PARCELS: HistoricalCadastralParcel[] = [
  {
    id: 'HIST-142A',
    currentParcelId: 'PCL-142A',
    surveyNumber1974: 'Old Survey No. 84, Hissa 2/A',
    surveyNumber1974Hi: 'जुना सर्व्हे क्र. ८४, हिस्सा २/अ',
    currentSurveyNumber: 'Gat No. 142/A',
    village: 'Shindewadi',
    sheetNumber: 'Sheet No. 14-B',
    surveyYear: 1974,
    extent1974Ha: 2.03,
    extent1974Gunthas: 81.2,
    coordinates1974: [
      [18.3840, 73.8905],
      [18.3857, 73.8910],
      [18.3866, 73.8938],
      [18.3848, 73.8935],
      [18.3840, 73.8905]
    ],
    landClass1974: 'Jirayat Class-II (Rainfed Agriculture)',
    archivalSource: 'Jamabandi Settlement Register Vol. IV, Page 112 (Record Room, Pune Collectorate)',
    boundaryStones: [
      {
        id: 'BS-142A-1',
        stoneNumber: 1,
        label: 'South-West Seema Chinha (Triangulation Pillar)',
        labelHi: 'दक्षिण-पश्चिम सीमा चिन्ह',
        originalPosition: [18.3840, 73.8905],
        currentStatus: 'VERIFIED_INTACT',
        notes: 'Original carved stone boundary pillar intact and undisturbed.'
      },
      {
        id: 'BS-142A-2',
        stoneNumber: 2,
        label: 'North-West Highway Margin Marker',
        labelHi: 'उत्तर-पश्चिम महामार्ग आरक्षण सीमा दगड',
        originalPosition: [18.3857, 73.8910],
        currentStatus: 'DISPLACED',
        displacementMeters: 4.8,
        notes: 'Pillar shifted 4.8m northwards into PWD highway reservation.'
      },
      {
        id: 'BS-142A-3',
        stoneNumber: 3,
        label: 'North-East RoW Boundary Pillar',
        labelHi: 'उत्तर-पूर्व आरक्षण सीमा स्तंभ',
        originalPosition: [18.3866, 73.8938],
        currentStatus: 'MISSING_DESTROYED',
        notes: 'Boundary marker removed during unauthorized compound wall construction.'
      },
      {
        id: 'BS-142A-4',
        stoneNumber: 4,
        label: 'South-East Village Cart Track Junction',
        labelHi: 'दक्षिण-पूर्व शिवार रस्ता जंक्शन',
        originalPosition: [18.3848, 73.8935],
        currentStatus: 'VERIFIED_INTACT',
        notes: 'Chiseled stone benchmark verified against 1974 Tippan sheet.'
      }
    ]
  },
  {
    id: 'HIST-142B',
    currentParcelId: 'PCL-142B',
    surveyNumber1974: 'Old Survey No. 84, Hissa 2/B',
    surveyNumber1974Hi: 'जुना सर्व्हे क्र. ८४, हिस्सा २/ब',
    currentSurveyNumber: 'Gat No. 142/B',
    village: 'Shindewadi',
    sheetNumber: 'Sheet No. 14-B',
    surveyYear: 1974,
    extent1974Ha: 1.51,
    extent1974Gunthas: 60.4,
    coordinates1974: [
      [18.3865, 73.8940],
      [18.3890, 73.8948],
      [18.3882, 73.8963],
      [18.3861, 73.8956],
      [18.3865, 73.8940]
    ],
    landClass1974: 'Bagayat (Canal Irrigated Farmland)',
    archivalSource: 'Jamabandi Settlement Register Vol. IV, Page 114',
    boundaryStones: [
      {
        id: 'BS-142B-1',
        stoneNumber: 1,
        label: 'West Boundary Common Pillar with 142/A',
        labelHi: 'पश्चिम सामाईक सीमा दगड',
        originalPosition: [18.3865, 73.8940],
        currentStatus: 'VERIFIED_INTACT',
        notes: 'Common demarcation verified with 1974 cadastral map.'
      },
      {
        id: 'BS-142B-2',
        stoneNumber: 2,
        label: 'East Gairan Boundary Marker',
        labelHi: 'पूर्व गायरान सरकारी जमीन सीमा दगड',
        originalPosition: [18.3882, 73.8963],
        currentStatus: 'DISPLACED',
        displacementMeters: 3.5,
        notes: 'Pushed eastward into government grazing land during orchard fencing.'
      }
    ]
  },
  {
    id: 'HIST-143',
    currentParcelId: 'PCL-143',
    surveyNumber1974: 'Old Survey No. 85, Hissa 1',
    surveyNumber1974Hi: 'जुना सर्व्हे क्र. ८५, हिस्सा १',
    currentSurveyNumber: 'Gat No. 143',
    village: 'Shindewadi',
    sheetNumber: 'Sheet No. 14-C',
    surveyYear: 1974,
    extent1974Ha: 0.93,
    extent1974Gunthas: 37.2,
    coordinates1974: [
      [18.3820, 73.8955],
      [18.3842, 73.8960],
      [18.3832, 73.8979],
      [18.3816, 73.8973],
      [18.3820, 73.8955]
    ],
    landClass1974: 'Jirayat Class-I',
    archivalSource: 'Jamabandi Settlement Register Vol. IV, Page 120',
    boundaryStones: [
      {
        id: 'BS-143-1',
        stoneNumber: 1,
        label: 'Natural Nala Buffer Demarcation Post',
        labelHi: 'नैसर्गिक ओढा बफर सीमा दगड',
        originalPosition: [18.3832, 73.8979],
        currentStatus: 'MISSING_DESTROYED',
        notes: 'Pillar destroyed during commercial landfilling of drainage stream.'
      }
    ]
  },
  {
    id: 'HIST-144',
    currentParcelId: 'PCL-144',
    surveyNumber1974: 'Old Survey No. 86, Hissa 3',
    surveyNumber1974Hi: 'जुना सर्व्हे क्र. ८६, हिस्सा ३',
    currentSurveyNumber: 'Gat No. 144/3',
    village: 'Shindewadi',
    sheetNumber: 'Sheet No. 14-C',
    surveyYear: 1974,
    extent1974Ha: 1.23,
    extent1974Gunthas: 49.2,
    coordinates1974: [
      [18.3885, 73.8970],
      [18.3908, 73.8981],
      [18.3903, 73.8999],
      [18.3881, 73.8990],
      [18.3885, 73.8970]
    ],
    landClass1974: 'Jirayat Class-II',
    archivalSource: 'Jamabandi Settlement Register Vol. IV, Page 128',
    boundaryStones: [
      {
        id: 'BS-144-1',
        stoneNumber: 1,
        label: 'North-East Agricultural Bund Marker',
        labelHi: 'उत्तर-पूर्व शेत बांध खूण',
        originalPosition: [18.3903, 73.8999],
        currentStatus: 'DISPLACED',
        displacementMeters: 1.8,
        notes: 'Shifted slightly across old field bund due to mechanized tilling.'
      }
    ]
  }
];

/**
 * Detailed Encroachment Pattern Detections (Current 2024 vs 1974 Survey)
 */
export const ENCROACHMENT_RECORDS: EncroachmentDetectionRecord[] = [
  {
    id: 'ENC-142A',
    parcelId: 'PCL-142A',
    currentSurveyNumber: 'Gat No. 142/A',
    historicalSurveyNumber1974: 'Old Survey No. 84, Hissa 2/A',
    village: 'Shindewadi',
    hasEncroachment: true,
    severity: 'CRITICAL',
    encroachmentAreaSqM: 418,
    encroachmentAreaHa: 0.0418,
    expansionPercentage: 20.69,
    encroachedLandType: 'PWD_ROW_RESERVE',
    encroachedLandTypeLabel: 'PWD Highway Right-of-Way Reserve',
    encroachedLandTypeLabelHi: 'सार्वजनिक बांधकाम महामार्ग आरक्षण क्षेत्र',
    encroachmentPolygon: [
      [18.3857, 73.8910],
      [18.3865, 73.8912],
      [18.3872, 73.8940],
      [18.3866, 73.8938],
      [18.3857, 73.8910]
    ],
    historicalGeom1974: [
      [18.3840, 73.8905],
      [18.3857, 73.8910],
      [18.3866, 73.8938],
      [18.3848, 73.8935],
      [18.3840, 73.8905]
    ],
    currentGeom2024: [
      [18.3840, 73.8905],
      [18.3865, 73.8912],
      [18.3872, 73.8940],
      [18.3848, 73.8935],
      [18.3840, 73.8905]
    ],
    displacedStonesCount: 2,
    statutoryViolation: 'MLRC 1966 Section 53 & RFCTLARR Act 2013 Section 11(4) - Unauthorized Expansion into Statutory Highway Corridor',
    description: 'Current northern boundary extends 418 m² beyond the 1974 surveyed boundary, encroaching directly into the designated 60m NH-48 statutory acquisition corridor. Semi-permanent tin godown structure situated on encroached land.',
    descriptionHi: 'सद्य उत्तर सीमा १९७४ च्या मूळ भूमापनापेक्षा ४१८ चौ.मी. पुढे जाऊन राष्ट्रीय महामार्गाच्या ६० मी. वैधानिक भूसंपादन क्षेत्रात अतिक्रमित झाली आहे. या जागेवर पत्र्याचे अनधिकृत शेड बांधण्यात आले आहे.',
    solatiumDeductionEstInr: 1485000, // ₹14.85 Lakhs ineligible compensation savings
    recommendedAction: 'Issue statutory eviction & solatium exclusion notice under Section 15; recalculate award to exclude 418 m² encroached PWD land.',
    recommendedActionHi: 'धारा १५ अंतर्गत अतिक्रमण निष्कासन नोटीस बजावून ४१८ चौ.मी. क्षेत्र नुकसानभरपाई व सोलेशियममधून वगळण्यात यावे.',
    fieldInspectionStatus: 'SURVEYOR_FLAGGED',
    detectedDate: '2026-09-15'
  },
  {
    id: 'ENC-142B',
    parcelId: 'PCL-142B',
    currentSurveyNumber: 'Gat No. 142/B',
    historicalSurveyNumber1974: 'Old Survey No. 84, Hissa 2/B',
    village: 'Shindewadi',
    hasEncroachment: true,
    severity: 'HIGH',
    encroachmentAreaSqM: 285,
    encroachmentAreaHa: 0.0285,
    expansionPercentage: 19.21,
    encroachedLandType: 'GOVT_GAIRAN_GRAZING',
    encroachedLandTypeLabel: 'Village Gairan (Public Grazing Reserve)',
    encroachedLandTypeLabelHi: 'ग्रामपंचायत गायरान (सार्वजनिक चराई जमीन)',
    encroachmentPolygon: [
      [18.3882, 73.8963],
      [18.3885, 73.8970],
      [18.3860, 73.8962],
      [18.3861, 73.8956],
      [18.3882, 73.8963]
    ],
    historicalGeom1974: [
      [18.3865, 73.8940],
      [18.3890, 73.8948],
      [18.3882, 73.8963],
      [18.3861, 73.8956],
      [18.3865, 73.8940]
    ],
    currentGeom2024: [
      [18.3865, 73.8940],
      [18.3890, 73.8948],
      [18.3885, 73.8970],
      [18.3860, 73.8962],
      [18.3865, 73.8940]
    ],
    displacedStonesCount: 1,
    statutoryViolation: 'Supreme Court Jagpal Singh vs State of Punjab Mandate & MLRC Sec 53 Encroachment on Common Gram Panchayat Land',
    description: 'Eastern pomegranate orchard wire-fencing pushed 285 m² into unallotted Government Gairan (Survey No. 87 Gairan poramboke).',
    descriptionHi: 'पूर्वेकडील डाळिंब बागेची कुंपण भिंत २८५ चौ.मी. ग्रामपंचायत सरकारी गायरान जमिनीत अतिक्रमित केली गेली आहे.',
    solatiumDeductionEstInr: 960000,
    recommendedAction: 'Serve notice to restore original 1974 boundary; restore encroached gairan area to Revenue Department register.',
    recommendedActionHi: '१९७४ ची मूळ सीमा पुनर्संचयित करण्याची नोटीस द्यावी व अतिक्रमित गायरान क्षेत्र महसूल दप्तरी जमा करावे.',
    fieldInspectionStatus: 'PENDING_JOINT_MEASUREMENT',
    detectedDate: '2026-09-18'
  },
  {
    id: 'ENC-143',
    parcelId: 'PCL-143',
    currentSurveyNumber: 'Gat No. 143',
    historicalSurveyNumber1974: 'Old Survey No. 85, Hissa 1',
    village: 'Shindewadi',
    hasEncroachment: true,
    severity: 'HIGH',
    encroachmentAreaSqM: 320,
    encroachmentAreaHa: 0.0320,
    expansionPercentage: 34.41,
    encroachedLandType: 'NATURAL_NALA_BUFFER',
    encroachedLandTypeLabel: 'Natural Nala (Drainage Stream Buffer)',
    encroachedLandTypeLabelHi: 'नैसर्गिक ओढा व जलप्रवाह बफर क्षेत्र',
    encroachmentPolygon: [
      [18.3832, 73.8979],
      [18.3838, 73.8985],
      [18.3815, 73.8978],
      [18.3816, 73.8973],
      [18.3832, 73.8979]
    ],
    historicalGeom1974: [
      [18.3820, 73.8955],
      [18.3842, 73.8960],
      [18.3832, 73.8979],
      [18.3816, 73.8973],
      [18.3820, 73.8955]
    ],
    currentGeom2024: [
      [18.3820, 73.8955],
      [18.3842, 73.8960],
      [18.3838, 73.8985],
      [18.3815, 73.8978],
      [18.3820, 73.8955]
    ],
    displacedStonesCount: 1,
    statutoryViolation: 'NGT River & Nala Protection Guidelines & Maharashtra Land Revenue Code Section 48',
    description: 'Eastern parking yard has backfilled and diverted 320 m² of the natural village storm drainage nala course shown in 1974 cadastral hydrography.',
    descriptionHi: 'पूर्वेकडील व्यावसायिक पार्किंगसाठी १९७४ च्या महसूल नकाशातील नैसर्गिक पावसाळी ओढ्याचा ३२० चौ.मी. प्रवाह बुजवून अतिक्रमण करण्यात आले आहे.',
    solatiumDeductionEstInr: 1120000,
    recommendedAction: 'Direct water resources engineer site audit; issue demolition order for illegal culvert landfill.',
    recommendedActionHi: 'जलसंपदा अभियंत्यांमार्फत तपासणी करून बेकायदेशीर भराव हटवण्याचे आदेश द्यावेत.',
    fieldInspectionStatus: 'NOTICE_DRAFTED',
    detectedDate: '2026-09-20'
  },
  {
    id: 'ENC-144',
    parcelId: 'PCL-144',
    currentSurveyNumber: 'Gat No. 144/3',
    historicalSurveyNumber1974: 'Old Survey No. 86, Hissa 3',
    village: 'Shindewadi',
    hasEncroachment: true,
    severity: 'MODERATE',
    encroachmentAreaSqM: 110,
    encroachmentAreaHa: 0.0110,
    expansionPercentage: 8.94,
    encroachedLandType: 'BOUND_DRIFT_AGRICULTURAL',
    encroachedLandTypeLabel: 'Field Bund Creep (Agricultural Shift)',
    encroachedLandTypeLabelHi: 'शेत बांध स्थलांतर (हळूहळू झालेली वाढ)',
    encroachmentPolygon: [
      [18.3903, 73.8999],
      [18.3905, 73.9002],
      [18.3880, 73.8992],
      [18.3881, 73.8990],
      [18.3903, 73.8999]
    ],
    historicalGeom1974: [
      [18.3885, 73.8970],
      [18.3908, 73.8981],
      [18.3903, 73.8999],
      [18.3881, 73.8990],
      [18.3885, 73.8970]
    ],
    currentGeom2024: [
      [18.3885, 73.8970],
      [18.3910, 73.8982],
      [18.3905, 73.9002],
      [18.3880, 73.8992],
      [18.3885, 73.8970]
    ],
    displacedStonesCount: 1,
    statutoryViolation: 'Minor Cadastral Discrepancy under Settlement Correction Rules',
    description: 'Minor 110 m² drift along eastern field bund over 50 years of regular tractor plowing across historical boundary line.',
    descriptionHi: 'गेल्या ५० वर्षांत ट्रॅक्टर नांगरणीमुळे शेत बांधामध्ये ११० चौ.मी.चे किरकोळ स्थलांतर.',
    solatiumDeductionEstInr: 345000,
    recommendedAction: 'Re-align boundary during joint demarcation with neighboring khatedar.',
    recommendedActionHi: 'लगतच्या खातेदारासोबत संयुक्त मोजणी करून बांध पूर्ववत करावा.',
    fieldInspectionStatus: 'PENDING_JOINT_MEASUREMENT',
    detectedDate: '2026-09-22'
  }
];

/**
 * Historical Survey Helpers
 */
export function getHistoricalParcel(parcelId: string): HistoricalCadastralParcel | undefined {
  return HISTORICAL_CADASTRAL_PARCELS.find(h => h.currentParcelId === parcelId);
}

export function getEncroachmentRecord(parcelId: string): EncroachmentDetectionRecord | undefined {
  return ENCROACHMENT_RECORDS.find(e => e.parcelId === parcelId);
}

export function getAllEncroachments(): EncroachmentDetectionRecord[] {
  return ENCROACHMENT_RECORDS;
}

export function getEncroachmentSummaryStats() {
  const records = ENCROACHMENT_RECORDS.filter(r => r.hasEncroachment);
  const totalAreaSqM = records.reduce((sum, r) => sum + r.encroachmentAreaSqM, 0);
  const totalSavingsInr = records.reduce((sum, r) => sum + r.solatiumDeductionEstInr, 0);
  const criticalCount = records.filter(r => r.severity === 'CRITICAL').length;
  const highCount = records.filter(r => r.severity === 'HIGH').length;
  const moderateCount = records.filter(r => r.severity === 'MODERATE').length;
  
  return {
    count: records.length,
    totalAreaSqM,
    totalAreaHa: Number((totalAreaSqM / 10000).toFixed(4)),
    totalSavingsInr,
    criticalCount,
    highCount,
    moderateCount
  };
}
