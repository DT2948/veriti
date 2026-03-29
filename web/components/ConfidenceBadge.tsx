import type { Incident, MapIncident } from "@/types/incident";

type Tier = Incident["confidence_tier"] | MapIncident["confidence_tier"];

const styles: Record<Tier, string> = {
  official: "bg-official/15 text-official ring-official/35",
  corroborated: "bg-corroborated/15 text-corroborated ring-corroborated/35",
  plausible: "bg-plausible/15 text-plausible ring-plausible/35",
  unverified: "bg-unverified/15 text-unverified ring-unverified/35",
};

export function ConfidenceBadge({ tier }: { tier: Tier }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em] ring-1 ${styles[tier]}`}
    >
      {tier}
    </span>
  );
}
