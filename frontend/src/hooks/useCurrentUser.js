import { useQuery } from "@tanstack/react-query";

import { authApi } from "../api/auth";

/**
 * Example React Query hook. Demonstrates the pattern used for
 * data-fetching hooks throughout the app — copy this shape for
 * new domain hooks (e.g. useProjects, useCampaigns).
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: ["currentUser"],
    queryFn: authApi.me,
    staleTime: 5 * 60 * 1000,
  });
}
