import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { insuranceService } from '@/services/insurance';

export function useInsuranceProducts() {
  return useQuery({
    queryKey: ['insurance', 'products'],
    queryFn: () => insuranceService.listProducts(),
    staleTime: 6 * 60 * 60 * 1000, // 6h — matches Redis catalog TTL
  });
}

export function useMyPolicies() {
  return useQuery({
    queryKey: ['insurance', 'policies'],
    queryFn: () => insuranceService.listMyPolicies(),
    staleTime: 60_000,
  });
}

export function useEnroll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (productId: string) => insuranceService.enroll(productId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['insurance', 'policies'] }),
  });
}

export function useCancelPolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (policyId: string) => insuranceService.cancelPolicy(policyId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['insurance', 'policies'] }),
  });
}
