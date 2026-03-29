"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import { createOfficialAlert } from "@/lib/api";

export function OfficialSourcePanel({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => Promise<void> | void;
}) {
  const [text, setText] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successLabel, setSuccessLabel] = useState<string | null>(null);

  if (!open) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessLabel(null);

    try {
      const incident = await createOfficialAlert({
        text,
        source_url: sourceUrl || undefined,
      });
      setSuccessLabel(`${incident.emoji ?? "📡"} ${incident.title}`);
      await onCreated();
      window.setTimeout(() => {
        setText("");
        setSourceUrl("");
        setSuccessLabel(null);
        onClose();
      }, 900);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Failed to parse and publish official source.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[1200] flex items-center justify-center bg-slate-950/80 px-4 backdrop-blur-sm">
      <div className="w-full max-w-xl rounded-md border border-line bg-panel">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-100">Official Source Intake</h2>
            <p className="mt-1 text-xs text-slate-500">
              Paste a government statement or official tweet to parse and publish.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-sm border border-line bg-transparent px-2.5 py-1.5 text-xs text-slate-300 transition hover:border-official/40 hover:text-slate-100"
          >
            Close
          </button>
        </div>

        <form className="space-y-3 px-4 py-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
              Official Statement
            </label>
            <textarea
              rows={5}
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Paste official tweet or statement..."
              className="w-full rounded-sm border border-line bg-panelSoft px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-official/60"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
              Source URL
            </label>
            <input
              type="url"
              value={sourceUrl}
              onChange={(event) => setSourceUrl(event.target.value)}
              placeholder="Source URL (optional)"
              className="w-full rounded-sm border border-line bg-panelSoft px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-official/60"
            />
          </div>

          {error ? (
            <div className="rounded-sm border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
              {error}
            </div>
          ) : null}

          {successLabel ? (
            <div className="rounded-sm border border-official/40 bg-official/10 px-3 py-2 text-sm text-official">
              Published {successLabel}
            </div>
          ) : null}

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded-sm border border-line bg-transparent px-3 py-1.5 text-xs text-slate-300 transition hover:border-official/40 hover:text-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !text.trim()}
              className="inline-flex items-center gap-2 rounded-sm border border-official/40 bg-official/10 px-3 py-1.5 text-xs font-medium text-slate-100 transition hover:bg-official/15 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-official animate-pulse" />
              ) : (
                <span>📡</span>
              )}
              Parse &amp; Publish
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
