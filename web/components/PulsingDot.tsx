export function PulsingDot({
  active,
  colorClass = "bg-emerald-400",
}: {
  active: boolean;
  colorClass?: string;
}) {
  return (
    <span
      className={`inline-flex h-2.5 w-2.5 rounded-full ${colorClass} ${
        active ? "animate-pulseMarker" : ""
      }`}
    />
  );
}
