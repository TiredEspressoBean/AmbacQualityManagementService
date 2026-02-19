import { Button } from "@/components/ui/button.tsx";
import { Eye } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";

type Props = {
    capaId: string;
};

export function EditCapaActionsCell({ capaId }: Props) {
    const navigate = useNavigate();

    const handleViewCapa = () => {
        navigate({
            to: "/quality/capas/$id",
            params: { id: String(capaId) },
        });
    };

    return (
        <div className="flex items-center gap-1">
            <Button
                variant="ghost"
                size="icon"
                onClick={handleViewCapa}
                title="View CAPA"
            >
                <Eye className="h-4 w-4" />
            </Button>
        </div>
    );
}