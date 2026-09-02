export type FilterValues = {
  q:string;
  market:string;
  importance:string;
  status:string;
};

export type SearchParamValues = Record<string, string|string[]|undefined>;

export const emptyFilters:FilterValues = { q:"", market:"", importance:"", status:"" };

export function filtersFromSearchParams(params:SearchParamValues):FilterValues {
  const one = (value:string|string[]|undefined) => Array.isArray(value) ? value[0] ?? "" : value ?? "";
  return {
    q:one(params.q),
    market:one(params.market),
    importance:one(params.importance),
    status:one(params.status),
  };
}

export function appendFilters(params:URLSearchParams, filters:FilterValues):URLSearchParams {
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  return params;
}
