import { useEffect, useState, useRef, useCallback } from "react";
import { api, ApiError } from "../api/client";
import type { CreativeAssetOut } from "../api/types";
import type {
  CreativeAssetCreateRequest,
  UploadIntentResponse,
  CompleteUploadResponse,
} from "../api/types";
import { statusLabel, MEDIA_TYPE_OPTIONS, mediaTypeLabel } from "../api/types";
import { useAuth } from "../auth/AuthContext";

// ── Helpers ──

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric", month: "short", year: "numeric",
  });
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

// ── Component ──

export default function CreativeLibraryPage() {
  const { logout } = useAuth();
  const [assets, setAssets] = useState<CreativeAssetOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form
  const [showForm, setShowForm] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createCode, setCreateCode] = useState("");
  const [createMediaType, setCreateMediaType] = useState("image/png");
  const [createSaving, setCreateSaving] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Upload state per asset
  const [uploadingId, setUploadingId] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Data loading ──

  const loadAssets = useCallback(async () => {
    try {
      const list = await api.get<CreativeAssetOut[]>("/creative-assets");
      setAssets(list);
      setError(null);
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 401) { logout(); return; }
      if (e instanceof ApiError && e.status === 403) {
        setError("Нет прав на просмотр креативов");
        return;
      }
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      await loadAssets();
      // eslint-disable-next-line
      if (cancelled) return;
    }
    init();
    return () => { cancelled = true; };
  }, [loadAssets]);

  // ── Create asset ──

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateSaving(true);
    setCreateError(null);
    try {
      const body: CreativeAssetCreateRequest = {
        code: createCode || createName.slice(0, 32).replace(/\s+/g, "_"),
        name: createName,
        media_type: createMediaType,
      };
      await api.post<CreativeAssetOut>("/creative-assets", body);
      setCreateName("");
      setCreateCode("");
      setCreateMediaType("image/png");
      setShowForm(false);
      await loadAssets();
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError
          ? (e.body as Record<string, unknown>)?.detail
            ? String((e.body as Record<string, unknown>).detail)
            : e.message
          : e instanceof Error ? e.message : "Ошибка создания";
      setCreateError(msg);
    } finally {
      setCreateSaving(false);
    }
  }

  // ── Upload flow ──

  async function handleUploadClick(assetId: string) {
    fileInputRef.current?.click();
    // Store which asset we're uploading for
    (fileInputRef.current as HTMLInputElement & { _assetId?: string })._assetId = assetId;
  }

  async function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const assetId = (e.target as HTMLInputElement & { _assetId?: string })._assetId;
    if (!assetId) return;

    setUploadingId(assetId);
    setUploadProgress(0);
    setUploadError(null);

    try {
      // Step 1: Get upload intent
      const intent = await api.post<UploadIntentResponse>(
        `/creative-assets/${assetId}/upload-intent`,
        {
          filename: file.name,
          content_type: file.type || "application/octet-stream",
          content_length: file.size,
        },
      );

      // Step 2: PUT file to presigned URL (no Authorization)
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("PUT", intent.upload_url);

        // Set headers from intent response (Content-Type etc.)
        for (const [k, v] of Object.entries(intent.headers)) {
          xhr.setRequestHeader(k, v);
        }
        // Do NOT send Authorization

        xhr.upload.onprogress = (ev) => {
          if (ev.lengthComputable) {
            setUploadProgress(Math.round((ev.loaded / ev.total) * 100));
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) resolve();
          else reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
        };
        xhr.onerror = () => reject(new Error("Сетевая ошибка при загрузке"));
        xhr.send(file);
      });

      // Step 3: Complete upload
      await api.post<CompleteUploadResponse>(
        `/creative-assets/${assetId}/complete-upload`,
        { upload_id: intent.upload_id },
      );

      // Refresh list
      await loadAssets();
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError
          ? (e.body as Record<string, unknown>)?.detail
            ? String((e.body as Record<string, unknown>).detail)
            : e.message
          : e instanceof Error ? e.message : "Ошибка загрузки";
      setUploadError(msg);
    } finally {
      setUploadingId(null);
      setUploadProgress(0);
      // Reset file input
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  // ── Render states ──

  if (loading) {
    return (
      <div style={styles.centered}>
        <p style={styles.muted}>Загрузка креативов...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.centered}>
        <div style={styles.errorBox}>
          <p style={{ margin: 0, fontWeight: 600 }}>Ошибка</p>
          <p style={{ margin: "0.25rem 0 0", fontSize: "0.875rem" }}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={styles.headerRow}>
        <h2 style={styles.heading}>Креативы</h2>
        <button
          type="button"
          onClick={() => setShowForm(!showForm)}
          style={styles.addBtn}
        >
          {showForm ? "Отмена" : "Добавить креатив"}
        </button>
      </div>

      {/* ── Upload error banner ── */}
      {uploadError && (
        <div style={styles.uploadErrorBanner}>
          <span>{uploadError}</span>
          <button type="button" onClick={() => setUploadError(null)}
            style={{ ...styles.smallBtn, marginLeft: "0.5rem" }}>
            ✕
          </button>
        </div>
      )}

      {/* ── Create form ── */}
      {showForm && (
        <form onSubmit={handleCreate} style={styles.form}>
          <div style={styles.formGrid}>
            <label style={styles.label}>
              Название *
              <input
                style={styles.input}
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                required
                placeholder="Новогодний баннер"
              />
            </label>
            <label style={styles.label}>
              Код
              <input
                style={styles.input}
                value={createCode}
                onChange={(e) => setCreateCode(e.target.value)}
                placeholder="Автоматически из названия"
              />
            </label>
            <label style={styles.label}>
              Тип медиа
              <select
                style={styles.select}
                value={createMediaType}
                onChange={(e) => setCreateMediaType(e.target.value)}
              >
                {MEDIA_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </label>
          </div>
          {createError && (
            <div style={styles.createError}>{createError}</div>
          )}
          <button
            type="submit"
            disabled={createSaving || !createName}
            style={{
              ...styles.submitBtn,
              opacity: createSaving || !createName ? 0.6 : 1,
            }}
          >
            {createSaving ? "Создание..." : "Создать"}
          </button>
        </form>
      )}

      {/* ── Upload progress ── */}
      {uploadingId && (
        <div style={styles.progressBar}>
          <div
            style={{
              ...styles.progressFill,
              width: `${uploadProgress}%`,
            }}
          />
          <span style={styles.progressText}>{uploadProgress}%</span>
        </div>
      )}

      {/* ── Table ── */}
      {assets.length === 0 ? (
        <div style={styles.emptyBox}>
          <p style={{ margin: 0, fontWeight: 500 }}>Нет креативов</p>
          <p style={{ margin: "0.25rem 0 0", fontSize: "0.85rem", color: "#94a3b8" }}>
            Нажмите «Добавить креатив», чтобы создать первый.
          </p>
        </div>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Название</th>
              <th style={styles.th}>Тип</th>
              <th style={styles.th}>Размер</th>
              <th style={styles.th}>Статус</th>
              <th style={styles.th}>Модерация</th>
              <th style={styles.th}>Создан</th>
              <th style={styles.th}></th>
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <tr key={a.id} style={styles.row}>
                <td style={styles.td}>
                  <div style={{ fontWeight: 500 }}>{a.name}</div>
                  <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>{a.code}</div>
                </td>
                <td style={styles.td}>{mediaTypeLabel(a.media_type)}</td>
                <td style={styles.td}>
                  {a.file_size_bytes > 0 ? fmtSize(a.file_size_bytes) : "—"}
                </td>
                <td style={styles.td}>
                  <span
                    style={{
                      ...styles.badge,
                      background:
                        a.status === "ready" ? "#059669"
                          : a.status === "metadata_only" ? "#d97706"
                            : "#64748b",
                    }}
                  >
                    {statusLabel(a.status)}
                  </span>
                </td>
                <td style={styles.td}>
                  <span style={{ fontSize: "0.8rem", color: "#64748b" }}>
                    {a.moderation_status === "approved"
                      ? "Одобрен"
                      : a.moderation_status === "pending_review"
                        ? "На проверке"
                        : a.moderation_status}
                  </span>
                </td>
                <td style={{ ...styles.td, fontSize: "0.8rem", color: "#64748b" }}>
                  {fmtDate(a.created_at)}
                </td>
                <td style={styles.td}>
                  {a.status === "metadata_only" && (
                    <button
                      type="button"
                      onClick={() => handleUploadClick(a.id)}
                      disabled={uploadingId === a.id}
                      style={styles.uploadBtn}
                    >
                      Загрузить файл
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* ── Hidden file input ── */}
      <input
        ref={fileInputRef}
        type="file"
        accept={MEDIA_TYPE_OPTIONS.map((o) => o.value).join(",")}
        style={{ display: "none" }}
        onChange={handleFileSelected}
      />
    </div>
  );
}

// ── Styles ──

const styles: Record<string, React.CSSProperties> = {
  centered: {
    display: "flex", alignItems: "center", justifyContent: "center", minHeight: 200,
  },
  muted: { color: "#64748b", fontSize: "0.875rem" },
  errorBox: {
    background: "#fef2f2", color: "#991b1b", padding: "1rem",
    borderRadius: 6, maxWidth: 480,
  },
  headerRow: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    marginBottom: "1rem",
  },
  heading: { margin: 0, fontSize: "1.25rem", fontWeight: 600 },
  addBtn: {
    padding: "0.4rem 0.8rem", background: "#2563eb", color: "#fff",
    border: "none", borderRadius: 4, cursor: "pointer", fontSize: "0.85rem",
  },
  // Form
  form: {
    background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6,
    padding: "1rem", marginBottom: "1rem",
  },
  formGrid: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem" },
  label: { display: "flex", flexDirection: "column" as const, gap: "0.25rem", fontSize: "0.85rem", color: "#475569" },
  input: { padding: "0.4rem 0.5rem", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: "0.85rem" },
  select: { padding: "0.4rem 0.5rem", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: "0.85rem", background: "#fff" },
  createError: {
    marginTop: "0.5rem", color: "#dc2626", fontSize: "0.8rem",
  },
  submitBtn: {
    marginTop: "0.75rem", padding: "0.4rem 1rem", background: "#16a34a", color: "#fff",
    border: "none", borderRadius: 4, cursor: "pointer", fontSize: "0.85rem",
    transition: "opacity 0.2s",
  },
  // Upload
  uploadErrorBanner: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    background: "#fef2f2", color: "#991b1b", padding: "0.5rem 0.75rem",
    borderRadius: 4, marginBottom: "0.75rem", fontSize: "0.85rem",
  },
  smallBtn: {
    background: "none", border: "none", color: "#991b1b", cursor: "pointer",
    fontSize: "1rem", padding: 0, lineHeight: 1,
  },
  progressBar: {
    position: "relative" as const, height: 24, background: "#e2e8f0",
    borderRadius: 4, marginBottom: "0.75rem", overflow: "hidden",
  },
  progressFill: {
    height: "100%", background: "#2563eb", borderRadius: 4,
    transition: "width 0.2s",
  },
  progressText: {
    position: "absolute" as const, top: 2, left: "50%",
    transform: "translateX(-50%)", fontSize: "0.75rem", color: "#1e293b",
    fontWeight: 500,
  },
  // Table
  emptyBox: {
    background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: 6,
    padding: "2rem", textAlign: "center" as const, color: "#64748b",
  },
  table: {
    width: "100%", borderCollapse: "collapse" as const, fontSize: "0.85rem",
    background: "#fff", borderRadius: 6, overflow: "hidden",
    boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
  },
  th: {
    textAlign: "left" as const, padding: "0.5rem 0.75rem", fontWeight: 600,
    color: "#475569", borderBottom: "1px solid #e2e8f0", fontSize: "0.75rem",
    textTransform: "uppercase" as const, letterSpacing: "0.05em",
  },
  td: {
    padding: "0.5rem 0.75rem", borderBottom: "1px solid #f1f5f9",
    verticalAlign: "middle" as const,
  },
  row: { transition: "background 0.1s" },
  badge: {
    display: "inline-block", padding: "0.1rem 0.4rem", borderRadius: 999,
    fontSize: "0.7rem", fontWeight: 500, color: "#fff", lineHeight: "1.4",
  },
  uploadBtn: {
    padding: "0.25rem 0.5rem", background: "#dbeafe", color: "#1e40af",
    border: "1px solid #bfdbfe", borderRadius: 4, cursor: "pointer",
    fontSize: "0.75rem",
  },
};
