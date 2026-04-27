import { useQuery } from '@tanstack/react-query';

interface FeatureFlags {
  mtnMomo: boolean;
  orangeMoney: boolean;
  virtualCard: boolean;
  insurance: boolean;
  autoSave: boolean;
  maintenanceMode: boolean;
}

const DEFAULT_FLAGS: FeatureFlags = {
  mtnMomo: true,
  orangeMoney: false,
  virtualCard: true,
  insurance: false,
  autoSave: false,
  maintenanceMode: false,
};

const fetchFlags = async (): Promise<FeatureFlags> => {
  const res = await fetch(`${process.env.EXPO_PUBLIC_API_BASE_URL}/config/features`);
  const json = await res.json();
  return json.data.flags;
};

export const useFeatureFlags = (): FeatureFlags => {
  const { data } = useQuery({
    queryKey: ['feature-flags'],
    queryFn: fetchFlags,
    staleTime: 5 * 60 * 1000,   // Cache 5 minutes
    gcTime: 30 * 60 * 1000,
  });
  return data ?? DEFAULT_FLAGS;
};
