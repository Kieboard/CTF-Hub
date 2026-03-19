# 🔍 Enumeration Cheatsheet

Quick reference for enumeration methodology across common CTF and lab scenarios.

---

## 🌐 Network Enumeration

### Nmap

```bash
# Fast initial scan
nmap -T4 -F <IP>

# Full TCP scan
nmap -p- -T4 <IP>

# Service/version + default scripts
nmap -sC -sV -p <ports> <IP>

# UDP scan (top 100)
nmap -sU --top-ports 100 <IP>

# Output all formats
nmap -sC -sV -p <ports> -oA nmap/<name> <IP>
```

### Rustscan (faster alternative)

```bash
rustscan -a <IP> -- -sC -sV
```

---

## 🌍 Web Enumeration

### Directory Fuzzing

```bash
# Gobuster
gobuster dir -u http://<IP> -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -x php,html,txt

# Feroxbuster (recursive)
feroxbuster -u http://<IP> -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt

# ffuf
ffuf -u http://<IP>/FUZZ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
```

### Subdomain Fuzzing

```bash
ffuf -u http://<IP> -H "Host: FUZZ.<domain>" -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -fs <size>
```

### Whatweb / Tech Detection

```bash
whatweb http://<IP>
```

### Nikto

```bash
nikto -h http://<IP>
```

---

## 🗂️ SMB Enumeration

```bash
# List shares (no creds)
smbclient -L //<IP> -N

# Connect to share
smbclient //<IP>/<share> -N

# Enumerate with enum4linux
enum4linux -a <IP>

# Nmap SMB scripts
nmap -p 445 --script smb-enum-shares,smb-enum-users <IP>

# CrackMapExec
crackmapexec smb <IP>
crackmapexec smb <IP> -u '' -p '' --shares
```

---

## 📂 FTP Enumeration

```bash
# Anonymous login
ftp <IP>
# username: anonymous
# password: (blank or email)

# Nmap FTP scripts
nmap -p 21 --script ftp-anon,ftp-bounce <IP>
```

---

## 📧 SMTP Enumeration

```bash
nmap -p 25 --script smtp-enum-users <IP>
nc <IP> 25
VRFY root
```

---

## 🔐 SNMP Enumeration

```bash
snmpwalk -c public -v1 <IP>
onesixtyone -c /usr/share/seclists/Discovery/SNMP/common-snmp-community-strings.txt <IP>
```

---

## 🐧 Linux Privilege Escalation Checklist

```bash
# Current user and groups
id
whoami
groups

# Sudo permissions
sudo -l

# SUID binaries
find / -perm -4000 2>/dev/null

# Writable files
find / -writable -type f 2>/dev/null | grep -v proc

# Cron jobs
cat /etc/crontab
ls -la /etc/cron*

# Running processes
ps aux

# Network connections
ss -tulpn
netstat -tulpn

# Passwords in files
grep -r "password" /etc/ 2>/dev/null
grep -r "password" /var/www/ 2>/dev/null

# OS version
uname -a
cat /etc/os-release

# Automated: LinPEAS
curl -L https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh | sh
```

---

## 🪟 Windows Privilege Escalation Checklist

```powershell
# Current user
whoami
whoami /priv
whoami /groups

# System info
systeminfo

# Network
ipconfig /all
netstat -ano

# Running services
net start
sc query

# Scheduled tasks
schtasks /query /fo LIST /v

# Installed software
wmic product get name,version

# Automated: WinPEAS
.\winPEASx64.exe
```

---

## 🔑 Password Cracking

```bash
# Hashcat
hashcat -m <mode> hash.txt /usr/share/wordlists/rockyou.txt

# John
john hash.txt --wordlist=/usr/share/wordlists/rockyou.txt

# Identify hash type
hash-identifier
hashid <hash>

# Common hash modes (hashcat -m)
# 0    = MD5
# 100  = SHA1
# 1800 = sha512crypt (Linux $6$)
# 3200 = bcrypt
# 5600 = NetNTLMv2
# 1000 = NTLM
```

---

## 🛠️ Useful Tools Reference

| Tool | Purpose |
|------|---------|
| `nmap` | Port scanning |
| `gobuster` / `ffuf` | Directory/subdomain fuzzing |
| `enum4linux` | SMB/Windows enumeration |
| `crackmapexec` | SMB/AD enumeration |
| `linpeas` / `winpeas` | Automated privesc enumeration |
| `john` / `hashcat` | Password cracking |
| `burpsuite` | Web proxy and fuzzing |
| `metasploit` | Exploitation framework |
| `impacket` | AD/Windows attack toolkit |
| `bloodhound` | AD attack path visualisation |

---

*Part of [CTF-Hub](https://github.com/Kieboard/CTF-Hub) — maintained by Kieboard*
