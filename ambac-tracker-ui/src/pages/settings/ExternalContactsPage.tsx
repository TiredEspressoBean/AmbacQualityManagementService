/**
 * External contacts — customer-side people who receive notifications from
 * customer-scoped rules and schedules. Until this page existed they could only be
 * picked in the rule editors, never created.
 *
 * Viewing needs `view_externalcontact`; the add / change / delete buttons each show
 * only for the matching model perm (the API enforces the same, TenantModelPermissions).
 *
 * Delete soft-archives the row, and the (customer, email) pair stays unique across
 * archived rows, so a deleted contact's email can't be re-added at that customer.
 * Disabling is the reversible way to stop mail.
 */
import { useMemo, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Pencil, Trash2, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
    AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { DataIOButtons } from "@/components/data-io-buttons";
import { ModelEditorPage, createColumnHelper } from "@/pages/editors/ModelEditorPage";
import { useRetrieveCompanies } from "@/hooks/useRetrieveCompanies";
import {
    externalContactsKeys, useDeleteExternalContact, useExternalContacts,
    useUpdateExternalContact, type ExternalContact,
} from "@/hooks/externalContacts";
import { useAllows } from "@/pages/scheduling/setup/shared";

const LIST = "/settings/notifications/external-contacts";
const col = createColumnHelper<ExternalContact>();

function contactsListHookFor(customer: string | null) {
    return function useContactsList({ offset, limit, ordering, search }: {
        offset: number; limit: number; ordering?: string; search?: string;
        filters?: Record<string, string>;
    }) {
        return useExternalContacts({
            offset, limit,
            ...(ordering ? { ordering } : {}),
            ...(search ? { search } : {}),
            ...(customer ? { customer } : {}),
        });
    };
}

function useCustomerOptions() {
    const { data } = useRetrieveCompanies({ limit: 500, ordering: "name" });
    return useMemo(
        () => (data?.results ?? []).map((c) => ({ id: String(c.id), name: c.name })),
        [data],
    );
}

export function ExternalContactsPage() {
    const navigate = useNavigate();
    const allows = useAllows();
    const canView = allows("view_externalcontact");
    const canAdd = allows("add_externalcontact");
    const canChange = allows("change_externalcontact");
    const canDelete = allows("delete_externalcontact");

    const [customer, setCustomer] = useState<string | null>(null);
    const [deleting, setDeleting] = useState<ExternalContact | null>(null);
    const customers = useCustomerOptions();
    const customerName = useMemo(
        () => new Map(customers.map((c) => [c.id, c.name])),
        [customers],
    );

    const update = useUpdateExternalContact();
    const del = useDeleteExternalContact();

    const back = (
        <Link
            to="/settings/notification-rules"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to Notifications
        </Link>
    );

    if (!canView) {
        return (
            <div className="space-y-4 p-6">
                {back}
                <p className="text-sm text-muted-foreground">
                    You don't have permission to view external contacts.
                </p>
            </div>
        );
    }

    const customerFilter = (
        <div className="flex items-center gap-1">
            <Select value={customer ?? "__all__"} onValueChange={(v) => setCustomer(v === "__all__" ? null : v)}>
                <SelectTrigger className="w-[200px]" aria-label="Filter by customer">
                    <SelectValue placeholder="All customers" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="__all__">All customers</SelectItem>
                    {customers.map((c) => (
                        <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                    ))}
                </SelectContent>
            </Select>
            {customer && (
                <Button variant="ghost" size="icon" aria-label="Clear customer filter" onClick={() => setCustomer(null)}>
                    <X className="h-4 w-4" />
                </Button>
            )}
        </div>
    );

    return (
        <>
            <ModelEditorPage
                title="External Contacts"
                useList={contactsListHookFor(customer)}
                listQueryKey={externalContactsKeys.all}
                showDetailsLink={false}
                sortOptions={[
                    { label: "Name (A-Z)", value: "name" },
                    { label: "Name (Z-A)", value: "-name" },
                    { label: "Newest", value: "-created_at" },
                    { label: "Recently updated", value: "-updated_at" },
                ]}
                headerContent={
                    <div className="space-y-2">
                        {back}
                        <p className="text-sm text-muted-foreground">
                            People at a customer who receive notifications from customer-scoped
                            rules and schedules. A disabled contact stays in the list but gets no mail.
                        </p>
                    </div>
                }
                extraToolbarContent={
                    <>
                        {customerFilter}
                        <DataIOButtons
                            endpoint="notifications/external-contacts"
                            displayName="External Contacts"
                            invalidateKeys={[externalContactsKeys.all]}
                            allowImport={canAdd || canChange}
                            {...(customer ? { queryParams: { customer } } : {})}
                        />
                    </>
                }
                columns={[
                    col({ header: "Name", priority: 1, renderCell: (c) => <span className="font-medium">{c.name}</span> }),
                    col({ header: "Email", priority: 1, renderCell: (c) => c.email }),
                    col({
                        header: "Customer",
                        priority: 1,
                        renderCell: (c) => customerName.get(String(c.customer)) ?? <span className="text-muted-foreground">—</span>,
                    }),
                    col({
                        header: "Role",
                        priority: 2,
                        renderCell: (c) => c.role
                            ? <Badge variant="secondary">{c.role}</Badge>
                            : <span className="text-muted-foreground">—</span>,
                    }),
                    col({
                        header: "Enabled",
                        priority: 1,
                        renderCell: (c) => (
                            <Switch
                                checked={c.enabled ?? true}
                                disabled={!canChange || update.isPending}
                                aria-label={`${c.enabled ? "Disable" : "Enable"} ${c.name}`}
                                onCheckedChange={(enabled) => update.mutate({ id: c.id, data: { enabled } })}
                            />
                        ),
                    }),
                ]}
                renderActions={(c) => (
                    <>
                        {canChange && (
                            <Button size="icon" variant="ghost" aria-label={`Edit ${c.name}`}
                                onClick={() => navigate({ to: "/settings/notifications/external-contacts/$id/edit", params: { id: c.id } })}>
                                <Pencil className="h-4 w-4" />
                            </Button>
                        )}
                        {canDelete && (
                            <Button size="icon" variant="ghost" className="text-destructive" aria-label={`Delete ${c.name}`}
                                onClick={() => setDeleting(c)}>
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        )}
                    </>
                )}
                {...(canAdd ? { onCreate: () => navigate({ to: `${LIST}/new` }) } : {})}
            />

            <AlertDialog open={!!deleting} onOpenChange={(o) => !o && setDeleting(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete {deleting?.name}?</AlertDialogTitle>
                        <AlertDialogDescription>
                            The contact is removed from every rule and schedule picker, and this email
                            can't be added again at the same customer. To stop mail for now, disable the
                            contact instead.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        {deleting?.enabled !== false && canChange && (
                            <Button variant="outline" onClick={() => {
                                if (deleting) update.mutate({ id: deleting.id, data: { enabled: false } });
                                setDeleting(null);
                            }}>
                                Disable instead
                            </Button>
                        )}
                        <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            onClick={() => {
                                if (deleting) del.mutate(deleting.id);
                                setDeleting(null);
                            }}
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}
