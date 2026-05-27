import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  notificationsService,
  UpdatePreferencesPayload,
  DEFAULT_PREFERENCES,
} from '@/services/notifications';

const NOTIFICATIONS_KEY = ['notifications'];
const UNREAD_COUNT_KEY = ['notifications', 'unread-count'];
const PREFS_KEY = ['notifications', 'preferences'];

// ── Read hooks ────────────────────────────────────────────────────────────────

export const useNotifications = () =>
  useQuery({
    queryKey: NOTIFICATIONS_KEY,
    queryFn: () => notificationsService.listNotifications(),
    staleTime: 30 * 1000,
  });

export const useUnreadCount = () =>
  useQuery({
    queryKey: UNREAD_COUNT_KEY,
    queryFn: () => notificationsService.getUnreadCount(),
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000, // poll every 60s for live bell badge
  });

export const useNotificationPreferences = () =>
  useQuery({
    queryKey: PREFS_KEY,
    queryFn: () => notificationsService.getPreferences(),
    staleTime: 5 * 60 * 1000,
    initialData: DEFAULT_PREFERENCES,
  });

// ── Mutation hooks ─────────────────────────────────────────────────────────────

export const useMarkRead = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notificationsService.markRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
      qc.invalidateQueries({ queryKey: UNREAD_COUNT_KEY });
    },
  });
};

export const useMarkAllRead = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationsService.markAllRead(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
      qc.invalidateQueries({ queryKey: UNREAD_COUNT_KEY });
    },
  });
};

export const useUpdateNotificationPreferences = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdatePreferencesPayload) =>
      notificationsService.updatePreferences(payload),
    onMutate: async (payload) => {
      await qc.cancelQueries({ queryKey: PREFS_KEY });
      const prev = qc.getQueryData(PREFS_KEY);
      qc.setQueryData(PREFS_KEY, (old: typeof DEFAULT_PREFERENCES) => ({ ...old, ...payload }));
      return { prev };
    },
    onError: (_err, _payload, context) => {
      if (context?.prev) qc.setQueryData(PREFS_KEY, context.prev);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: PREFS_KEY });
    },
  });
};
