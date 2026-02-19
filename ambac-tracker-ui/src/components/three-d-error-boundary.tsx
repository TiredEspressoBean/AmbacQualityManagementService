import React, { Component, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ThreeDErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error("3D Viewer Error:", error, errorInfo);
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null });
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="flex items-center justify-center h-full w-full bg-background">
                    <div className="text-center p-8 max-w-md">
                        <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-destructive" />
                        <h3 className="text-lg font-semibold mb-2">3D Viewer Error</h3>
                        <p className="text-sm text-muted-foreground mb-4">
                            Failed to render the 3D model. This could be due to browser compatibility,
                            WebGL issues, or a corrupted model file.
                        </p>
                        {this.state.error && (
                            <details className="text-xs text-left mb-4 p-2 bg-muted rounded">
                                <summary className="cursor-pointer font-medium">Error Details</summary>
                                <pre className="mt-2 overflow-auto">
                                    {this.state.error.toString()}
                                </pre>
                            </details>
                        )}
                        <Button onClick={this.handleReset} variant="outline">
                            Try Again
                        </Button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
