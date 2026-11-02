"""Alert delivery. Every channel is optional and failures never crash the trip loop.

Free + automatic : Telegram bot (contact links their Telegram once)
Free + one-tap   : tel: / sms: / wa.me links returned to the app (user taps; no server cost, works in India)
Optional paid    : Twilio SMS / voice call (trial accounts can only reach *verified* numbers)
Control room     : POST to CONTROL_ROOM_WEBHOOK_URL (simulated/logged if unset)
"""
import logging
import re
from urllib.parse import quote

import httpx

from . import settings

log = logging.getLogger("raahi.alerts")
REASONS = {"off_route": "went off the planned route", "stalled": "has stopped for an unusually long time",
           "signal_lost": "stopped sending location", "sos": "pressed SOS"}


def intl(phone):
    """Digits only, India (+91) assumed for bare 10-digit numbers, leading 0 stripped."""
    d = re.sub(r"\D", "", phone or "").lstrip("0")
    return "91" + d if len(d) == 10 else d


def maps_link(pos):
    return f"https://www.google.com/maps?q={pos[0]:.6f},{pos[1]:.6f}" if pos else None


def message_for(t, kind="alert"):
    who = t.user_name
    if kind == "safe":
        return f"Raahi: {who} confirmed they are safe. Please ignore the earlier alert."
    why = REASONS.get(t.reason, "may need help")
    loc = maps_link(t.last_pos)
    return f"Raahi SAFETY ALERT: {who} {why} on route '{t.route_name}'." + (f" Last location: {loc}" if loc else "") + " Please call them now. In an emergency dial 112."


def contact_links(t, kind="alert"):
    """Deep links the app can show as one-tap buttons (free, no provider needed)."""
    body = quote(message_for(t, kind))
    out = []
    for c in t.contacts:
        wa = intl(c.get("phone", ""))
        if not wa:
            continue
        out.append({"name": c.get("name", ""), "tel": f"tel:+{wa}", "sms": f"sms:+{wa}?body={body}",
                    "whatsapp": f"https://wa.me/{wa}?text={body}"})
    return out


async def _telegram(client, chat_id, text):
    r = await client.post(f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                          json={"chat_id": chat_id, "text": text})
    r.raise_for_status()


async def _twilio(client, to, **data):
    kind = "Calls" if "Twiml" in data else "Messages"
    r = await client.post(f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_SID}/{kind}.json",
                          auth=(settings.TWILIO_SID, settings.TWILIO_TOKEN),
                          data={"To": to, "From": settings.TWILIO_FROM, **data})
    r.raise_for_status()


async def notify_contacts(t, kind="alert", client=None):
    """Returns per-channel results so the app/logs can show what actually went out."""
    text = message_for(t, kind)
    results = []
    own = client is None
    client = client or httpx.AsyncClient(timeout=10)
    try:
        for i, c in enumerate(t.contacts):
            name = c.get("name", "contact")
            if settings.TELEGRAM_BOT_TOKEN and c.get("telegram_chat_id"):
                try:
                    await _telegram(client, c["telegram_chat_id"], text)
                    results.append({"contact": name, "channel": "telegram", "ok": True})
                except Exception as e:
                    log.error("telegram failed: %s", e)
                    results.append({"contact": name, "channel": "telegram", "ok": False})
            if settings.TWILIO_SID and settings.TWILIO_FROM and c.get("phone"):
                to = "+" + intl(c["phone"])
                try:
                    await _twilio(client, to, Body=text)
                    results.append({"contact": name, "channel": "sms", "ok": True})
                    if kind == "alert" and i == 0 and settings.TWILIO_CALL_PRIMARY:
                        say = "This is an automated safety alert from Raahi. " + text.split(" Last location")[0]
                        await _twilio(client, to, Twiml=f"<Response><Say>{say}</Say></Response>")
                        results.append({"contact": name, "channel": "call", "ok": True})
                except Exception as e:
                    log.error("twilio failed: %s", e)
                    results.append({"contact": name, "channel": "sms/call", "ok": False})
    finally:
        if own:
            await client.aclose()
    log.warning("ALERT %s trip=%s results=%s", kind, t.id, results)
    return results


async def control_room(t, client=None):
    payload = {"trip_id": t.id, "user": t.user_name, "reason": t.reason, "route": t.route_name,
               "last_position": t.last_pos, "maps": maps_link(t.last_pos)}
    if not settings.CONTROL_ROOM_WEBHOOK_URL:
        log.warning("CONTROL ROOM (simulated, no webhook configured): %s", payload)
        return {"simulated": True}
    own = client is None
    client = client or httpx.AsyncClient(timeout=10)
    try:
        r = await client.post(settings.CONTROL_ROOM_WEBHOOK_URL, json=payload)
        r.raise_for_status()
        return {"simulated": False, "ok": True}
    except Exception as e:
        log.error("control room webhook failed: %s", e)
        return {"simulated": False, "ok": False}
    finally:
        if own:
            await client.aclose()


async def telegram_reply(chat_id, text):
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await _telegram(c, chat_id, text)
    except Exception as e:
        log.error("telegram reply failed: %s", e)
