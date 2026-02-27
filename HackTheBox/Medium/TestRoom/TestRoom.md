<p align="right">
  <sub>
    <b>Platform:</b> HackTheBox<br>
    <b>Difficulty:</b> Medium<br>
    <b>Status:</b> Completed ✅<br>
    <b>URL:</b> <a href="https://app.hackthebox.com/machines/Meow">TestRoom</a><br>
    <b>Date:</b> February 27, 2026<br>
    <b>Tags:</b> #hackthebox #medium #htb
  </sub>
</p>

---

# TestRoom

## 🧠 Overview

A straightforward box that exposed an unauthenticated Telnet service — one of those classic misconfigurations that shouldn't exist in the wild but still does. No credentials required, direct root access on connect.

## 🎯 Objectives

- Enumerate open ports and identify attack surface
- Gain initial access
- Retrieve the flag

## 🔍 Reconnaissance & Initial Analysis

I started with an nmap scan to identify open ports and services.

```bash
nmap -sC -sV <target-ip>
```

This revealed port 23 (Telnet) was open. Telnet is inherently insecure — traffic is unencrypted and, in misconfigured setups, can allow unauthenticated access entirely.

## ⚙️ Exploitation

With Telnet open, I connected directly to the target.

```bash
telnet <target-ip>
```

No credentials were required. The service dropped me straight into a root shell — classic case of a completely unauthenticated, misconfigured Telnet daemon running as root.

## 🏁 Flags / Proof

```
test{fake_flag}
```

## 🧩 Key Takeaways

- Telnet should never be exposed on a production system — it's unencrypted and, as seen here, can be trivially misconfigured to allow unauthenticated access
- Always check legacy ports (21, 23, 513, etc.) during enumeration; they're easy to overlook but often the path of least resistance
- Getting root directly through a service is rare in modern environments, but misconfigurations like this are still found in the wild

## 🛠️ Tools & References

- [nmap](https://nmap.org/) — Port scanning and service enumeration
- [telnet](https://linux.die.net/man/1/telnet) — Telnet client for connecting to TCP services