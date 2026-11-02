import "./BottomNav.css";

const TABS = [
  { id: "plan", label: "Plan", icon: PlanIcon },
  { id: "trip", label: "Trip", icon: TripIcon },
  { id: "alerts", label: "Alerts", icon: AlertIcon },
  { id: "profile", label: "Profile", icon: ProfileIcon },
];

export default function BottomNav({ active, onChange }) {
  return (
    <nav className="bottom-nav" aria-label="Primary">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const isActive = active === tab.id;
        return (
          <button
            key={tab.id}
            className={`nav-item ${isActive ? "is-active" : ""}`}
            onClick={() => onChange(tab.id)}
            aria-current={isActive ? "page" : undefined}
          >
            <Icon active={isActive} />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

function PlanIcon({ active }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M4 12c3-6 6-6 8-3s5 3 8-3" stroke={active ? "var(--amber)" : "currentColor"} strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="4" cy="12" r="1.6" fill={active ? "var(--amber)" : "currentColor"} />
      <circle cx="20" cy="6" r="1.6" fill={active ? "var(--amber)" : "currentColor"} />
    </svg>
  );
}

function TripIcon({ active }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="8.5" stroke={active ? "var(--amber)" : "currentColor"} strokeWidth="1.8" />
      <circle cx="12" cy="12" r="2.4" fill={active ? "var(--amber)" : "currentColor"} />
    </svg>
  );
}

function AlertIcon({ active }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M12 3.5c-4 4.2-6.5 7.4-6.5 10.4a6.5 6.5 0 0 0 13 0c0-3-2.5-6.2-6.5-10.4Z" stroke={active ? "var(--amber)" : "currentColor"} strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

function ProfileIcon({ active }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8.2" r="3.4" stroke={active ? "var(--amber)" : "currentColor"} strokeWidth="1.8" />
      <path d="M4.5 20c1.6-3.6 4.6-5.4 7.5-5.4s5.9 1.8 7.5 5.4" stroke={active ? "var(--amber)" : "currentColor"} strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
