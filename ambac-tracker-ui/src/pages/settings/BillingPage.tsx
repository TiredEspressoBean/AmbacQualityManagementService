import { Link } from "@tanstack/react-router";
import { ArrowLeft, CreditCard, Check, Zap } from "lucide-react";

import { useTenantContext } from "@/components/tenant-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const PLANS = [
    {
        name: "Starter",
        price: "$49",
        period: "/month",
        description: "For small teams getting started with quality management",
        features: [
            "Up to 5 users",
            "Basic work orders",
            "Part tracking",
            "Email support",
        ],
        tier: "starter",
    },
    {
        name: "Pro",
        price: "$149",
        period: "/month",
        description: "For growing teams that need advanced features",
        features: [
            "Up to 25 users",
            "Advanced analytics",
            "CAPA management",
            "Document control",
            "API access",
            "Priority support",
        ],
        tier: "pro",
        popular: true,
    },
    {
        name: "Enterprise",
        price: "Custom",
        period: "",
        description: "For large organizations with custom requirements",
        features: [
            "Unlimited users",
            "SSO / SAML",
            "Custom integrations",
            "Dedicated support",
            "SLA guarantee",
            "On-premise option",
        ],
        tier: "enterprise",
    },
];

export function BillingPage() {
    const { tenant } = useTenantContext();
    const currentTier = tenant?.tier || "starter";

    return (
        <div className="container mx-auto p-6 max-w-5xl">
            {/* Header */}
            <div className="mb-8">
                <Link
                    to="/settings"
                    className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4"
                >
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back to Settings
                </Link>
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <CreditCard className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold">Billing & Plans</h1>
                        <p className="text-muted-foreground text-sm">
                            Manage your subscription and billing information
                        </p>
                    </div>
                </div>
            </div>

            {/* Current Plan */}
            <Card className="mb-8">
                <CardHeader>
                    <CardTitle className="text-lg">Current Plan</CardTitle>
                    <CardDescription>
                        You are currently on the{" "}
                        <span className="font-medium text-foreground capitalize">{currentTier}</span> plan
                        {tenant?.status === "trial" && (
                            <Badge variant="secondary" className="ml-2">
                                Trial
                            </Badge>
                        )}
                    </CardDescription>
                </CardHeader>
            </Card>

            {/* Plans */}
            <div className="grid md:grid-cols-3 gap-6 mb-8">
                {PLANS.map((plan) => {
                    const isCurrent = plan.tier === currentTier;
                    return (
                        <Card
                            key={plan.tier}
                            className={`relative ${plan.popular ? "border-primary shadow-md" : ""}`}
                        >
                            {plan.popular && (
                                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                                    <Badge className="bg-primary">Most Popular</Badge>
                                </div>
                            )}
                            <CardHeader>
                                <CardTitle>{plan.name}</CardTitle>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-3xl font-bold">{plan.price}</span>
                                    <span className="text-muted-foreground">{plan.period}</span>
                                </div>
                                <CardDescription>{plan.description}</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ul className="space-y-2 mb-6">
                                    {plan.features.map((feature) => (
                                        <li key={feature} className="flex items-center gap-2 text-sm">
                                            <Check className="h-4 w-4 text-primary flex-shrink-0" />
                                            {feature}
                                        </li>
                                    ))}
                                </ul>
                                <Button
                                    className="w-full"
                                    variant={isCurrent ? "outline" : plan.popular ? "default" : "outline"}
                                    disabled={isCurrent}
                                >
                                    {isCurrent ? (
                                        "Current Plan"
                                    ) : plan.tier === "enterprise" ? (
                                        "Contact Sales"
                                    ) : (
                                        <>
                                            <Zap className="h-4 w-4 mr-2" />
                                            Upgrade
                                        </>
                                    )}
                                </Button>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>

            {/* Coming Soon Notice */}
            <Card className="bg-muted/50">
                <CardContent className="pt-6">
                    <p className="text-center text-muted-foreground">
                        Online billing coming soon. Contact{" "}
                        <a href="mailto:sales@example.com" className="text-primary hover:underline">
                            sales@example.com
                        </a>{" "}
                        to upgrade your plan.
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
