/** Create / edit one external contact (a customer-side notification recipient). */
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "@tanstack/react-router";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import {
    createExternalContactMutationOptions, updateExternalContactMutationOptions,
    useRetrieveExternalContact,
} from "@/hooks/externalContacts";
import { SetupFormFrame, toastApiError, useAllows } from "@/pages/scheduling/setup/shared";

const LIST = "/settings/notifications/external-contacts";
const FIELDS = ["customer", "email", "name", "role", "non_field_errors"];
// Errors are toasted here with the field the API names, not the global generic toast.
const LOCAL_ERRORS = { suppressGlobalError: true } as const;

export function ExternalContactFormPage() {
    const navigate = useNavigate();
    const params = useParams({ strict: false });
    const id = params.id as string | undefined;
    const mode = id ? "edit" : "create";
    const allows = useAllows();
    const canSave = allows(mode === "edit" ? "change_externalcontact" : "add_externalcontact");

    const queryClient = useQueryClient();
    const { data: existing, isLoading } = useRetrieveExternalContact(id ?? "");
    const createOpts = createExternalContactMutationOptions(queryClient);
    const updateOpts = updateExternalContactMutationOptions(queryClient);
    const create = useMutation({ ...createOpts, meta: { ...createOpts.meta, ...LOCAL_ERRORS } });
    const update = useMutation({ ...updateOpts, meta: { ...updateOpts.meta, ...LOCAL_ERRORS } });

    const { data: companies } = useRetrieveCompanies({ limit: 500, ordering: "name" });
    const customers = useMemo(
        () => (companies?.results ?? []).map((c) => ({ id: String(c.id), name: c.name })),
        [companies],
    );

    const [customer, setCustomer] = useState("");
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [role, setRole] = useState("");
    const [enabled, setEnabled] = useState(true);

    useEffect(() => {
        if (mode !== "edit" || !existing) return;
        setCustomer(String(existing.customer));
        setName(existing.name);
        setEmail(existing.email);
        setRole(existing.role ?? "");
        setEnabled(existing.enabled ?? true);
    }, [mode, existing]);

    function submit() {
        if (!canSave) {
            toast.error("You don't have permission to save external contacts");
            return;
        }
        if (!customer) { toast.error("Pick the customer this contact works for"); return; }
        if (!name.trim()) { toast.error("Enter the contact's name"); return; }
        if (!email.trim()) { toast.error("Enter the contact's email"); return; }
        const payload = { customer, name: name.trim(), email: email.trim(), role: role.trim(), enabled };
        const onSuccess = () => navigate({ to: LIST });
        const onError = (e: unknown) => toastApiError(e, FIELDS);
        if (mode === "edit" && id) update.mutate({ id, data: payload }, { onSuccess, onError });
        else create.mutate(payload, { onSuccess, onError });
    }

    return (
        <SetupFormFrame
            title={mode === "edit" ? "Edit external contact" : "New external contact"}
            description="A person at a customer who receives notifications from customer-scoped rules and schedules."
            backTo={LIST}
            loading={mode === "edit" && isLoading}
            saving={create.isPending || update.isPending}
            submitLabel={mode === "edit" ? "Save changes" : "Create contact"}
            onSubmit={submit}
        >
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Customer</CardTitle>
                    <CardDescription>
                        The company this person works for. Customer-scoped rules for that company can mail them.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Select value={customer} onValueChange={(v) => v && setCustomer(v)}>
                        <SelectTrigger aria-label="Customer"><SelectValue placeholder="Select a customer" /></SelectTrigger>
                        <SelectContent>
                            {customers.map((c) => (
                                <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Contact</CardTitle>
                    <CardDescription>One contact per email at each customer.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1.5">
                        <Label htmlFor="ec-name">Name</Label>
                        <Input id="ec-name" value={name} maxLength={128} onChange={(e) => setName(e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="ec-email">Email</Label>
                        <Input id="ec-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="ec-role">Role</Label>
                        <Input id="ec-role" value={role} maxLength={64} placeholder="e.g. quality, procurement"
                            onChange={(e) => setRole(e.target.value)} />
                        <p className="text-xs text-muted-foreground">A free-form label for what they receive mail about.</p>
                    </div>
                    <div className="flex items-start gap-3 pt-6">
                        <Switch id="ec-enabled" checked={enabled} onCheckedChange={setEnabled} />
                        <div className="space-y-1">
                            <Label htmlFor="ec-enabled">Enabled</Label>
                            <p className="text-xs text-muted-foreground">A disabled contact gets no notifications.</p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </SetupFormFrame>
    );
}
