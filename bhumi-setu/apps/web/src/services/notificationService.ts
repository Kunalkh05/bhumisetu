/**
 * Notification service for the BHUMISETU platform.
 * Handles API calls for notification management.
 */

import { API_ROUTES } from '../utils/constants';
import type { NotificationRecord, NotificationPreferences } from '../types/notification';

const API_BASE = import.meta.env.VITE_API_URL || '';

interface NotificationListResponse {
  data: NotificationRecord[];
  pagination: {
    total: number;
    page: number;
    pageSize: number;
    hasMore: boolean;
  };
}

/**
 * Fetch notifications for the current user.
 */
export async function getNotifications(
  page: number = 1,
  pageSize: number = 20,
  unreadOnly: boolean = false,
): Promise<NotificationListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (unreadOnly) {
    params.set('unread_only', 'true');
  }

  const response = await fetch(
    `${API_BASE}/api/v1/notifications?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        'Content-Type': 'application/json',
      },
    },
  );

  if (!response.ok) {
    throw response;
  }

  return response.json();
}

/**
 * Mark a notification as read.
 */
export async function markAsRead(notificationId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/v1/notifications/${notificationId}/read`,
    {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        'Content-Type': 'application/json',
      },
    },
  );

  if (!response.ok) {
    throw response;
  }
}

/**
 * Mark all notifications as read.
 */
export async function markAllAsRead(): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/v1/notifications/read-all`,
    {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        'Content-Type': 'application/json',
      },
    },
  );

  if (!response.ok) {
    throw response;
  }
}

/**
 * Get notification preferences for the current user.
 */
export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  const response = await fetch(
    `${API_BASE}/api/v1/notifications/preferences`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        'Content-Type': 'application/json',
      },
    },
  );

  if (!response.ok) {
    throw response;
  }

  return response.json();
}

/**
 * Update notification preferences.
 */
export async function updateNotificationPreferences(
  prefs: Partial<NotificationPreferences>,
): Promise<NotificationPreferences> {
  const response = await fetch(
    `${API_BASE}/api/v1/notifications/preferences`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(prefs),
    },
  );

  if (!response.ok) {
    throw response;
  }

  return response.json();
}

/**
 * Get count of unread notifications (for badge display).
 */
export async function getUnreadCount(): Promise<number> {
  const response = await fetch(
    `${API_BASE}/api/v1/notifications/unread-count`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      },
    },
  );

  if (!response.ok) {
    throw response;
  }

  const data = await response.json();
  return data.count;
}
