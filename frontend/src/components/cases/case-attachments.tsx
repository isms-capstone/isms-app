"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type Attachment = {
  id: number;
  filename: string;
  content_type: string;
  download_url: string;
  thumbnail_url?: string | null;
  preview_url?: string | null;
};

function proxy(url: string) {
  return url.replace(/^\/api\/v1\//, "/api/backend/");
}

function AttachmentCard({ file }: { file: Attachment }) {
  const dialog = useRef<HTMLDialogElement>(null);
  return (
    <div className="space-y-2">
      {file.thumbnail_url && file.preview_url && (
        <>
          <button
            type="button"
            aria-label={`เปิดภาพ ${file.filename}`}
            onClick={() => dialog.current?.showModal()}
          >
            <Image
              unoptimized
              src={proxy(file.thumbnail_url)}
              alt={file.filename}
              width={160}
              height={120}
              className="h-auto max-h-40 w-auto rounded"
            />
          </button>
          <dialog
            ref={dialog}
            className="m-auto max-h-[95vh] max-w-[95vw] rounded p-4 backdrop:bg-black/60"
          >
            <form method="dialog" className="mb-2">
              <button type="submit" className="button">
                ปิดภาพ
              </button>
            </form>
            {file.preview_url && (
              <Image
                unoptimized
                loading="lazy"
                src={proxy(file.preview_url)}
                alt={file.filename}
                width={960}
                height={720}
                className="h-auto max-h-[80vh] w-auto max-w-full object-contain"
              />
            )}
          </dialog>
        </>
      )}
      <a
        href={proxy(file.download_url)}
        download={file.filename}
        className="text-link block break-all"
      >
        {file.filename}
      </a>
    </div>
  );
}

export function TimelineAttachment({
  ticketId,
  attachmentId,
  filename,
}: {
  ticketId: number;
  attachmentId: number;
  filename: string;
}) {
  const [file, setFile] = useState<Attachment | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    api<Attachment>(`/tickets/${ticketId}/attachments/${attachmentId}/access`, {
      signal: controller.signal,
    })
      .then(setFile)
      .catch(() => {});
    return () => controller.abort();
  }, [ticketId, attachmentId]);

  return file ? <AttachmentCard file={file} /> : <p>{filename}</p>;
}

const ACCEPTED_FILES =
  "image/jpeg,image/png,image/webp,image/gif,application/pdf,.mp4,.webm,.zip,.gz";

export function CaseAttachments({
  ticketId,
  canUpload = false,
}: {
  ticketId: number;
  canUpload?: boolean;
}) {
  const [files, setFiles] = useState<Attachment[] | null>(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState("");
  const [reload, setReload] = useState(0);
  const input = useRef<HTMLInputElement>(null);

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
  }, [ticketId, reload]);

  async function upload(selected: File[]) {
    setError("");
    let done = 0;
    try {
      for (const file of selected) {
        setUploading(`กำลังแนบ ${file.name} (${done + 1}/${selected.length})`);
        const body = new FormData();
        body.append("file", file);
        await api(`/tickets/${ticketId}/attachments`, { method: "POST", body });
        done += 1;
      }
    } catch (e) {
      const detail = e instanceof Error ? e.message : "แนบไฟล์ไม่สำเร็จ";
      setError(
        done ? `แนบแล้ว ${done} ไฟล์ แต่ไฟล์ถัดไปไม่สำเร็จ · ${detail}` : detail,
      );
    } finally {
      setUploading("");
      if (input.current) input.current.value = "";
      setReload((n) => n + 1);
    }
  }

  return (
    <section className="surface detail-card" aria-label="ไฟล์แนบ">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2>ไฟล์แนบ</h2>
        {canUpload && (
          <>
            <input
              ref={input}
              type="file"
              aria-label="เลือกไฟล์ที่จะแนบ"
              accept={ACCEPTED_FILES}
              multiple
              hidden
              onChange={(event) => {
                const selected = Array.from(event.target.files ?? []);
                if (selected.length) upload(selected);
              }}
            />
            <button
              type="button"
              className="button button-secondary"
              disabled={Boolean(uploading)}
              onClick={() => input.current?.click()}
            >
              แนบไฟล์
            </button>
          </>
        )}
      </div>
      {canUpload && (
        <p className="field-hint">
          ภาพ, MP4, WebM, PDF หรือไฟล์ log แบบ ZIP/GZIP ไม่เกิน 25 MB ต่อไฟล์
        </p>
      )}
      {uploading && <p role="status">{uploading}</p>}
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      {!files ? (
        !error && <p role="status">กำลังโหลดไฟล์แนบ…</p>
      ) : files.length === 0 ? (
        <p className="field-hint">ยังไม่มีไฟล์แนบ</p>
      ) : (
        <ul className="space-y-3">
          {files.map((file) => (
            <li key={file.id}>
              <AttachmentCard file={file} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
