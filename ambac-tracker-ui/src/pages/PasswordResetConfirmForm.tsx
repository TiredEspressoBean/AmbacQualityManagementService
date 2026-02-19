import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api/generated'
import { getCookie } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Mail, CheckCircle, AlertCircle } from 'lucide-react'
import { PasswordInput } from '@/components/ui/password-input'

// Helper to extract user-friendly error messages from API errors
function getPasswordResetErrorMessage(error: unknown, fallback: string): string {
    const apiError = (error as any)?.response?.data;
    if (apiError?.email?.[0]) return apiError.email[0];
    if (apiError?.new_password1?.[0]) return apiError.new_password1[0];
    if (apiError?.new_password2?.[0]) return apiError.new_password2[0];
    if (apiError?.non_field_errors?.[0]) return apiError.non_field_errors[0];
    if (apiError?.detail) return apiError.detail;
    if (apiError?.token?.[0]) return "Invalid or expired reset link";
    if (apiError?.uid?.[0]) return "Invalid reset link";
    if (error instanceof Error) return error.message;
    return fallback;
}

// 🔗 Hook Types
type PasswordResetRequestInput = Parameters<typeof api.auth_password_reset_create>[0]
type PasswordResetRequestResponse = Awaited<ReturnType<typeof api.auth_password_reset_create>>

type PasswordResetConfirmInput = Parameters<typeof api.auth_password_reset_confirm_create>[0]
type PasswordResetConfirmResponse = Awaited<ReturnType<typeof api.auth_password_reset_confirm_create>>

// 🪝 Custom Hooks
export const usePasswordResetRequest = () => {
    return useMutation<PasswordResetRequestResponse, unknown, PasswordResetRequestInput>({
        mutationFn: (data) =>
            api.auth_password_reset_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
    })
}

export const usePasswordResetConfirm = () => {
    return useMutation<PasswordResetConfirmResponse, unknown, PasswordResetConfirmInput>({
        mutationFn: (data) =>
            api.auth_password_reset_confirm_create(data, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            }),
    })
}

// 📝 Form Schemas
const passwordResetRequestSchema = z.object({
    email: z.string().min(1, 'Email is required').email('Invalid email address'),
})

const passwordResetConfirmSchema = z
    .object({
        new_password1: z
            .string()
            .min(8, 'Password must be at least 8 characters')
            .regex(
                /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                'Password must contain at least one uppercase letter, one lowercase letter, and one number'
            ),
        new_password2: z.string(),
    })
    .refine((data) => data.new_password1 === data.new_password2, {
        message: "Passwords don't match",
        path: ['new_password2'],
    })

type PasswordResetRequestForm = z.infer<typeof passwordResetRequestSchema>
type PasswordResetConfirmForm = z.infer<typeof passwordResetConfirmSchema>

// 🧩 Components
interface PasswordResetRequestProps {
    onSuccess?: () => void
}

export const PasswordResetRequest = ({ onSuccess }: PasswordResetRequestProps) => {
    const mutation = usePasswordResetRequest()

    const form = useForm<PasswordResetRequestForm>({
        resolver: zodResolver(passwordResetRequestSchema),
        defaultValues: {
            email: '',
        },
    })

    const onSubmit = (data: PasswordResetRequestForm) => {
        mutation.mutate(
            { email: data.email },
            {
                onSuccess: () => {
                    onSuccess?.()
                },
            }
        )
    }

    if (mutation.isSuccess) {
        return (
            <div className="flex flex-col min-h-[50vh] h-full w-full items-center justify-center px-4">
                <Card className="mx-auto max-w-sm">
                    <CardContent className="pt-6">
                        <Alert>
                            <CheckCircle className="h-4 w-4" />
                            <AlertDescription>
                                Password reset email sent! Check your inbox for further instructions.
                            </AlertDescription>
                        </Alert>
                    </CardContent>
                </Card>
            </div>
        )
    }

    return (
        <div className="flex flex-col min-h-[50vh] h-full w-full items-center justify-center px-4">
            <Card className="mx-auto max-w-sm">
                <CardHeader>
                    <CardTitle className="text-2xl">Reset your password</CardTitle>
                    <CardDescription>
                        Enter your email address and we'll send you a link to reset your password.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                            <div className="grid gap-4">
                                <FormField
                                    control={form.control}
                                    name="email"
                                    render={({ field }) => (
                                        <FormItem className="grid gap-2">
                                            <FormLabel htmlFor="email">Email</FormLabel>
                                            <FormControl>
                                                <Input
                                                    id="email"
                                                    placeholder="Enter your email"
                                                    type="email"
                                                    autoComplete="email"
                                                    {...field}
                                                    disabled={mutation.isPending}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                {mutation.isError && (
                                    <Alert variant="destructive">
                                        <AlertCircle className="h-4 w-4" />
                                        <AlertDescription>
                                            {getPasswordResetErrorMessage(mutation.error, 'An error occurred while sending the reset email')}
                                        </AlertDescription>
                                    </Alert>
                                )}

                                <Button type="submit" className="w-full" disabled={mutation.isPending}>
                                    {mutation.isPending ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Sending...
                                        </>
                                    ) : (
                                        <>
                                            <Mail className="mr-2 h-4 w-4" />
                                            Send reset email
                                        </>
                                    )}
                                </Button>
                            </div>
                        </form>
                    </Form>
                </CardContent>
            </Card>
        </div>
    )
}

interface PasswordResetConfirmProps {
    token: string
    uid: string
    onSuccess?: () => void
}

export const PasswordResetConfirm = ({ token, uid, onSuccess }: PasswordResetConfirmProps) => {
    const mutation = usePasswordResetConfirm()

    const form = useForm<PasswordResetConfirmForm>({
        resolver: zodResolver(passwordResetConfirmSchema),
        defaultValues: {
            new_password1: '',
            new_password2: '',
        },
    })

    const onSubmit = (data: PasswordResetConfirmForm) => {
        mutation.mutate(
            {
                    token,
                    uid,
                    new_password1: data.new_password1,
                    new_password2: data.new_password2,
            },
            {
                onSuccess: () => {
                    onSuccess?.()
                },
            }
        )
    }

    if (mutation.isSuccess) {
        return (
            <div className="flex flex-col min-h-[50vh] h-full w-full items-center justify-center px-4">
                <Card className="mx-auto max-w-sm">
                    <CardContent className="pt-6">
                        <Alert>
                            <CheckCircle className="h-4 w-4" />
                            <AlertDescription>
                                Password reset successful! You can now log in with your new password.
                            </AlertDescription>
                        </Alert>
                    </CardContent>
                </Card>
            </div>
        )
    }

    return (
        <div className="flex flex-col min-h-[50vh] h-full w-full items-center justify-center px-4">
            <Card className="mx-auto max-w-sm">
                <CardHeader>
                    <CardTitle className="text-2xl">Set new password</CardTitle>
                    <CardDescription>
                        Enter your new password below.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                            <div className="grid gap-4">
                                <FormField
                                    control={form.control}
                                    name="new_password1"
                                    render={({ field }) => (
                                        <FormItem className="grid gap-2">
                                            <FormLabel htmlFor="new_password1">New Password</FormLabel>
                                            <FormControl>
                                                <PasswordInput
                                                    id="new_password1"
                                                    placeholder="Enter new password"
                                                    autoComplete="new-password"
                                                    {...field}
                                                    disabled={mutation.isPending}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="new_password2"
                                    render={({ field }) => (
                                        <FormItem className="grid gap-2">
                                            <FormLabel htmlFor="new_password2">Confirm New Password</FormLabel>
                                            <FormControl>
                                                <PasswordInput
                                                    id="new_password2"
                                                    placeholder="Confirm new password"
                                                    autoComplete="new-password"
                                                    {...field}
                                                    disabled={mutation.isPending}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                {mutation.isError && (
                                    <Alert variant="destructive">
                                        <AlertCircle className="h-4 w-4" />
                                        <AlertDescription>
                                            {getPasswordResetErrorMessage(mutation.error, 'An error occurred while resetting your password')}
                                        </AlertDescription>
                                    </Alert>
                                )}

                                <Button type="submit" className="w-full" disabled={mutation.isPending}>
                                    {mutation.isPending ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Resetting...
                                        </>
                                    ) : (
                                        'Reset password'
                                    )}
                                </Button>
                            </div>
                        </form>
                    </Form>
                </CardContent>
            </Card>
        </div>
    )
}