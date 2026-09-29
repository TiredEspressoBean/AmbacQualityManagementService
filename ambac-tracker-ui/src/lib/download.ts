/** Save a Blob as a file download. */
export function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * The server's message for a failed `responseType: "blob"` request.
 *
 * With a blob response type, axios hands back an error body as a Blob too, so the
 * usual `error.response.data.detail` is undefined — the reason ("narrow the filter",
 * "you don't have permission") has to be read out of the Blob.
 */
export async function blobErrorMessage(error: unknown, fallback: string): Promise<string> {
    const response = (error as { response?: { status?: number; data?: unknown } } | null)?.response;
    if (!response) return fallback;
    const data = response.data;
    try {
        const text = data instanceof Blob ? await data.text() : null;
        const body = (text ? JSON.parse(text) : data) as { detail?: unknown } | null;
        if (body && typeof body.detail === "string") return body.detail;
    } catch {
        // not JSON — fall through
    }
    if (response.status === 403) return "You don't have permission to do that.";
    return fallback;
}
