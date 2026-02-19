import { useState } from "react"
import { schemas } from "@/lib/api/generated"
import { asUserInfo } from "@/lib/extended-types"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/ui/status-badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Plus, User, Calendar, AlertTriangle, Pencil, Trash2, CheckCircle, Info } from "lucide-react"
import { useCreateCapaTask } from "@/hooks/useCreateCapaTask"
import { useUpdateCapaTask } from "@/hooks/useUpdateCapaTask"
import { useDeleteCapaTask } from "@/hooks/useDeleteCapaTask"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

type CapaTasksTabProps = {
    capa: any
}

const taskTypeLabels: Record<string, string> = {
    CONTAINMENT: "Containment",
    CORRECTIVE: "Corrective Action",
    PREVENTIVE: "Preventive Action",
}

const taskStatusLabels: Record<string, string> = {
    NOT_STARTED: "Not Started",
    IN_PROGRESS: "In Progress",
    COMPLETED: "Completed",
    CANCELLED: "Cancelled",
}

type TaskFormData = {
    task_type: "CONTAINMENT" | "CORRECTIVE" | "PREVENTIVE"
    description: string
    due_date: string
    status: "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED"
    completion_notes: string
}

const initialFormData: TaskFormData = {
    task_type: "CORRECTIVE",
    description: "",
    due_date: "",
    status: "NOT_STARTED",
    completion_notes: "",
}

export function CapaTasksTab({ capa }: CapaTasksTabProps) {
    const [dialogOpen, setDialogOpen] = useState(false)
    const [editingTask, setEditingTask] = useState<any>(null)
    const [formData, setFormData] = useState<TaskFormData>(initialFormData)
    const [completeDialogOpen, setCompleteDialogOpen] = useState(false)
    const [completingTask, setCompletingTask] = useState<any>(null)
    const [completionNotes, setCompletionNotes] = useState("")

    const createTaskMutation = useCreateCapaTask()
    const updateTaskMutation = useUpdateCapaTask()
    const deleteTaskMutation = useDeleteCapaTask()
    const queryClient = useQueryClient()

    if (!capa) {
        return null
    }

    const tasks = capa.tasks || []

    // Group tasks by type
    const containmentTasks = tasks.filter((t: { task_type?: string }) => t.task_type === "CONTAINMENT")
    const correctiveTasks = tasks.filter((t: { task_type?: string }) => t.task_type === "CORRECTIVE")
    const preventiveTasks = tasks.filter((t: { task_type?: string }) => t.task_type === "PREVENTIVE")

    const handleOpenDialog = (task?: any) => {
        if (task) {
            setEditingTask(task)
            setFormData({
                task_type: task.task_type,
                description: task.description || "",
                due_date: task.due_date || "",
                status: task.status || "NOT_STARTED",
                completion_notes: task.completion_notes || "",
            })
        } else {
            setEditingTask(null)
            setFormData(initialFormData)
        }
        setDialogOpen(true)
    }

    const handleSubmit = async () => {
        try {
            const payload: any = {
                capa: capa?.id,
                task_type: formData.task_type,
                description: formData.description,
                due_date: formData.due_date || null,
                status: formData.status,
                completion_notes: formData.completion_notes || null,
            }

            if (editingTask) {
                await updateTaskMutation.mutateAsync({ id: editingTask.id, data: payload })
                toast.success("Task updated successfully")
            } else {
                await createTaskMutation.mutateAsync(payload)
                toast.success("Task created successfully")
            }
            queryClient.invalidateQueries({ queryKey: ["capa", capa?.id] })
            setDialogOpen(false)
        } catch (error) {
            toast.error(editingTask ? "Failed to update task" : "Failed to create task")
            console.error(error)
        }
    }

    const handleDelete = async (taskId: string) => {
        if (!confirm("Are you sure you want to delete this task?")) return
        try {
            await deleteTaskMutation.mutateAsync(taskId)
            queryClient.invalidateQueries({ queryKey: ["capa", capa?.id] })
            toast.success("Task deleted successfully")
        } catch (error) {
            toast.error("Failed to delete task")
            console.error(error)
        }
    }

    const handleOpenCompleteDialog = (task: any) => {
        setCompletingTask(task)
        setCompletionNotes("")
        setCompleteDialogOpen(true)
    }

    const handleCompleteTask = async () => {
        if (!completingTask) return
        try {
            await updateTaskMutation.mutateAsync({
                id: completingTask.id,
                data: {
                    capa: capa?.id,
                    task_type: completingTask.task_type,
                    description: completingTask.description,
                    status: "COMPLETED",
                    completion_notes: completionNotes,
                }
            })
            queryClient.invalidateQueries({ queryKey: ["capa", capa?.id] })
            toast.success("Task marked as completed")
            setCompleteDialogOpen(false)
        } catch (error) {
            toast.error("Failed to complete task")
            console.error(error)
        }
    }

    const updateField = (field: keyof TaskFormData, value: string) => {
        setFormData((prev) => ({ ...prev, [field]: value }))
    }

    const TaskCard = ({ task }: { task: any }) => {
        const assignedInfo = asUserInfo(task.assigned_to_info)

        return (
            <div className="flex items-start gap-4 p-4 rounded-lg border">
                <Checkbox
                    checked={task.status === "COMPLETED"}
                    disabled={task.status === "COMPLETED"}
                    onCheckedChange={() => task.status !== "COMPLETED" && handleOpenCompleteDialog(task)}
                    className="mt-1"
                />
                <div className="flex-1 space-y-2">
                    <div className="flex items-start justify-between">
                        <div>
                            <p className="font-medium">{task.description}</p>
                            <p className="text-sm text-muted-foreground font-mono">{task.task_number}</p>
                        </div>
                        <div className="flex items-center gap-2">
                            <StatusBadge status={task.status} label={task.status_display} />
                            {task.is_overdue && (
                                <Badge variant="destructive" className="gap-1">
                                    <AlertTriangle className="h-3 w-3" />
                                    Overdue
                                </Badge>
                            )}
                            <Button variant="ghost" size="icon" onClick={() => handleOpenDialog(task)}>
                                <Pencil className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" onClick={() => handleDelete(task.id)}>
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        {assignedInfo?.username && (
                            <div className="flex items-center gap-1">
                                <User className="h-3 w-3" />
                                {assignedInfo.username}
                            </div>
                        )}
                        {task.due_date && (
                            <div className={`flex items-center gap-1 ${task.is_overdue ? "text-destructive" : ""}`}>
                                <Calendar className="h-3 w-3" />
                                {new Date(task.due_date).toLocaleDateString()}
                            </div>
                        )}
                        <Badge variant="secondary" className="text-xs">
                            {task.completion_mode_display}
                        </Badge>
                    </div>

                    {/* Completion Notes */}
                    {task.completion_notes && (
                        <div className="mt-2 p-2 bg-muted/50 rounded text-sm">
                            <p className="text-muted-foreground text-xs mb-1">Completion Notes:</p>
                            <p>{task.completion_notes}</p>
                        </div>
                    )}
                </div>
            </div>
        )
    }

    const TaskSection = ({ title, tasks, type }: { title: string; tasks: any[]; type: string }) => {
        if (tasks.length === 0) return null

        return (
            <div className="space-y-3">
                <div className="flex items-center gap-2">
                    <h4 className="font-medium">{title}</h4>
                    <StatusBadge status={type} label={tasks.length.toString()} />
                </div>
                <div className="space-y-2">
                    {tasks.map((task: any) => (
                        <TaskCard key={task.id} task={task} />
                    ))}
                </div>
            </div>
        )
    }

    const TaskDialog = () => (
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>{editingTask ? "Edit Task" : "Add Task"}</DialogTitle>
                    <DialogDescription>
                        {editingTask ? "Update task details" : "Create a new task for this CAPA"}
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label>Task Type</Label>
                        <Select
                            value={formData.task_type}
                            onValueChange={(v) => updateField("task_type", v)}
                        >
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {schemas.TaskTypeEnum.options.map((type) => (
                                    <SelectItem key={type} value={type}>
                                        {taskTypeLabels[type] ?? type}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label>Description</Label>
                        <Textarea
                            value={formData.description}
                            onChange={(e) => updateField("description", e.target.value)}
                            placeholder="Describe the task..."
                            rows={3}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label>Due Date</Label>
                        <Input
                            type="date"
                            value={formData.due_date}
                            onChange={(e) => updateField("due_date", e.target.value)}
                        />
                    </div>

                    {editingTask && (
                        <div className="space-y-2">
                            <Label>Status</Label>
                            <Select
                                value={formData.status}
                                onValueChange={(v) => updateField("status", v)}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {schemas.CapaTaskStatusEnum.options.map((status) => (
                                        <SelectItem key={status} value={status}>
                                            {taskStatusLabels[status] ?? status}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    )}

                    {editingTask && formData.status === "COMPLETED" && (
                        <div className="space-y-2">
                            <Label>Completion Notes</Label>
                            <Textarea
                                value={formData.completion_notes}
                                onChange={(e) => updateField("completion_notes", e.target.value)}
                                placeholder="Notes about task completion..."
                                rows={2}
                            />
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => setDialogOpen(false)}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSubmit}
                        disabled={createTaskMutation.isPending || updateTaskMutation.isPending}
                    >
                        {createTaskMutation.isPending || updateTaskMutation.isPending
                            ? "Saving..."
                            : editingTask ? "Update" : "Create"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )

    const CompleteDialog = () => (
        <Dialog open={completeDialogOpen} onOpenChange={setCompleteDialogOpen}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>Complete Task</DialogTitle>
                    <DialogDescription>
                        Mark this task as completed
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="p-3 bg-muted/50 rounded-lg">
                        <p className="font-medium">{completingTask?.description}</p>
                    </div>
                    <div className="space-y-2">
                        <Label>Completion Notes (optional)</Label>
                        <Textarea
                            value={completionNotes}
                            onChange={(e) => setCompletionNotes(e.target.value)}
                            placeholder="Notes about how the task was completed..."
                            rows={3}
                        />
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => setCompleteDialogOpen(false)}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleCompleteTask}
                        disabled={updateTaskMutation.isPending}
                    >
                        <CheckCircle className="h-4 w-4 mr-2" />
                        {updateTaskMutation.isPending ? "Completing..." : "Mark Complete"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )

    return (
        <>
            <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle>Tasks</CardTitle>
                        <CardDescription>
                            {tasks.length} task{tasks.length !== 1 ? "s" : ""} •{" "}
                            {tasks.filter((t: { status?: string }) => t.status === "COMPLETED").length} completed
                        </CardDescription>
                    </div>
                    <Button onClick={() => handleOpenDialog()}>
                        <Plus className="h-4 w-4 mr-2" />
                        Add Task
                    </Button>
                </CardHeader>
                <CardContent className="space-y-6">
                    {tasks.length === 0 ? (
                        <p className="text-muted-foreground text-center py-8">
                            No tasks have been created yet. Add tasks to track corrective and preventive actions.
                        </p>
                    ) : (
                        <>
                            <TaskSection title="Containment Actions" tasks={containmentTasks} type="CONTAINMENT" />
                            <TaskSection title="Corrective Actions" tasks={correctiveTasks} type="CORRECTIVE" />
                            <TaskSection title="Preventive Actions" tasks={preventiveTasks} type="PREVENTIVE" />
                        </>
                    )}

                    <div className="flex items-start gap-2 p-3 bg-muted/50 rounded-lg text-sm text-muted-foreground">
                        <Info className="h-4 w-4 mt-0.5 shrink-0" />
                        <p>
                            Assigned users receive an email notification when tasks are created.
                            When all tasks are completed and RCA is finalized, the CAPA initiator and QA team
                            will be notified that this CAPA is ready for verification.
                        </p>
                    </div>
                </CardContent>
            </Card>
            <TaskDialog />
            <CompleteDialog />
        </>
    )
}
