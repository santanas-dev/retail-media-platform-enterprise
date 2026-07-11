import { useState, useEffect } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type {
  AdvertiserOrganizationOut,
  AdvertiserBrandOut,
  AdvertiserContractOut,
  AdvertiserContactOut,
} from "../api/types";

const styles = {
  page: { maxWidth: 800 },
  h2: { fontSize: "1.25rem", fontWeight: 600, margin: "0 0 0.75rem" },
  card: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: "1rem",
    marginBottom: "1rem",
  },
  label: { fontSize: "0.8rem", color: "#64748b" },
  value: { fontSize: "0.95rem" },
  kv: { marginBottom: "0.4rem" } as React.CSSProperties,
  table: { width: "100%", borderCollapse: "collapse" as const, fontSize: "0.875rem" },
  th: { textAlign: "left" as const, padding: "0.4rem 0.5rem", borderBottom: "2px solid #e2e8f0", color: "#475569" },
  td: { padding: "0.35rem 0.5rem", borderBottom: "1px solid #f1f5f9" },
  input: {
    width: "100%",
    padding: "0.5rem",
    border: "1px solid #cbd5e1",
    borderRadius: 6,
    fontSize: "0.9rem",
    marginBottom: "0.5rem",
    boxSizing: "border-box" as const,
  },
  btn: {
    padding: "0.5rem 1.25rem",
    background: "#1e293b",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    fontSize: "0.9rem",
    cursor: "pointer",
  },
  error: { color: "#dc2626", fontSize: "0.85rem", marginTop: "0.25rem" },
  success: { color: "#16a34a", fontSize: "0.85rem", marginTop: "0.25rem" },
  banner: {
    background: "#fef3c7",
    border: "1px solid #f59e0b",
    borderRadius: 6,
    padding: "0.5rem 1rem",
    marginBottom: "1rem",
    fontSize: "0.85rem",
  },
  loading: { color: "#64748b", padding: "1rem 0" },
  empty: { color: "#94a3b8", fontSize: "0.85rem", padding: "0.5rem 0" },
};

export default function ProfilePage() {
  const { user, refreshMe } = useAuth();

  const [org, setOrg] = useState<AdvertiserOrganizationOut | null>(null);
  const [brands, setBrands] = useState<AdvertiserBrandOut[]>([]);
  const [contracts, setContracts] = useState<AdvertiserContractOut[]>([]);
  const [contacts, setContacts] = useState<AdvertiserContactOut[]>([]);
  const [contacts403, setContacts403] = useState(false);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  // Password change
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwSaving, setPwSaving] = useState(false);
  const [pwError, setPwError] = useState("");
  const [pwSuccess, setPwSuccess] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [orgRes, brandsRes, contractsRes] = await Promise.all([
          api.get<AdvertiserOrganizationOut[]>("/advertiser-organizations"),
          api.get<AdvertiserBrandOut[]>("/advertiser-brands"),
          api.get<AdvertiserContractOut[]>("/advertiser-contracts"),
        ]);
        if (cancelled) return;
        setOrg((orgRes as AdvertiserOrganizationOut[])?.[0] ?? null);
        setBrands(brandsRes as AdvertiserBrandOut[]);
        setContracts(contractsRes as AdvertiserContractOut[]);

        // Contacts may 403 if no advertisers.contacts.read — graceful
        try {
          const contactsRes = await api.get<AdvertiserContactOut[]>(
            "/advertiser-contacts",
          );
          if (!cancelled) setContacts(contactsRes as AdvertiserContactOut[]);
        } catch {
          if (!cancelled) setContacts403(true);
        }
      } catch (e: unknown) {
        if (!cancelled) setLoadError("Не удалось загрузить данные организации");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setPwError("");
    setPwSuccess("");

    if (!currentPw || !newPw || !confirmPw) {
      setPwError("Все поля обязательны");
      return;
    }
    if (newPw !== confirmPw) {
      setPwError("Пароли не совпадают");
      return;
    }
    if (newPw.length < 8) {
      setPwError("Пароль должен быть не менее 8 символов");
      return;
    }

    setPwSaving(true);
    try {
      await api.changePassword(currentPw, newPw);
      setPwSuccess("Пароль изменён");
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
      // Refresh /me so must_change_password banner disappears
      if (refreshMe) refreshMe();
    } catch (e: unknown) {
      const err = e as { status?: number; message?: string };
      if (err?.status === 400) {
        setPwError(err?.message || "Неверный текущий пароль или слабый новый пароль");
      } else {
        setPwError("Ошибка при смене пароля");
      }
    } finally {
      setPwSaving(false);
    }
  }

  if (loading) return <div style={styles.loading}>Загрузка профиля...</div>;
  if (loadError) return <div style={{ color: "#dc2626" }}>{loadError}</div>;

  return (
    <div style={styles.page}>
      <h2 style={styles.h2}>Профиль</h2>

      {/* must_change_password banner */}
      {user?.must_change_password && (
        <div style={styles.banner}>
          ⚠️ Необходимо сменить пароль. Используйте форму ниже.
        </div>
      )}

      {/* User info */}
      <div style={styles.card}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 0.6rem" }}>
          Пользователь
        </h3>
        <div style={styles.kv}>
          <span style={styles.label}>Имя пользователя: </span>
          <span style={styles.value}>{user?.username || "—"}</span>
        </div>
        <div style={styles.kv}>
          <span style={styles.label}>Отображаемое имя: </span>
          <span style={styles.value}>{user?.display_name || "—"}</span>
        </div>
        <div style={styles.kv}>
          <span style={styles.label}>Тип учётной записи: </span>
          <span style={styles.value}>{user?.auth_provider || "—"}</span>
        </div>
      </div>

      {/* Organization */}
      {org && (
        <div style={styles.card}>
          <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 0.6rem" }}>
            Организация
          </h3>
          <div style={styles.kv}>
            <span style={styles.label}>Название: </span>
            <span style={styles.value}>{org.display_name}</span>
          </div>
          <div style={styles.kv}>
            <span style={styles.label}>Юридическое название: </span>
            <span style={styles.value}>{org.legal_name}</span>
          </div>
          <div style={styles.kv}>
            <span style={styles.label}>Код: </span>
            <span style={styles.value}>{org.code}</span>
          </div>
          <div style={styles.kv}>
            <span style={styles.label}>Статус: </span>
            <span style={styles.value}>{org.status}</span>
          </div>
        </div>
      )}

      {/* Brands */}
      <div style={styles.card}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 0.6rem" }}>
          Бренды ({brands.length})
        </h3>
        {brands.length === 0 ? (
          <div style={styles.empty}>Нет брендов</div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Код</th>
                <th style={styles.th}>Название</th>
                <th style={styles.th}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {brands.map((b) => (
                <tr key={b.id}>
                  <td style={styles.td}>{b.code}</td>
                  <td style={styles.td}>{b.name}</td>
                  <td style={styles.td}>{b.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Contracts */}
      <div style={styles.card}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 0.6rem" }}>
          Договоры ({contracts.length})
        </h3>
        {contracts.length === 0 ? (
          <div style={styles.empty}>Нет договоров</div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Код</th>
                <th style={styles.th}>Название</th>
                <th style={styles.th}>Бюджет</th>
                <th style={styles.th}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {contracts.map((c) => (
                <tr key={c.id}>
                  <td style={styles.td}>{c.code}</td>
                  <td style={styles.td}>{c.name || "—"}</td>
                  <td style={styles.td}>
                    {c.budget_limit_amount != null
                      ? `${c.budget_limit_amount.toLocaleString()} ${c.budget_limit_currency}`
                      : "—"}
                  </td>
                  <td style={styles.td}>{c.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Contacts */}
      <div style={styles.card}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 0.6rem" }}>
          Контакты
        </h3>
        {contacts403 ? (
          <div style={styles.empty}>Нет доступа к контактам</div>
        ) : contacts.length === 0 ? (
          <div style={styles.empty}>Нет контактов</div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>ФИО</th>
                <th style={styles.th}>Тип</th>
                <th style={styles.th}>Email</th>
                <th style={styles.th}>Телефон</th>
              </tr>
            </thead>
            <tbody>
              {contacts.map((c) => (
                <tr key={c.id}>
                  <td style={styles.td}>{c.full_name}</td>
                  <td style={styles.td}>{c.contact_type}</td>
                  <td style={styles.td}>{c.email}</td>
                  <td style={styles.td}>{c.phone || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Password change */}
      <div style={styles.card}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 0.6rem" }}>
          Сменить пароль
        </h3>
        <form onSubmit={handleChangePassword}>
          <input
            type="password"
            placeholder="Текущий пароль"
            value={currentPw}
            onChange={(e) => setCurrentPw(e.target.value)}
            style={styles.input}
            autoComplete="current-password"
          />
          <input
            type="password"
            placeholder="Новый пароль (минимум 8 символов)"
            value={newPw}
            onChange={(e) => setNewPw(e.target.value)}
            style={styles.input}
            autoComplete="new-password"
          />
          <input
            type="password"
            placeholder="Подтвердите новый пароль"
            value={confirmPw}
            onChange={(e) => setConfirmPw(e.target.value)}
            style={styles.input}
            autoComplete="new-password"
          />
          {pwError && <div style={styles.error}>{pwError}</div>}
          {pwSuccess && <div style={styles.success}>{pwSuccess}</div>}
          <button type="submit" style={styles.btn} disabled={pwSaving}>
            {pwSaving ? "Сохранение..." : "Сменить пароль"}
          </button>
        </form>
      </div>
    </div>
  );
}
