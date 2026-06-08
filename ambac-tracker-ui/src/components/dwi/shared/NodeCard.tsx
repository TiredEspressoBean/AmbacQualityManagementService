import type React from "react";

export function NodeCard({
    icon,
    label,
    badges,
    rightSlot,
    children,
    className = "",
}: {
    icon: React.ReactNode;
    label: string;
    badges?: React.ReactNode;
    rightSlot?: React.ReactNode;
    children?: React.ReactNode;
    className?: string;
}) {
    return (
        <div className={`rounded-md border bg-muted/30 p-3 ${className}`}>
            <div className="flex flex-wrap items-center gap-2">
                {icon}
                <span className="font-medium">{label}</span>
                {badges}
                {rightSlot && <span className="ml-auto text-xs text-muted-foreground">{rightSlot}</span>}
            </div>
            {children && <div className="mt-2">{children}</div>}
        </div>
    );
}
