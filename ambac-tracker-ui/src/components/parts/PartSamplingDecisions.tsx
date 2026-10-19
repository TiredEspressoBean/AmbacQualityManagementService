import { queryOptions, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/generated";

const partSamplingDecisionsOptions = (partId: string) =>
    queryOptions({
        queryKey: ["part-sampling-decisions", partId] as const,
        queryFn: () => api.api_Parts_sampling_decisions_list({ params: { id: partId } }),
    });

/**
 * Why this part was — or wasn't — sampled for inspection: each logged decision with the
 * rule behind it ("Selected by every 5th part", "Not selected — no rule in … chose it").
 * The question an auditor asks of an uninspected part. Newest first.
 */
export function PartSamplingDecisions({ partId }: { partId: string }) {
    const { data, isLoading } = useQuery(partSamplingDecisionsOptions(partId));
    if (isLoading || !data || data.length === 0) return null;
    return (
        <div className="space-y-1 rounded-md border bg-muted/30 p-3">
            <div className="text-xs font-medium text-muted-foreground">Sampling decisions</div>
            <ul className="space-y-0.5 text-xs">
                {data.map((d) => (
                    <li key={d.id} className="flex flex-wrap items-baseline gap-x-2">
                        <span className={d.selected ? "font-medium" : ""}>{d.summary}</span>
                        <span className="text-muted-foreground">
                            {d.ruleset_type === "FALLBACK" ? "fallback ruleset · " : ""}
                            {new Date(d.timestamp).toLocaleString()}
                        </span>
                    </li>
                ))}
            </ul>
        </div>
    );
}
