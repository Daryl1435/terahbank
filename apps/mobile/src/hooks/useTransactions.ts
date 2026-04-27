import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { transactionsService } from '@/services/transactions';
import type { DepositRequest, TransferRequest, WithdrawRequest } from '@/services/transactions';

// ── Read hooks ────────────────────────────────────────────────────────────────

/**
 * FR-037: Searchable, paginated transaction list.
 * Re-fetches on mount so the list is always fresh after a deposit/transfer.
 */
export const useTransactions = (params?: {
  account_id?: string;
  status?: string;
  limit?: number;
}) =>
  useQuery({
    queryKey: ['transactions', params],
    queryFn: () => transactionsService.listTransactions(params),
    staleTime: 10_000,       // 10s — transactions change more often than balances
  });

export const useTransaction = (transactionId: string) =>
  useQuery({
    queryKey: ['transactions', transactionId],
    queryFn: () => transactionsService.getTransaction(transactionId),
    enabled: !!transactionId,
    staleTime: 5_000,
  });

/**
 * FR-041: Real-time status poll — called every 3s while transaction is pending/processing.
 * Set `enabled` to false once status is terminal (success/failed/reversed).
 */
export const useTransactionStatus = (
  transactionId: string,
  enabled: boolean,
) =>
  useQuery({
    queryKey: ['transactions', transactionId, 'status'],
    queryFn: () => transactionsService.pollStatus(transactionId),
    enabled: enabled && !!transactionId,
    refetchInterval: 3_000,          // Poll every 3s
    staleTime: 0,                    // Always re-fetch
    refetchIntervalInBackground: false,
  });

// ── Mutation hooks ────────────────────────────────────────────────────────────

/**
 * FR-038: MTN MoMo deposit — returns 202 with pending transaction.
 * Idempotency key is auto-generated in transactionsService.deposit().
 * NEVER retry on error (double-charge risk).
 */
export const useDeposit = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DepositRequest) => transactionsService.deposit(payload),
    retry: 0,    // Never retry payment mutations
    onSuccess: () => {
      // Invalidate both transactions list and account balances
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
};

/**
 * FR-034/035: Internal transfer — synchronous, immediate result.
 * pin_token must be obtained from authService.verifyPin() immediately before calling.
 */
export const useTransfer = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TransferRequest) => transactionsService.transfer(payload),
    retry: 0,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
};

export const useWithdraw = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: WithdrawRequest) => transactionsService.withdraw(payload),
    retry: 0,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
};
