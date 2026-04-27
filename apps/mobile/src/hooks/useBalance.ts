import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { accountsService, OpenProjectAccountRequest, OpenStandardAccountRequest, OpenTermDepositRequest } from '@/services/accounts';

// ── Read hooks ────────────────────────────────────────────────────────────────

export const useAccounts = () =>
  useQuery({
    queryKey: ['accounts'],
    queryFn: () => accountsService.listAccounts(),
    staleTime: 30 * 1000, // Match server-side Redis balance cache (30s TTL)
  });

export const useAccount = (accountId: string) =>
  useQuery({
    queryKey: ['accounts', accountId],
    queryFn: () => accountsService.getAccount(accountId),
    staleTime: 30 * 1000,
    enabled: !!accountId,
  });

// FR-046: Total balance = sum of all account balances (BIGINT, smallest XAF unit)
export const useTotalBalance = () => {
  const { data, ...rest } = useAccounts();

  const accounts = data?.accounts ?? null;
  // Use server-computed total_balance when available — more accurate than client sum
  const totalBalance = data?.total_balance ?? null;

  return { totalBalance, accounts, ...rest };
};

// ── Mutation hooks ────────────────────────────────────────────────────────────

// FR-010/011: Open Standard Savings Account
export const useOpenStandardAccount = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OpenStandardAccountRequest) =>
      accountsService.openStandardAccount(payload),
    onSuccess: () => {
      // Invalidate accounts list so the new account appears immediately
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
};

// FR-016/022: Open Project Account (Vault)
export const useOpenProjectAccount = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OpenProjectAccountRequest) =>
      accountsService.openProjectAccount(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
};

// FR-023: Open Term Deposit
export const useOpenTermDeposit = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OpenTermDepositRequest) =>
      accountsService.openTermDeposit(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
};
