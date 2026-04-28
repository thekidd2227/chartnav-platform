// Public-facing security information page for ChartNav.
// Renders at /chartnav/security. No authentication required.
// Plain clinical language. No compliance theater.

export function SecurityInfoPage() {
  return (
    <div className="security-info-page">
      <header className="security-info-page__header">
        <a href="/" className="security-info-page__back" aria-label="Back to ChartNav">
          <img
            src="/brand/chartnav-logo.svg"
            alt="ChartNav"
            width="140"
            height="32"
          />
        </a>
        <h1>Security</h1>
      </header>

      <main className="security-info-page__body">
        <section className="security-info-section">
          <h2>Data protection</h2>
          <ul>
            <li>All data encrypted in transit (TLS 1.2+) and at rest (AES-256).</li>
            <li>PHI is never stored in browser local storage or client-side caches.</li>
            <li>Database access is org-scoped. Cross-organization data leakage is structurally prevented at the query layer.</li>
          </ul>
        </section>

        <section className="security-info-section">
          <h2>Authentication and access control</h2>
          <ul>
            <li>JWT-based authentication with RS256/ES256 signature verification.</li>
            <li>Role-based access control (RBAC) with six defined roles: admin, clinician, reviewer, front desk, technician, biller/coder.</li>
            <li>Session governance with configurable idle and absolute timeouts per organization.</li>
            <li>MFA enforcement available at the organization level.</li>
            <li>Security-admin allowlist controls who can modify security policies.</li>
          </ul>
        </section>

        <section className="security-info-section">
          <h2>Audit trail</h2>
          <ul>
            <li>All sign, review, amend, export, and admin actions emit structured audit events.</li>
            <li>Audit events include actor, timestamp, organization, request ID, and action detail.</li>
            <li>Configurable audit sink (log, webhook, or external SIEM).</li>
            <li>Audit records are append-only. No deletion or modification after write.</li>
          </ul>
        </section>

        <section className="security-info-section">
          <h2>Clinical note integrity</h2>
          <ul>
            <li>Signed notes are immutable. Corrections create a new version via the amendment chain.</li>
            <li>Content fingerprint (SHA-256) is computed at sign time and stored alongside the note.</li>
            <li>Evidence chain links note lifecycle events with hash-chained integrity verification.</li>
            <li>Export snapshots preserve point-in-time state for forensic review.</li>
          </ul>
        </section>

        <section className="security-info-section">
          <h2>AI governance</h2>
          <ul>
            <li>All AI-generated outputs are logged with input/output hashes. Raw PHI is never stored in the AI audit trail.</li>
            <li>Human review is required before AI-generated clinical content is finalized.</li>
            <li>Prompt injection and jailbreak attempts are detected and logged as security events.</li>
            <li>AI use cases are registered with risk indicators (PHI exposure, output type, review requirements).</li>
          </ul>
        </section>

        <section className="security-info-section">
          <h2>Infrastructure</h2>
          <ul>
            <li>Rate limiting on all API endpoints.</li>
            <li>Request ID propagation for end-to-end traceability.</li>
            <li>CORS restricted to configured origins only.</li>
            <li>Structured error responses with stable error codes for client-side handling.</li>
          </ul>
        </section>

        <section className="security-info-section">
          <h2>Responsible disclosure</h2>
          <p>
            If you discover a security vulnerability, please contact{" "}
            <strong>security@chartnav.io</strong>. We acknowledge reports
            within two business days and aim to resolve confirmed
            vulnerabilities promptly.
          </p>
        </section>
      </main>

      <footer className="security-info-page__footer">
        <p>&copy; {new Date().getFullYear()} ChartNav. All rights reserved.</p>
      </footer>
    </div>
  );
}
