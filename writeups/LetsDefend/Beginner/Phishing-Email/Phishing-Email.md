<p align="right">
  <sub>
    <b>Platform:</b> LetsDefend<br>
    <b>Difficulty:</b> Beginner<br>
    <b>Status:</b> Completed ✅<br>
    <b>URL:</b> <a href="https://app.letsdefend.io/challenge/phishing-email">Phishing Email</a><br>
    <b>Date:</b> Apr 15, 2026<br>
    <b>Tags:</b> #letsdefend #beginner #phishing #email-analysis #osint
  </sub>
</p>

---

## 🧠 Overview

A leaked email address resulted in receiving a suspicious PayPal email written in German. The task was to perform a full phishing email analysis — examining raw headers, embedded URLs, and domain reputation data to determine whether the email was malicious and document the indicators for defensive use.

---

## 🎯 Objectives

- Extract and analyse the phishing email sample from the provided archive
- Identify the `Return-Path` header and assess sender legitimacy
- Extract and evaluate embedded URLs within the email body
- Assess domain reputation of linked infrastructure
- Retrieve the body SHA-256 hash for threat intel pivoting
- Confirm whether the email constitutes a phishing attempt

---

## 🔍 Evidence & Initial Analysis

### Extracting the Sample

The challenge file was provided as a password-protected archive at:

```plaintext
C:\Users\LetsDefend\Desktop\Files\PhishingChallenge.zip
```

Extracted using the password `infected` — standard handling practice for malware and phishing samples to prevent accidental execution or detonation.

### Opening the Email

The extracted `.eml` file was opened in **Mozilla Thunderbird**. Rather than reading the rendered email, I navigated directly to **View Source** to access the raw headers and HTML body. The rendered view is designed to deceive — the source is where the forensic evidence lives.

---

## 🔬 Investigation

### Return-Path Analysis

With the raw source open, I used the find function to search for `return`, locating the `Return-Path` header immediately.

```plaintext
Return-Path: bounce@rjttznyzjjzydnillquh.designclub.uk.com
```

**Key Evidence:** The return path resolved to a randomly generated subdomain on `designclub.uk.com` — entirely unrelated to PayPal. This is a classic spoofing configuration where bounce traffic and replies are routed to attacker-controlled infrastructure rather than the legitimate sender's domain.

---

### Embedded URL Extraction

I analysed the raw HTML source using knowledge of how anchor tags and `href` attributes are structured. Phishing emails commonly embed malicious destinations inside `<a href="">` tags styled to mimic legitimate links.

```plaintext
storage.googleapis.com
```

**Key Evidence:** The actual link destination was a Google Cloud Storage bucket — not a PayPal domain. The display text likely showed something PayPal-branded while the `href` pointed elsewhere.

---

### Domain Reputation Assessment

I submitted the domain to VirusTotal for reputation analysis:

```plaintext
https://www.virustotal.com/gui/domain/storage.googleapis.com
```

**Finding:** VirusTotal returned a clean result — expected, as `storage.googleapis.com` is a legitimate Google service. However, a clean VT score does not equal safe in context.

Cross-referencing with open-source research confirmed that `storage.googleapis.com` is a well-documented abuse vector. Threat actors regularly host phishing pages and malware payloads on Google Cloud Storage because:

- It is a trusted domain, bypassing most URL reputation filters
- It serves content over HTTPS by default, adding false legitimacy
- Buckets are trivial to spin up and tear down, making takedown difficult

**Assessment: Suspicious — confirmed abuse vector despite clean reputation score.**

---

### Body SHA-256 Retrieval

Within VirusTotal, I navigated to the **Details** tab on the URL analysis. This surfaces the body hash of the fetched page content.

```plaintext
13945ecc33afee74ac7f72e1d5bb73050894356c4bf63d02a1a53e76830567f5
```

**Key Evidence:** This hash provides a stable identifier for the phishing page content, enabling pivoting across threat intel platforms to identify reuse of the same page under different URLs.

---

## 🚨 Findings

| Question | Answer |
|---|---|
| Return Path | `bounce@rjttznyzjjzydnillquh.designclub.uk.com` |
| Domain in URL | `storage.googleapis.com` |
| Domain suspicious? | Yes |
| Body SHA-256 | `13945ecc33afee74ac7f72e1d5bb73050894356c4bf63d02a1a53e76830567f5` |
| Phishing email? | Yes |

**IOC Found:** `bounce@rjttznyzjjzydnillquh.designclub.uk.com` — attacker-controlled bounce/reply handler

**IOC Found:** `storage.googleapis.com` — phishing page hosting via GCS bucket

**IOC Found:** Body SHA-256 `13945ecc33afee74ac7f72e1d5bb73050894356c4bf63d02a1a53e76830567f5`

### Attack Chain

1. Target email address obtained via data leak
2. Attacker crafted a spoofed PayPal email in German to increase perceived legitimacy for the target demographic
3. `Return-Path` set to attacker-controlled domain (`designclub.uk.com`) to handle bounces and replies
4. Malicious link embedded in HTML body pointing to a Google Cloud Storage bucket
5. Trusted domain used to bypass URL reputation filtering
6. Victim clicks link and lands on phishing page hosted on GCS

---

## 🗺️ MITRE ATT&CK Mapping

- **T1566.002** — Phishing: Spearphishing Link
- **T1598.003** — Phishing for Information: Spearphishing Link
- **T1585.001** — Establish Accounts: Social Media Accounts *(infrastructure staging via cloud storage)*
- **T1036** — Masquerading *(spoofed sender identity impersonating PayPal)*

---

## 🧩 Key Takeaways

- **Never trust the rendered email view.** Raw source analysis exposed the spoofed return path immediately — the rendered view would have shown a convincing PayPal email.
- **A clean VirusTotal result does not equal safe.** `storage.googleapis.com` passes reputation checks but is actively abused for phishing content hosting. Context matters.
- **Localisation is a deliberate social engineering tactic.** Sending in German adds perceived legitimacy for German-speaking targets and may reduce suspicion from analysts who assume it's simply a regional message.
- **Randomised subdomains are a tell.** The `rjttznyzjjzydnillquh` subdomain pattern is characteristic of automated phishing kit infrastructure.
- **Body SHA-256 hashes enable threat intel pivoting.** The same phishing page content can resurface under different URLs — a stable hash allows tracking across submissions.

---

## 🛡️ Defensive Recommendations

- **Enforce SPF, DKIM, and DMARC** on the organisation's email domain. This email would likely fail alignment checks — proper DMARC enforcement with a `reject` policy would have prevented delivery.
- **Deploy email gateway rules** to flag or quarantine emails where `Return-Path` and `From` domains do not align. Mismatched return paths are a reliable phishing signal.
- **Alert on links to cloud storage platforms** (GCS, S3, Azure Blob) in inbound email. Legitimate vendors do not link customers to raw cloud storage buckets.
- **User awareness training** — teach staff to inspect link destinations before clicking, treat unexpected financial emails with suspicion, and report anomalies regardless of perceived legitimacy.
- **Integrate threat intel feeds** that track abuse of cloud hosting platforms for phishing delivery. Detections based purely on domain reputation will miss these attacks.

---

## 🛠️ Tools & References

| Tool | Usage |
|---|---|
| Mozilla Thunderbird | Raw `.eml` source analysis |
| VirusTotal | Domain reputation analysis, body SHA-256 retrieval |
| Google Search | Contextual research on `storage.googleapis.com` abuse patterns |

- [VirusTotal](https://www.virustotal.com)
- [MITRE ATT&CK — T1566.002: Spearphishing Link](https://attack.mitre.org/techniques/T1566/002/)
- [LetsDefend — Phishing Email Challenge](https://app.letsdefend.io/challenge/phishing-email)

---

<p align="center"><img src="https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExaDdhdmt6N2dhazFqbTdsdmk0ZThkdTBrYjBoOGdobWF2NzRmbXBjeCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/8kDPdrfdBUP8k/giphy.gif" width="300"></p>
