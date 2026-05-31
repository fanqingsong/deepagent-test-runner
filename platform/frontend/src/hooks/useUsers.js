import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getUsers, updateUser, deleteUser } from '../api';
import { useAuth } from '../contexts/AuthContext';

/**
 * Users list with React Query caching and mutations.
 */
export function useUsers({ enabled: enabledProp } = {}) {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const enabled = enabledProp ?? isAuthenticated;

  const query = useQuery({
    queryKey: ['users'],
    queryFn: getUsers,
    enabled,
    staleTime: 5000,
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, userData }) => updateUser(userId, userData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  return {
    users: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    updateUser: updateMutation.mutateAsync,
    deleteUser: deleteMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  };
}
