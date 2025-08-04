import React from 'react'
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
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Mail, CheckCircle, AlertCircle } from 'lucide-react'

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
            <div className="space-y-4">
                <Alert>
                    <CheckCircle className="h-4 w-4" />
                    <AlertDescription>
                        Password reset email sent! Check your inbox for further instructions.
                    </AlertDescription>
                </Alert>
            </div>
        )
    }

    return (
        <div className="space-y-4">
            <div className="space-y-2 text-center">
                <h2 className="text-2xl font-semibold tracking-tight">
                    Reset your password
                </h2>
                <p className="text-sm text-muted-foreground">
                    Enter your email address and we'll send you a link to reset your password.
                </p>
            </div>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                    <FormField
                        control={form.control}
                        name="email"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Email</FormLabel>
                                <FormControl>
                                    <Input
                                        placeholder="Enter your email"
                                        type="email"
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
                                {mutation.error instanceof Error
                                    ? mutation.error.message
                                    : 'An error occurred while sending the reset email'}
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
                </form>
            </Form>
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
            <div className="space-y-4">
                <Alert>
                    <CheckCircle className="h-4 w-4" />
                    <AlertDescription>
                        Password reset successful! You can now log in with your new password.
                    </AlertDescription>
                </Alert>
            </div>
        )
    }

    return (
        <div className="space-y-4">
            <div className="space-y-2 text-center">
                <h2 className="text-2xl font-semibold tracking-tight">
                    Set new password
                </h2>
                <p className="text-sm text-muted-foreground">
                    Enter your new password below.
                </p>
            </div>

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                    <FormField
                        control={form.control}
                        name="new_password1"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>New Password</FormLabel>
                                <FormControl>
                                    <Input
                                        placeholder="Enter new password"
                                        type="password"
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
                            <FormItem>
                                <FormLabel>Confirm New Password</FormLabel>
                                <FormControl>
                                    <Input
                                        placeholder="Confirm new password"
                                        type="password"
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
                                {mutation.error instanceof Error
                                    ? mutation.error.message
                                    : 'An error occurred while resetting your password'}
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
                </form>
            </Form>
        </div>
    )
}