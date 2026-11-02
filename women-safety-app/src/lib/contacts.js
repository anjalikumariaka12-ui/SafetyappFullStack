// Contacts + user name live on the device (localStorage); they're sent to the server only when a trip starts,
// and the server forgets them when the trip ends.
const KEY = "raahi.contacts.v1";
const NAME = "raahi.name.v1";

export function loadContacts() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || [];
  } catch {
    return [];
  }
}
export function saveContacts(list) {
  localStorage.setItem(KEY, JSON.stringify(list));
}
export const getUserName = () => localStorage.getItem(NAME) || "";
export const setUserName = (n) => localStorage.setItem(NAME, n);

const intl = (phone) => {
  const d = (phone || "").replace(/\D/g, "").replace(/^0+/, "");
  return d.length === 10 ? `91${d}` : d;
};

// One-tap call / SMS / WhatsApp links: free, work even if the backend is down.
export function quickLinks(contacts, position, userName) {
  const where = position ? ` My location: https://www.google.com/maps?q=${position[0].toFixed(6)},${position[1].toFixed(6)}` : "";
  const text = encodeURIComponent(`Raahi SAFETY ALERT: ${userName || "I"} may need help.${where} Please call now. In an emergency dial 112.`);
  return contacts
    .filter((c) => intl(c.phone))
    .map((c) => ({
      name: c.name,
      tel: `tel:+${intl(c.phone)}`,
      sms: `sms:+${intl(c.phone)}?body=${text}`,
      whatsapp: `https://wa.me/${intl(c.phone)}?text=${text}`,
    }));
}
