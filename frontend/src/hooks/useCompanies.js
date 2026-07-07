import { useQuery } from "@tanstack/react-query";

import { companiesApi } from "../api/companies";

/**
 * Fetches the list of companies (leads) discovered by the automation
 * pipeline. Not yet wired into the Companies page — swap the sample
 * data there for this hook once the backend has real records.
 */
export function useCompanies(params = {}) {
  return useQuery({
    queryKey: ["companies", params],
    queryFn: () => companiesApi.list(params),
  });
}
