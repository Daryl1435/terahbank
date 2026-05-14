import { getAccessToken } from '@/stores/authStore';

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

// ── Types ──────────────────────────────────────────────────────────────────────

export interface NotificationItem {
  notification_id: string;
  type: string;
  title: string;
  body: string;
  metadata: Record<string, unknown> | null;
  read: boolean;
  created_at: string;
}

export interface NotificationPreferences {
  push_enabled: boolean;
  email_enabled: boolean;
  sms_enabled: boolean;
  in_app_enabled: boolean;
  transaction_alerts: boolean;
  security_alerts: boolean;
  monthly_summary: boolean;
  milestone_alerts: boolean;
  maturity_reminders: boolean;
}

export type UpdatePreferencesPayload = Partial<NotificationPreferences>;

// ── Helpers ────────────────────────────────────────────────────────────────────

const authHeaders = async (): Promise<HeadersInit> => {
  const token = await getAccessToken();
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
};

const apiUrl = (path: string) => `${BASE_URL}/api/v1/notifications${path}`;

// ── Service ────────────────────────────────────────────────────────────────────

export const notificationsService = {
  async listNotifications(): Promise<{ notifications: NotificationItem[]; unread_count: number }> {
    const res = await fetch(apiUrl('/'), { headers: await authHeaders() });
    const json = await res.json();
    if (!res.ok || !json.success) throw new Error(json.message ?? 'Failed to load notifications');
    return json.data;
  },

  async getUnreadCount(): Promise<number> {
    const res = await fetch(apiUrl('/unread-count'), { headers: await authHeaders() });
    const json = await res.json();
    if (!res.ok || !json.success) return 0;
    return json.data.unread_count ?? 0;
  },

  async markRead(notificationId: string): Promise<void> {
    const res = await fetch(apiUrl(`/${notificationId}/read`), {
      method: 'PATCH',
      headers: await authHeaders(),
    });
    const json = await res.json();
    if (!res.ok || !json.success) throw new Error('Failed to mark as read');
  },

  async markAllRead(): Promise<void> {
    const res = await fetch(apiUrl('/read-all'), {
      method: 'POST',
      headers: await authHeaders(),
    });
    const json = await res.json();
    if (!res.ok || !json.success) throw new Error('Failed to mark all as read');
  },

  async getPreferences(): Promise<NotificationPreferences> {
    const res = await fetch(apiUrl('/preferences'), { headers: await authHeaders() });
    const json = await res.json();
    if (!res.ok || !json.success) throw new Error('Failed to load preferences');
    return json.data;
  },

  async updatePreferences(payload: UpdatePreferencesPayload): Promise<NotificationPreferences> {
    const res = await fetch(apiUrl('/preferences'), {
      method: 'PATCH',
      headers: await authHeaders(),
      body: JSON.stringify(payload),
    });
    const json = await res.json();
    if (!res.ok || !json.success) throw new Error('Failed to update preferences');
    return json.data;
  },

  async registerDeviceToken(token: string, platform: 'android' | 'ios'): Promise<void> {
    const res = await fetch(apiUrl('/device-token'), {
      method: 'POST',
      headers: await authHeaders(),
      body: JSON.stringify({ token, platform }),
    });
    const json = await res.json();
    if (!res.ok || !json.success) throw new Error('Failed to register device token');
  },
};
