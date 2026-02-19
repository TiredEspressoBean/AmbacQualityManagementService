/**
 * Color conversion utilities for tenant branding.
 * Generates OKLCH color palettes from a single brand color with
 * automatic light/dark mode support.
 */

/**
 * OKLCH color components
 */
export interface OklchColor {
    l: number; // Lightness: 0-1
    c: number; // Chroma: 0-0.4 (saturation)
    h: number; // Hue: 0-360
}

/**
 * Generated color palette for a single color
 */
export interface ColorPalette {
    // Full shade palette (100-900)
    shades: {
        100: string;
        200: string;
        300: string;
        400: string;
        500: string;
        600: string;
        700: string;
        800: string;
        900: string;
    };
    // Semantic colors for light mode
    light: {
        color: string;
        foreground: string;
        accent: string;
        accentForeground: string;
        ring: string;
    };
    // Semantic colors for dark mode
    dark: {
        color: string;
        foreground: string;
        accent: string;
        accentForeground: string;
        ring: string;
    };
    // Raw OKLCH components for CSS variable usage
    hue: number;
    chroma: number;
}

/**
 * Generated brand palette with primary and optional secondary colors
 */
export interface BrandPalette {
    primary: ColorPalette;
    secondary?: ColorPalette;
    // Legacy accessors for backwards compatibility
    shades: ColorPalette["shades"];
    light: {
        primary: string;
        primaryForeground: string;
        accent: string;
        accentForeground: string;
        ring: string;
    };
    dark: {
        primary: string;
        primaryForeground: string;
        accent: string;
        accentForeground: string;
        ring: string;
    };
    hue: number;
    chroma: number;
}

/**
 * Convert hex color to RGB (0-1 range)
 */
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!result) return null;
    return {
        r: parseInt(result[1], 16) / 255,
        g: parseInt(result[2], 16) / 255,
        b: parseInt(result[3], 16) / 255,
    };
}

/**
 * Convert linear RGB to OKLCH components
 */
function rgbToOklch(r: number, g: number, b: number): OklchColor {
    // Convert sRGB to linear RGB
    const toLinear = (c: number) =>
        c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    const lr = toLinear(r);
    const lg = toLinear(g);
    const lb = toLinear(b);

    // Convert to OKLab
    const l_ = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
    const m_ = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
    const s_ = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);

    const L = 0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_;
    const a = 1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_;
    const bVal = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_;

    // Convert OKLab to OKLCH
    const c = Math.sqrt(a * a + bVal * bVal);
    let h = Math.atan2(bVal, a) * (180 / Math.PI);
    if (h < 0) h += 360;

    return { l: L, c, h };
}

/**
 * Convert hex color to OKLCH components
 */
export function hexToOklchComponents(hex: string): OklchColor | null {
    const rgb = hexToRgb(hex);
    if (!rgb) return null;
    return rgbToOklch(rgb.r, rgb.g, rgb.b);
}

/**
 * Format OKLCH components as CSS string
 */
export function formatOklch(l: number, c: number, h: number): string {
    return `oklch(${l.toFixed(3)} ${c.toFixed(3)} ${h.toFixed(1)})`;
}

/**
 * Convert hex color to OKLCH CSS string
 */
export function hexToOklch(hex: string): string {
    const oklch = hexToOklchComponents(hex);
    if (!oklch) return hex;
    return formatOklch(oklch.l, oklch.c, oklch.h);
}

/**
 * Generate a color palette from a single hex color.
 * Creates 9 shades (100-900) and light/dark mode semantic colors.
 *
 * The approach:
 * - Keep the hue constant
 * - Vary lightness from 97% (100) to 15% (900)
 * - Chroma peaks at middle shades, reduces at extremes for better aesthetics
 */
export function generateColorPalette(hex: string): ColorPalette | null {
    const base = hexToOklchComponents(hex);
    if (!base) return null;

    const { c: baseChroma, h: hue } = base;

    // Clamp chroma to reasonable bounds
    const maxChroma = Math.min(baseChroma, 0.25);

    // Generate shade palette
    // Lightness decreases 100->900, chroma peaks at 500
    const shades = {
        100: formatOklch(0.97, maxChroma * 0.15, hue),
        200: formatOklch(0.90, maxChroma * 0.35, hue),
        300: formatOklch(0.82, maxChroma * 0.55, hue),
        400: formatOklch(0.72, maxChroma * 0.80, hue),
        500: formatOklch(0.60, maxChroma, hue),          // Peak saturation
        600: formatOklch(0.50, maxChroma * 0.95, hue),
        700: formatOklch(0.40, maxChroma * 0.80, hue),
        800: formatOklch(0.28, maxChroma * 0.50, hue),
        900: formatOklch(0.18, maxChroma * 0.25, hue),
    };

    // Light mode: use 500-600 range for color (good contrast on white)
    // Dark mode: use 300-400 range for color (good contrast on dark bg)
    const light = {
        color: formatOklch(0.55, maxChroma, hue),
        foreground: "oklch(1 0 0)", // White text
        accent: formatOklch(0.95, maxChroma * 0.2, hue), // Very light tint
        accentForeground: formatOklch(0.25, maxChroma * 0.5, hue),
        ring: formatOklch(0.55, maxChroma, hue),
    };

    const dark = {
        color: formatOklch(0.75, maxChroma * 0.75, hue), // Lighter, less saturated
        foreground: formatOklch(0.15, maxChroma * 0.3, hue), // Dark text
        accent: formatOklch(0.25, maxChroma * 0.3, hue), // Dark tint
        accentForeground: formatOklch(0.90, maxChroma * 0.2, hue),
        ring: formatOklch(0.65, maxChroma * 0.6, hue),
    };

    return {
        shades,
        light,
        dark,
        hue,
        chroma: maxChroma,
    };
}

/**
 * Generate a full brand palette from primary and optional secondary hex colors.
 */
export function generateBrandPalette(
    primaryHex: string,
    secondaryHex?: string
): BrandPalette | null {
    const primary = generateColorPalette(primaryHex);
    if (!primary) return null;

    const secondary = secondaryHex ? generateColorPalette(secondaryHex) : undefined;

    return {
        primary,
        secondary,
        // Legacy accessors for backwards compatibility
        shades: primary.shades,
        light: {
            primary: primary.light.color,
            primaryForeground: primary.light.foreground,
            accent: primary.light.accent,
            accentForeground: primary.light.accentForeground,
            ring: primary.light.ring,
        },
        dark: {
            primary: primary.dark.color,
            primaryForeground: primary.dark.foreground,
            accent: primary.dark.accent,
            accentForeground: primary.dark.accentForeground,
            ring: primary.dark.ring,
        },
        hue: primary.hue,
        chroma: primary.chroma,
    };
}

/**
 * CSS variables that we set for branding
 */
const BRAND_VARIABLES = [
    // Primary
    "--brand-primary-light",
    "--brand-primary-dark",
    "--brand-primary-foreground-light",
    "--brand-primary-foreground-dark",
    "--brand-accent-light",
    "--brand-accent-dark",
    "--brand-accent-foreground-light",
    "--brand-accent-foreground-dark",
    "--brand-ring-light",
    "--brand-ring-dark",
    "--brand-hue",
    "--brand-chroma",
    // Secondary
    "--brand-secondary-light",
    "--brand-secondary-dark",
    "--brand-secondary-foreground-light",
    "--brand-secondary-foreground-dark",
    "--brand-secondary-accent-light",
    "--brand-secondary-accent-dark",
] as const;

/**
 * Apply tenant branding colors to CSS variables.
 * Sets up light-dark() compatible variables.
 */
export function applyBrandingColors(
    primaryColor: string | undefined,
    secondaryColor?: string | undefined
): void {
    if (!primaryColor) return;

    const palette = generateBrandPalette(primaryColor, secondaryColor);
    if (!palette) return;

    const root = document.documentElement;

    // Set primary brand variables
    root.style.setProperty("--brand-primary-light", palette.light.primary);
    root.style.setProperty("--brand-primary-dark", palette.dark.primary);
    root.style.setProperty("--brand-primary-foreground-light", palette.light.primaryForeground);
    root.style.setProperty("--brand-primary-foreground-dark", palette.dark.primaryForeground);
    root.style.setProperty("--brand-accent-light", palette.light.accent);
    root.style.setProperty("--brand-accent-dark", palette.dark.accent);
    root.style.setProperty("--brand-accent-foreground-light", palette.light.accentForeground);
    root.style.setProperty("--brand-accent-foreground-dark", palette.dark.accentForeground);
    root.style.setProperty("--brand-ring-light", palette.light.ring);
    root.style.setProperty("--brand-ring-dark", palette.dark.ring);
    root.style.setProperty("--brand-hue", palette.hue.toFixed(1));
    root.style.setProperty("--brand-chroma", palette.chroma.toFixed(3));

    // Set secondary brand variables if provided
    if (palette.secondary) {
        root.style.setProperty("--brand-secondary-light", palette.secondary.light.color);
        root.style.setProperty("--brand-secondary-dark", palette.secondary.dark.color);
        root.style.setProperty("--brand-secondary-foreground-light", palette.secondary.light.foreground);
        root.style.setProperty("--brand-secondary-foreground-dark", palette.secondary.dark.foreground);
        root.style.setProperty("--brand-secondary-accent-light", palette.secondary.light.accent);
        root.style.setProperty("--brand-secondary-accent-dark", palette.secondary.dark.accent);
    }

    // Mark that branding is active (for CSS to detect)
    root.dataset.branded = "true";
}

/**
 * Reset branding colors to defaults (remove inline styles)
 */
export function resetBrandingColors(): void {
    const root = document.documentElement;

    for (const variable of BRAND_VARIABLES) {
        root.style.removeProperty(variable);
    }

    delete root.dataset.branded;
}

/**
 * Legacy function for backwards compatibility
 * @deprecated Use generateBrandPalette instead
 */
export function getContrastForeground(hex: string): string {
    const rgb = hexToRgb(hex);
    if (!rgb) return "oklch(0.985 0 0)";

    const luminance = 0.2126 * rgb.r + 0.7152 * rgb.g + 0.0722 * rgb.b;

    return luminance > 0.5
        ? "oklch(0.21 0.006 285.885)"
        : "oklch(0.985 0 0)";
}
