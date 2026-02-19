import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { ArrowLeft, Palette, Upload, X, Loader2, RotateCcw } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { useTenantSettings } from "@/hooks/useTenantSettings";
import { generateBrandPalette } from "@/lib/color-utils";
import { useUpdateTenantSettings } from "@/hooks/useUpdateTenantSettings";
import { useUploadTenantLogo, useDeleteTenantLogo } from "@/hooks/useUploadTenantLogo";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

// Preset color options
const COLOR_PRESETS = [
    { name: "Blue", value: "#2563eb" },
    { name: "Indigo", value: "#4f46e5" },
    { name: "Purple", value: "#7c3aed" },
    { name: "Pink", value: "#db2777" },
    { name: "Red", value: "#dc2626" },
    { name: "Orange", value: "#ea580c" },
    { name: "Amber", value: "#d97706" },
    { name: "Green", value: "#16a34a" },
    { name: "Teal", value: "#0d9488" },
    { name: "Cyan", value: "#0891b2" },
    { name: "Slate", value: "#475569" },
];

const DEFAULT_PRIMARY_COLOR = "#2563eb";

const formSchema = z.object({
    primary_color: z.string().regex(/^#[0-9a-fA-F]{6}$/, "Must be a valid hex color"),
    secondary_color: z.string().regex(/^#[0-9a-fA-F]{6}$/, "Must be a valid hex color").optional().or(z.literal("")),
    theme_mode: z.enum(["light", "dark", "system"]),
});

type FormValues = z.infer<typeof formSchema>;

export function BrandingSettingsPage() {
    const { data: settings, isLoading, isError } = useTenantSettings();
    const updateSettings = useUpdateTenantSettings();
    const uploadLogo = useUploadTenantLogo();
    const deleteLogo = useDeleteTenantLogo();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [logoPreview, setLogoPreview] = useState<string | null>(null);

    // Extract branding from settings
    const branding = (settings?.settings as Record<string, unknown>)?.branding as Record<string, string> | undefined;

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        values: {
            primary_color: branding?.primary_color || DEFAULT_PRIMARY_COLOR,
            secondary_color: branding?.secondary_color || "",
            theme_mode: (branding?.theme_mode as "light" | "dark" | "system") || "system",
        },
    });

    const watchedPrimaryColor = form.watch("primary_color");
    const watchedSecondaryColor = form.watch("secondary_color");

    // Generate palette preview from the watched colors
    const palette = useMemo(() => {
        return generateBrandPalette(watchedPrimaryColor, watchedSecondaryColor || undefined);
    }, [watchedPrimaryColor, watchedSecondaryColor]);

    const onSubmit = async (values: FormValues) => {
        try {
            await updateSettings.mutateAsync({
                settings: {
                    ...((settings?.settings as Record<string, unknown>) || {}),
                    branding: {
                        ...branding,
                        primary_color: values.primary_color,
                        secondary_color: values.secondary_color || undefined,
                        theme_mode: values.theme_mode,
                    },
                },
            });
            toast.success("Branding settings updated");
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Failed to update branding");
        }
    };

    const handleLogoSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        if (!file.type.startsWith("image/")) {
            toast.error("Please select an image file");
            return;
        }

        if (file.size > 2 * 1024 * 1024) {
            toast.error("Image must be less than 2MB");
            return;
        }

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

    const handleResetColors = () => {
        form.setValue("primary_color", DEFAULT_PRIMARY_COLOR);
        form.setValue("secondary_color", "");
    };

    if (isError) {
        return (
            <div className="container mx-auto p-6 max-w-2xl">
                <div className="text-center py-12">
                    <p className="text-destructive">Failed to load branding settings</p>
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
                        <Palette className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold">Branding</h1>
                        <p className="text-muted-foreground text-sm">
                            Customize your organization's visual identity
                        </p>
                    </div>
                </div>
            </div>

            {/* Logo Section */}
            <Card className="mb-6">
                <CardHeader>
                    <CardTitle className="text-lg">Logo</CardTitle>
                    <CardDescription>
                        Your logo appears in the sidebar and on reports. Recommended: 200x200 PNG with transparent background.
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
                                    className="h-20 w-20 rounded-lg object-contain border bg-white"
                                />
                                {(uploadLogo.isPending || deleteLogo.isPending) && (
                                    <div className="absolute inset-0 flex items-center justify-center bg-background/80 rounded-lg">
                                        <Loader2 className="h-6 w-6 animate-spin" />
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="h-20 w-20 rounded-lg border-2 border-dashed flex items-center justify-center text-muted-foreground bg-muted/30">
                                <Palette className="h-8 w-8" />
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

            {/* Colors Section */}
            <Card className="mb-6">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle className="text-lg">Colors</CardTitle>
                            <CardDescription>
                                Choose your brand colors for the application interface.
                            </CardDescription>
                        </div>
                        <Button variant="ghost" size="sm" onClick={handleResetColors}>
                            <RotateCcw className="h-4 w-4 mr-2" />
                            Reset
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="space-y-4">
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                        </div>
                    ) : (
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                                <FormField
                                    control={form.control}
                                    name="primary_color"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Primary Color</FormLabel>
                                            <div className="flex gap-3">
                                                <FormControl>
                                                    <div className="flex gap-2 flex-1">
                                                        <Input
                                                            type="color"
                                                            {...field}
                                                            className="w-12 h-10 p-1 cursor-pointer"
                                                        />
                                                        <Input
                                                            type="text"
                                                            value={field.value}
                                                            onChange={(e) => field.onChange(e.target.value)}
                                                            placeholder="#2563eb"
                                                            className="flex-1 font-mono"
                                                        />
                                                    </div>
                                                </FormControl>
                                            </div>
                                            <div className="flex flex-wrap gap-2 mt-2">
                                                {COLOR_PRESETS.map((preset) => (
                                                    <button
                                                        key={preset.value}
                                                        type="button"
                                                        onClick={() => field.onChange(preset.value)}
                                                        className="w-8 h-8 rounded-md border-2 transition-all hover:scale-110"
                                                        style={{
                                                            backgroundColor: preset.value,
                                                            borderColor: field.value === preset.value ? "white" : "transparent",
                                                            boxShadow: field.value === preset.value ? `0 0 0 2px ${preset.value}` : undefined,
                                                        }}
                                                        title={preset.name}
                                                    />
                                                ))}
                                            </div>
                                            <FormDescription>
                                                Used for buttons, links, and highlights
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="secondary_color"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Secondary Color (Optional)</FormLabel>
                                            <div className="flex gap-3">
                                                <FormControl>
                                                    <div className="flex gap-2 flex-1">
                                                        <Input
                                                            type="color"
                                                            value={field.value || "#6b7280"}
                                                            onChange={(e) => field.onChange(e.target.value)}
                                                            className="w-12 h-10 p-1 cursor-pointer"
                                                        />
                                                        <Input
                                                            type="text"
                                                            value={field.value || ""}
                                                            onChange={(e) => field.onChange(e.target.value)}
                                                            placeholder="None"
                                                            className="flex-1 font-mono"
                                                        />
                                                        {field.value && (
                                                            <Button
                                                                type="button"
                                                                variant="ghost"
                                                                size="icon"
                                                                onClick={() => field.onChange("")}
                                                            >
                                                                <X className="h-4 w-4" />
                                                            </Button>
                                                        )}
                                                    </div>
                                                </FormControl>
                                            </div>
                                            <div className="flex flex-wrap gap-2 mt-2">
                                                {COLOR_PRESETS.map((preset) => (
                                                    <button
                                                        key={preset.value}
                                                        type="button"
                                                        onClick={() => field.onChange(preset.value)}
                                                        className="w-8 h-8 rounded-md border-2 transition-all hover:scale-110"
                                                        style={{
                                                            backgroundColor: preset.value,
                                                            borderColor: field.value === preset.value ? "white" : "transparent",
                                                            boxShadow: field.value === preset.value ? `0 0 0 2px ${preset.value}` : undefined,
                                                        }}
                                                        title={preset.name}
                                                    />
                                                ))}
                                            </div>
                                            <FormDescription>
                                                Used for secondary buttons and accents. Leave empty to auto-generate from primary.
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="theme_mode"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Theme</FormLabel>
                                            <Select onValueChange={field.onChange} value={field.value}>
                                                <FormControl>
                                                    <SelectTrigger>
                                                        <SelectValue placeholder="Select theme" />
                                                    </SelectTrigger>
                                                </FormControl>
                                                <SelectContent>
                                                    <SelectItem value="system">System (auto)</SelectItem>
                                                    <SelectItem value="light">Light</SelectItem>
                                                    <SelectItem value="dark">Dark</SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <FormDescription>
                                                Default theme for all users in your organization
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

            {/* Preview Section */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Preview</CardTitle>
                    <CardDescription>
                        See how your branding looks in both light and dark modes
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Light Mode Preview */}
                        <div className="border rounded-lg p-4 bg-white text-gray-900">
                            <div className="text-xs font-medium text-gray-500 mb-3">Light Mode</div>
                            <div className="flex items-center gap-3 mb-4">
                                {currentLogoUrl ? (
                                    <img
                                        src={currentLogoUrl}
                                        alt="Logo preview"
                                        className="h-10 w-10 rounded object-contain"
                                    />
                                ) : (
                                    <div
                                        className="h-10 w-10 rounded flex items-center justify-center text-white font-bold"
                                        style={{ background: palette?.light.primary }}
                                    >
                                        {settings?.name?.charAt(0)?.toUpperCase() || "A"}
                                    </div>
                                )}
                                <span className="font-semibold">{settings?.name || "Your Organization"}</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <button
                                    type="button"
                                    className="px-3 py-1.5 rounded-md text-sm font-medium"
                                    style={{
                                        background: palette?.light.primary,
                                        color: palette?.light.primaryForeground,
                                    }}
                                >
                                    Primary
                                </button>
                                {palette?.secondary ? (
                                    <button
                                        type="button"
                                        className="px-3 py-1.5 rounded-md text-sm font-medium"
                                        style={{
                                            background: palette.secondary.light.color,
                                            color: palette.secondary.light.foreground,
                                        }}
                                    >
                                        Secondary
                                    </button>
                                ) : (
                                    <button
                                        type="button"
                                        className="px-3 py-1.5 rounded-md text-sm font-medium bg-gray-100 text-gray-700"
                                    >
                                        Secondary
                                    </button>
                                )}
                            </div>
                            <div className="mt-3 flex gap-1">
                                <div
                                    className="flex-1 h-1 rounded-full"
                                    style={{ background: palette?.light.primary }}
                                />
                                {palette?.secondary && (
                                    <div
                                        className="flex-1 h-1 rounded-full"
                                        style={{ background: palette.secondary.light.color }}
                                    />
                                )}
                            </div>
                        </div>

                        {/* Dark Mode Preview */}
                        <div className="border rounded-lg p-4 bg-gray-900 text-gray-100">
                            <div className="text-xs font-medium text-gray-400 mb-3">Dark Mode</div>
                            <div className="flex items-center gap-3 mb-4">
                                {currentLogoUrl ? (
                                    <img
                                        src={currentLogoUrl}
                                        alt="Logo preview"
                                        className="h-10 w-10 rounded object-contain"
                                    />
                                ) : (
                                    <div
                                        className="h-10 w-10 rounded flex items-center justify-center font-bold"
                                        style={{
                                            background: palette?.dark.primary,
                                            color: palette?.dark.primaryForeground,
                                        }}
                                    >
                                        {settings?.name?.charAt(0)?.toUpperCase() || "A"}
                                    </div>
                                )}
                                <span className="font-semibold">{settings?.name || "Your Organization"}</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <button
                                    type="button"
                                    className="px-3 py-1.5 rounded-md text-sm font-medium"
                                    style={{
                                        background: palette?.dark.primary,
                                        color: palette?.dark.primaryForeground,
                                    }}
                                >
                                    Primary
                                </button>
                                {palette?.secondary ? (
                                    <button
                                        type="button"
                                        className="px-3 py-1.5 rounded-md text-sm font-medium"
                                        style={{
                                            background: palette.secondary.dark.color,
                                            color: palette.secondary.dark.foreground,
                                        }}
                                    >
                                        Secondary
                                    </button>
                                ) : (
                                    <button
                                        type="button"
                                        className="px-3 py-1.5 rounded-md text-sm font-medium bg-gray-700 text-gray-200"
                                    >
                                        Secondary
                                    </button>
                                )}
                            </div>
                            <div className="mt-3 flex gap-1">
                                <div
                                    className="flex-1 h-1 rounded-full"
                                    style={{ background: palette?.dark.primary }}
                                />
                                {palette?.secondary && (
                                    <div
                                        className="flex-1 h-1 rounded-full"
                                        style={{ background: palette.secondary.dark.color }}
                                    />
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Color Palettes */}
                    {palette && (
                        <div className="mt-4 pt-4 border-t space-y-4">
                            <div>
                                <div className="text-xs font-medium text-muted-foreground mb-2">Primary Palette</div>
                                <div className="flex gap-1 rounded-md overflow-hidden">
                                    {Object.entries(palette.shades).map(([shade, color]) => (
                                        <div
                                            key={shade}
                                            className="flex-1 h-8"
                                            style={{ background: color }}
                                            title={`${shade}: ${color}`}
                                        />
                                    ))}
                                </div>
                                <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                                    <span>100</span>
                                    <span>500</span>
                                    <span>900</span>
                                </div>
                            </div>
                            {palette.secondary && (
                                <div>
                                    <div className="text-xs font-medium text-muted-foreground mb-2">Secondary Palette</div>
                                    <div className="flex gap-1 rounded-md overflow-hidden">
                                        {Object.entries(palette.secondary.shades).map(([shade, color]) => (
                                            <div
                                                key={shade}
                                                className="flex-1 h-8"
                                                style={{ background: color }}
                                                title={`${shade}: ${color}`}
                                            />
                                        ))}
                                    </div>
                                    <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                                        <span>100</span>
                                        <span>500</span>
                                        <span>900</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
