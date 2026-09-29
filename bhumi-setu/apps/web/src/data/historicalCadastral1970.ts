export interface HistoricalCadastralParcel1970 {
  id: string;
  oldSurveyNumber: string;
  oldSurveyNumberHi: string;
  correspondingModernGat: string;
  village: string;
  settlementYear: number;
  tenureType: string;
  recordedArea1974Ha: number;
  coordinates: [number, number][];
  boundaryStones: {
    stoneId: string;
    stoneNo: number;
    coords: [number, number];
    status: 'INTACT_VERIFIED' | 'DISPLACED' | 'MISSING_DESTROYED';
  }[];
}

export interface HistoricalNaturalFeature {
  id: string;
  name: string;
  nameHi: string;
  type: 'NALA_WATERCOURSE' | 'CART_TRACK_PANAND' | 'VILLAGE_GAOTHAN_FRINGE' | 'GRAZING_GAIRAN';
  coordinates: [number, number][] | [number, number][][];
  isPolygon?: boolean;
}

export interface EncroachmentIncident {
  id: string;
  title: string;
  titleHi: string;
  modernParcelId: string;
  modernSurveyNumber: string;
  historicalSurveyNumber: string;
  encroachmentType: 
    | 'HIGHWAY_ROW_BUFFER' 
    | 'WATERCOURSE_STREAM_BED' 
    | 'COMMUNAL_GAIRAN_EXPANSION' 
    | 'UNAUTHORIZED_SUBDIVISION';
  encroachedAreaHa: number;
  encroachedAreaSqM: number;
  encroachmentDepthM: number;
  severity: 'CRITICAL' | 'HIGH' | 'MODERATE';
  detectedCoordinates: [number, number][]; // Polygon geometry of encroached sliver
  statutoryViolation: string;
  evictionNoticeEligible: boolean;
  legalProvision: string;
  description: string;
  recommendedAction: string;
}

export interface HistoricalSettlementMapMetadata {
  settlementYear: number;
  surveyAuthority: string;
  villageName: string;
  taluka: string;
  district: string;
  sheetNo: string;
  scaleRatio: string;
  georeferenceAccuracyM: number;
}

export const HISTORICAL_MAP_METADATA: HistoricalSettlementMapMetadata = {
  settlementYear: 1974,
  surveyAuthority: 'Settlement Commissioner & Director of Land Records, Government of Maharashtra',
  villageName: 'Shindewadi',
  taluka: 'Haveli',
  district: 'Pune',
  sheetNo: 'Village Settlement Consolidation Sheet No. 03 (Gaon Nakasha 1974)',
  scaleRatio: '1:2000 (Metric Chain Settlement Standard)',
  georeferenceAccuracyM: 0.45,
};

export const HISTORICAL_PARCELS_1974: HistoricalCadastralParcel1970[] = [
  {
    id: 'HIST-SURV-88-1',
    oldSurveyNumber: 'Old Survey No. 88/1',
    oldSurveyNumberHi: 'जुना सर्व्हे क्र. ८८/१',
    correspondingModernGat: 'Gat No. 142/A',
    village: 'Shindewadi',
    settlementYear: 1974,
    tenureType: 'Occupant Class I (Rayatwari)',
    recordedArea1974Ha: 2.21,
    coordinates: [
      [18.3842, 73.8907],
      [18.3864, 73.8914],
      [18.3870, 73.8934],
      [18.3846, 73.8930],
      [18.3842, 73.8907],
    ],
    boundaryStones: [
      { stoneId: 'STN-11', stoneNo: 11, coords: [18.3842, 73.8907], status: 'INTACT_VERIFIED' },
      { stoneId: 'STN-12', stoneNo: 12, coords: [18.3864, 73.8914], status: 'DISPLACED' },
      { stoneId: 'STN-13', stoneNo: 13, coords: [18.3870, 73.8934], status: 'MISSING_DESTROYED' },
      { stoneId: 'STN-14', stoneNo: 14, coords: [18.3846, 73.8930], status: 'INTACT_VERIFIED' },
    ],
  },
  {
    id: 'HIST-SURV-88-2',
    oldSurveyNumber: 'Old Survey No. 88/2',
    oldSurveyNumberHi: 'जुना सर्व्हे क्र. ८८/२',
    correspondingModernGat: 'Gat No. 142/B',
    village: 'Shindewadi',
    settlementYear: 1974,
    tenureType: 'Occupant Class I (Rayatwari)',
    recordedArea1974Ha: 1.72,
    coordinates: [
      [18.3865, 73.8940],
      [18.3888, 73.8947],
      [18.3883, 73.8965],
      [18.3861, 73.8959],
      [18.3865, 73.8940],
    ],
    boundaryStones: [
      { stoneId: 'STN-15', stoneNo: 15, coords: [18.3865, 73.8940], status: 'INTACT_VERIFIED' },
      { stoneId: 'STN-16', stoneNo: 16, coords: [18.3888, 73.8947], status: 'INTACT_VERIFIED' },
      { stoneId: 'STN-17', stoneNo: 17, coords: [18.3883, 73.8965], status: 'DISPLACED' },
      { stoneId: 'STN-18', stoneNo: 18, coords: [18.3861, 73.8959], status: 'INTACT_VERIFIED' },
    ],
  },
  {
    id: 'HIST-SURV-89',
    oldSurveyNumber: 'Old Survey No. 89',
    oldSurveyNumberHi: 'जुना सर्व्हे क्र. ८९ (ओढा काठ)',
    correspondingModernGat: 'Gat No. 143',
    village: 'Shindewadi',
    settlementYear: 1974,
    tenureType: 'Occupant Class I (Dry Crop Agricultural)',
    recordedArea1974Ha: 1.09,
    coordinates: [
      [18.3818, 73.8956],
      [18.3832, 73.8961],
      [18.3830, 73.8983],
      [18.3814, 73.8977],
      [18.3818, 73.8956],
    ],
    boundaryStones: [
      { stoneId: 'STN-21', stoneNo: 21, coords: [18.3818, 73.8956], status: 'INTACT_VERIFIED' },
      { stoneId: 'STN-22', stoneNo: 22, coords: [18.3832, 73.8961], status: 'MISSING_DESTROYED' },
      { stoneId: 'STN-23', stoneNo: 23, coords: [18.3830, 73.8983], status: 'DISPLACED' },
      { stoneId: 'STN-24', stoneNo: 24, coords: [18.3814, 73.8977], status: 'INTACT_VERIFIED' },
    ],
  },
  {
    id: 'HIST-SURV-90',
    oldSurveyNumber: 'Old Survey No. 90',
    oldSurveyNumberHi: 'जुना सर्व्हे क्र. ९०',
    correspondingModernGat: 'Gat No. 144/3',
    village: 'Shindewadi',
    settlementYear: 1974,
    tenureType: 'Occupant Class I',
    recordedArea1974Ha: 1.32,
    coordinates: [
      [18.3885, 73.8970],
      [18.3908, 73.8980],
      [18.3902, 73.8998],
      [18.3880, 73.8990],
      [18.3885, 73.8970],
    ],
    boundaryStones: [
      { stoneId: 'STN-31', stoneNo: 31, coords: [18.3885, 73.8970], status: 'INTACT_VERIFIED' },
      { stoneId: 'STN-32', stoneNo: 32, coords: [18.3908, 73.8980], status: 'INTACT_VERIFIED' },
    ],
  },
];

export const HISTORICAL_NATURAL_FEATURES: HistoricalNaturalFeature[] = [
  {
    id: 'FEAT-NALA-1974',
    name: '1974 Natural Drainage Nala (Village Stream)',
    nameHi: '१९७४ नैसर्गिक ओढा / नाला प्रवाह',
    type: 'NALA_WATERCOURSE',
    coordinates: [
      [18.3826, 73.8948],
      [18.3835, 73.8962],
      [18.3840, 73.8975],
      [18.3845, 73.8990],
      [18.3852, 73.9015],
    ],
  },
  {
    id: 'FEAT-ROAD-1974',
    name: '1974 Traditional Panand Bullock-Cart Track',
    nameHi: '१९७४ पाणंद रस्ता व पारंपारिक बैलगाडी मार्ग',
    type: 'CART_TRACK_PANAND',
    coordinates: [
      [18.3845, 73.8890],
      [18.3860, 73.8932],
      [18.3875, 73.8960],
      [18.3892, 73.8995],
    ],
  },
  {
    id: 'FEAT-GAIRAN-1974',
    name: '1974 Communal Grazing Land (Gairan)',
    nameHi: '१९७४ ग्रामपंचायत गायरान राखीव क्षेत्र',
    type: 'GRAZING_GAIRAN',
    isPolygon: true,
    coordinates: [
      [18.3883, 73.8965],
      [18.3895, 73.8975],
      [18.3880, 73.8988],
      [18.3861, 73.8959],
      [18.3883, 73.8965],
    ],
  },
];

export const DETECTED_ENCROACHMENTS: EncroachmentIncident[] = [
  {
    id: 'ENC-01',
    title: 'Commercial Frontage & Compound Wall Encroachment into 1974 Highway Corridor',
    titleHi: '१९७४ महामार्ग संरेखणात व्यावसायिक सीमाभिंत व प्रवेशद्वार अतिक्रमण',
    modernParcelId: 'PCL-142A',
    modernSurveyNumber: 'Gat No. 142/A',
    historicalSurveyNumber: 'Old Survey No. 88/1',
    encroachmentType: 'HIGHWAY_ROW_BUFFER',
    encroachedAreaHa: 0.24,
    encroachedAreaSqM: 2400,
    encroachmentDepthM: 18.5,
    severity: 'CRITICAL',
    // Sliver between 1974 boundary and modern Gat 142/A eastern boundary
    detectedCoordinates: [
      [18.3870, 73.8934],
      [18.3872, 73.8940],
      [18.3848, 73.8935],
      [18.3846, 73.8930],
      [18.3870, 73.8934],
    ],
    statutoryViolation: 'Section 53 Maharashtra Land Revenue Code 1966 & NHAI Control of National Highways (Land and Traffic) Act 2002',
    evictionNoticeEligible: true,
    legalProvision: 'MLRC 1966 Section 53 (Summary Eviction of Encroachers) & RFCTLARR Act 2013 Section 11(4)',
    description: 'PostGIS spatial overlay verifies that modern Gat 142/A plot fencing and concrete security gate extend 18.5 meters beyond the 1974 Cadastral Stone #12 directly into the surveyed highway right-of-way.',
    recommendedAction: 'Issue statutory 7-day Form 8 summary demolition notice under Section 53 MLRC 1966 before compensation award calculation.',
  },
  {
    id: 'ENC-02',
    title: 'Natural Drainage Nala Bed Reclamation for G+3 Commercial Parking',
    titleHi: 'नैसर्गिक ओढा पात्राचे भराव अतिक्रमण (जी+३ पार्किंग क्षेत्र)',
    modernParcelId: 'PCL-143',
    modernSurveyNumber: 'Gat No. 143',
    historicalSurveyNumber: 'Old Survey No. 89 (Nala Bed)',
    encroachmentType: 'WATERCOURSE_STREAM_BED',
    encroachedAreaHa: 0.16,
    encroachedAreaSqM: 1600,
    encroachmentDepthM: 12.0,
    severity: 'CRITICAL',
    detectedCoordinates: [
      [18.3832, 73.8961],
      [18.3842, 73.8960],
      [18.3838, 73.8985],
      [18.3830, 73.8983],
      [18.3832, 73.8961],
    ],
    statutoryViolation: 'Maharashtra Land Revenue Code 1966 Section 20(2) & Environment Protection Act 1986 Watercourse Preservation',
    evictionNoticeEligible: true,
    legalProvision: 'National Green Tribunal (NGT) Pune Bench Guidelines on Natural Nala Preservation (50m Buffer)',
    description: 'Modern commercial structure and reinforced concrete parking apron constructed directly over 1974 village seasonal stream course, constricting flood flow capacity by 60%.',
    recommendedAction: 'Disallow commercial land rate solatium on 0.16 Ha encroached stream bed and issue restoration summons to developer.',
  },
  {
    id: 'ENC-03',
    title: 'Agricultural Boundary Migration into 1974 Communal Grazing Land (Gairan)',
    titleHi: '१९७४ शासकीय गायरान जमिनीत शेती कुंपण सरकवणे',
    modernParcelId: 'PCL-142B',
    modernSurveyNumber: 'Gat No. 142/B',
    historicalSurveyNumber: 'Old Survey No. 88/2',
    encroachmentType: 'COMMUNAL_GAIRAN_EXPANSION',
    encroachedAreaHa: 0.08,
    encroachedAreaSqM: 800,
    encroachmentDepthM: 6.5,
    severity: 'MODERATE',
    detectedCoordinates: [
      [18.3883, 73.8965],
      [18.3885, 73.8970],
      [18.3860, 73.8962],
      [18.3861, 73.8959],
      [18.3883, 73.8965],
    ],
    statutoryViolation: 'Maharashtra Land Revenue (Disposal of Government Land) Rules & MLRC 1966 Section 50',
    evictionNoticeEligible: true,
    legalProvision: 'Supreme Court Jagpal Singh vs State of Punjab (2011) Common Land Eviction Mandate',
    description: 'Boundary stone #17 found shifted by 6.5 meters eastward, absorbing 800 sq.m of community grazing land into orchard fencing.',
    recommendedAction: 'Order Talathi & Circle Officer Haveli to re-fix boundary stone #17 at original 1974 coordinates and repossess grazing land.',
  },
];
