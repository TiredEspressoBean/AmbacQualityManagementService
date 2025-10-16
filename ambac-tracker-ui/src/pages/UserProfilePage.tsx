import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useAuthUser } from "@/hooks/useAuthUser";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getCookie } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Loader2, Save, User as UserIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { NotificationPreferencesCard } from "@/components/notification-preferences-card";

const profileSchema = z.object({
    first_name: z.string().max(150, "First name must be 150 characters or less").optional(),
    last_name: z.string().max(150, "Last name must be 150 characters or less").optional(),
    email: z.string().email("Invalid email address").max(254, "Email must be 254 characters or less").optional(),
});

type ProfileFormData = z.infer<typeof profileSchema>;

export function UserProfilePage() {
    const { data: user, isLoading: isLoadingUser } = useAuthUser();
    const queryClient = useQueryClient();
    const [isEditing, setIsEditing] = useState(false);

    const form = useForm<ProfileFormData>({
        resolver: zodResolver(profileSchema),
        values: {
            first_name: user?.first_name || "",
            last_name: user?.last_name || "",
            email: user?.email || "",
        },
    });

    const updateProfileMutation = useMutation({
        mutationFn: async (data: ProfileFormData) => {
            const res = await fetch("/auth/user/", {
                method: "PATCH",
                credentials: "include",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken") ?? "",
                },
                body: JSON.stringify(data),
            });

            if (!res.ok) {
                const error = await res.json();
                throw new Error(error.detail || "Failed to update profile");
            }

            return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["authUser"] });
            toast.success("Profile updated successfully");
            setIsEditing(false);
        },
        onError: (error: Error) => {
            toast.error(error.message || "Failed to update profile");
        },
    });

    const onSubmit = (data: ProfileFormData) => {
        updateProfileMutation.mutate(data);
    };

    if (isLoadingUser) {
        return (
            <div className="flex items-center justify-center min-h-[calc(100vh-4rem)]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (!user) {
        return (
            <div className="flex items-center justify-center min-h-[calc(100vh-4rem)]">
                <Card>
                    <CardContent className="pt-6">
                        <p className="text-muted-foreground">Not authenticated. Please log in.</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="container max-w-3xl mx-auto py-8">
            <div className="space-y-6">
                {/* Header Section */}
                <div className="flex items-center gap-4 pb-4 border-b">
                    <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                        <UserIcon className="h-8 w-8 text-primary" />
                    </div>
                    <div className="flex-1">
                        <h1 className="text-2xl font-bold tracking-tight">{user.full_name || user.username}</h1>
                        <p className="text-sm text-muted-foreground">@{user.username}</p>
                    </div>
                    <div className="flex gap-2">
                        {user.is_staff && <Badge variant="secondary">Staff</Badge>}
                        {user.is_active ? (
                            <Badge variant="outline" className="text-green-600 border-green-600">
                                Active
                            </Badge>
                        ) : (
                            <Badge variant="outline" className="text-red-600 border-red-600">
                                Inactive
                            </Badge>
                        )}
                    </div>
                </div>

                {/* Account Information */}
                <Card>
                    <CardHeader>
                        <CardTitle>Account Information</CardTitle>
                        <CardDescription>Your account details and membership</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <dl className="space-y-3">
                            <div className="flex items-center justify-between py-2">
                                <dt className="text-sm font-medium text-muted-foreground">Company</dt>
                                <dd className="text-sm font-medium">{user.parent_company?.name || "No company assigned"}</dd>
                            </div>
                            <div className="flex items-center justify-between py-2">
                                <dt className="text-sm font-medium text-muted-foreground">Member since</dt>
                                <dd className="text-sm font-medium">{new Date(user.date_joined).toLocaleDateString()}</dd>
                            </div>
                            {user.groups && user.groups.length > 0 && (
                                <div className="flex items-center justify-between py-2">
                                    <dt className="text-sm font-medium text-muted-foreground">Groups</dt>
                                    <dd className="flex flex-wrap gap-2 justify-end">
                                        {user.groups.map((group) => (
                                            <Badge key={group.id} variant="outline">
                                                {group.name}
                                            </Badge>
                                        ))}
                                    </dd>
                                </div>
                            )}
                        </dl>
                    </CardContent>
                </Card>

                {/* Personal Information */}
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle>Personal Information</CardTitle>
                                <CardDescription>Update your personal details</CardDescription>
                            </div>
                            {!isEditing && (
                                <Button onClick={() => setIsEditing(true)} variant="outline" size="sm">
                                    Edit
                                </Button>
                            )}
                        </div>
                    </CardHeader>
                    <CardContent>
                        {!isEditing ? (
                            <dl className="space-y-3">
                                <div className="flex items-center justify-between py-2">
                                    <dt className="text-sm font-medium text-muted-foreground">First Name</dt>
                                    <dd className="text-sm font-medium">{user.first_name || "—"}</dd>
                                </div>
                                <div className="flex items-center justify-between py-2">
                                    <dt className="text-sm font-medium text-muted-foreground">Last Name</dt>
                                    <dd className="text-sm font-medium">{user.last_name || "—"}</dd>
                                </div>
                                <div className="flex items-center justify-between py-2">
                                    <dt className="text-sm font-medium text-muted-foreground">Email</dt>
                                    <dd className="text-sm font-medium">{user.email || "—"}</dd>
                                </div>
                            </dl>
                        ) : (
                            <Form {...form}>
                                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                                    <div className="grid gap-4 md:grid-cols-2">
                                        <FormField
                                            control={form.control}
                                            name="first_name"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>First Name</FormLabel>
                                                    <FormControl>
                                                        <Input placeholder="John" {...field} />
                                                    </FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />

                                        <FormField
                                            control={form.control}
                                            name="last_name"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Last Name</FormLabel>
                                                    <FormControl>
                                                        <Input placeholder="Doe" {...field} />
                                                    </FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                    </div>

                                    <FormField
                                        control={form.control}
                                        name="email"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Email</FormLabel>
                                                <FormControl>
                                                    <Input type="email" placeholder="john.doe@example.com" {...field} />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />

                                    <div className="flex gap-2">
                                        <Button
                                            type="submit"
                                            disabled={updateProfileMutation.isPending}
                                            size="sm"
                                        >
                                            {updateProfileMutation.isPending ? (
                                                <>
                                                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                                    Saving...
                                                </>
                                            ) : (
                                                "Save Changes"
                                            )}
                                        </Button>
                                        <Button
                                            type="button"
                                            variant="outline"
                                            size="sm"
                                            onClick={() => {
                                                form.reset();
                                                setIsEditing(false);
                                            }}
                                            disabled={updateProfileMutation.isPending}
                                        >
                                            Cancel
                                        </Button>
                                    </div>
                                </form>
                            </Form>
                        )}
                    </CardContent>
                </Card>

                {/* Notification Preferences */}
                <NotificationPreferencesCard />
            </div>
        </div>
    );
}
