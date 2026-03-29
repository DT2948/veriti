"use client";

import { useEffect, useRef, useState } from "react";

import { PulsingDot } from "@/components/PulsingDot";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type AudioState = "idle" | "loading" | "playing" | "error";

interface HeaderProps {
  autoRefresh: boolean;
  onToggleAutoRefresh: (value: boolean) => void;
  incidentCount: number;
  refreshing: boolean;
  onOpenOfficialSource: () => void;
}

export function Header({
  autoRefresh,
  onToggleAutoRefresh,
  incidentCount,
  refreshing,
  onOpenOfficialSource,
}: HeaderProps) {
  void onToggleAutoRefresh;

  const [audioState, setAudioState] = useState<AudioState>("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const errorTimerRef = useRef<number | null>(null);

  const clearAudioResources = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current.onended = null;
      audioRef.current.onerror = null;
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      if (errorTimerRef.current) {
        window.clearTimeout(errorTimerRef.current);
      }
      clearAudioResources();
    };
  }, []);

  const setTemporaryErrorState = () => {
    clearAudioResources();
    setAudioState("error");
    if (errorTimerRef.current) {
      window.clearTimeout(errorTimerRef.current);
    }
    errorTimerRef.current = window.setTimeout(() => {
      setAudioState("idle");
      errorTimerRef.current = null;
    }, 3000);
  };

  const handleAudioBriefing = async () => {
    if (audioState === "playing") {
      clearAudioResources();
      setAudioState("idle");
      return;
    }

    if (audioState === "loading") {
      return;
    }

    if (errorTimerRef.current) {
      window.clearTimeout(errorTimerRef.current);
      errorTimerRef.current = null;
    }

    try {
      setAudioState("loading");
      clearAudioResources();

      const response = await fetch(`${API_BASE_URL}/api/v1/audio-briefing`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`Audio briefing failed: ${response.status}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);

      audioRef.current = audio;
      audioUrlRef.current = url;

      audio.onended = () => {
        clearAudioResources();
        setAudioState("idle");
      };
      audio.onerror = () => {
        setTemporaryErrorState();
      };

      await audio.play();
      setAudioState("playing");
    } catch {
      setTemporaryErrorState();
    }
  };

  const audioButtonClass =
    audioState === "playing"
      ? "border-primary/60 bg-primary/10 text-primary"
      : audioState === "loading"
        ? "border-primary/40 bg-elevated text-textPrimary"
        : audioState === "error"
          ? "border-danger/50 bg-danger/10 text-danger"
          : "border-line bg-transparent text-textSecondary hover:border-primary/40 hover:text-textPrimary";

  const audioButtonLabel =
    audioState === "playing"
      ? "Stop briefing"
      : audioState === "loading"
        ? "Generating..."
        : audioState === "error"
          ? "Unavailable"
          : "Audio briefing";

  return (
    <header className="flex min-h-[50px] items-center justify-between border-b border-line bg-ink px-3 py-2">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-md border border-line bg-panel text-[11px] font-semibold tracking-[0.18em] text-textPrimary">
          V
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-semibold uppercase tracking-[0.22em] text-textPrimary">
              Veriti
            </h1>
            {refreshing ? (
              <span className="text-[10px] uppercase tracking-[0.18em] text-textMuted">
                Refreshing
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="inline-flex items-center gap-2 px-1 text-[11px] uppercase tracking-[0.18em] text-textMuted">
          <PulsingDot active={autoRefresh} colorClass="bg-success" />
          <span>LIVE</span>
        </div>

        <button
          type="button"
          onClick={onOpenOfficialSource}
          className="inline-flex items-center rounded-sm border border-line bg-transparent px-2.5 py-1.5 text-xs text-textSecondary transition hover:border-primaryHover/40 hover:text-textPrimary"
        >
          Official Source
        </button>

        <button
          type="button"
          onClick={handleAudioBriefing}
          className={`inline-flex items-center gap-2 rounded-sm border px-2.5 py-1.5 text-xs transition ${audioButtonClass}`}
        >
          {audioState === "loading" ? (
            <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
          ) : audioState === "playing" ? (
            <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
          ) : audioState === "error" ? (
            <span className="h-2 w-2 rounded-full bg-danger" />
          ) : (
            <span className="h-2 w-2 rounded-full bg-textMuted" />
          )}
          {audioButtonLabel}
        </button>

        <div className="px-1 text-xs text-textMuted">{incidentCount} active</div>
      </div>
    </header>
  );
}
