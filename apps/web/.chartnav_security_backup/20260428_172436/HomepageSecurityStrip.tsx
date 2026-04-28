/**
 * HomepageSecurityStrip
 * Inserts near the proof/trust area on the ChartNav homepage.
 *
 * Placement in home.en.json: add to "proof" or "trust" section block.
 * Placement in JSX: render after <ProofChips /> / before first content section.
 *
 * Do NOT hardcode copy here — read from home.en.json securityStrip key.
 * If key not yet in home.en.json, add the JSON block below first.
 *
 * home.en.json addition:
 * {
 *   "securityStrip": {
 *     "copy": "IBM watsonx-powered AI workflows, human review, role-based access, audit visibility, and security event logging — built for organizations that cannot afford blind automation.",
 *     "linkLabel": "Security & Governance →",
 *     "linkHref": "/chartnav/security"
 *   }
 * }
 */

import { Link } from 'wouter';

interface SecurityStripProps {
  copy:      string;
  linkLabel: string;
  linkHref:  string;
}

export function HomepageSecurityStrip({ copy, linkLabel, linkHref }: SecurityStripProps) {
  return (
    <div className="cn-security-strip" role="complementary" aria-label="Security overview">
      <div className="cn-container">
        <div className="cn-security-strip__inner">
          <p className="cn-security-strip__copy">
            <strong>Security & Governance — </strong>
            {copy}
          </p>
          <Link href={linkHref} className="cn-security-strip__link">
            {linkLabel}
          </Link>
        </div>
      </div>
    </div>
  );
}
