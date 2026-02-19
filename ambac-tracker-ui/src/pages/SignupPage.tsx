'use client'

import { useEffect } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'

import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
    FormDescription,
} from '@/components/ui/form'
import { Button } from '@/components/ui/button'
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card'
import { PasswordInput } from '@/components/ui/password-input'
import { Checkbox } from '@/components/ui/checkbox'

import { useAcceptInvitation } from '@/hooks/useAcceptInvitation'

const signupSchema = z.object({
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
    opt_in_notifications: z.boolean().default(false),
}).refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
})

export default function SignupPage() {
    const navigate = useNavigate()
    const search = useSearch({ strict: false }) as { token?: string }
    const acceptInvitation = useAcceptInvitation()

    const form = useForm<z.infer<typeof signupSchema>>({
        resolver: zodResolver(signupSchema),
        defaultValues: {
            password: '',
            confirmPassword: '',
            opt_in_notifications: false,
        },
    })

    // Validate token exists
    useEffect(() => {
        if (!search.token) {
            toast.error('Invalid or missing invitation token')
            navigate({ to: '/login' })
        }
    }, [search.token, navigate])

    async function onSubmit(values: z.infer<typeof signupSchema>) {
        if (!search.token) {
            toast.error('Invalid invitation token')
            return
        }

        try {
            const response = await acceptInvitation.mutateAsync({
                token: search.token,
                password: values.password,
                opt_in_notifications: values.opt_in_notifications,
            })

            toast.success(response.detail || 'Account created successfully!')

            // Redirect to login page after successful signup
            setTimeout(() => {
                navigate({ to: '/login' })
            }, 1500)

        } catch (error: any) {
            console.error('Signup error:', error)
            const apiError = error?.response?.data;
            let errorMessage = 'Failed to create account. Please try again.';

            if (apiError?.email?.[0]) {
                errorMessage = `Email: ${apiError.email[0]}`;
            } else if (apiError?.password1?.[0]) {
                errorMessage = apiError.password1[0];
            } else if (apiError?.password2?.[0]) {
                errorMessage = apiError.password2[0];
            } else if (apiError?.non_field_errors?.[0]) {
                errorMessage = apiError.non_field_errors[0];
            } else if (apiError?.detail) {
                errorMessage = apiError.detail;
            } else if (error?.message) {
                errorMessage = error.message;
            }

            toast.error(errorMessage)
        }
    }

    return (
        <div className="flex flex-col min-h-[50vh] h-full w-full items-center justify-center px-4">
            <Card className="mx-auto max-w-sm">
                <CardHeader>
                    <CardTitle className="text-2xl">Set Your Password</CardTitle>
                    <CardDescription>
                        Create a password for your account to complete the signup process.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Form {...form}>
                        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                            <div className="grid gap-4">
                                <FormField
                                    control={form.control}
                                    name="password"
                                    render={({ field }) => (
                                        <FormItem className="grid gap-2">
                                            <FormLabel htmlFor="password">Password</FormLabel>
                                            <FormControl>
                                                <PasswordInput
                                                    id="password"
                                                    placeholder="Enter your password"
                                                    autoComplete="new-password"
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control}
                                    name="confirmPassword"
                                    render={({ field }) => (
                                        <FormItem className="grid gap-2">
                                            <FormLabel htmlFor="confirmPassword">Confirm Password</FormLabel>
                                            <FormControl>
                                                <PasswordInput
                                                    id="confirmPassword"
                                                    placeholder="Confirm your password"
                                                    autoComplete="new-password"
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control}
                                    name="opt_in_notifications"
                                    render={({ field }) => (
                                        <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                            <FormControl>
                                                <Checkbox
                                                    checked={field.value}
                                                    onCheckedChange={field.onChange}
                                                />
                                            </FormControl>
                                            <div className="space-y-1 leading-none">
                                                <FormLabel>
                                                    Email notifications
                                                </FormLabel>
                                                <FormDescription>
                                                    Receive email notifications about important updates
                                                </FormDescription>
                                            </div>
                                        </FormItem>
                                    )}
                                />
                                <Button
                                    type="submit"
                                    className="w-full"
                                    disabled={acceptInvitation.isPending}
                                >
                                    {acceptInvitation.isPending ? 'Creating account...' : 'Create Account'}
                                </Button>
                            </div>
                        </form>
                    </Form>
                </CardContent>
            </Card>
        </div>
    )
}