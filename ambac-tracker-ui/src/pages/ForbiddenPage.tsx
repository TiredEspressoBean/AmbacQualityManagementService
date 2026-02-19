import { ShieldX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "@tanstack/react-router";

export default function ForbiddenPage() {
    const navigate = useNavigate();

    return (
        <div className="min-h-full flex items-center justify-center">
            <section className="px-6 py-16">
                <div className="max-w-lg mx-auto text-center">
                    <ShieldX className="w-20 h-20 mx-auto mb-6 text-destructive" />
                    <h1 className="text-4xl font-bold mb-4">
                        Access Denied
                    </h1>
                    <p className="text-lg text-muted-foreground mb-8">
                        You don't have permission to access this resource.
                        If you believe this is an error, please contact your administrator.
                    </p>
                    <div className="flex gap-4 justify-center">
                        <Button
                            variant="outline"
                            onClick={() => navigate({ to: "/" })}
                        >
                            Go Home
                        </Button>
                        <Button
                            onClick={() => window.history.back()}
                        >
                            Go Back
                        </Button>
                    </div>
                </div>
            </section>
        </div>
    );
}
