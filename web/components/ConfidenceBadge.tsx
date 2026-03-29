import type { Incident, MapIncident } from "@/types/incident";

type Tier = Incident["confidence_tier"] | MapIncident["confidence_tier"];

const styles: Record<Tier, string> = {
  official: "border border-success/40 bg-success/10 text-success",
  corroborated: "border border-corroborated/40 bg-corroborated/10 text-corroborated",
  plausible: "border border-plausible/40 bg-plausible/10 text-plausible",
  unverified: "border border-unverified/40 bg-unverified/10 text-slate-400",
};

export function ConfidenceBadge({ tier }: { tier: Tier }) {
  return (
    <span
      className={`inline-flex items-center rounded-sm px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${styles[tier]}`}
    >
      {tier}
    </span>
  );
}
