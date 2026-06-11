<p align="right">
  <sub>
    <b>Platform:</b> LetsDefend<br>
    <b>Difficulty:</b> Beginner<br>
    <b>Status:</b> Completed ✅<br>
    <b>URL:</b> <a href="https://app.letsdefend.io/challenge/pcap-analysis">PCAP Analysis</a><br>
    <b>Date:</b> Apr 21, 2026<br>
    <b>Tags:</b> #letsdefend #beginner #challenge #network-forensics #pcap-analysis #dfir
  </sub>
</p>

---

## 🧠 Overview

A PCAP capture from P13's machine was submitted for analysis. The objective was to reconstruct network activity, identify communication pairs, and determine the nature of any file transfer events observed within the traffic. Analysis was conducted using Wireshark, focusing on conversation statistics and HTTP stream reconstruction.

---

## 🎯 Objectives

- Identify the sender and receiver IP addresses involved in the primary communication
- Locate any web server activity and identify the server's IP
- Determine the uploaded file name, upload directory, and web server software
- Establish the duration of the file transfer

---

## 🔍 Evidence & Initial Analysis

**File:** `Pcap_Analysis.pcapng`
**Location:** `/root/Desktop/ChallengeFile/Pcap_Analysis.pcapng`

The PCAP was opened in Wireshark. The first step was to get a high-level picture of which hosts were communicating. Navigated to **Statistics → Conversations → IPv4** tab to enumerate active communication pairs.

**Key Evidence:** Multiple IPs were present, but two stood out as the primary local communication pair, and a third as a web server target involved in file upload activity.

---

## 🔬 Investigation

### Step 1 — Identifying the Communication Pair

The IPv4 Conversations view immediately surfaced the most active pairs. The primary exchange occurred entirely within the local subnet.

- **Sender (P13):** `192.168.235.137`
- **Receiver (Cu713):** `192.168.235.131`

**Finding:** This is internal LAN traffic between two user machines — no external C2 or exfiltration at this stage.

---

### Step 2 — Identifying Web Server Activity

Further review of the conversation list identified a second communication stream between P13's machine and a separate host on a different subnet segment.

- **Web Server IP:** `192.168.1.7`

Traffic to this host was HTTP-based. Following the HTTP stream confirmed file upload activity via a PHP endpoint.

---

### Step 3 — HTTP Stream Analysis

Filtered for HTTP traffic and followed the TCP stream for the upload request to `192.168.1.7`.

```
http and ip.addr == 192.168.1.7
```

The HTTP POST request revealed the following:

- **Uploaded file name:** `file`
- **Upload path:** `/uploads`
- **Web server software:** `Apache`

**Finding:** A file named `file` was uploaded via HTTP POST to the `/uploads` directory on an Apache web server. This is consistent with a web shell upload scenario or data staging — a common post-exploitation technique.

---

### Step 4 — Transfer Duration

TCP conversation statistics were used to confirm the duration of the file transfer.

**Key Evidence:** The transfer completed in **0.0073 seconds** — a near-instant transfer consistent with a small payload or script upload.

---

## 🚨 Findings

| # | Finding | Detail |
|---|---------|--------|
| 1 | **Primary Communication Pair** | Sender: `192.168.235.137` / Receiver: `192.168.235.131` |
| 2 | **Web Server IP** | `192.168.1.7` |
| 3 | **Uploaded File Name** | `file` |
| 4 | **Upload Directory** | `/uploads` |
| 5 | **Web Server Software** | Apache |
| 6 | **Transfer Duration** | `0.0073` seconds |

**IOC Found:** HTTP POST file upload to `/uploads` on an internal Apache server — potential web shell staging activity originating from host `192.168.235.137`.

---

## 🗺️ MITRE ATT&CK Mapping

- **T1105** — Ingress Tool Transfer *(file uploaded to internal web server via HTTP POST)*
- **T1071.001** — Application Layer Protocol: Web Protocols *(HTTP used as the file transfer mechanism)*
- **T1190** — Exploit Public-Facing Application *(upload endpoint abused to stage a file)*
- **T1059.004** — Command and Scripting Interpreter: Unix Shell *(potential post-upload execution of staged payload)*

---

## 🧩 Key Takeaways

- Wireshark's **Statistics → Conversations** is the fastest way to triage a PCAP — always start there to identify active hosts before diving into individual packets.
- An HTTP POST to an `/uploads` directory on an internal web server is a significant red flag. A file generically named `file` with no extension strongly suggests deliberate obfuscation.
- Internal-to-internal traffic isn't automatically safe. Lateral movement and staging often occur entirely within the LAN — east-west visibility matters.
- A transfer duration of 0.0073 seconds indicates a small file — consistent with a script or web shell rather than bulk data exfiltration.

---

## 🛡️ Defensive Recommendations

- **Restrict file upload functionality** on internal web servers — enforce allowlists for permitted file types and block executable extensions at the server level.
- **Monitor HTTP POST traffic** to `/uploads` or similar directories. Flag these as high-confidence detection rules in your SIEM or IDS.
- **Inspect internal east-west traffic** — deploy network monitoring on internal segments and treat LAN-to-LAN HTTP file transfers as suspicious by default.
- **Harden Apache configurations** — disable directory listing, restrict upload directories from serving executable content, and enforce strict MIME type validation.
- **Alert on generic filenames** (e.g., `file`, `shell`, `cmd`) in HTTP upload requests — these are common web shell naming patterns that warrant immediate investigation.

---

## 🛠️ Tools & References

- [Wireshark](https://www.wireshark.org/) — PCAP analysis, TCP stream following, conversation statistics
- [MITRE ATT&CK T1105](https://attack.mitre.org/techniques/T1105/) — Ingress Tool Transfer
- [MITRE ATT&CK T1071.001](https://attack.mitre.org/techniques/T1071/001/) — Application Layer Protocol: Web Protocols
- [MITRE ATT&CK T1190](https://attack.mitre.org/techniques/T1190/) — Exploit Public-Facing Application
- [LetsDefend PCAP Analysis Challenge](https://app.letsdefend.io/challenge/pcap-analysis)

---

<p align="center"><img src="https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExaDdhdmt6N2dhazFqbTdsdmk0ZThkdTBrYjBoOGdobWF2NzRmbXBjeCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/8kDPdrfdBUP8k/giphy.gif" width="300"></p>
