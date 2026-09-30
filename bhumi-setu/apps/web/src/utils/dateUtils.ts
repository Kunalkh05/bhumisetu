/**
 * Date and time utility functions for the BHUMISETU platform.
 *
 * Handles Indian Standard Time (IST) formatting, statutory deadline
 * calculations, and working day computations per Indian government
 * holiday calendar.
 */

/**
 * Indian national holidays (gazetted) for 2026.
 * Used for working day calculations in statutory timelines.
 */
const GAZETTED_HOLIDAYS_2026: string[] = [
  '2026-01-26', // Republic Day
  '2026-03-10', // Maha Shivaratri
  '2026-03-17', // Holi
  '2026-03-30', // Id-ul-Fitr
  '2026-04-02', // Good Friday
  '2026-04-06', // Ram Navami
  '2026-04-14', // Dr. Ambedkar Jayanti
  '2026-04-21', // Mahavir Jayanti
  '2026-05-01', // May Day
  '2026-05-25', // Buddha Purnima
  '2026-06-06', // Id-ul-Zuha (Bakrid)
  '2026-07-06', // Muharram
  '2026-08-15', // Independence Day
  '2026-08-16', // Janmashtami
  '2026-09-05', // Milad-un-Nabi
  '2026-10-02', // Mahatma Gandhi Jayanti
  '2026-10-20', // Dussehra
  '2026-11-09', // Diwali (Deepavali)
  '2026-11-11', // Guru Nanak Jayanti
  '2026-12-25', // Christmas Day
];

/**
 * Format a date in Indian standard format (DD/MM/YYYY).
 */
export function formatDateIndian(date: Date): string {
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
}

/**
 * Format a date with time in IST timezone.
 */
export function formatDateTimeIST(date: Date): string {
  return date.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

/**
 * Format a relative time string (e.g., "2 days ago", "in 5 hours").
 */
export function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(Math.abs(diffMs) / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffMonths = Math.floor(diffDays / 30);
  const diffYears = Math.floor(diffDays / 365);

  const isFuture = diffMs < 0;
  const prefix = isFuture ? 'in ' : '';
  const suffix = isFuture ? '' : ' ago';

  if (diffYears > 0) return `${prefix}${diffYears} year${diffYears > 1 ? 's' : ''}${suffix}`;
  if (diffMonths > 0) return `${prefix}${diffMonths} month${diffMonths > 1 ? 's' : ''}${suffix}`;
  if (diffDays > 0) return `${prefix}${diffDays} day${diffDays > 1 ? 's' : ''}${suffix}`;
  if (diffHours > 0) return `${prefix}${diffHours} hour${diffHours > 1 ? 's' : ''}${suffix}`;
  if (diffMinutes > 0) return `${prefix}${diffMinutes} minute${diffMinutes > 1 ? 's' : ''}${suffix}`;
  return 'just now';
}

/**
 * Check if a date falls on a weekend (Saturday or Sunday).
 */
export function isWeekend(date: Date): boolean {
  const day = date.getDay();
  return day === 0 || day === 6;
}

/**
 * Check if a date is a gazetted holiday.
 */
export function isGazettedHoliday(date: Date): boolean {
  const dateStr = date.toISOString().split('T')[0];
  return GAZETTED_HOLIDAYS_2026.includes(dateStr);
}

/**
 * Check if a date is a working day (not weekend, not holiday).
 */
export function isWorkingDay(date: Date): boolean {
  return !isWeekend(date) && !isGazettedHoliday(date);
}

/**
 * Add a specified number of working days to a date.
 * Skips weekends and gazetted holidays.
 *
 * Used for calculating statutory deadlines under RFCTLARR Act.
 */
export function addWorkingDays(startDate: Date, workingDays: number): Date {
  const result = new Date(startDate);
  let daysAdded = 0;

  while (daysAdded < workingDays) {
    result.setDate(result.getDate() + 1);
    if (isWorkingDay(result)) {
      daysAdded++;
    }
  }

  return result;
}

/**
 * Count working days between two dates (exclusive of both endpoints).
 */
export function countWorkingDays(start: Date, end: Date): number {
  let count = 0;
  const current = new Date(start);
  current.setDate(current.getDate() + 1);

  while (current < end) {
    if (isWorkingDay(current)) {
      count++;
    }
    current.setDate(current.getDate() + 1);
  }

  return count;
}

/**
 * Calculate statutory deadline dates for key RFCTLARR milestones.
 *
 * Section 11: Preliminary notification
 * Section 15: Hearing objections (within 60 days of Section 11)
 * Section 19: Declaration (within 12 months of Section 11)
 * Section 23: Award (within 12 months of Section 19)
 */
export function calculateStatutoryDeadlines(section11Date: Date) {
  return {
    section11: section11Date,
    section15Deadline: addWorkingDays(section11Date, 60),
    section19Deadline: new Date(
      section11Date.getFullYear() + 1,
      section11Date.getMonth(),
      section11Date.getDate(),
    ),
    section23Deadline: new Date(
      section11Date.getFullYear() + 2,
      section11Date.getMonth(),
      section11Date.getDate(),
    ),
  };
}
