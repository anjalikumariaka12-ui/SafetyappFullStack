import "./shared.css";
import StatusPill from "../components/StatusPill";
import { useEffect, useState } from "react";
import { ALERT_HISTORY } from "../lib/mockData";
import { api, apiEnabled } from "../lib/api";
import { getUserName, loadContacts, saveContacts, setUserName } from "../lib/contacts";

function toneFor(level) {
  if (level === "none") return "safe";
  if (level === "checkin") return "warn";
  return "danger";
}

export default function AlertsScreen() {
  return (
    <div className="screen">
      <div className="screen-header">
        <h1 className="screen-title">Alerts &amp; contacts</h1>
        <p className="screen-subtitle">Everything that's happened on your trips, and who gets notified.</p>
      </div>

      <div className="screen-body">
        <div>
          <p className="section-label" style={{ marginBottom: 8 }}>Trip history</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {ALERT_HISTORY.map((a) => (
              <div className="card" key={a.id}>
                <div className="row" style={{ alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13.5 }}>{a.route}</div>
                    <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>{a.date}</div>
                  </div>
                  <StatusPill tone={toneFor(a.level)}>
                    {a.level === "none" ? "No alert" : a.level === "checkin" ? "Checked in" : "Contacts alerted"}
                  </StatusPill>
                </div>
                <p style={{ margin: "10px 0 0", fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {a.outcome}
                </p>
              </div>
            ))}
          </div>
        </div>

        <ContactsSection />
      </div>
    </div>
  );
}

function ContactsSection() {
  const [contacts, setContacts] = useState(loadContacts);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [me, setMe] = useState(getUserName);
  const [link, setLink] = useState(null); // { contactId, code, deep_link } | { error }

  const update = (list) => { setContacts(list); saveContacts(list); };
  const add = () => {
    if (!name.trim() || phone.replace(/\D/g, "").length < 10) return;
    update([...contacts, { id: String(Date.now()), name: name.trim(), phone: phone.trim() }]);
    setName(""); setPhone("");
  };

  async function linkTelegram(contactId) {
    try {
      const l = await api.telegramLink();
      setLink({ contactId, ...l });
    } catch {
      setLink({ contactId, error: "Telegram alerts aren't set up on the server yet." });
    }
  }

  // Poll until the contact has pressed Start in the bot (up to ~3 min), then remember their chat id.
  useEffect(() => {
    if (!link?.code) return undefined;
    let tries = 0;
    const id = setInterval(async () => {
      tries += 1;
      try {
        const st = await api.telegramStatus(link.code);
        if (st.linked) {
          update(loadContacts().map((c) => (c.id === link.contactId ? { ...c, telegramChatId: st.chat_id } : c)));
          setLink(null);
        }
      } catch { /* keep trying */ }
      if (tries > 60) setLink(null);
    }, 3000);
    return () => clearInterval(id);
  }, [link?.code]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      <p className="section-label" style={{ marginBottom: 8 }}>Emergency contacts</p>
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <span className="field-label">Your name (shown in alerts)</span>
        <input className="input" value={me} placeholder="e.g. Priya" onChange={(e) => { setMe(e.target.value); setUserName(e.target.value); }} />
      </div>
      <div className="card" style={{ padding: "6px 14px", marginTop: 10 }}>
        {contacts.length === 0 && <p style={{ fontSize: 12.5, color: "var(--text-muted)" }}>No contacts yet. Add someone who should be alerted.</p>}
        {contacts.map((c, i) => (
          <div key={c.id} style={{ padding: "12px 0", borderBottom: "1px solid var(--border)" }}>
            <div className="row">
              <div>
                <div style={{ fontSize: 13.5, fontWeight: 500 }}>{c.name}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{c.phone}</div>
              </div>
              {i === 0 && <StatusPill tone="warn">Primary</StatusPill>}
            </div>
            <div className="row" style={{ marginTop: 8, justifyContent: "flex-start" }}>
              {apiEnabled && (c.telegramChatId ? (
                <StatusPill tone="safe">Telegram linked</StatusPill>
              ) : (
                <button className="back-btn" onClick={() => linkTelegram(c.id)}>Link Telegram (auto alerts)</button>
              ))}
              <button className="back-btn" onClick={() => update(contacts.filter((x) => x.id !== c.id))}>Remove</button>
            </div>
            {link?.contactId === c.id && (
              <p style={{ margin: "8px 0 0", fontSize: 12, lineHeight: 1.5, color: "var(--text-secondary)" }}>
                {link.error || (
                  <>Send this to {c.name} and ask them to open it and press Start: <a href={link.deep_link} target="_blank" rel="noreferrer" style={{ color: "var(--amber)" }}>{link.deep_link}</a> (waiting…)</>
                )}
              </p>
            )}
          </div>
        ))}
      </div>
      <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 10 }}>
        <input className="input" placeholder="Contact name" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="input" placeholder="Phone (e.g. 98765 43210)" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} />
        <button className="btn btn-ghost" onClick={add}>+ Add emergency contact</button>
      </div>
      <p style={{ fontSize: 11.5, color: "var(--text-muted)", lineHeight: 1.5, margin: "8px 2px 0" }}>
        Contacts stay on this phone and are sent to the server only while a trip is running.
      </p>
    </div>
  );
}
