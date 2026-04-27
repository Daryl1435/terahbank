import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchCards,
  issueCard,
  freezeCard,
  unfreezeCard,
  updateCardLimits,
  type IssueCardRequest,
  type UpdateLimitsRequest,
} from '@/services/cards';

export function useCards() {
  return useQuery({
    queryKey: ['cards'],
    queryFn: fetchCards,
    staleTime: 60_000,
  });
}

export function useIssueCard() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: IssueCardRequest) => issueCard(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cards'] }),
  });
}

export function useFreezeCard() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cardId: string) => freezeCard(cardId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cards'] }),
  });
}

export function useUnfreezeCard() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cardId: string) => unfreezeCard(cardId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cards'] }),
  });
}

export function useUpdateCardLimits() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ cardId, payload }: { cardId: string; payload: UpdateLimitsRequest }) =>
      updateCardLimits(cardId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cards'] }),
  });
}
