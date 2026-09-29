import React, { createContext, useContext, useState, useEffect } from 'react';
import { 
  AcquisitionCase, 
  CaseStage, 
  UserSession, 
  AuditEvent, 
  ValidationIssue, 
  ExtractedField, 
  Objection, 
  Award, 
  Payout, 
  ImportBatch, 
  DataSubjectRequest, 
  RiskBand,
  RecommendedAction,
  OfficerTab
} from '../types';
import { 
  DEMO_USERS, 
  INITIAL_CASES, 
  INITIAL_AUDIT_LOG, 
  MOCK_IMPORT_BATCHES, 
  MOCK_DSR_REQUESTS, 
  MOCK_PROJECTS,
  MOCK_MODEL_STATS
} from '../data/mockData';
import { backendApi, BackendConnectionStatus } from '../services/backendApi';

export type PortalMode = 'OFFICER' | 'CITIZEN';
export type Language = 'en' | 'hi';
export type FontScale = 'normal' | 'large' | 'xlarge';

interface ToastNotification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  messageHi?: string;
}

interface AppContextType {
  currentUser: UserSession;
  setCurrentUser: (user: UserSession) => void;
  portalMode: PortalMode;
  setPortalMode: (mode: PortalMode) => void;
  language: Language;
  setLanguage: (lang: Language) => void;
  isDarkMode: boolean;
  setIsDarkMode: (dark: boolean) => void;
  isHighContrast: boolean;
  setIsHighContrast: (high: boolean) => void;
  fontScale: FontScale;
  setFontScale: (scale: FontScale) => void;
  officerTab: OfficerTab;
  setOfficerTab: (tab: OfficerTab) => void;
  // Aliases for compatibility
  currentPortal: PortalMode;
  setCurrentPortal: (mode: PortalMode) => void;
  currentOfficerTab: OfficerTab;
  setCurrentOfficerTab: (tab: OfficerTab) => void;
  
  // Cases & Entities
  cases: AcquisitionCase[];
  selectedCaseId: string;
  setSelectedCaseId: (id: string) => void;
  selectedCase: AcquisitionCase;
  projects: typeof MOCK_PROJECTS;
  auditLog: AuditEvent[];
  importBatches: ImportBatch[];
  dsrRequests: DataSubjectRequest[];
  modelStats: typeof MOCK_MODEL_STATS;
  
  // Actions
  transitionCaseStage: (caseId: string, newStage: CaseStage) => boolean;
  correctOcrField: (caseId: string, docId: string, fieldId: string, correctedValue: string) => void;
  confirmOcrField: (caseId: string, docId: string, fieldId: string) => void;
  resolveValidationIssue: (caseId: string, issueId: string, resolutionReason?: string) => void;
  waiveValidationIssue: (caseId: string, issueId: string, waiverReason: string) => boolean;
  disposeObjection: (caseId: string, objectionId: string, outcome: 'ACCEPTED' | 'REJECTED', reasons: string) => void;
  createAward: (caseId: string, award: Omit<Award, 'id'>) => void;
  disbursePayout: (caseId: string, awardId: string, amount: number, reference: string) => boolean;
  overrideCaseRisk: (caseId: string, newRiskBand: RiskBand, reason: string) => void;
  actOnRecommendedAction: (caseId: string, actionId: string, disposition: 'ACCEPTED' | 'REJECTED' | 'DEFERRED', note?: string) => void;
  submitDsrRequest: (caseRef: string, citizenName: string, mobile: string, type: 'ACCESS_REQUEST' | 'CORRECTION_REQUEST', targetField?: string, assertedValue?: string) => void;
  disposeDsrRequest: (dsrId: string, notes: string) => void;
  submitCitizenObjection: (caseId: string, objectionData: {
    objectorName: string;
    objectorContact: string;
    surveyNumber: string;
    groundsCategory: 'Valuation & Compensation' | 'Measurement / Boundary Dispute' | 'Ownership / Title Claim' | 'Environmental / Religious Structure';
    substance: string;
  }) => string;
  runBulkImportSimulation: (rowsCount: number) => ImportBatch;
  
  // Toast & Accessibility Announcement
  toasts: ToastNotification[];
  addToast: (toast: Omit<ToastNotification, 'id'>) => void;
  removeToast: (id: string) => void;
  
  // Citizen OTP Simulation State
  citizenOtpSent: boolean;
  setCitizenOtpSent: (sent: boolean) => void;
  citizenSessionValid: boolean;
  setCitizenSessionValid: (valid: boolean) => void;

  // Backend Integration State
  backendStatus: BackendConnectionStatus;
  refreshBackendData: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<UserSession>(DEMO_USERS[0]); // Default to Collector
  const [portalMode, setPortalMode] = useState<PortalMode>('CITIZEN'); // Default to Citizen Portal to showcase public homepage & scheme banners
  const [language, setLanguage] = useState<Language>('en');
  const [isDarkMode, setIsDarkMode] = useState<boolean>(false);
  const [isHighContrast, setIsHighContrast] = useState<boolean>(false);
  const [fontScale, setFontScale] = useState<FontScale>('normal');
  const [officerTab, setOfficerTab] = useState<OfficerTab>('DASHBOARD');
  
  const [cases, setCases] = useState<AcquisitionCase[]>(INITIAL_CASES);
  const [selectedCaseId, setSelectedCaseId] = useState<string>(INITIAL_CASES[0].id);
  const [auditLog, setAuditLog] = useState<AuditEvent[]>(INITIAL_AUDIT_LOG);
  const [importBatches, setImportBatches] = useState<ImportBatch[]>(MOCK_IMPORT_BATCHES);
  const [dsrRequests, setDsrRequests] = useState<DataSubjectRequest[]>(MOCK_DSR_REQUESTS);
  const [toasts, setToasts] = useState<ToastNotification[]>([]);
  
  const [citizenOtpSent, setCitizenOtpSent] = useState(false);
  const [citizenSessionValid, setCitizenSessionValid] = useState(false);
  const [backendStatus, setBackendStatus] = useState<BackendConnectionStatus>({
    connected: false,
    statusText: 'Connecting to backend...'
  });

  const refreshBackendData = async () => {
    const status = await backendApi.checkHealth();
    setBackendStatus(status);
    if (status.connected) {
      await backendApi.setPersonaSession(currentUser);
      const backendCases = await backendApi.getCases();
      if (backendCases && backendCases.length > 0) {
        setCases(prev => {
          return prev.map(c => {
            const match = backendCases.find((bc: any) => String(bc.id) === String(c.id) || bc.case_reference === c.caseReference);
            if (match) {
              return {
                ...c,
                stage: (match.stage_key ? `STAGE_${match.stage_key.toUpperCase()}` : c.stage) as CaseStage,
                isBreached: match.deadline_breached ?? c.isBreached,
                entityVersion: match.entity_version ?? c.entityVersion,
              };
            }
            return c;
          });
        });
      }
    }
  };

  useEffect(() => {
    const unsub = backendApi.subscribeStatus(setBackendStatus);
    refreshBackendData();
    return unsub;
  }, []);

  useEffect(() => {
    backendApi.setPersonaSession(currentUser).catch(() => {});
  }, [currentUser]);

  const selectedCase = cases.find(c => c.id === selectedCaseId) || cases[0];

  const addToast = (toast: Omit<ToastNotification, 'id'>) => {
    const id = 'toast-' + Math.random().toString(36).substr(2, 9);
    setToasts(prev => [...prev, { ...toast, id }]);
    setTimeout(() => {
      removeToast(id);
    }, 4500);
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  // Switch HTML root class for Dark Mode and High Contrast
  useEffect(() => {
    const root = document.documentElement;
    if (isDarkMode) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    if (isHighContrast) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }

    root.classList.remove('font-normal', 'font-large', 'font-xlarge');
    root.classList.add(`font-${fontScale}`);
  }, [isDarkMode, isHighContrast, fontScale]);

  // Stage Transition with BLOCKING validation issue enforcement (Req 5.7)
  const transitionCaseStage = (caseId: string, newStage: CaseStage): boolean => {
    const targetCase = cases.find(c => c.id === caseId);
    if (!targetCase) return false;

    // Check if user has permission
    if (!currentUser.permissions.canTransitionStage) {
      addToast({
        type: 'error',
        message: 'Access Denied: Your role lacks statutory stage transition authority.',
        messageHi: 'पहुँच अस्वीकृत: आपकी भूमिका के पास सांविधिक चरण परिवर्तन की अनुमति नहीं है।',
      });
      return false;
    }

    // Check for open BLOCKING issues
    const blockingIssues = targetCase.validationIssues.filter(
      v => v.severity === 'BLOCKING' && v.resolutionState === 'OPEN'
    );

    if (blockingIssues.length > 0) {
      addToast({
        type: 'error',
        message: `Transition Rejected: ${blockingIssues.length} BLOCKING validation issue(s) must be resolved or waived before progressing.`,
        messageHi: `चरण परिवर्तन अस्वीकृत: आगे बढ़ने से पहले ${blockingIssues.length} अवरोधक त्रुटियों का समाधान आवश्यक है।`,
      });
      return false;
    }

    const priorStage = targetCase.stage;
    
    // Compute new stage deadline based on statutory rules
    const stageDeadlines: Record<CaseStage, number> = {
      STAGE_1_SIA: 60,
      STAGE_2_PRELIM_NOTIF: 90,
      STAGE_3_OBJECTIONS: 60,
      STAGE_4_DECLARATION: 365,
      STAGE_5_AWARD_COMPENSATION: 365,
      STAGE_6_DISBURSEMENT: 90,
      STAGE_7_COMPLETED: 0,
    };

    const newDeadlineDate = new Date();
    newDeadlineDate.setDate(newDeadlineDate.getDate() + (stageDeadlines[newStage] || 60));

    setCases(prev => prev.map(c => {
      if (c.id !== caseId) return c;
      return {
        ...c,
        stage: newStage,
        stageStartDate: new Date().toISOString().split('T')[0],
        stageDeadline: newDeadlineDate.toISOString().split('T')[0],
        daysRemaining: stageDeadlines[newStage] || 60,
        isBreached: false,
      };
    }));

    // Record Immutable Audit Event
    const newEvent: AuditEvent = {
      id: `EVT-${Date.now()}`,
      caseId: targetCase.id,
      actorId: currentUser.id,
      actorName: currentUser.name,
      actorRole: currentUser.role,
      eventType: 'STAGE_TRANSITION',
      entityType: 'Acquisition_Case',
      entityId: targetCase.id,
      occurrenceTime: new Date().toISOString(),
      details: `Transitioned stage from ${priorStage} to ${newStage} by ${currentUser.name} (${currentUser.designation}).`,
      priorValue: priorStage,
      newValue: newStage,
    };

    setAuditLog(prev => [newEvent, ...prev]);

    addToast({
      type: 'success',
      message: `Statutory milestone updated: Moved to ${newStage.replace(/_/g, ' ')}.`,
      messageHi: `सांविधिक चरण सफलतापूर्वक अद्यतन किया गया।`,
    });

    backendApi.transitionCaseStage(caseId, newStage).catch(() => {});

    return true;
  };

  // OCR Field Correction
  const correctOcrField = (caseId: string, docId: string, fieldId: string, correctedValue: string) => {
    setCases(prev => prev.map(c => {
      if (c.id !== caseId) return c;
      return {
        ...c,
        documents: c.documents.map(doc => {
          if (doc.id !== docId) return doc;
          return {
            ...doc,
            extractedFields: doc.extractedFields.map(fld => {
              if (fld.id !== fieldId) return fld;
              return {
                ...fld,
                extractedValue: correctedValue,
                reviewState: 'CORRECTED',
                correctedBy: currentUser.name,
                correctedAt: new Date().toISOString(),
              };
            }),
          };
        }),
      };
    }));

    const auditEvt: AuditEvent = {
      id: `EVT-${Date.now()}`,
      caseId,
      actorId: currentUser.id,
      actorName: currentUser.name,
      actorRole: currentUser.role,
      eventType: 'OCR_FIELD_CORRECTED',
      entityType: 'Extracted_Field',
      entityId: fieldId,
      occurrenceTime: new Date().toISOString(),
      details: `OCR Field corrected by ${currentUser.name}. Updated value: "${correctedValue}"`,
      newValue: correctedValue,
    };
    setAuditLog(prev => [auditEvt, ...prev]);

    addToast({
      type: 'success',
      message: `OCR Extracted Field updated and recorded in audit log.`,
      messageHi: `ओसीआर फ़ील्ड मान सफलतापूर्वक संशोधित एवं रिकॉर्ड किया गया।`,
    });
  };

  // OCR Field Confirmation
  const confirmOcrField = (caseId: string, docId: string, fieldId: string) => {
    setCases(prev => prev.map(c => {
      if (c.id !== caseId) return c;
      return {
        ...c,
        documents: c.documents.map(doc => {
          if (doc.id !== docId) return doc;
          return {
            ...doc,
            extractedFields: doc.extractedFields.map(fld => {
              if (fld.id !== fieldId) return fld;
              return {
                ...fld,
                reviewState: 'CONFIRMED',
                correctedBy: currentUser.name,
                correctedAt: new Date().toISOString(),
              };
            }),
          };
        }),
      };
    }));

    const auditEvt: AuditEvent = {
      id: `EVT-${Date.now()}`,
      caseId,
      actorId: currentUser.id,
      actorName: currentUser.name,
      actorRole: currentUser.role,
      eventType: 'OCR_FIELD_CONFIRMED',
      entityType: 'Extracted_Field',
      entityId: fieldId,
      occurrenceTime: new Date().toISOString(),
      details: `OCR Field verified and confirmed without alteration by ${currentUser.name}.`,
    };
    setAuditLog(prev => [auditEvt, ...prev]);

    addToast({
      type: 'success',
      message: `OCR Field confirmed successfully.`,
      messageHi: `ओसीआर फ़ील्ड सफलतापूर्वक पुष्ट किया गया।`,
    });
  };

  // Resolve Validation Issue by Correction
  const resolveValidationIssue = (caseId: string, issueId: string, resolutionReason?: string) => {
    setCases(prev => prev.map(c => {
      if (c.id !== caseId) return c;
      return {
        ...c,
        validationIssues: c.validationIssues.map(iss => {
          if (iss.id !== issueId) return iss;
          return {
            ...iss,
            resolutionState: 'RESOLVED_BY_CORRECTION',
          };
        }),
      };
    }));

    const auditEvt: AuditEvent = {
      id: `EVT-${Date.now()}`,
      caseId,
      actorId: currentUser.id,
      actorName: currentUser.name,
      actorRole: currentUser.role,
      eventType: 'VALIDATION_ISSUE_RESOLVED',
      entityType: 'Validation_Issue',
      entityId: issueId,
      occurrenceTime: new Date().toISOString(),
      details: `Validation issue ${issueId} resolved by data correction. ${resolutionReason || ''}`,
    };
    setAuditLog(prev => [auditEvt, ...prev]);

    addToast({
      type: 'success',
      message: `Validation issue marked as RESOLVED.`,
      messageHi: `सत्यापन त्रुटि सफलतापूर्वक हल की गई।`,
    });
  };

  // Waive Validation Issue with RBAC & Reason Audit (Req 14.5, 14.6)
  const waiveValidationIssue = (caseId: string, issueId: string, waiverReason: string): boolean => {
    const targetCase = cases.find(c => c.id === caseId);
    const targetIssue = targetCase?.validationIssues.find(i => i.id === issueId);
    if (!targetIssue) return false;

    if (targetIssue.severity === 'BLOCKING' && !currentUser.permissions.canWaiveBlockingValidation) {
      addToast({
        type: 'error',
        message: 'Permission Denied: Only District Collector holds authority to waive BLOCKING statutory issues.',
        messageHi: 'पहुँच अस्वीकृत: केवल जिलाधिकारी ही अवरोधक त्रुटियों को माफ कर सकते हैं।',
      });
      return false;
    }

    if (!waiverReason || waiverReason.trim().length < 8) {
      addToast({
        type: 'warning',
        message: 'Statutory compliance requires a valid recorded reason (min 8 characters) to waive an issue.',
        messageHi: 'त्रुटि माफ़ी के लिए वैध कारण दर्ज करना अनिवार्य है।',
      });
      return false;
    }

    setCases(prev => prev.map(c => {
      if (c.id !== caseId) return c;
      return {
        ...c,
        validationIssues: c.validationIssues.map(iss => {
          if (iss.id !== issueId) return iss;
          return {
            ...iss,
            resolutionState: 'WAIVED',
            waiverReason,
            waivedBy: currentUser.name,
            waivedAt: new Date().toISOString(),
          };
        }),
      };
    }));

    const auditEvt: AuditEvent = {
      id: `EVT-${Date.now()}`,
      caseId,
      actorId: currentUser.id,
      actorName: currentUser.name,
      actorRole: currentUser.role,
      eventType: 'VALIDATION_ISSUE_WAIVED',
      entityType: 'Validation_Issue',
      entityId: issueId,
      occurrenceTime: new Date().toISOString(),
      details: `Validation Issue waived by ${currentUser.name}. Reason: "${waiverReason}"`,
    };
    setAuditLog(prev => [auditEvt, ...prev]);

    addToast({
      type: 'info',
      message: `Validation issue WAIVED and reason recorded in compliance log.`,
      messageHi: `सत्यापन त्रुटि माफ की गई एवं अनुपालन लॉग में दर्ज की गई।`,
    });

    backendApi.waiveValidationIssue(issueId, waiverReason).catch(() => {});

    return true;
  };

  // Dispose Public Objection (Req 8.3, 8.4)
  const disposeObjection = (caseId: string, objectionId: string, outcome: 'ACCEPTED' | 'REJECTED', reasons: string) => {
    if (!reasons || reasons.trim().length < 5) {
      addToast({
        type: 'error',
        message: 'Section 15(2) requires recorded legal grounds/reasons for disposing an objection.',
        messageHi: 'आपत्ति निपटारे हेतु विधिक कारण दर्ज करना आवश्यक है।',
      });
      return;
    }

    setCases(prev => prev.map(c => {
      if (c.id !== caseId) return c;
      return {
        ...c,
        objections: c.objections.map(obj => {
          if (obj.id !== objectionId) return obj;
          return {
            ...obj,
            disposalState: outcome,
            disposalDate: new Date().toISOString().split('T')[0],
            disposalReasons: reasons,
            decidingOfficer: currentUser.name,
          };
        }),
      };
    }));

    const auditEvt: AuditEvent = {
      id: `EVT-${Date.now()}`,
      caseId,
      actorId: currentUser.id,
      actorName: currentUser.name,
      actorRole: currentUser.role,
      eventType: 'OBJECTION_DISPOSED',
      entityType: 'Objection',
      entityId: objectionId,
      occurrenceTime: new Date().toISOString(),
      details: `Objection ${objectionId} was ${outcome} by ${currentUser.name}. Grounds: "${reasons}"`,
      newValue: outcome,
    };
    setAuditLog(prev => [auditEvt, ...prev]);

    addToast({
      type: 'success',
      message: `Section 15 Objection order recorded: ${outcome}.`,
      messageHi: `धारा 15 आपत्ति आदेश दर्ज: ${outcome === 'ACCEPTED' ? 'स्वीकृत' : 'अस्वीकृत'}।`,
    });
  };

  // Create Award with Arithmetic check (Req 9.2, 9.3)
  const createAward = (caseId: string, awardData: Omit<Award, 'id'>) => {
    const compSum = awardData.components.reduce((sum, c) => sum + c.amount, 0);
    if (Math.abs(compSum - awardData.totalAmount) > 0.01) {
      addToast({
        type: 'error',
        message: `Arithmetic Mismatch: Sum of components (₹${compSum}) does not equal total award (₹${awardData.totalAmount}).`,
        messageHi: `अंकगणितीय त्रुटि: घटकों का योग कुल पंचाट राशि के बराबर नहीं है।`,
      });
      return;
    }

    const newAward: Award = {
      ...awardData,
      id: `AWD-${Date.now()}`,
    };

    setCases(prev => prev.map(c => {
      if (c.id !== caseId) return c;
      return {
        ...c,
        awards: [...c.awards, newAward],
        totalAwardedAmount: c.totalAwardedAmount + newAward.totalAmount,
      };
    }));

    const auditEvt: AuditEvent = {
      id: `EVT-${Date.now()}`,
      caseId,
      actorId: currentUser.id,
      actorName: currentUser.name,
      actorRole: currentUser.role,
      eventType: 'AWARD_DETERMINED',
      entityType: 'Award',
      entityId: newAward.id,
      occurrenceTime: new Date().toISOString(),
      details: `Compensation Award of ₹${newAward.totalAmount.toLocaleString('en-IN')} determined for ${newAward.ownerName} by ${currentUser.name}.`,
    };
    setAuditLog(prev => [auditEvt, ...prev]);

    addToast({
      type: 'success',
      message: `Section 23 Award record created successfully.`,
      messageHi: `धारा 23 मुआवजा पंचाट अभिलेख सफलतापूर्वक सृजित।`,
    });
  };

  // Disburse Payout (Req 9.4, 9.5)
  const disbursePayout = (caseId: string, awardId: string, amount: number, reference: string): boolean => {
    const targetCase = cases.find(c => c.id === caseId);
    const targetAward = targetCase?.awards.find(a => a.id === awardId);
    if (!targetAward) return false;

    // Calculate existing payouts against this award
    const currentPayoutsSum = (targetCase?.payouts || [])
      .filter(p => p.awardId === awardId)
      .reduce((sum, p) => sum + p.amount, 0);

    if (currentPayoutsSum + amount > targetAward.totalAmount) {
      addToast({
        type: 'error',
        message: `Excess Payout Rejected: Total payout cannot exceed Award total ₹${targetAward.totalAmount.toLocaleString('en-IN')}. Remaining disbursable: ₹${(targetAward.totalAmount - currentPayoutsSum).toLocaleString('en-IN')}`,
        messageHi: `अतिरिक्त भुगतान अस्वीकृत: कुल भुगतान पंचाट राशि से अधिक नहीं हो सकता।`,
      });
      return false;
    }

    const newPayout: Payout = {
      id: `PAY-${Date.now()}`,
      awardId,
      amount,
      payoutDate: new Date().toISOString().split('T')[0],
      instrumentReference: reference || `DBT/PFMS/${new Date().getFullYear()}/${Math.floor(100000 + Math.random() * 900000)}`,
      beneficiaryName: targetAward.ownerName,
      bankAccountMasked: 'SBIN0001234 - XX9012',
      ifsc: 'SBIN0001234',
      status: 'SUCCESS',
    };

    const newDisbursedTotal = currentPayoutsSum + amount;
    const newDisbursementState = newDisbursedTotal >= targetAward.totalAmount ? 'FULLY_PAID' : 'PART_PAID';

    setCases(prev => prev.map(c => {
      if (c.id !== caseId) return c;
      return {
        ...c,
        totalDisbursedAmount: c.totalDisbursedAmount + amount,
        payouts: [...c.payouts, newPayout],
        awards: c.awards.map(a => a.id === awardId ? { ...a, disbursementState: newDisbursementState } : a),
      };
    }));

    const auditEvt: AuditEvent = {
      id: `EVT-${Date.now()}`,
      caseId,
      actorId: currentUser.id,
      actorName: currentUser.name,
      actorRole: currentUser.role,
      eventType: 'PAYOUT_RECORDED',
      entityType: 'Payout',
      entityId: newPayout.id,
      occurrenceTime: new Date().toISOString(),
      details: `Disbursed DBT Compensation ₹${amount.toLocaleString('en-IN')} to ${targetAward.ownerName} via ${newPayout.instrumentReference}`,
    };
    setAuditLog(prev => [auditEvt, ...prev]);

    addToast({
      type: 'success',
      message: `DBT Payout of ₹${amount.toLocaleString('en-IN')} successfully initiated.`,
      messageHi: `डीबीटी मुआवजा राशि ₹${amount.toLocaleString('en-IN')} का भुगतान सफलतापूर्वक प्रेषित।`,
    });

    return true;
  };

  // Override ML Risk Band (Req 20.6, 20.7)
  const overrideCaseRisk = (caseId: string, newRiskBand: RiskBand, reason: string) => {
    if (!reason || reason.trim().length < 8) {
      addToast({
        type: 'warning',
        message: 'Reason for overriding AI risk calculation must be specified (min 8 chars).',
        messageHi: 'एआई जोखिम गणना को ओवरराइड करने हेतु कारण दर्ज करें।',
      });
      return;
    }

    setCases(prev => prev.map(c => {
      if (c.id !== caseId) return c;
      return {
        ...c,
        officerOverride: {
          overriddenAt: new Date().toISOString(),
          officerId: currentUser.id,
          officerName: currentUser.name,
          originalRiskBand: c.riskBand,
          newRiskBand,
          reason,
        },
      };
    }));

    const auditEvt: AuditEvent = {
      id: `EVT-${Date.now()}`,
      caseId,
      actorId: currentUser.id,
      actorName: currentUser.name,
      actorRole: currentUser.role,
      eventType: 'OFFICER_OVERRIDE_RECORDED',
      entityType: 'Acquisition_Case',
      entityId: caseId,
      occurrenceTime: new Date().toISOString(),
      details: `Officer ${currentUser.name} manually overrode AI Risk Band to ${newRiskBand}. Reason: "${reason}"`,
      newValue: newRiskBand,
    };
    setAuditLog(prev => [auditEvt, ...prev]);

    addToast({
      type: 'info',
      message: `Officer Risk Override recorded in compliance ledger.`,
      messageHi: `अधिकारी जोखिम ओवरराइड अनुपालन बही में दर्ज किया गया।`,
    });

    backendApi.overrideRiskBand(caseId, newRiskBand, reason).catch(() => {});
  };

  // Recommended Action Disposition (Req 21.9)
  const actOnRecommendedAction = (caseId: string, actionId: string, disposition: 'ACCEPTED' | 'REJECTED' | 'DEFERRED', note?: string) => {
    setCases(prev => prev.map(c => {
      if (c.id !== caseId) return c;
      return {
        ...c,
        recommendedActions: c.recommendedActions.map(act => {
          if (act.id !== actionId) return act;
          return {
            ...act,
            disposition,
            dispositionNote: note,
            actedBy: currentUser.name,
            actedAt: new Date().toISOString(),
          };
        }),
      };
    }));

    const auditEvt: AuditEvent = {
      id: `EVT-${Date.now()}`,
      caseId,
      actorId: currentUser.id,
      actorName: currentUser.name,
      actorRole: currentUser.role,
      eventType: 'RECOMMENDED_ACTION_ACCEPTED',
      entityType: 'Recommended_Action',
      entityId: actionId,
      occurrenceTime: new Date().toISOString(),
      details: `Recommended Action ${actionId} was ${disposition} by ${currentUser.name}. ${note ? `Note: ${note}` : ''}`,
      newValue: disposition,
    };
    setAuditLog(prev => [auditEvt, ...prev]);

    addToast({
      type: 'success',
      message: `Action marked as ${disposition}.`,
      messageHi: `कार्यवाही को ${disposition === 'ACCEPTED' ? 'स्वीकृत' : disposition === 'REJECTED' ? 'अस्वीकृत' : 'आस्थगित'} के रूप में चिह्नित किया गया।`,
    });

    backendApi.disposeRecommendedAction(caseId, actionId, disposition, note || '').catch(() => {});
  };

  // Submit DPDP Data Subject Request (Req 32.5, 32.7)
  const submitDsrRequest = (
    caseRef: string, 
    citizenName: string, 
    mobile: string, 
    type: 'ACCESS_REQUEST' | 'CORRECTION_REQUEST',
    targetField?: string,
    assertedValue?: string
  ) => {
    const newDsr: DataSubjectRequest = {
      id: `DSR-${Date.now()}`,
      requestType: type,
      caseReference: caseRef,
      citizenName,
      mobile,
      submittedAt: new Date().toISOString(),
      status: type === 'ACCESS_REQUEST' ? 'SERVED' : 'PENDING',
      targetField,
      assertedValue,
      completedAt: type === 'ACCESS_REQUEST' ? new Date().toISOString() : undefined,
    };

    setDsrRequests(prev => [newDsr, ...prev]);

    const auditEvt: AuditEvent = {
      id: `EVT-${Date.now()}`,
      actorId: 'CITIZEN_SESSION',
      actorName: citizenName,
      actorRole: 'CITIZEN',
      eventType: type === 'ACCESS_REQUEST' ? 'DATA_ACCESS_REQUEST_SERVED' : 'CITIZEN_SESSION_ISSUED',
      entityType: 'DataSubjectRequest',
      entityId: newDsr.id,
      occurrenceTime: new Date().toISOString(),
      details: `Citizen ${citizenName} submitted DPDP Act 2023 ${type} for case ${caseRef}.`,
    };
    setAuditLog(prev => [auditEvt, ...prev]);

    addToast({
      type: 'success',
      message: type === 'ACCESS_REQUEST' 
        ? 'DPDP Access Disclosure generated and served in compliant text format.' 
        : 'DPDP Data Correction Request submitted to Revenue Competent Authority.',
      messageHi: 'डीपीडीपी अधिनियम 2023 के तहत आपका अनुरोध सफलतापूर्वक दर्ज कर लिया गया है।',
    });

    backendApi.submitCitizenDsr({
      caseRef,
      citizenName,
      mobile,
      type,
      targetField,
      assertedValue
    }).catch(() => {});
  };

  const disposeDsrRequest = (dsrId: string, notes: string) => {
    setDsrRequests(prev => prev.map(d => {
      if (d.id !== dsrId) return d;
      return {
        ...d,
        status: 'DISPOSED_BY_OFFICER',
        disposalNotes: notes,
        completedAt: new Date().toISOString(),
      };
    }));

    addToast({
      type: 'success',
      message: 'DPDP Request disposed and response logged for citizen.',
      messageHi: 'डीपीडीपी अनुरोध का निपटारा किया गया।',
    });

    backendApi.disposeDsarRequest(dsrId, notes).catch(() => {});
  };

  const submitCitizenObjection = (
    caseId: string,
    objectionData: {
      objectorName: string;
      objectorContact: string;
      surveyNumber: string;
      groundsCategory: 'Valuation & Compensation' | 'Measurement / Boundary Dispute' | 'Ownership / Title Claim' | 'Environmental / Religious Structure';
      substance: string;
    }
  ): string => {
    const trackingId = `OBJ-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
    const newObjection: Objection = {
      id: trackingId,
      caseId,
      parcelId: 'PCL-142A',
      objectorName: objectionData.objectorName,
      objectorContact: objectionData.objectorContact,
      receiptDate: new Date().toISOString().split('T')[0],
      groundsCategory: objectionData.groundsCategory,
      substance: objectionData.substance,
      isWithinWindow: true,
      disposalState: 'PENDING',
    };

    setCases(prev => prev.map(c => {
      if (c.id !== caseId) return c;
      return {
        ...c,
        objections: [newObjection, ...c.objections],
      };
    }));

    const auditEvt: AuditEvent = {
      id: `EVT-${Date.now()}`,
      actorId: 'CITIZEN_PORTAL',
      actorName: objectionData.objectorName,
      actorRole: 'CITIZEN',
      eventType: 'OBJECTION_RECORDED',
      entityType: 'Objection',
      entityId: trackingId,
      occurrenceTime: new Date().toISOString(),
      details: `Citizen ${objectionData.objectorName} filed Section 15 objection ${trackingId} for case ${caseId}.`,
    };
    setAuditLog(prev => [auditEvt, ...prev]);

    backendApi.submitCitizenObjection({
      caseId,
      objectorName: objectionData.objectorName,
      contact: objectionData.objectorContact,
      surveyNumber: objectionData.surveyNumber,
      groundsCategory: objectionData.groundsCategory,
      substance: objectionData.substance
    }).catch(() => {});

    return trackingId;
  };

  // Bulk Record Import with Partial-Commit Semantics (Req 30.5, 30.6)
  const runBulkImportSimulation = (rowsCount: number): ImportBatch => {
    const passedCount = Math.floor(rowsCount * 0.95);
    const failedCount = rowsCount - passedCount;

    const newBatch: ImportBatch = {
      id: `BATCH-${Date.now()}`,
      batchNumber: `IMP/PUN/${new Date().getFullYear()}/MIG/${Math.floor(100 + Math.random() * 900)}`,
      submittedBy: `${currentUser.name} (${currentUser.designation})`,
      submittedAt: new Date().toISOString(),
      totalRows: rowsCount,
      committedRows: passedCount,
      rejectedRows: failedCount,
      status: 'COMPLETED',
      rows: [
        {
          rowNumber: 1,
          entityType: 'Land_Parcel',
          surveyNumber: 'Gat No. 201/1',
          ownerName: 'Vithal Shankar Patil',
          extentHa: '3.12',
          share: '1.00',
          status: 'COMMITTED',
        },
        {
          rowNumber: 2,
          entityType: 'Land_Parcel',
          surveyNumber: 'Gat No. 201/2',
          ownerName: 'Sunil Vithal Patil',
          extentHa: '1.45',
          share: '1.00',
          status: 'COMMITTED',
        },
        {
          rowNumber: 3,
          entityType: 'Land_Parcel',
          surveyNumber: 'Gat No. 202',
          ownerName: 'Invalid Co-Ownership Shares Record',
          extentHa: '2.00',
          share: '0.80 + 0.40 = 1.20',
          status: 'REJECTED',
          rejectionRule: 'RULE_PARCEL_SHARE_SUM_EQUALS_ONE',
          errorMessage: 'Shares sum 1.20 exceeds statutory tolerance 1.00 ± 0.0001',
        },
      ],
    };

    setImportBatches(prev => [newBatch, ...prev]);

    const auditEvt: AuditEvent = {
      id: `EVT-${Date.now()}`,
      actorId: currentUser.id,
      actorName: currentUser.name,
      actorRole: currentUser.role,
      eventType: 'IMPORT_BATCH_COMMITTED',
      entityType: 'Import_Batch',
      entityId: newBatch.id,
      occurrenceTime: new Date().toISOString(),
      details: `Bulk Import Batch ${newBatch.batchNumber} executed. ${passedCount} committed, ${failedCount} rejected with partial-commit semantics.`,
    };
    setAuditLog(prev => [auditEvt, ...prev]);

    addToast({
      type: 'success',
      message: `Bulk Import Complete: ${passedCount} records committed to state registry (${failedCount} rejected for review).`,
      messageHi: `थोक आयात पूर्ण: ${passedCount} रिकॉर्ड सफलतापूर्वक दर्ज किए गए।`,
    });

    return newBatch;
  };

  return (
    <AppContext.Provider
      value={{
        currentUser,
        setCurrentUser,
        portalMode,
        setPortalMode,
        language,
        setLanguage,
        isDarkMode,
        setIsDarkMode,
        isHighContrast,
        setIsHighContrast,
        fontScale,
        setFontScale,
        officerTab,
        setOfficerTab,
        currentPortal: portalMode,
        setCurrentPortal: setPortalMode,
        currentOfficerTab: officerTab,
        setCurrentOfficerTab: setOfficerTab,
        cases,
        selectedCaseId,
        setSelectedCaseId,
        selectedCase,
        projects: MOCK_PROJECTS,
        auditLog,
        importBatches,
        dsrRequests,
        modelStats: MOCK_MODEL_STATS,
        transitionCaseStage,
        correctOcrField,
        confirmOcrField,
        resolveValidationIssue,
        waiveValidationIssue,
        disposeObjection,
        createAward,
        disbursePayout,
        overrideCaseRisk,
        actOnRecommendedAction,
        submitDsrRequest,
        disposeDsrRequest,
        submitCitizenObjection,
        runBulkImportSimulation,
        toasts,
        addToast,
        removeToast,
        citizenOtpSent,
        setCitizenOtpSent,
        citizenSessionValid,
        setCitizenSessionValid,
        backendStatus,
        refreshBackendData,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
