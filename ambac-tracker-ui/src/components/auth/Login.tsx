'use client'

import { Link, useRouter } from '@tanstack/react-router'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { queryClient } from '@/lib/queryClient'

import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/components/ui/form'
import { Button } from '@/components/ui/button'
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { PasswordInput } from '@/components/ui/password-input'

import { api, schemas } from '@/lib/api/generated'
import { getCookie } from '@/lib/utils'
import { isFieldRequired } from '@/lib/zod-config'
import { getAppName, getAppTagline } from '@/lib/branding'
import { useTenantContext } from '@/components/tenant-provider'

// Make sure you've done this somewhere globally:
api.axios.defaults.withCredentials = true
const Login = schemas.LoginRequest

const required = {
    email: isFieldRequired(Login.shape.email),
    password: isFieldRequired(Login.shape.password),
}


export default function LoginPreview() {
    const router = useRouter()
    const { tenant } = useTenantContext()
    const tenantTagline = (tenant as { tagline?: string | null } | null)?.tagline
    const form = useForm<z.infer<typeof Login>>({
        resolver: zodResolver(Login),
        defaultValues: {
            email: '',
            password: '',
        },
    })

    async function onSubmit(values: z.infer<typeof Login>) {
        try {
            await api.auth_login_create({
                email: values.email,
                password: values.password
            }, {
                headers: { "X-CSRFToken": getCookie("csrftoken") },
            })
        } catch (error: any) {
            // Only an actual login-POST rejection is a failed login.
            const apiError = error?.response?.data;
            let message = "Login failed";

            if (apiError?.non_field_errors?.[0]) {
                // DRF returns "Unable to log in with provided credentials."
                message = "Invalid email or password";
            } else if (apiError?.email?.[0]) {
                message = apiError.email[0];
            } else if (apiError?.password?.[0]) {
                message = apiError.password[0];
            } else if (apiError?.detail) {
                message = apiError.detail;
            } else if (error instanceof Error) {
                message = error.message;
            }

            toast.error(message);
            return
        }

        // Login succeeded — do NOT gate the redirect on the follow-up
        // `/auth/user/` calls. A transient 401 there (e.g. right after a
        // session change) would otherwise be swallowed as "Login failed" and
        // strand us on /login despite a 200 login. Auth rides the session
        // cookie set by this POST; nudge a refresh and navigate — the root
        // layout fetches `authUser` (with retry) on its own.
        toast.success(`Welcome back, ${values.email}!`)
        void queryClient.invalidateQueries({ queryKey: ['authUser'] })
        router.navigate({ to: "/" })
    }

    return (
        <div className="flex flex-col min-h-[50vh] h-full w-full items-center justify-center px-4">
            <Card className="mx-auto max-w-sm">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl">{getAppName(tenant?.name)}</CardTitle>
                    <CardDescription>
                        {getAppTagline(tenantTagline)}
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
                                            <FormLabel htmlFor="email" required={required.email}>Email</FormLabel>
                                            <FormControl>
                                                <Input
                                                    id="email"
                                                    placeholder="johndoe"
                                                    autoComplete="email"
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control}
                                    name="password"
                                    render={({ field }) => (
                                        <FormItem className="grid gap-2">
                                            <div className="flex justify-between items-center">
                                                <FormLabel htmlFor="password" required={required.password}>Password</FormLabel>
                                                <Link
                                                    to="/password-reset-request"
                                                    className="ml-auto inline-block text-sm underline"
                                                >
                                                    Forgot your password?
                                                </Link>
                                            </div>
                                            <FormControl>
                                                <PasswordInput
                                                    id="password"
                                                    placeholder="******"
                                                    autoComplete="current-password"
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <Button type="submit" className="w-full">
                                    Login
                                </Button>
                                <Button
                                    type="button"
                                    variant="outline"
                                    className="w-full"
                                    onClick={() => {
                                        window.location.href = '/accounts/microsoft/login/'
                                    }}
                                >
                                    Login with Microsoft
                                </Button>
                            </div>
                        </form>
                    </Form>
                </CardContent>
            </Card>
        </div>
    )
}
