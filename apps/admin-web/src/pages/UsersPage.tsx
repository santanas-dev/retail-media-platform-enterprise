import { useState, useEffect, useCallback } from "react";
import { api, ApiError } from "../api/client";
import type { UserOut, UserDetailOut, PaginatedUsers } from "../api/types";

interface UsersPageState {
  users: UserOut[];
  total: number;
  loading: boolean;
  error: string | null;
  selectedUser: UserDetailOut | null;
  actionError: string | null;
}

export default function UsersPage() {
  const [state, setState] = useState<UsersPageState>({
    users: [],
    total: 0,
    loading: true,
    error: null,
    selectedUser: null,
    actionError: null,
  });

  // Create form
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    username: "",
    display_name: "",
    advertiser_organization_id: "",
    auto_generate_password: true,
    temporary_password: "",
    must_change_password: true,
  });
  const [createResult, setCreateResult] = useState<{
    message: string;
    one_time_password?: string;
  } | null>(null);

  // Reset password form
  const [resetOpen, setResetOpen] = useState(false);
  const [resetUserId, setResetUserId] = useState("");
  const [resetForm, setResetForm] = useState({
    auto_generate_password: true,
    new_temporary_password: "",
    revoke_sessions: true,
  });
  const [resetResult, setResetResult] = useState<{
    message: string;
    one_time_password?: string;
  } | null>(null);

  // ── Load users ──

  const loadUsers = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await api.get<PaginatedUsers>("/users?limit=50");
      setState((s) => ({
        ...s,
        users: data.items,
        total: data.total,
        loading: false,
      }));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка загрузки";
      setState((s) => ({ ...s, error: msg, loading: false }));
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // ── Create local advertiser ──

  async function handleCreate() {
    setCreateResult(null);
    try {
      const body: Record<string, unknown> = {
        username: createForm.username,
        display_name: createForm.display_name,
        advertiser_organization_id: createForm.advertiser_organization_id,
        must_change_password: createForm.must_change_password,
        auto_generate_password: createForm.auto_generate_password,
      };
      if (!createForm.auto_generate_password && createForm.temporary_password) {
        body.temporary_password = createForm.temporary_password;
        body.auto_generate_password = false;
      }

      const resp = await api.post<{
        user_id: string;
        username: string;
        display_name: string;
        one_time_password?: string;
        message: string;
      }>("/users/local-advertiser", body);

      setCreateResult({
        message: resp.message,
        one_time_password: resp.one_time_password,
      });
      setCreateOpen(false);
      loadUsers();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка создания";
      setCreateResult({ message: msg });
    }
  }

  // ── Activate / Deactivate ──

  async function handleDeactivate(userId: string) {
    try {
      await api.post(`/users/${userId}/deactivate`);
      loadUsers();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка";
      setState((s) => ({ ...s, actionError: msg }));
    }
  }

  async function handleActivate(userId: string) {
    try {
      await api.post(`/users/${userId}/activate`);
      loadUsers();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка";
      setState((s) => ({ ...s, actionError: msg }));
    }
  }

  // ── Reset password ──

  function openReset(userId: string) {
    setResetUserId(userId);
    setResetOpen(true);
    setResetResult(null);
    setResetForm({
      auto_generate_password: true,
      new_temporary_password: "",
      revoke_sessions: true,
    });
  }

  async function handleReset() {
    setResetResult(null);
    try {
      const body: Record<string, unknown> = {
        auto_generate_password: resetForm.auto_generate_password,
        revoke_sessions: resetForm.revoke_sessions,
      };
      if (!resetForm.auto_generate_password && resetForm.new_temporary_password) {
        body.new_temporary_password = resetForm.new_temporary_password;
        body.auto_generate_password = false;
      }

      const resp = await api.post<{
        user_id: string;
        must_change_password: boolean;
        sessions_revoked: boolean;
        one_time_password?: string;
        message: string;
      }>(`/users/${resetUserId}/reset-password`, body);

      setResetResult({
        message: resp.message,
        one_time_password: resp.one_time_password,
      });
      setResetOpen(false);
      loadUsers();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка сброса пароля";
      setResetResult({ message: msg });
    }
  }

  // ── Styles ──

  const pageStyle: React.CSSProperties = {
    maxWidth: 1100,
    margin: "0 auto",
  };
  const headerStyle: React.CSSProperties = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "1rem",
  };
  const tableStyle: React.CSSProperties = {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "0.875rem",
  };
  const thStyle: React.CSSProperties = {
    textAlign: "left",
    padding: "0.5rem",
    borderBottom: "2px solid #e2e8f0",
    color: "#475569",
    fontWeight: 600,
  };
  const tdStyle: React.CSSProperties = {
    padding: "0.5rem",
    borderBottom: "1px solid #e2e8f0",
    verticalAlign: "top",
  };
  const btnStyle: React.CSSProperties = {
    padding: "0.25rem 0.5rem",
    fontSize: "0.75rem",
    border: "1px solid #cbd5e1",
    borderRadius: 4,
    background: "#fff",
    cursor: "pointer",
    marginRight: "0.25rem",
    marginBottom: "0.25rem",
  };
  const dangerBtn: React.CSSProperties = {
    ...btnStyle,
    color: "#dc2626",
    borderColor: "#fca5a5",
  };
  const badge: React.CSSProperties = {
    display: "inline-block",
    padding: "0.1rem 0.4rem",
    borderRadius: 4,
    fontSize: "0.7rem",
    fontWeight: 600,
    marginRight: "0.25rem",
  };
  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "0.375rem 0.5rem",
    border: "1px solid #cbd5e1",
    borderRadius: 4,
    fontSize: "0.875rem",
    boxSizing: "border-box",
    marginBottom: "0.5rem",
  };
  const labelStyle: React.CSSProperties = {
    display: "block",
    fontSize: "0.8rem",
    color: "#475569",
    marginBottom: "0.25rem",
  };

  // ── Render ──

  const statusBadge = (status: string) => {
    const active = status === "active";
    return (
      <span
        style={{
          ...badge,
          background: active ? "#dcfce7" : "#fee2e2",
          color: active ? "#166534" : "#991b1b",
        }}
      >
        {active ? "Активен" : "Неактивен"}
      </span>
    );
  };

  const providerLabel = (p: string) => {
    const map: Record<string, string> = {
      local_advertiser: "Локальный (рекламодатель)",
      local_break_glass: "Локальный (break-glass)",
      ad: "Active Directory",
    };
    return map[p] ?? p;
  };

  if (state.loading) {
    return <p>Загрузка пользователей...</p>;
  }

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <h1 style={{ margin: 0 }}>Пользователи</h1>
        <button
          type="button"
          onClick={() => {
            setCreateOpen(!createOpen);
            setCreateResult(null);
          }}
          style={{ ...btnStyle, padding: "0.5rem 1rem", fontSize: "0.875rem" }}
        >
          {createOpen ? "Отмена" : "+ Создать рекламодателя"}
        </button>
      </div>

      {state.error && (
        <p style={{ color: "#dc2626", marginBottom: "1rem" }}>{state.error}</p>
      )}
      {state.actionError && (
        <p style={{ color: "#dc2626", marginBottom: "0.5rem" }}>
          {state.actionError}
        </p>
      )}

      {/* ── Create form ── */}
      {createOpen && (
        <div
          style={{
            background: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: 8,
            padding: "1rem",
            marginBottom: "1rem",
            maxWidth: 420,
          }}
        >
          <h3>Создать локального рекламодателя</h3>
          <label style={labelStyle}>Имя пользователя</label>
          <input
            style={inputStyle}
            value={createForm.username}
            onChange={(e) =>
              setCreateForm({ ...createForm, username: e.target.value })
            }
            placeholder="advertiser_login"
          />
          <label style={labelStyle}>Отображаемое имя</label>
          <input
            style={inputStyle}
            value={createForm.display_name}
            onChange={(e) =>
              setCreateForm({ ...createForm, display_name: e.target.value })
            }
            placeholder="Иванов Иван"
          />
          <label style={labelStyle}>ID организации рекламодателя</label>
          <input
            style={inputStyle}
            value={createForm.advertiser_organization_id}
            onChange={(e) =>
              setCreateForm({
                ...createForm,
                advertiser_organization_id: e.target.value,
              })
            }
            placeholder="UUID организации"
          />
          <label style={{ ...labelStyle, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={createForm.auto_generate_password}
              onChange={(e) =>
                setCreateForm({
                  ...createForm,
                  auto_generate_password: e.target.checked,
                })
              }
            />
            Авто-генерация пароля (16 символов)
          </label>
          {!createForm.auto_generate_password && (
            <>
              <label style={labelStyle}>Временный пароль</label>
              <input
                style={inputStyle}
                type="text"
                value={createForm.temporary_password}
                onChange={(e) =>
                  setCreateForm({
                    ...createForm,
                    temporary_password: e.target.value,
                  })
                }
                placeholder="мин. 8 символов"
              />
            </>
          )}
          <label style={{ ...labelStyle, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={createForm.must_change_password}
              onChange={(e) =>
                setCreateForm({
                  ...createForm,
                  must_change_password: e.target.checked,
                })
              }
            />
            Требовать смену пароля при первом входе
          </label>
          <button
            type="button"
            onClick={handleCreate}
            style={{ ...btnStyle, marginTop: "0.5rem", padding: "0.375rem 1rem" }}
          >
            Создать
          </button>
          {createResult && (
            <div
              style={{
                marginTop: "0.75rem",
                padding: "0.5rem",
                background: createResult.one_time_password
                  ? "#fef3c7"
                  : "#fee2e2",
                borderRadius: 4,
                fontSize: "0.8rem",
              }}
            >
              {createResult.one_time_password ? (
                <>
                  <strong>⚠️ Одноразовый пароль (показан только сейчас):</strong>
                  <br />
                  <code>{createResult.one_time_password}</code>
                  <br />
                  {createResult.message}
                </>
              ) : (
                createResult.message
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Reset password modal ── */}
      {resetOpen && (
        <div
          style={{
            background: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: 8,
            padding: "1rem",
            marginBottom: "1rem",
            maxWidth: 420,
          }}
        >
          <h3>Сброс пароля</h3>
          <label style={{ ...labelStyle, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={resetForm.auto_generate_password}
              onChange={(e) =>
                setResetForm({
                  ...resetForm,
                  auto_generate_password: e.target.checked,
                })
              }
            />
            Авто-генерация пароля (16 символов)
          </label>
          {!resetForm.auto_generate_password && (
            <>
              <label style={labelStyle}>Новый временный пароль</label>
              <input
                style={inputStyle}
                type="text"
                value={resetForm.new_temporary_password}
                onChange={(e) =>
                  setResetForm({
                    ...resetForm,
                    new_temporary_password: e.target.value,
                  })
                }
                placeholder="мин. 8 символов"
              />
            </>
          )}
          <label style={{ ...labelStyle, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={resetForm.revoke_sessions}
              onChange={(e) =>
                setResetForm({
                  ...resetForm,
                  revoke_sessions: e.target.checked,
                })
              }
            />
            Отозвать все активные сессии
          </label>
          <div style={{ marginTop: "0.5rem" }}>
            <button
              type="button"
              onClick={handleReset}
              style={{ ...btnStyle, padding: "0.375rem 1rem" }}
            >
              Сбросить пароль
            </button>
            <button
              type="button"
              onClick={() => setResetOpen(false)}
              style={{ ...btnStyle, marginLeft: "0.5rem" }}
            >
              Отмена
            </button>
          </div>
          {resetResult && (
            <div
              style={{
                marginTop: "0.75rem",
                padding: "0.5rem",
                background: resetResult.one_time_password
                  ? "#fef3c7"
                  : "#fee2e2",
                borderRadius: 4,
                fontSize: "0.8rem",
              }}
            >
              {resetResult.one_time_password ? (
                <>
                  <strong>⚠️ Одноразовый пароль (показан только сейчас):</strong>
                  <br />
                  <code>{resetResult.one_time_password}</code>
                  <br />
                  {resetResult.message}
                </>
              ) : (
                resetResult.message
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Users table ── */}
      <table style={tableStyle}>
        <thead>
          <tr>
            <th style={thStyle}>Пользователь</th>
            <th style={thStyle}>Провайдер</th>
            <th style={thStyle}>Статус</th>
            <th style={thStyle}>Действия</th>
          </tr>
        </thead>
        <tbody>
          {state.users.map((u) => (
            <tr key={u.id}>
              <td style={tdStyle}>
                <strong>{u.display_name}</strong>
                <br />
                <span style={{ color: "#94a3b8", fontSize: "0.8rem" }}>
                  {u.username}
                </span>
              </td>
              <td style={tdStyle}>{providerLabel(u.auth_provider)}</td>
              <td style={tdStyle}>{statusBadge(u.status)}</td>
              <td style={tdStyle}>
                {u.status === "active" ? (
                  <button
                    type="button"
                    style={dangerBtn}
                    onClick={() => handleDeactivate(u.id)}
                  >
                    Деактивировать
                  </button>
                ) : (
                  <button
                    type="button"
                    style={btnStyle}
                    onClick={() => handleActivate(u.id)}
                  >
                    Активировать
                  </button>
                )}
                {u.auth_provider.startsWith("local_") && (
                  <button
                    type="button"
                    style={btnStyle}
                    onClick={() => openReset(u.id)}
                  >
                    Сбросить пароль
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {state.users.length === 0 && !state.loading && (
        <p style={{ color: "#94a3b8", marginTop: "1rem" }}>
          Нет пользователей.
        </p>
      )}
    </div>
  );
}
