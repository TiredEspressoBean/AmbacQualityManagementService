import { format } from "date-fns";
import { CalendarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RequiredMark } from "@/components/ui/required-mark";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { parseDateOnly } from "@/lib/date-only";
import { cn } from "@/lib/utils";

/** The concession a Use As Is or Repair decision is refused without: what the server's
 *  decide takes — a reference (required) and the date it was given (today if left
 *  blank). The same two fields wherever such a decision is made (disposition form, NCR
 *  decide); the server marks it required and received when it records the decision. */
export function ConcessionFields({ decision, reference, onReference, date, onDate, locked, idPrefix = "concession" }: {
    decision: string;
    reference: string;
    onReference: (v: string) => void;
    /** YYYY-MM-DD, or empty. */
    date: string | null | undefined;
    onDate: (v: string | undefined) => void;
    /** Recorded with the decision: shown, not edited. */
    locked?: boolean;
    idPrefix?: string;
}) {
    return (
        <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
            <p className="text-sm text-muted-foreground">
                {decision === "REPAIR" ? "Repair" : "Use As Is"} accepts nonconforming product: it needs a
                customer or design concession.
                {locked && " It was recorded with the decision and can't be changed now."}
            </p>
            <div className="space-y-2">
                <Label htmlFor={`${idPrefix}-reference`}>
                    Concession reference<RequiredMark />
                </Label>
                <Input id={`${idPrefix}-reference`} value={reference} disabled={locked}
                       onChange={(e) => onReference(e.target.value)}
                       placeholder="PO#, email reference, or approval document number" />
            </div>
            <div className="flex flex-col space-y-2">
                <Label>Concession date <span className="text-muted-foreground">(today if blank)</span></Label>
                <Popover>
                    <PopoverTrigger asChild>
                        <Button variant="outline" disabled={locked}
                                className={cn("w-[240px] pl-3 text-left font-normal", !date && "text-muted-foreground")}>
                            {date ? format(parseDateOnly(date), "PPP") : <span>Pick a date</span>}
                            <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                        </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                            mode="single"
                            selected={date ? parseDateOnly(date) : undefined}
                            // A DateField: the local YYYY-MM-DD, not a UTC timestamp.
                            onSelect={(d) => onDate(d ? format(d, "yyyy-MM-dd") : undefined)}
                            initialFocus
                        />
                    </PopoverContent>
                </Popover>
            </div>
        </div>
    );
}
