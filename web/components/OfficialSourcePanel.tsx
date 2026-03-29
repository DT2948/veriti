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
    <div className="fixed inset-0 z-[1200] flex items-center justify-center bg-slate-950/70 px-4 backdrop-blur-sm">
      <div className="w-full max-w-xl rounded-3xl border border-line bg-[#0f1726] shadow-[0_30px_80px_rgba(0,0,0,0.45)]">
        <div className="flex items-center justify-between border-b border-[#243148] px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Official Source Intake</h2>
            <p className="mt-1 text-sm text-slate-400">
              Paste a government statement or official tweet to parse and publish.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-[#243148] bg-[#111c2d] px-3 py-2 text-sm text-slate-300 transition hover:border-[#4c8dff]/40 hover:text-slate-100"
          >
            Close
          </button>
        </div>

        <form className="space-y-4 px-5 py-5" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.14em] text-slate-500">
              Official Statement
            </label>
            <textarea
              rows={5}
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Paste official tweet or statement..."
              className="w-full rounded-2xl border border-[#243148] bg-[#111c2d] px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-[#4c8dff]/60"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.14em] text-slate-500">
              Source URL
            </label>
            <input
              type="url"
              value={sourceUrl}
              onChange={(event) => setSourceUrl(event.target.value)}
              placeholder="Source URL (optional)"
              className="w-full rounded-2xl border border-[#243148] bg-[#111c2d] px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-[#4c8dff]/60"
            />
          </div>

          {error ? (
            <div className="rounded-2xl border border-corroborated/40 bg-corroborated/10 px-4 py-3 text-sm text-corroborated">
              {error}
            </div>
          ) : null}

          {successLabel ? (
            <div className="rounded-2xl border border-official/40 bg-official/10 px-4 py-3 text-sm text-official">
              Published {successLabel}
            </div>
          ) : null}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-[#243148] bg-[#111c2d] px-4 py-2 text-sm text-slate-300 transition hover:border-[#4c8dff]/40 hover:text-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !text.trim()}
              className="inline-flex items-center gap-2 rounded-full border border-[#4c8dff]/40 bg-[#4c8dff]/15 px-4 py-2 text-sm font-medium text-[#9fc0ff] transition hover:bg-[#4c8dff]/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#9fc0ff] animate-pulse" />
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
