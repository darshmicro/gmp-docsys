# Using This on Mobile Phones (Same Office WiFi)

**Good news: you don't need a separate mobile app, and nothing new needs
to be installed anywhere.** This system is a website that only runs
inside your office network — any phone connected to your office WiFi can
open it in its normal browser (Safari on iPhone, Chrome on Android),
exactly the way a desktop computer does. The screens now automatically
rearrange themselves to fit a phone screen properly (this was just added
— menus tuck into a slide-out drawer, tables scroll instead of squeezing
illegibly small, buttons are bigger and easier to tap).

## Setting It Up on Someone's Phone (Once, Per Phone)

1. Make sure the phone is connected to the **same office WiFi** as the
   server computer — a phone on cellular data or a different WiFi network
   will not be able to reach it, since this system is intentionally not
   exposed to the public internet.
2. Open the phone's browser (Safari on iPhone, Chrome on Android).
3. Type in the same address you use on desktop computers — either:
   - `http://SERVERNAME:8000` (using the server's name), or
   - `http://192.168.x.x:8000` (using the server's actual network
     address/IP — ask whoever manages your network for this if the name
     alone doesn't work from a phone)
4. The login page should appear, already resized to fit the phone screen.
5. **Add it to the Home Screen so it looks and feels like an app icon:**
   - **iPhone (Safari):** tap the Share icon (square with an arrow) at
     the bottom of the screen, then tap **Add to Home Screen**.
   - **Android (Chrome):** tap the three-dot menu in the top-right
     corner, then tap **Add to Home screen** (or **Install app**, if
     that's what appears).
6. An icon now appears on the phone's home screen. Tapping it opens
   straight to the login page, just like a normal app — but it's still
   just a bookmark to the same website; no data of any kind is stored on
   the phone.

## What Changed to Make This Work Well

Previously, the menu bar down the side of the screen was a fixed width
that would have made everything else uncomfortably squeezed on a phone.
Now:
- On a phone-sized screen, that menu tucks away behind a **☰** button in
  the top-left corner — tap it to open the menu, tap anywhere outside it
  (or tap a menu item) to close it again.
- Tables that have a lot of columns (like the Audit Trail or Document
  Master list) now scroll sideways within their own box instead of
  squashing every column into unreadable tiny text.
- Buttons and input boxes are a bit taller, so they're easier to tap
  accurately with a finger.

## Things Worth Knowing

- **Everything a phone user does is exactly as real as a desktop user** —
  the same permissions apply (a Viewer role can't issue documents from a
  phone any more than from a desktop), and every action still goes into
  the same audit trail.
- **If someone leaves the office WiFi**, the app stops being reachable
  (by design — this is meant to stay inside your building's network, not
  be reachable from anywhere in the world). This is a security feature,
  not a bug.
- **No data is ever stored on the phone itself.** Exactly like the
  desktop setup, everything lives on the server/database — losing or
  replacing a phone loses nothing.
