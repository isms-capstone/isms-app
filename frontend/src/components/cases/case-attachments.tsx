"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Attachment = { id: number; filename: string; content_type: string };
const previewTypes = ["image/jpeg", "image/png", "image/webp"];

export function CaseAttachments({ ticketId }: { ticketId: number }) {
  const [files, setFiles] = useState<Attachment[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    api<Attachment[]>(`/tickets/${ticketId}/attachments`, {
      signal: controller.signal,
    })
      .then(setFiles)
      .catch((error) => {
        if (!controller.signal.aborted) setError(error.message);
      });
    return () => controller.abort();
  }, [ticketId]);

  return (
    <section className="surface detail-card" aria-label="ไฟล์แนบ">
      <h2>ไฟล์แนบ</h2>
      {error ? (
        <p role="alert" className="form-error">
          {error}
        </p>
      ) : !files ? (
        <p role="status">กำลังโหลดไฟล์แนบ…</p>
      ) : files.length === 0 ? (
        <p className="field-hint">ยังไม่มีไฟล์แนบ</p>
      ) : (
        <ul className="space-y-3">
          {files.map((file) => {
            const url = `/api/backend/tickets/${ticketId}/attachments/${file.id}/download`;
            return (
              <li key={file.id}>
                {previewTypes.includes(file.content_type) && (
                  <Image
                    unoptimized
                    src={url}
                    alt={file.filename}
                    width={640}
                    height={480}
                    className="h-auto max-h-80 w-auto max-w-full rounded object-contain"
                  />
                )}
                <a
                  href={url}
                  download={file.filename}
                  className="text-link break-all"
                >
                  {file.filename}
                </a>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
