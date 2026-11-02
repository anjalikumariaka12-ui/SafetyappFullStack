const TONES = {
  safe: { bg: "var(--teal-dim)", fg: "var(--teal)" },
  warn: { bg: "var(--amber-dim)", fg: "var(--amber)" },
  danger: { bg: "var(--coral-dim)", fg: "var(--coral)" },
  neutral: { bg: "rgba(244,241,234,0.08)", fg: "var(--text-secondary)" },
};

export default function StatusPill({ tone = "neutral", children }) {
  const t = TONES[tone] || TONES.neutral;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "4px 10px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 500,
        background: t.bg,
        color: t.fg,
        lineHeight: 1.4,
      }}
    >
      {children}
    </span>
  );
}
