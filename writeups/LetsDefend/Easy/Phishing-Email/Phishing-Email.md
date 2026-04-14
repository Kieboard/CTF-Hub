<p align="right">
  <sub>
    <b>Platform:</b> LetsDefend<br>
    <b>Difficulty:</b> Easy<br>
    <b>Status:</b> Completed ✅<br>
    <b>URL:</b> <a href="https://app.letsdefend.io/challenge/phishing-email">Phishing Email</a><br>
    <b>Date:</b> Apr 14, 2026<br>
    <b>Tags:</b> #letsdefend #easy
  </sub>
</p>

---

## 🧠 Overview

A leaked email address results in receiving a suspicious PayPal email written in German. The goal is to perform a full phishing email analysis — examining headers, embedded URLs, and reputation data to determine whether the email is malicious.

---

## 🎯 Objectives

- Extract and analyse the phishing email sample
- Identify the return path and embedded URLs
- Assess domain reputation
- Retrieve the body SHA-256 hash
- Confirm whether the email constitutes a phishing attempt

---

## 🔍 Reconnaissance & Initial Analysis

### Extracting the Sample

The challenge file was provided as a password-protected zip at the following path on the LetsDefend machine:

```
C:\Users\LetsDefend\Desktop\Files\PhishingChallenge.zip
```

I extracted it using the password `infected`, which is standard practice for malware/phishing samples to prevent accidental execution.

### Opening the Email

I opened the extracted `.eml` file in **Mozilla Thunderbird**. Rather than just reading the rendered email, I went straight to **View Source** to get the raw email headers and body — this is where all the useful forensic data lives.

---

### Question 1 — What is the return path of the email?

With the source open, I used the find function and searched for `return` to locate the `Return-Path` header.

**Key Finding:** The return path was not a PayPal domain at all — a massive red flag straight away.

```
Return-Path: bounce@rjttznyzjjzydnillquh.designclub.uk.com
```

**Result:** The return path pointed to a randomly generated-looking subdomain on `designclub.uk.com` — completely unrelated to PayPal. Classic spoofing setup where replies or bounces get routed to attacker-controlled infrastructure.

---

### Question 2 — What is the domain name of the URL in this email?

I combed through the raw HTML source using my knowledge of how anchor tags and href attributes work. Phishing emails typically embed malicious URLs inside `<a href="">` tags styled to look legitimate.

**Critical Discovery:** The embedded URL pointed to:

```
storage.googleapis.com
```

**Result:** The actual link destination was a Google Cloud Storage bucket — not PayPal.

---

### Question 3 — Is the domain suspicious?

I ran the domain through VirusTotal first:

```
https://www.virustotal.com/gui/domain/storage.googleapis.com
```

**Result:** VirusTotal returned it as clean, which makes sense — `storage.googleapis.com` is a legitimate Google service. However, a clean VT result doesn't mean the URL is safe in context.

A quick search confirmed what I already suspected: **`storage.googleapis.com` is a well-documented abuse vector**. Threat actors regularly host phishing pages and malware payloads on Google Cloud Storage because:
- It's a trusted domain, bypassing many URL reputation filters
- It uses HTTPS by default, giving a false sense of legitimacy
- Buckets are trivial to spin up and tear down

**Answer: Yes — suspicious in context.**

---

### Question 4 — What is the body SHA-256 of the domain?

Back in VirusTotal, I navigated to the **Details** tab for the URL analysis, which surfaces the body hash of the fetched content.

**Key Finding:**

```
13945ecc33afee74ac7f72e1d5bb73050894356c4bf63d02a1a53e76830567f5
```

**Result:** This hash can be used to pivot and identify if the same phishing page has been observed elsewhere or submitted under a different URL.

---

### Question 5 — Is this a phishing email?

Yes. Every indicator pointed to it:

- Return path routed to a non-PayPal domain with a randomised subdomain
- Email written in German targeting a leaked address (social engineering via localisation)
- Embedded URL redirected to a Google Cloud Storage bucket instead of PayPal
- No legitimate PayPal infrastructure involved anywhere in the chain

**Answer: Yes.**

---

## 🏁 Flags / Proof

| Question | Answer |
|---|---|
| Return Path | `bounce@rjttznyzjjzydnillquh.designclub.uk.com` |
| Domain in URL | `storage.googleapis.com` |
| Domain suspicious? | Yes |
| Body SHA-256 | `13945ecc33afee74ac7f72e1d5bb73050894356c4bf63d02a1a53e76830567f5` |
| Phishing email? | Yes |

---

## 🧩 Key Takeaways

- **Never trust the display name or rendered email.** Always check raw headers — the return path here immediately exposed the spoofing.
- **A clean VirusTotal score doesn't equal safe.** `storage.googleapis.com` is whitelisted by most tools but is actively abused for hosting phishing content.
- **Localisation is a social engineering tactic.** Sending the email in German increases perceived legitimacy for German-speaking targets.
- **Body SHA-256 hashes are useful for threat intel pivoting** — they let you track if the same phishing page resurfaces under different URLs.

---

## ⛓️ Attack Chain Summary

1. Target's email address obtained via data leak
2. Attacker crafts a spoofed PayPal email in German to add legitimacy
3. `Return-Path` set to attacker-controlled domain (`designclub.uk.com`) to handle bounces/replies
4. Malicious link embedded in HTML body pointing to a Google Cloud Storage bucket
5. Trusted domain (`storage.googleapis.com`) used to bypass URL reputation filters
6. Victim clicks link and lands on phishing page hosted on GCS

---

## 🔎 Detection Strategies

### Offensive Indicators

- `Return-Path` domain does not match the claimed sender domain (PayPal)
- Randomised subdomain in return path (`rjttznyzjjzydnillquh`) — typical of automated phishing infrastructure
- Embedded href resolving to `storage.googleapis.com` instead of `paypal.com`
- Email language inconsistency (German PayPal email to a non-German target)
- Body SHA-256: `13945ecc33afee74ac7f72e1d5bb73050894356c4bf63d02a1a53e76830567f5`

### Defensive Mitigations

- **Implement SPF, DKIM, and DMARC** on your email domain — this email would likely fail alignment checks
- **Deploy email gateway rules** to flag or quarantine emails where `Return-Path` and `From` domains don't align
- **Block or alert on links to cloud storage platforms** (GCS, S3, Azure Blob) in inbound email — legitimate vendors don't link to raw cloud buckets
- **User awareness training** — teach staff to hover over links before clicking and to treat unexpected financial emails with suspicion
- **Leverage threat intel feeds** that track abuse of cloud hosting platforms for phishing

---

## 🛠️ Tools & References

| Tool | Usage |
|---|---|
| Mozilla Thunderbird | Viewing raw `.eml` source |
| VirusTotal | Domain and URL reputation analysis, body SHA-256 retrieval |
| Google Search | Contextual research on `storage.googleapis.com` abuse |

- [VirusTotal](https://www.virustotal.com)
- [MITRE ATT&CK - Phishing: Spearphishing Link (T1566.002)](https://attack.mitre.org/techniques/T1566/002/)
- [Google Cloud Storage Phishing Abuse — documented threat vector](https://www.google.com)

---

![](https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExaDdhdmt6N2dhazFqbTdsdmk0ZThkdTBrYjBoOGdobWF2NzRmbXBjeCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/8kDPdrfdBUP8k/giphy.gif)
