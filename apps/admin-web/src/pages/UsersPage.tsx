import { useState, useEffect, useCallback } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type {
  UserOut,
  UserDetailOut,
  PaginatedUsers,
  RoleOut,
  AssignRoleRequest,
  AssignRoleResponse,
} from "../api/types";

interface UsersPageState {
  users: UserOut[];
  total: number;
  loading: boolean;
  error: string | null;
  selectedUser: UserDetailOut | null;
  actionError: string | null;
}

export default function UsersPage() {
  const { user } = useAuth();
  const canCreateAdvertiser =
    user?.permissions?.includes("users.manage") ?? false;
  const canManageRoles =
    user?.permissions?.includes("roles.manage") ?? false;

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

  // Role management
  const [rolesOpen, setRolesOpen] = useState(false);
  const [availableRoles, setAvailableRoles] = useState<RoleOut[]>([]);
  const [selectedRoleCode, setSelectedRoleCode] = useState("");
  const [selectedScopeType, setSelectedScopeType] = useState<string>("");
  const [selectedScopeId, setSelectedScopeId] = useState("");
  const [roleAssignError, setRoleAssignError] = useState<string | null>(null);

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

  // ── Load user detail + roles ──

  async function loadUserDetail(userId: string) {
    setState((s) => ({ ...s, actionError: null }));
    try {
      const detail = await api.get<UserDetailOut>(`/users/${userId}`);
      setState((s) => ({ ...s, selectedUser: detail }));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка загрузки";
      setState((s) => ({ ...s, actionError: msg }));
    }
  }

  // ── Open role management ──

  async function openRoleManagement(userId: string) {
    setRolesOpen(true);
    setRoleAssignError(null);
    setSelectedRoleCode("");
    setSelectedScopeType("");
    setSelectedScopeId("");
    // Load detail if not already loaded for this user
    if (!state.selectedUser || state.selectedUser.id !== userId) {
      await loadUserDetail(userId);
    }
    // Load available roles
    try {
      const roles = await api.get<RoleOut[]>("/roles");
      setAvailableRoles(roles);
    } catch {
      setAvailableRoles([]);
    }
  }

  // ── Assign role ──

  async function handleAssignRole() {
    if (!selectedRoleCode || !state.selectedUser) return;
    setRoleAssignError(null);
    try {
      const body: AssignRoleRequest = {
        role_code: selectedRoleCode,
      };
      if (selectedScopeType && selectedScopeId) {
        body.scope_type = selectedScopeType;
        body.scope_id = selectedScopeId;
      }
      await api.put<AssignRoleResponse>(
        `/users/${state.selectedUser.id}/roles`,
        body,
      );
      // Reload detail to get updated roles
      await loadUserDetail(state.selectedUser.id);
      setSelectedRoleCode("");
      setSelectedScopeType("");
      setSelectedScopeId("");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка назначения роли";
      setRoleAssignError(msg);
    }
  }

  // ── Remove role ──

  async function handleRemoveRole(assignmentId: string) {
    if (!state.selectedUser) return;
    setRoleAssignError(null);
    try {
      await api.del(
        `/users/${state.selectedUser.id}/roles/${assignmentId}`,
      );
      await loadUserDetail(state.selectedUser.id);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка удаления роли";
      setRoleAssignError(msg);
    }
  }

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
      // Don't close on success — user needs to copy one-time password
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
        {canCreateAdvertiser && (
          <button
            type="button"
            data-testid="user-create-advertiser-open"
            onClick={() => {
              setCreateOpen(!createOpen);
              setCreateResult(null);
            }}
            style={{ ...btnStyle, padding: "0.5rem 1rem", fontSize: "0.875rem" }}
          >
            {createOpen ? "Отмена" : "+ Создать рекламодателя"}
          </button>
        )}
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
            data-testid="user-create-advertiser-username"
            style={inputStyle}
            value={createForm.username}
            onChange={(e) =>
              setCreateForm({ ...createForm, username: e.target.value })
            }
            placeholder="advertiser_login"
          />
          <label style={labelStyle}>Отображаемое имя</label>
          <input
            data-testid="user-create-advertiser-display-name"
            style={inputStyle}
            value={createForm.display_name}
            onChange={(e) =>
              setCreateForm({ ...createForm, display_name: e.target.value })
            }
            placeholder="Иванов Иван"
          />
          <label style={labelStyle}>ID организации рекламодателя</label>
          <input
            data-testid="user-create-advertiser-org-id"
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
            data-testid="user-create-advertiser-submit"
            onClick={handleCreate}
            style={{ ...btnStyle, marginTop: "0.5rem", padding: "0.375rem 1rem" }}
          >
            Создать
          </button>
          {createResult && (
            <div
              data-testid="user-create-advertiser-result"
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

      {/* ── Role management panel ── */}
      {rolesOpen && state.selectedUser && (
        <div
          data-testid="user-roles-panel"
          style={{
            background: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: 8,
            padding: "1rem",
            marginBottom: "1rem",
            maxWidth: 520,
          }}
        >
          <h3>
            Управление ролями — {state.selectedUser.display_name}
          </h3>

          {/* Current roles */}
          <div style={{ marginBottom: "0.75rem" }}>
            <strong>Текущие роли:</strong>
            {state.selectedUser.roles.length === 0 && (
              <p style={{ color: "#94a3b8", margin: "0.25rem 0" }}>
                Нет назначенных ролей
              </p>
            )}
            <ul style={{ margin: "0.25rem 0", paddingLeft: "1.25rem" }}>
              {state.selectedUser.roles.map((r) => (
                <li
                  key={r.id}
                  style={{ marginBottom: "0.25rem", fontSize: "0.85rem" }}
                >
                  <strong>{r.role_name}</strong> ({r.role_code})
                  {r.scope_type && (
                    <span style={{ color: "#64748b" }}>
                      {" "}
                      — scope: {r.scope_type}/{r.scope_id?.slice(0, 8)}…
                    </span>
                  )}
                  {canManageRoles && (
                    <button
                      type="button"
                      data-testid="user-roles-remove"
                      onClick={() => handleRemoveRole(r.id)}
                      style={{
                        ...dangerBtn,
                        marginLeft: "0.5rem",
                        fontSize: "0.65rem",
                        padding: "0.1rem 0.3rem",
                      }}
                    >
                      ✕
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>

          {/* Assign new role */}
          {canManageRoles && (
            <div
              style={{
                borderTop: "1px solid #e2e8f0",
                paddingTop: "0.75rem",
              }}
            >
              <strong style={{ fontSize: "0.85rem" }}>
                Назначить роль:
              </strong>
              {roleAssignError && (
                <p style={{ color: "#dc2626", fontSize: "0.8rem", margin: "0.25rem 0" }}>
                  {roleAssignError}
                </p>
              )}
              <div style={{ marginTop: "0.5rem" }}>
                <select
                  data-testid="user-roles-role"
                  value={selectedRoleCode}
                  onChange={(e) => setSelectedRoleCode(e.target.value)}
                  style={{
                    ...inputStyle,
                    width: "auto",
                    minWidth: 180,
                    marginBottom: 0,
                  }}
                >
                  <option value="">— Выберите роль —</option>
                  {availableRoles.map((r) => (
                    <option key={r.id} value={r.code}>
                      {r.name} ({r.code})
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  data-testid="user-roles-save"
                  onClick={handleAssignRole}
                  disabled={!selectedRoleCode}
                  style={{
                    ...btnStyle,
                    padding: "0.3rem 0.75rem",
                    marginLeft: "0.5rem",
                    opacity: selectedRoleCode ? 1 : 0.5,
                  }}
                >
                  Сохранить
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setRolesOpen(false);
                    setState((s) => ({ ...s, selectedUser: null }));
                    setRoleAssignError(null);
                  }}
                  style={{
                    ...btnStyle,
                    padding: "0.3rem 0.75rem",
                    marginLeft: "0.25rem",
                  }}
                >
                  Закрыть
                </button>
              </div>
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
                {canManageRoles && (
                  <button
                    type="button"
                    data-testid="user-roles-open"
                    onClick={() => openRoleManagement(u.id)}
                    style={btnStyle}
                  >
                    Роли
                  </button>
                )}
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
