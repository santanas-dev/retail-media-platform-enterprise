import { useAuth } from "../auth/AuthContext";
import s from "./Dashboard.module.css";

const STATUS_LABELS: Record<string, string> = {
  active: "Активен",
  inactive: "Неактивен",
  suspended: "Приостановлен",
};

export default function DashboardPage() {
  const { user } = useAuth();

  if (!user) {
    return <div className={s.empty}>Нет данных пользователя.</div>;
  }

  const org = user.advertiser_organization;

  return (
    <div className={s.wrapper}>
      <h1 className={s.title}>Мой кабинет</h1>

      {/* ── Organization card ── */}
      <section className={s.card}>
        <h2 className={s.cardTitle}>Организация</h2>
        {org ? (
          <dl className={s.dl}>
            <dt>Название</dt>
            <dd>{org.legal_name}</dd>
            <dt>Отображаемое имя</dt>
            <dd>{org.display_name}</dd>
            <dt>Код</dt>
            <dd>{org.code}</dd>
            <dt>Статус</dt>
            <dd>
              <span className={`${s.badge} ${s[org.status] ?? ""}`}>
                {STATUS_LABELS[org.status] ?? org.status}
              </span>
            </dd>
          </dl>
        ) : (
          <p className={s.muted}>
            Организация не привязана. Обратитесь к администратору платформы.
          </p>
        )}
      </section>

      {/* ── User info card ── */}
      <section className={s.card}>
        <h2 className={s.cardTitle}>Пользователь</h2>
        <dl className={s.dl}>
          <dt>Имя</dt>
          <dd>{user.display_name || "—"}</dd>
          <dt>Логин</dt>
          <dd>{user.username || "—"}</dd>
          <dt>Тип доступа</dt>
          <dd>
            {user.advertiser_organization_id ? (
              <span className={`${s.badge} ${s.active}`}>
                Рекламодатель (ограниченный доступ)
              </span>
            ) : (
              <span className={`${s.badge} ${s.inactive}`}>
                Доступ не настроен
              </span>
            )}
          </dd>
          <dt>Провайдер</dt>
          <dd>{user.auth_provider}</dd>
        </dl>
      </section>

      {/* ── Permissions (collapsed by default) ── */}
      {user.permissions && user.permissions.length > 0 && (
        <details className={s.card}>
          <summary className={s.cardTitle}>Разрешения</summary>
          <ul className={s.permList}>
            {user.permissions.map((p) => (
              <li key={p} className={s.permItem}>
                {p}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
