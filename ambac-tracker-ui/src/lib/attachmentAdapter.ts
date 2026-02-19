import type {
  AttachmentAdapter,
  PendingAttachment,
  CompleteAttachment,
} from "@assistant-ui/react";

/**
 * Ephemeral attachment adapter for AI chat.
 * Handles text files and images, converting them to inline content
 * that gets passed directly to the LLM without persistent storage.
 */
export class EphemeralAttachmentAdapter implements AttachmentAdapter {
  accept(): string {
    return "image/*,text/*,.txt,.md,.csv,.json,.xml,.html,.pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  }

  async add(state: { file: File }): Promise<PendingAttachment> {
    const { file } = state;

    // Validate file size (10MB limit)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      return {
        id: crypto.randomUUID(),
        type: "document",
        name: file.name,
        contentType: file.type || "application/octet-stream",
        file,
        status: { type: "incomplete", reason: "error" },
      };
    }

    const isImage = file.type.startsWith("image/");

    return {
      id: crypto.randomUUID(),
      type: isImage ? "image" : "document",
      name: file.name,
      contentType: file.type || "application/octet-stream",
      file,
      status: { type: "requires-action", reason: "composer-send" },
    };
  }

  async send(attachment: PendingAttachment): Promise<CompleteAttachment> {
    const { file } = attachment;

    if (!file) {
      return {
        id: attachment.id,
        type: attachment.type,
        name: attachment.name,
        contentType: attachment.contentType,
        content: [],
        status: { type: "complete" },
      };
    }

    if (attachment.type === "image") {
      const base64 = await this.fileToBase64DataURL(file);
      return {
        id: attachment.id,
        type: "image",
        name: attachment.name,
        contentType: attachment.contentType,
        content: [{ type: "image", image: base64 }],
        status: { type: "complete" },
      };
    }

    // Binary documents (PDF, Word, etc.) - send as base64
    const binaryTypes = ["application/pdf", "application/msword", "application/vnd.openxmlformats"];
    if (binaryTypes.some(t => attachment.contentType.startsWith(t))) {
      const base64 = await this.fileToBase64DataURL(file);
      return {
        id: attachment.id,
        type: "document",
        name: attachment.name,
        contentType: attachment.contentType,
        content: [{ type: "file", name: attachment.name, mimeType: attachment.contentType, data: base64 }],
        status: { type: "complete" },
      };
    }

    // Text/document files
    const text = await file.text();
    return {
      id: attachment.id,
      type: "document",
      name: attachment.name,
      contentType: attachment.contentType,
      content: [
        {
          type: "text",
          text: `<attachment name="${attachment.name}">\n${text}\n</attachment>`,
        },
      ],
      status: { type: "complete" },
    };
  }

  async remove(): Promise<void> {
    // No cleanup needed for ephemeral attachments
  }

  fileToBase64DataURL(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }
}
