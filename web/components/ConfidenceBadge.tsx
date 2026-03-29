import type { Incident, MapIncident } from "@/types/incident";

type Tier = Incident["confidence_tier"] | MapIncident["confidence_tier"];

const styles: Record<Tier, string> = {
  official: "border border-success/40 bg-success/10 text-success",
  corroborated: "border border-corroborated/40 bg-corroborated/10 text-corroborated",
  plausible: "border border-plausible/40 bg-plausible/10 text-plausible",
  unverified: "border border-unverified/40 bg-unverified/10 text-unverified",
};

const ranges: Record<Tier, string> = {
  official: "90-100%",
  corroborated: "50-89%",
  plausible: "35-49%",
  unverified: "10-34%",
};

export function formatConfidenceScore(score: number): string {
  return `${Math.round(Math.max(0, Math.min(1, score)) * 100)}%`;
}

export function confidenceRangeLabel(tier: Tier): string {
  return ranges[tier];
}

export function ConfidenceBadge({ tier }: { tier: Tier }) {
  return (
    <span
      className={`inline-flex items-center rounded-sm px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${styles[tier]}`}
    >
      {tier}
    </span>
  );
}
