import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { ArrowLeft, Building2, Upload, X, Loader2 } from "lucide-react";
import { useRef, useState } from "react";

import { useTenantSettings } from "@/hooks/useTenantSettings";
import { useUpdateTenantSettings } from "@/hooks/useUpdateTenantSettings";
import { useUploadTenantLogo, useDeleteTenantLogo } from "@/hooks/useUploadTenantLogo";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

const TIMEZONES = [
    { value: "UTC", label: "UTC" },
    { value: "America/New_York", label: "Eastern Time (US)" },
    { value: "America/Chicago", label: "Central Time (US)" },
    { value: "America/Denver", label: "Mountain Time (US)" },
    { value: "America/Los_Angeles", label: "Pacific Time (US)" },
    { value: "America/Phoenix", label: "Arizona (US)" },
    { value: "America/Anchorage", label: "Alaska (US)" },
    { value: "Pacific/Honolulu", label: "Hawaii (US)" },
    { value: "Europe/London", label: "London (UK)" },
    { value: "Europe/Paris", label: "Paris (EU)" },
    { value: "Europe/Berlin", label: "Berlin (EU)" },
    { value: "Asia/Tokyo", label: "Tokyo (Japan)" },
    { value: "Asia/Shanghai", label: "Shanghai (China)" },
    { value: "Asia/Singapore", label: "Singapore" },
    { value: "Australia/Sydney", label: "Sydney (Australia)" },
];

const formSchema = z.object({
    name: z.string().min(1, "Organization name is required").max(100),
    contact_email: z.string().email("Invalid email").or(z.literal("")),
    contact_phone: z.string().max(30).optional(),
    website: z.string().url("Invalid URL").or(z.literal("")),
    address: z.string().max(500).optional(),
    default_timezone: z.string(),
});

type FormValues = z.infer<typeof formSchema>;

export function OrganizationSettingsPage() {
    const { data: settings, isLoading, isError } = useTenantSettings();
    const updateSettings = useUpdateTenantSettings();
    const uploadLogo = useUploadTenantLogo();
    const deleteLogo = useDeleteTenantLogo();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [logoPreview, setLogoPreview] = useState<string | null>(null);

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        values: settings ? {
            name: settings.name,
            contact_email: settings.contact_email || "",
            contact_phone: settings.contact_phone || "",
            website: settings.website || "",
            address: settings.address || "",
            default_timezone: settings.default_timezone || "UTC",
        } : undefined,
    });

    const onSubmit = async (values: FormValues) => {
        try {
            await updateSettings.mutateAsync(values);
            toast.success("Organization settings updated");
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Failed to update settings");
        }
    };

    const handleLogoSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith("image/")) {
            toast.error("Please select an image file");
            return;
        }

        // Validate file size (max 2MB)
        if (file.size > 2 * 1024 * 1024) {
            toast.error("Image must be less than 2MB");
            return;
        }

        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => setLogoPreview(e.target?.result as string);
        reader.readAsDataURL(file);

        try {
            await uploadLogo.mutateAsync(file);
            toast.success("Logo uploaded successfully");
            setLogoPreview(null);
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Failed to upload logo");
            setLogoPreview(null);
        }

        // Reset file input
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    const handleLogoDelete = async () => {
        try {
            await deleteLogo.mutateAsync();
            toast.success("Logo removed");
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Failed to remove logo");
        }
    };

    if (isError) {
        return (
            <div className="container mx-auto p-6 max-w-2xl">
                <div className="text-center py-12">
                    <p className="text-destructive">Failed to load organization settings</p>
                    <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>
                        Retry
                    </Button>
                </div>
            </div>
        );
    }

    const currentLogoUrl = logoPreview || settings?.logo_url;

    return (
        <div className="container mx-auto p-6 max-w-2xl">
            {/* Header */}
            <div className="mb-6">
                <Link to="/settings" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4">
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back to Settings
                </Link>
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Building2 className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold">Organization Settings</h1>
                        <p className="text-muted-foreground text-sm">
                            Manage your organization's profile and contact information
                        </p>
                    </div>
                </div>
            </div>

            {/* Logo Section */}
            <Card className="mb-6">
                <CardHeader>
                    <CardTitle className="text-lg">Organization Logo</CardTitle>
                    <CardDescription>
                        Upload your organization's logo. Recommended size: 200x200 pixels.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center gap-6">
                        {isLoading ? (
                            <Skeleton className="h-20 w-20 rounded-lg" />
                        ) : currentLogoUrl ? (
                            <div className="relative">
                                <img
                                    src={currentLogoUrl}
                                    alt="Organization logo"
                                    className="h-20 w-20 rounded-lg object-contain border"
                                />
                                {(uploadLogo.isPending || deleteLogo.isPending) && (
                                    <div className="absolute inset-0 flex items-center justify-center bg-background/80 rounded-lg">
                                        <Loader2 className="h-6 w-6 animate-spin" />
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="h-20 w-20 rounded-lg border-2 border-dashed flex items-center justify-center text-muted-foreground">
                                <Building2 className="h-8 w-8" />
                            </div>
                        )}
                        <div className="flex flex-col gap-2">
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                onChange={handleLogoSelect}
                                className="hidden"
                            />
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => fileInputRef.current?.click()}
                                disabled={uploadLogo.isPending || deleteLogo.isPending}
                            >
                                <Upload className="h-4 w-4 mr-2" />
                                {currentLogoUrl ? "Change Logo" : "Upload Logo"}
                            </Button>
                            {settings?.logo_url && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={handleLogoDelete}
                                    disabled={uploadLogo.isPending || deleteLogo.isPending}
                                    className="text-destructive hover:text-destructive"
                                >
                                    <X className="h-4 w-4 mr-2" />
                                    Remove Logo
                                </Button>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Form */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Organization Details</CardTitle>
                    <CardDescription>
                        This information may be displayed on reports and documents.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="space-y-4">
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-20 w-full" />
                        </div>
                    ) : (
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                                <FormField
                                    control={form.control}
                                    name="name"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Organization Name *</FormLabel>
                                            <FormControl>
                                                <Input placeholder="Acme Manufacturing" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <div className="grid gap-4 sm:grid-cols-2">
                                    <FormField
                                        control={form.control}
                                        name="contact_email"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Contact Email</FormLabel>
                                                <FormControl>
                                                    <Input type="email" placeholder="contact@example.com" {...field} />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />

                                    <FormField
                                        control={form.control}
                                        name="contact_phone"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Contact Phone</FormLabel>
                                                <FormControl>
                                                    <Input type="tel" placeholder="+1 (555) 123-4567" {...field} />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                </div>

                                <FormField
                                    control={form.control}
                                    name="website"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Website</FormLabel>
                                            <FormControl>
                                                <Input type="url" placeholder="https://www.example.com" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="address"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Address</FormLabel>
                                            <FormControl>
                                                <Textarea
                                                    placeholder="123 Main St&#10;City, State 12345&#10;Country"
                                                    rows={3}
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormDescription>
                                                Full mailing address for your organization
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="default_timezone"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Default Timezone</FormLabel>
                                            <Select onValueChange={field.onChange} value={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select timezone" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    {TIMEZONES.map((tz) => (
                                                        <SelectItem key={tz.value} value={tz.value}>
                                                            {tz.label}
                                                        </SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                            <FormDescription>
                                                Used for scheduling and report timestamps
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <div className="flex justify-end pt-4">
                                    <Button type="submit" disabled={updateSettings.isPending}>
                                        {updateSettings.isPending && (
                                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        )}
                                        Save Changes
                                    </Button>
                                </div>
                            </form>
                        </Form>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
