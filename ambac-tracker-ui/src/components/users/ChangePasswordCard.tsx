/**
 * Self-service password change for the logged-in user (mounted on /profile).
 *
 * Hits dj-rest-auth's POST /auth/password/change/. The backend requires the
 * current password (REST_AUTH OLD_PASSWORD_FIELD_ENABLED), so a hijacked open
 * session can't silently reset the password. Client-side rules mirror Django's
 * AUTH_PASSWORD_VALIDATORS for fast feedback; the server stays authoritative.
 */
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { Loader2, KeyRound } from "lucide-react";
import { toast } from "sonner";

import { api } from "@/lib/api/generated";
import { getCookie } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { PasswordInput } from "@/components/ui/password-input";

const schema = z
    .object({
        old_password: z.string().min(1, "Enter your current password"),
        new_password1: z
            .string()
            .min(8, "Password must be at least 8 characters")
            .regex(
                /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                "Password must contain at least one uppercase letter, one lowercase letter, and one number",
            ),
        new_password2: z.string(),
    })
    .refine((d) => d.new_password1 === d.new_password2, {
        message: "Passwords don't match",
        path: ["new_password2"],
    });

type ChangePasswordForm = z.infer<typeof schema>;

export function ChangePasswordCard() {
    const form = useForm<ChangePasswordForm>({
        resolver: zodResolver(schema),
        defaultValues: { old_password: "", new_password1: "", new_password2: "" },
    });

    const mutation = useMutation({
        mutationFn: (data: ChangePasswordForm) =>
            api.auth_password_change_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
        onSuccess: () => {
            toast.success("Password changed");
            form.reset();
        },
        onError: (error: unknown) => {
            // eslint-disable-next-line local/no-as-any -- axios error body needs verbose narrowing
            const apiError = (error as any)?.response?.data;
            let handled = false;
            if (apiError?.old_password?.[0]) {
                form.setError("old_password", { message: apiError.old_password[0] });
                handled = true;
            }
            if (apiError?.new_password1?.[0]) {
                form.setError("new_password1", { message: apiError.new_password1[0] });
                handled = true;
            }
            if (apiError?.new_password2?.[0]) {
                form.setError("new_password2", { message: apiError.new_password2[0] });
                handled = true;
            }
            if (!handled) {
                toast.error("Could not change password", {
                    description:
                        apiError?.detail ??
                        (error instanceof Error ? error.message : undefined),
                });
            }
        },
    });

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                    <KeyRound className="h-5 w-5" />
                    Change password
                </CardTitle>
                <CardDescription>
                    Enter your current password and choose a new one.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <Form {...form}>
                    <form
                        onSubmit={form.handleSubmit((d) => mutation.mutate(d))}
                        className="space-y-4 max-w-sm"
                    >
                        <FormField
                            control={form.control}
                            name="old_password"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Current password</FormLabel>
                                    <FormControl>
                                        <PasswordInput autoComplete="current-password" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="new_password1"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>New password</FormLabel>
                                    <FormControl>
                                        <PasswordInput autoComplete="new-password" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="new_password2"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Confirm new password</FormLabel>
                                    <FormControl>
                                        <PasswordInput autoComplete="new-password" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <Button type="submit" disabled={mutation.isPending}>
                            {mutation.isPending && (
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            )}
                            Change password
                        </Button>
                    </form>
                </Form>
            </CardContent>
        </Card>
    );
}
