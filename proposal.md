# ข้อเสนอโครงการสหกิจศึกษา

## Deterministic Enumeration and Checklist-Driven Reporting for Web Application Penetration Testing

---

## 1. ที่มาและความสำคัญของปัญหา

จากประสบการณ์ตรงในการฝึกงานด้าน penetration testing พบว่าขั้นตอน enumeration (การสำรวจพื้นผิวเป้าหมาย เช่น การสแกนพอร์ต ค้นหา endpoint ตรวจสอบ technology stack และ security header) เป็นขั้นตอนที่ใช้เวลามากที่สุดในทุกการทดสอบ แต่กลับให้คุณค่าทางการวิเคราะห์ (analytical value) ต่ำเมื่อเทียบกับเวลาที่เสียไป เนื่องจากผู้ทดสอบต้องสลับใช้เครื่องมือหลายตัว (nmap, ffuf, nikto, whatweb ฯลฯ) แยกกัน แล้วนำผลลัพธ์มารวมด้วยมือ

ปัจจุบันมีเครื่องมือเชิงพาณิชย์ (Pentest-Tools.com, Dradis, Penti) และเครื่องมือที่ขับเคลื่อนด้วย AI agent (VulnBot, PentAGI, Zen-AI-Pentest) จำนวนมากที่พยายามแก้ปัญหานี้ แต่มีข้อจำกัดร่วมกันคือ:

1. เป็นระบบปิดหรือพึ่งพา cloud ทำให้ไม่เหมาะกับการทดสอบระบบที่มีข้อมูลอ่อนไหวสูงอย่างระบบธนาคาร
2. เครื่องมือสาย AI agent ใช้ large language model เป็นผู้ตัดสินใจในขั้นตอน enumeration โดยตรง ซึ่งนำมาซึ่งต้นทุน token ที่สูง ผลลัพธ์ที่ไม่ deterministic และความเสี่ยงต่อ hallucination ซึ่งไม่เหมาะกับงานที่ต้องการความน่าเชื่อถือระดับ audit

โครงการนี้จึงมุ่งพัฒนาเครื่องมือที่ตัดปัญหาทั้งสองข้อ โดยใช้ AI เฉพาะในขั้นตอนที่ไม่กระทบความถูกต้องของข้อมูล (เช่น การเรียบเรียงข้อความรายงาน) แต่ให้ขั้นตอน enumeration ทั้งหมดทำงานแบบ deterministic ผ่านการเรียกใช้เครื่องมือมาตรฐานโดยตรง

---

## 2. วัตถุประสงค์ของโครงการ

- เพื่อพัฒนาเครื่องมือแบบ terminal-native ที่รวมเครื่องมือ enumeration สำหรับ web application ไว้ในจุดเดียว พร้อมระบบติดตามสถานะว่าเทคนิค/เครื่องมือใดถูกทดสอบแล้วบ้าง
- เพื่อออกแบบระบบ checklist ที่อ้างอิงมาตรฐาน OWASP Web Security Testing Guide (WSTG) และเชื่อมโยงแต่ละรายการเข้ากับเครื่องมือที่เกี่ยวข้องโดยอัตโนมัติ
- เพื่อพัฒนาโมดูล generate รายงานที่แปลงผลลัพธ์ดิบจากเครื่องมือให้อยู่ในรูปแบบที่พร้อมนำไปปรับใช้กับ template ของแต่ละบริษัท (เนื่องจากแต่ละบริษัทมี report format ของตนเองไม่ตายตัว) โดยรายงานที่ generate จะประกอบด้วยข้อมูลที่เป็นประโยชน์ต่อผู้ทดสอบ ได้แก่:
  - รายละเอียด finding พร้อม evidence และ raw output อ้างอิง
  - OWASP category ที่เกี่ยวข้อง
  - CVSS vector และคะแนนความรุนแรง
  - CWE ID ที่เกี่ยวข้อง
  - สถานะการยืนยัน (verified โดยผู้ทดสอบ / unverified จาก tool)
  - ข้อเสนอแนะเบื้องต้นสำหรับการแก้ไข (remediation)
- เพื่อให้ enumeration ทั้งกระบวนการทำงานแบบ offline/local ได้ 100% โดยไม่ต้องพึ่งพา AI หรือ cloud service ภายนอก เหมาะกับการทดสอบระบบที่มีความอ่อนไหวสูง

---

## 3. ขอบเขตของโครงการ

### ขอบเขต (In-scope)

- Target: Web application (HTTP/HTTPS) เท่านั้น — ไม่ครอบคลุม network infrastructure, Active Directory, wireless หรือ mobile application
- เครื่องมือที่รวมในเวอร์ชันแรก แบ่งตามหมวดการทำงาน:

| หมวดหมู่ | เครื่องมือ | หน้าที่ |
|---|---|---|
| Asset & Subdomain Discovery | subfinder, amass (passive), dnsx | ค้นหา subdomain และ asset ที่เกี่ยวข้องกับ target |
| Host & Port Enumeration | nmap | ตรวจสอบพอร์ตเปิดและระบุ service/version |
| HTTP Probing & Screenshot | httpx, gowitness/aquatone | ตรวจสอบว่า host ใดตอบสนอง HTTP และเก็บภาพหน้าจอเบื้องต้น |
| Content & Endpoint Discovery | ffuf/gobuster, katana | ค้นหา directory, file และ endpoint จากการ brute-force และ crawl JS/HTML |
| Technology & CMS Fingerprinting | whatweb, wappalyzer-cli, wpscan | ระบุ technology stack และตรวจสอบ CMS เฉพาะทาง (เช่น WordPress) |
| TLS & Header Analysis | testssl.sh, security header checker | ตรวจสอบ TLS posture และ security header (HSTS, CSP, X-Frame-Options ฯลฯ) |
| Vulnerability Signature Scanning | nikto, nuclei | สแกนหา signature ของช่องโหว่ที่รู้จักแล้วผ่าน template-based scanning (ยัง deterministic ไม่ใช่ AI-driven) |
| Parameter & API Discovery | arjun, GraphQL/REST endpoint checker | ค้นหา hidden parameter และ endpoint ของ API |
| WAF Detection | wafw00f | ตรวจสอบว่า target มี WAF ป้องกันอยู่หรือไม่ |
- ระบบ checklist อ้างอิง OWASP WSTG หมวด Information Gathering และ Configuration Management เป็นหลัก
- Export รายงานเป็น Word (.docx) และ Markdown พร้อม field OWASP category, CVSS vector/score และ CWE ID ต่อ finding

### นอกขอบเขต (Out-of-scope)

- การ exploit ช่องโหว่อัตโนมัติ (automated exploitation) — เครื่องมือทำหน้าที่ enumerate และรวบรวมหลักฐานเท่านั้น การยืนยันช่องโหว่ยังเป็นหน้าที่ของผู้ทดสอบ
- การพัฒนา scanner หรือ exploit ใหม่ตั้งแต่ต้น — โครงการนี้เป็น orchestration layer ที่ wrap เครื่องมือ open-source ที่มีอยู่แล้ว

---

## 4. การทบทวนเครื่องมือที่เกี่ยวข้องและจุดต่างของโครงการ

การสำรวจเครื่องมือที่มีอยู่ในตลาด (ข้อมูล ณ กลางปี 2026) พบกลุ่มเครื่องมือหลัก 3 กลุ่ม ดังตาราง:

| กลุ่มเครื่องมือ | ตัวอย่าง | ข้อจำกัดเทียบกับโครงการนี้ |
|---|---|---|
| Commercial / SaaS reporting | Dradis, Pentest-Tools.com, Penti | เป็น cloud-based หรือมีค่าใช้จ่าย ไม่เหมาะกับข้อมูลอ่อนไหวระดับธนาคาร |
| AI agent แบบ autonomous | VulnBot, PentAGI, Zen-AI-Pentest | ใช้ LLM ตัดสินใจในขั้น enumeration โดยตรง ต้นทุน token สูง ผลไม่ deterministic |
| CLI recon อัตโนมัติ (ไม่มี AI) | AutoRecon, reconFTW | รวมเครื่องมือและจัดเก็บผลลัพธ์ได้ แต่ไม่มีระบบ checklist tracking และไม่ generate รายงานตรง format CVSS/OWASP/CWE |

### จุดที่โครงการนี้แตกต่างและเติมเต็มช่องว่าง

- **Evidence-chain ที่ตรวจสอบย้อนกลับได้**: ทุก finding เชื่อมโยงกับ raw command และ raw output ต้นฉบับ เพื่อรองรับการตรวจสอบเชิง audit
- **Confidence flag**: แยกระหว่าง finding ที่ tool ตรวจพบอัตโนมัติ (unverified) กับที่ผู้ทดสอบยืนยันด้วยมือ (verified) เพื่อลดปัญหารายงานที่มี false positive จำนวนมากจนผู้รับรายงานเพิกเฉย
- **Offline-first เต็มรูปแบบ**: ไม่มีการส่งข้อมูลออกนอกเครื่องหรือเครือข่ายทดสอบ
- **Time-tracking ต่อ checklist item**: บันทึกเวลาที่เครื่องมือใช้ในการทำ enumeration แต่ละรายการ เพื่อสร้างข้อมูล baseline ที่ใช้ปรับปรุงเครื่องมือในระยะยาว (ไม่ใช้เปรียบเทียบโดยตรงกับเวลาที่ผู้ทดสอบแต่ละคนใช้ เนื่องจากทักษะและประสบการณ์ของผู้ทดสอบแต่ละคนแตกต่างกัน)

---

## 5. แนวทางการดำเนินงาน

สถาปัตยกรรมระบบแบ่งเป็น 3 ส่วนหลัก:

- **Tool Orchestration Layer**: wrapper เรียกเครื่องมือ external ผ่าน subprocess และ parse ผลลัพธ์ดิบให้เป็น structured data (JSON)
- **Checklist & State Engine**: จับคู่รายการใน OWASP WSTG กับเครื่องมือที่เกี่ยวข้อง ติดตามสถานะการทดสอบ และรองรับการเพิ่ม finding ด้วยมือผ่าน Terminal UI (Textual)
- **Reporting Engine**: แปลง finding ที่ยืนยันแล้วเป็นรายงานตาม template พร้อมคำนวณ CVSS และ mapping CWE/OWASP อัตโนมัติ

---

## 6. แผนการดำเนินงาน (ระยะเวลา 4 เดือน)

| เดือน | หัวข้อหลัก | รายละเอียด |
|---|---|---|
| เดือนที่ 1 | ออกแบบสถาปัตยกรรมหลัก | ออกแบบโครงสร้าง engagement state, พัฒนา Tool Orchestration Layer และ wrapper สำหรับเครื่องมือ enumeration ชุดแรก (nmap, ffuf, httpx) |
| เดือนที่ 2 | Checklist & State Engine | จับคู่ checklist กับ OWASP WSTG, พัฒนา Terminal UI สำหรับติ๊กสถานะและเพิ่ม finding ด้วยมือ |
| เดือนที่ 3 | Reporting Engine | พัฒนาระบบคำนวณ CVSS, mapping CWE/OWASP, และ export รายงานเป็น .docx/.md ตาม template |
| เดือนที่ 4 | ทดสอบและสรุปผล | ทดสอบกับ lab จริง (HackTheBox, internal lab), ประเมินความครบถ้วนของ checklist coverage และความสม่ำเสมอของผลลัพธ์เมื่อรันซ้ำ (reproducibility), จัดทำเอกสารและเตรียมนำเสนอ |

---

## 7. ผลลัพธ์ที่คาดว่าจะได้รับ

- เครื่องมือ CLI/TUI ที่ใช้งานได้จริงสำหรับ web application enumeration แบบ checklist-driven
- รายงาน pentest ต้นแบบที่ generate อัตโนมัติ พร้อม OWASP/CVSS/CWE metadata
- ข้อมูลเชิงปริมาณเกี่ยวกับความครบถ้วนของ checklist coverage และความสม่ำเสมอของผลลัพธ์เมื่อรันซ้ำ (reproducibility) ของเครื่องมือ
- เอกสารทางเทคนิคและคู่มือการใช้งานสำหรับต่อยอดในทีม pentest จริง

---

## 8. เทคโนโลยีที่ใช้

- ภาษาโปรแกรม: Python
- Terminal UI: Textual
- การจัดเก็บ state: SQLite หรือ flat file (JSON/YAML)
- การสร้างรายงาน: python-docx / Markdown template engine
- เครื่องมือ enumeration ที่ wrap: subfinder, amass, dnsx, nmap, httpx, gowitness/aquatone, ffuf/gobuster, katana, whatweb, wappalyzer-cli, wpscan, testssl.sh, nikto, nuclei, arjun, wafw00f
