// Mock data standing in for the trained route-scoring model and
// crowd-sourced safety layer described in the project proposal.
// Coordinates are loosely centred on Bhubaneswar, Odisha (KIIT campus area).

export const ORIGIN = {
  label: "KIIT Campus, Patia",
  lat: 20.3553,
  lng: 85.8189,
};

export const DESTINATION = {
  label: "Bhubaneswar Railway Station",
  lat: 20.2961,
  lng: 85.8245,
};

export const SAVED_PLACES = [
  { id: "home", label: "Home — Chandrasekharpur", icon: "home" },
  { id: "station", label: "Bhubaneswar Railway Station", icon: "train" },
  { id: "hostel", label: "Friend's PG, Patia", icon: "pin" },
];

// Three candidate routes for the same trip, each with a distinct path
// and a distinct safety profile — this is the output of the route-scoring model.
export const ROUTES = [
  {
    id: "r1",
    name: "Via Patia Main Road",
    score: 87,
    tag: "Recommended",
    distanceKm: 6.4,
    minutes: 19,
    path: [
      [20.3553, 85.8189],
      [20.3488, 85.8241],
      [20.3402, 85.8272],
      [20.3299, 85.8302],
      [20.3196, 85.8298],
      [20.2961, 85.8245],
    ],
    factors: [
      { label: "Street lighting", value: 0.9 },
      { label: "Crowd safety rating", value: 0.85 },
      { label: "Police proximity", value: 0.82 },
      { label: "Historical incident density", value: 0.15 },
    ],
    note: "Passes Patia police outpost and stays on lit, populated roads for the full stretch.",
  },
  {
    id: "r2",
    name: "Via Infocity Shortcut",
    score: 54,
    tag: "Faster, less safe",
    distanceKm: 5.1,
    minutes: 14,
    path: [
      [20.3553, 85.8189],
      [20.3517, 85.8286],
      [20.3411, 85.8354],
      [20.325, 85.8331],
      [20.2961, 85.8245],
    ],
    factors: [
      { label: "Street lighting", value: 0.45 },
      { label: "Crowd safety rating", value: 0.4 },
      { label: "Police proximity", value: 0.3 },
      { label: "Historical incident density", value: 0.58 },
    ],
    note: "5 minutes faster, but a 1.2 km stretch through Infocity has sparse lighting after 9 PM.",
  },
  {
    id: "r3",
    name: "Via NH16 Bypass",
    score: 68,
    tag: "Longer, moderate",
    distanceKm: 8.2,
    minutes: 24,
    path: [
      [20.3553, 85.8189],
      [20.3612, 85.8298],
      [20.3487, 85.8421],
      [20.3204, 85.8402],
      [20.2961, 85.8245],
    ],
    factors: [
      { label: "Street lighting", value: 0.7 },
      { label: "Crowd safety rating", value: 0.62 },
      { label: "Police proximity", value: 0.55 },
      { label: "Historical incident density", value: 0.32 },
    ],
    note: "Well-lit highway stretch but longer, with one isolated flyover section.",
  },
];

export const EMERGENCY_CONTACTS = [
  { id: "c1", name: "Ananya (Sister)", phone: "+91 98xxx xx210", primary: true },
  { id: "c2", name: "Rohit (Roommate)", phone: "+91 90xxx xx884", primary: false },
  { id: "c3", name: "Mother", phone: "+91 94xxx xx017", primary: false },
];

export const ALERT_HISTORY = [
  {
    id: "a1",
    date: "Yesterday, 9:42 PM",
    route: "Via Patia Main Road",
    outcome: "Reached safely",
    level: "none",
  },
  {
    id: "a2",
    date: "12 Aug, 8:15 PM",
    route: "Via Infocity Shortcut",
    outcome: "Check-in prompt shown — confirmed safe",
    level: "checkin",
  },
  {
    id: "a3",
    date: "3 Aug, 10:03 PM",
    route: "Via NH16 Bypass",
    outcome: "Contacts alerted — driver stopped 6 min at a flagged zone",
    level: "contacts",
  },
];

export const ESCALATION_STEPS = [
  {
    id: "checkin",
    title: "In-app check-in",
    detail: "A quiet prompt asks \u201cStill okay?\u201d with a 30-second timer.",
  },
  {
    id: "contacts",
    title: "Alert emergency contacts",
    detail: "If unanswered, your primary contacts get your live location silently.",
  },
  {
    id: "control-room",
    title: "Control-room escalation",
    detail: "If still unresolved, the trip is flagged to the campus/city helpline integration.",
  },
];
