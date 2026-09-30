/**
 * Notification type definitions for the BHUMISETU platform.
 * Covers statutory notices, system alerts, and user notifications.
 */

/** Statutory notice types under RFCTLARR Act 2013 */
export type StatutoryNoticeType =
  | 'section_4_preliminary'
  | 'section_9_hearing'
  | 'section_11_notification'
  | 'section_12_survey'
  | 'section_15_objection_hearing'
  | 'section_16_report'
  | 'section_19_declaration'
  | 'section_21_notice_to_persons'
  | 'section_23_award'
  | 'section_25_possession'
  | 'section_38_temporary';

/** System notification priority levels */
export type NotificationPriority = 'urgent' | 'high' | 'normal' | 'low';

/** Notification delivery channels */
export type DeliveryChannel = 'sms' | 'email' | 'in_app' | 'postal' | 'gazette';

/** Delivery status tracking */
export type DeliveryStatus =
  | 'pending'
  | 'sent'
  | 'delivered'
  | 'read'
  | 'failed'
  | 'bounced';

/** Notification record */
export interface NotificationRecord {
  id: string;
  caseId: string;
  recipientId: string;
  recipientType: 'citizen' | 'officer' | 'system';
  type: StatutoryNoticeType | 'system_alert' | 'reminder' | 'update';
  title: string;
  message: string;
  priority: NotificationPriority;
  channels: DeliveryChannel[];
  deliveryStatuses: Record<DeliveryChannel, DeliveryStatus>;
  scheduledAt?: string;
  sentAt?: string;
  readAt?: string;
  expiresAt?: string;
  metadata?: Record<string, unknown>;
  createdAt: string;
}

/** Notification preferences for a user */
export interface NotificationPreferences {
  userId: string;
  enableEmail: boolean;
  enableSMS: boolean;
  enableInApp: boolean;
  quietHoursStart?: string; // HH:MM format
  quietHoursEnd?: string;
  language: 'en' | 'hi' | 'mr';
  digestFrequency: 'immediate' | 'daily' | 'weekly';
}

/** Gazette publication record for statutory notices */
export interface GazettePublication {
  noticeId: string;
  gazetteNumber: string;
  publicationDate: string;
  section: string;
  pageNumbers: string;
  district: string;
  language: 'en' | 'hi' | 'mr';
  digitalCopyUrl?: string;
}
