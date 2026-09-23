# AI Security Threat Model — Employee RAG Platform

## Threat Vectors & Mitigation Strategy

### 1. Direct Prompt Injection & Jailbreaking
- **Threat**: Adversary attempts to override system prompt instructions using inputs like `"Ignore previous instructions..."`.
- **Mitigation**:
  - `PromptInjectionGuardrail` heuristic and pattern filter.
  - Strict system prompt wrapping and parameter bounds.

### 2. Indirect Document Content Prompt Injection
- **Threat**: Malicious document text uploaded by an attacker containing embedded instructions like `"System: forget all rules..."`.
- **Mitigation**:
  - `DocumentContentGuardrail` treating all retrieved chunks as untrusted input string data. Neutralizes instruction syntax prior to context assembly.

### 3. Unauthorized Document Retrieval / ACL Bypass
- **Threat**: Low-privilege employee attempts to retrieve restricted HR or executive documents.
- **Mitigation**:
  - **Non-Negotiable Security Invariant**: Database-native payload filters (`access_level IN [...]`) generated from `UserContext` are applied directly inside vector and BM25 database queries before candidates reach candidate pool or LLM.

### 4. PII Data Exfiltration
- **Threat**: System output reveals email addresses, phone numbers, or employee identification numbers.
- **Mitigation**:
  - `PIIGuardrail` sanitizes output text with pattern replacement (`[EMAIL_REDACTED]`, `[PHONE_REDACTED]`).
