import {ChevronDown} from "lucide-react";

export default function ProgressLabel({ currentStage, progress }: { currentStage: string, progress: number }) {
    return (
        <div className="flex items-center gap-2 w-full mt-12 mb-6">
            <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">Order Received</span>
            <div className="relative flex-1 h-3 bg-gray-200 dark:bg-gray-700 rounded-full">
                <div
                    className="absolute left-0 top-0 h-3 bg-green-500 dark:bg-green-400 rounded-full transition-all duration-500"
                    style={{width: `${progress}%`}}
                />
                <div
                    className="grid justify-items-center absolute -top-9 text-xs font-semibold text-green-600 dark:text-green-400 whitespace-nowrap"
                    style={{left: `${progress}%`, transform: 'translateX(-50%)'}}
                >
                    <div>{currentStage || 'Starting'}</div>
                    <div><ChevronDown size={14}/></div>
                </div>
            </div>
            <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">Shipped</span>
        </div>
    );
}
