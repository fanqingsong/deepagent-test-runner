import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSchedules, deleteSchedule } from '../api';
import authService from '../services/authService';
import { useAuth } from '../contexts/AuthContext';

/**
 * Schedules list with React Query caching and mutations.
 */
export function useSchedules({ enabled: enabledProp } = {}) {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const enabled = enabledProp ?? isAuthenticated;

  const query = useQuery({
    queryKey: ['schedules'],
    queryFn: async () => {
      if (authService.isAuthenticated()) {
        await authService.ensureValidToken();
      }
      return getSchedules();
    },
    enabled,
    staleTime: 5000,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSchedule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
  });

  const schedules = query.data?.items ?? query.data ?? [];

  return {
    schedules,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    deleteSchedule: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
  };
}
