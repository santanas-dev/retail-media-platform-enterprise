import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import { hasPermission } from "../auth/permissions";

/**
 * CAMPAIGN-PERMISSION-SPLIT-001 — route-level guard for screens whose every
 * action needs a permission the signed-in user may not hold.
 *
 * Without it a cabinet user could open an operator screen by typing the URL,
 * fill in a whole form and only then be told 403. The API still enforces the
 * rule; this just makes the refusal readable and immediate.
 */
export default function RequirePermission({
  permission,
  children,
}: {
  permission: string;
  children: ReactNode;
}) {
  const { user } = useAuth();

  if (!hasPermission(user, permission)) {
    return (
      <div data-testid="permission-denied" style={{ maxWidth: 520 }}>
        <h2 style={{ fontSize: "1.125rem", margin: "0 0 0.5rem", color: "#991b1b" }}>
          Раздел недоступен
        </h2>
        <p style={{ margin: 0, color: "#475569", fontSize: "0.9rem", lineHeight: 1.5 }}>
          Этот раздел ведут менеджеры площадки. В кабинете доступны просмотр
          ваших кампаний и подача заявок — раздел «Заявки».
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
