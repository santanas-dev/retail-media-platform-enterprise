/**
 * CAMPAIGN-PERMISSION-SPLIT-001 — permission codes the cabinet reasons about.
 *
 * The advertiser role holds `campaign_briefs.manage` (its own self-service
 * write surface) and NOT `campaigns.manage` (operator campaign create, edit
 * and lifecycle). The API and PostgreSQL RLS are what actually enforce this;
 * the checks below only keep the cabinet from offering an action that is
 * guaranteed to come back 403, and from rendering an operator-only screen.
 * They are defence in depth, never the security boundary.
 */

/** Operator campaign management: create, edit, lifecycle, creative upload. */
export const CAMPAIGNS_MANAGE = "campaigns.manage";

/** Advertiser self-service brief writes: create draft, edit draft, submit. */
export const CAMPAIGN_BRIEFS_MANAGE = "campaign_briefs.manage";

export function hasPermission(
  user: { permissions?: string[] } | null | undefined,
  code: string,
): boolean {
  return Boolean(user?.permissions?.includes(code));
}
