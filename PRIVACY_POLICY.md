# Privacy Policy

**Last updated:** April 2026

This Privacy Policy explains how Veritas ("we," "us," "our") collects, uses, retains, and protects personal data when you use the Service. It is written to comply in good faith with the **EU General Data Protection Regulation (GDPR)** and the **California Consumer Privacy Act (CCPA/CPRA)**. If you are located in another jurisdiction, equivalent protections apply where required by local law.

## 1. Who we are

The Service is operated by Stanislav Vynnytskyi, a student developer. Contact: `stanislavvynnytskiy09@gmail.com`.

For GDPR purposes, we act as the **data controller** for personal data we collect.

## 2. What we collect

### 2a. When you register an account (mobile app)

- Email address
- Display name
- Hashed password (never stored in plain text)
- Account creation timestamp
- Consent record (whether you accepted these Terms and this Policy)

### 2b. When you submit a fact-check

- The URL of the video you submit
- The generated transcript, visual description, verdict, and sources (linked to your account)
- Timestamp and job status
- Optional: device push token (only if you enable notifications)

### 2c. When you use the public web demo (no account)

- The URL you submit
- The generated verdict (stored temporarily for result polling)
- Approximate IP address (for rate limiting only, not tied to identity)

### 2d. Automatically

- Basic server logs (IP, timestamp, endpoint, user-agent) for security and debugging
- Error diagnostics (stack traces, failed request metadata)

### 2e. What we do **not** collect

- We do not collect precise location data
- We do not sell personal data to third parties
- We do not serve advertisements or share data with advertising networks
- We do not use third-party analytics that build identity profiles across websites

## 3. Why we collect it — legal basis (GDPR Art. 6)

| Purpose | Legal basis |
|---|---|
| Running the Service you requested (producing a fact-check) | Performance of a contract (Art. 6(1)(b)) |
| Account registration, login, email verification | Performance of a contract |
| Rate limiting and abuse prevention | Legitimate interests (Art. 6(1)(f)) |
| Complying with legal obligations (e.g., lawful requests) | Legal obligation (Art. 6(1)(c)) |
| Marketing or newsletters (only if we add them) | Consent (Art. 6(1)(a)) — we will ask you separately |

## 4. How long we keep it

| Data | Retention |
|---|---|
| Account data (email, name, hashed password) | Until you delete your account |
| Fact-check results linked to your account | Until you delete them, or until you delete your account |
| Anonymous fact-check jobs (web demo) | Auto-deleted after 1 hour (TTL index in database) |
| Server logs | Up to 30 days |
| Error diagnostics | Up to 90 days |

Once retention expires, data is deleted or fully anonymized.

## 5. Who we share it with

We use a small number of trusted third-party processors to operate the Service. Each one processes only the data necessary to perform its function.

- **MongoDB Atlas** — database hosting
- **Render** — application hosting (if deployed)
- **Anthropic** (via the Emergent proxy) — AI analysis of transcripts and frames
- **Tavily, DuckDuckGo, Wikipedia, Brave Search** — web search for evidence
- **SerpApi** (optional) — reverse image search
- **imgbb** (optional) — short-lived image hosting for reverse image search
- **Stripe** (via the Emergent proxy, if subscriptions are enabled) — payment processing
- **Resend or similar** (if email verification is enabled) — transactional email

We do not share personal data with any of these providers beyond what is strictly necessary to operate the Service. We do not sell personal data and we do not share it with advertisers.

If we become legally compelled to disclose data (subpoena, court order, etc.), we will attempt to notify affected users unless prohibited by law.

## 6. International data transfers

Some of the providers listed above are located in the United States or other countries outside the EEA. Where required by GDPR, these transfers are covered by Standard Contractual Clauses (SCCs) or equivalent safeguards. By using the Service, you acknowledge that your data may be processed outside your country of residence.

## 7. Your rights

### Under GDPR (EEA, UK, Switzerland)

You have the right to:

- **Access** the personal data we hold about you
- **Rectification** — correct inaccurate data
- **Erasure** ("right to be forgotten") — delete your data
- **Restriction** of processing in certain cases
- **Portability** — receive your data in a machine-readable format
- **Object** to processing based on legitimate interests
- **Withdraw consent** at any time, where processing is based on consent
- **Lodge a complaint** with your local data protection authority

### Under CCPA/CPRA (California)

You have the right to:

- **Know** what personal information we collect, use, and disclose
- **Delete** personal information we hold about you
- **Correct** inaccurate personal information
- **Opt out** of "sale" or "sharing" of personal information (we do not sell or share)
- **Non-discrimination** for exercising these rights

### How to exercise your rights

Email `stanislavvynnytskiy09@gmail.com` with the subject line "Privacy Request" and describe what you want. We will respond within 30 days (GDPR) or 45 days (CCPA). We may ask for verification that you are the account holder before acting on a request.

## 8. Security

We use industry-standard measures to protect personal data: encrypted transport (HTTPS/TLS), hashed passwords (bcrypt), least-privilege database access, and environment-based secret management. No system is perfectly secure; if we discover a breach affecting your data, we will notify you and, where required, the relevant authority within 72 hours per GDPR Art. 33.

## 9. Children's privacy

Veritas is not intended for children under 13. We do not knowingly collect personal information from children under 13. If you believe we have collected data from a child under 13, email us and we will delete it.

For users aged 13-17, parents or guardians may contact us to review or delete their child's data.

## 10. Cookies and similar technologies

The mobile app does not use cookies. The web demo (if deployed) may use a minimal set of functional cookies (session identifier, rate-limit tokens). We do not use advertising, cross-site tracking, or analytics cookies without explicit consent. A cookie banner will be shown where legally required.

## 11. Changes to this Policy

We may update this Policy from time to time. Material changes will be announced in the app or repository. Continued use of the Service after changes take effect constitutes acceptance.

## 12. Contact

Questions, requests, or complaints: `stanislavvynnytskiy09@gmail.com`.

EU users also have the right to contact their national data protection authority directly.

---

**Note:** This Policy is a good-faith template for a student portfolio project and is not legal advice. If Veritas ever processes data for real commercial customers, this Policy should be reviewed and tailored by a qualified privacy lawyer, and a formal Data Processing Agreement (DPA) should be signed with each commercial sub-processor.
