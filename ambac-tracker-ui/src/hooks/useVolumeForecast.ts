import { useMutation, useQuery, useQueryClient, queryOptions } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import type { Schema } from "@/lib/api/types";

const csrf = () => ({ "X-CSRFToken": getCookie("csrftoken") });

export type ForecastGrid = Schema<"VolumeForecastGrid">;
export type ForecastImportResult = Schema<"VolumeForecastImportResult">;

export const forecastGridOptions = (months = 24) =>
  queryOptions({
    queryKey: ["planning", "volume-forecast", months],
    queryFn: () => api.api_VolumeForecasts_grid_retrieve({ queries: { months } }),
  });

export function useForecastGrid(months = 24) {
  return useQuery(forecastGridOptions(months));
}

/** A forecast edit changes the capacity and material outlook too. */
const invalidate = (qc: ReturnType<typeof useQueryClient>) => {
  qc.invalidateQueries({ queryKey: ["planning", "volume-forecast"] });
  qc.invalidateQueries({ queryKey: ["planning", "capacity-load"] });
};

/** Set cells; null or 0 clears one. All or nothing. */
export function useSetForecastCells() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cells: { part_type: string; month: string; quantity: number | null }[]) =>
      api.api_VolumeForecasts_set_cells_create({ cells }, { headers: csrf() }),
    onSuccess: () => invalidate(qc),
  });
}

/** Upload a forecast sheet: each row replaces the month it names. */
export function useImportForecast() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) =>
      api.api_VolumeForecasts_import_sheet_create({ file }, { headers: csrf() }),
    onSuccess: () => invalidate(qc),
  });
}
