import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, ApiError, getToken, IDENTITY_BASE_URL } from "../api/client";
import type {
  CampaignOut,
  CampaignFlightOut,
  CampaignPlacementOut,
  CampaignCreativeOut,
  CreativeAssetOut,
  CampaignApprovalOut,
  CampaignStatusHistoryOut,
  CampaignPopSummaryOut,
  CampaignPopByDayOut,
  CampaignPopBySurfaceOut,
} from "../api/types";
import { statusLabel, statusColor, surfaceLabel, mediaTypeLabel, timezoneLabel } from "../api/types";
import { useAuth } from "../auth/AuthContext";

// ── Helpers ──

const APPROVAL_LABELS: Record<string, string> = {
  pending: "На рассмотрении",
  approved: "Согласовано",
  rejected: "Отклонено",
};

function approvalLabel(d: string | null): string {
  return d && APPROVAL_LABELS[d] ? APPROVAL_LABELS[d] : d ?? "—";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function budgetLabel(amount: number | null, currency: string): string {
  if (amount == null) return "—";
  return `${amount.toLocaleString("ru-RU")} ${currency}`;
}

// ── Component ──

export default function CampaignDetailPage() {
  const { id: campaignId } = useParams<{ id: string }>();
  const { logout } = useAuth();
  const navigate = useNavigate();

  const [campaign, setCampaign] = useState<CampaignOut | null>(null);
  const [editing, setEditing] = useState(false);
  const [flights, setFlights] = useState<CampaignFlightOut[]>([]);
  const [placements, setPlacements] = useState<CampaignPlacementOut[]>([]);
  const [ccLinks, setCcLinks] = useState<CampaignCreativeOut[]>([]);
  const [creativeAssets, setCreativeAssets] = useState<CreativeAssetOut[]>([]);
  const [approvals, setApprovals] = useState<CampaignApprovalOut[]>([]);
  const [statusHistory, setStatusHistory] = useState<CampaignStatusHistoryOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [showAttachModal, setShowAttachModal] = useState(false);
  const [attachingAssetId, setAttachingAssetId] = useState<string | null>(null);
  const [attachError, setAttachError] = useState("");
  const [submittingApproval, setSubmittingApproval] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [camps, flts, plcs, ccs, assets, apprs, hist] = await Promise.all([
          api.get<{items: CampaignOut[], total: number, limit: number, offset: number}>("/campaigns"),
          api.get<CampaignFlightOut[]>("/campaign-flights"),
          api.get<CampaignPlacementOut[]>("/campaign-placements"),
          api.get<CampaignCreativeOut[]>("/campaign-creatives"),
          api.get<CreativeAssetOut[]>("/creative-assets"),
          api.get<CampaignApprovalOut[]>("/campaign-approvals"),
          api.get<CampaignStatusHistoryOut[]>("/campaign-status-history"),
        ]);
        if (cancelled) return;

        const found = camps.items.find((c) => c.id === campaignId);
        if (!found) {
          setNotFound(true);
          setLoading(false);
          return;
        }
        setCampaign(found);
        setFlights(flts.filter((f) => f.campaign_id === campaignId));
        setPlacements(plcs.filter((p) => p.campaign_id === campaignId));
        setCcLinks(ccs.filter((cc) => cc.campaign_id === campaignId));
        setCreativeAssets(assets);
        setApprovals(apprs.filter((a) => a.campaign_id === campaignId));
        setStatusHistory(hist.filter((h) => h.campaign_id === campaignId));
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          logout();
          return;
        }
        if (e instanceof ApiError && (e.status === 403 || e.status === 404)) {
          setNotFound(true);
          setLoading(false);
          return;
        }
        setError(e instanceof Error ? e.message : "Ошибка загрузки");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [campaignId, logout]);

  // ── Attach creative handler ──
  async function handleAttachCreative(assetId: string) {
    setAttachingAssetId(assetId);
    setAttachError("");
    try {
      await api.post(`/campaigns/${campaignId}/creatives/attach`, {
        creative_asset_id: assetId,
        sort_order: ccLinks.length,
      });
      // Refresh creatives list
      const freshLinks = await api.get<CampaignCreativeOut[]>(
        `/campaign-creatives?campaign_id=${campaignId}`,
      );
      setCcLinks(Array.isArray(freshLinks) ? freshLinks.filter((cc: CampaignCreativeOut) => cc.campaign_id === campaignId) : []);
      setShowAttachModal(false);
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        if (e.status === 409) setAttachError("Креатив уже привязан или кампания не в черновике");
        else if (e.status === 422) setAttachError("Некорректные данные. Проверьте статус креатива.");
        else if (e.status === 403) setAttachError("Нет прав на привязку креатива");
        else setAttachError(e.message);
      } else {
        setAttachError("Неизвестная ошибка");
      }
    } finally {
      setAttachingAssetId(null);
    }
  }

  // ── Submit approval handler ──
  async function handleSubmitApproval() {
    setSubmittingApproval(true);
    setSubmitError("");
    try {
      const result = await api.post<{ message: string; campaign_id: string; old_status: string; new_status: string }>(
        `/campaigns/${campaignId}/request-approval`,
      );
      setCampaign((prev) => prev ? { ...prev, status: result.new_status } : prev);
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        if (e.status === 422) setSubmitError("Кампания не готова к отправке. Проверьте флайты, размещения и креативы.");
        else if (e.status === 403) setSubmitError("Нет прав на отправку кампании");
        else if (e.status === 409) setSubmitError("Кампания уже не в черновике");
        else setSubmitError(e.message);
      } else {
        setSubmitError("Неизвестная ошибка");
      }
    } finally {
      setSubmittingApproval(false);
    }
  }

  // ── Render states ──

  if (loading) {
    return (
      <div style={styles.centered}>
        <p style={styles.muted}>Загрузка кампании...</p>
      </div>
    );
  }

  if (notFound || error) {
    return (
      <div style={styles.centered}>
        <div style={styles.inaccessibleBox}>
          <h3 style={{ margin: "0 0 0.5rem", fontSize: "1rem" }}>
            Кампания не найдена или недоступна
          </h3>
          <p style={{ margin: 0, fontSize: "0.85rem", color: "#64748b" }}>
            Возможно, у вас нет прав на просмотр этой кампании.
          </p>
          <button
            type="button"
            onClick={() => navigate("/campaigns", { replace: true })}
            style={styles.backBtn}
          >
            ← К списку кампаний
          </button>
        </div>
      </div>
    );
  }

  if (!campaign) {
    return null;
  }

  // ── Derived data ──

  const assetById = new Map(creativeAssets.map((a) => [a.id, a]));

  return (
    <div>
      {/* ── Back ── */}
      <button
        type="button"
        onClick={() => navigate("/campaigns")}
        style={styles.backLink}
      >
        ← К списку кампаний
      </button>

      {/* ── Header ── */}
      <div style={styles.header}>
        <div>
          <h2 style={{ margin: "0 0 0.25rem", fontSize: "1.25rem" }}>
            {campaign.name}
          </h2>
          <span style={{ fontSize: "0.8rem", color: "#64748b" }}>
            {campaign.code}
          </span>
        </div>
        <span
          style={{
            ...styles.badge,
            background: statusColor(campaign.status),
          }}
        >
          {statusLabel(campaign.status)}
        </span>
        {campaign.status === "draft" && !editing && (
          <button
            type="button"
            onClick={() => setEditing(true)}
            style={{
              padding: "0.35rem 0.75rem",
              background: "#fff",
              color: "#1e293b",
              border: "1px solid #cbd5e1",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: "0.8rem",
            }}
          >
            Редактировать
          </button>
        )}
      </div>

      {/* ── Readiness panel + submit (draft only) ── */}
      {campaign.status === "draft" && !editing && (
        <ReadinessPanel
          flightsCount={flights.length}
          placementsCount={placements.length}
          attachedCreativesCount={ccLinks.length}
          attachedReadyCount={ccLinks.filter(
            (cc) => assetById.get(cc.creative_asset_id)?.status === "ready",
          ).length}
          onSubmit={handleSubmitApproval}
          submitting={submittingApproval}
          error={submitError}
        />
      )}

      {/* ── Non-draft status message ── */}
      {campaign.status !== "draft" && campaign.status !== "archived" && (
        <div style={{
          background: "#f0f9ff",
          border: "1px solid #bae6fd",
          borderRadius: 8,
          padding: "0.75rem 1rem",
          marginBottom: "1rem",
          fontSize: "0.85rem",
          color: "#0369a1",
        }}>
          Изменения доступны только в черновике. Кампания на рассмотрении или опубликована.
        </div>
      )}

      {/* ── Edit form (draft only) ── */}
      {editing && (
        <EditCampaignForm
          campaign={campaign}
          onSaved={(updated) => {
            setCampaign(updated);
            setEditing(false);
          }}
          onCancel={() => setEditing(false)}
        />
      )}

      {/* ── Sections ── */}
      <Section title="Обзор">
        <KvList
          items={[
            ["Код", campaign.code],
            ["Название", campaign.name],
            ["Статус", statusLabel(campaign.status)],
            [
              "Период",
              campaign.start_at
                ? `${formatDate(campaign.start_at)} — ${formatDate(campaign.end_at ?? "")}`
                : "—",
            ],
            ["Бюджет", budgetLabel(campaign.budget_limit_amount, campaign.budget_limit_currency)],
            ["Приоритет", String(campaign.priority)],
            ["Часовой пояс", timezoneLabel(campaign.timezone)],
            ...(campaign.description
              ? [["Описание", campaign.description] as [string, string]]
              : []),
          ]}
        />
      </Section>

      <Section title="Периоды / Флайты">
        {flights.length === 0 ? (
          <EmptyState text="Флайты не заданы" />
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Название</th>
                <th style={styles.th}>Начало</th>
                <th style={styles.th}>Окончание</th>
                <th style={styles.th}>Приоритет</th>
              </tr>
            </thead>
            <tbody>
              {flights.map((f) => (
                <tr key={f.id} style={styles.row}>
                  <td style={styles.td}>{f.name || "—"}</td>
                  <td style={styles.td}>{formatDate(f.start_at)}</td>
                  <td style={styles.td}>{formatDate(f.end_at)}</td>
                  <td style={styles.td}>{f.priority}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Размещения">
        {placements.length === 0 ? (
          <EmptyState text="Размещения не заданы" />
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Поверхность</th>
                <th style={styles.th}>Доля показов</th>
                <th style={styles.th}>Показов</th>
                <th style={styles.th}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {placements.map((p) => (
                <tr key={p.id} style={styles.row}>
                  <td style={styles.td}>
                    {surfaceLabel(p.display_surface_id || p.store_id || p.cluster_id || p.branch_id || "") || "—"}
                  </td>
                  <td style={styles.td}>{p.share_of_voice_pct}%</td>
                  <td style={styles.td}>
                    {p.impressions_delivered}
                    {p.max_impressions ? ` / ${p.max_impressions}` : ""}
                  </td>
                  <td style={styles.td}>{statusLabel(p.status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Креативы">
        {ccLinks.length === 0 ? (
          <EmptyState text="Креативы не привязаны" />
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Название</th>
                <th style={styles.th}>Тип</th>
                <th style={styles.th}>Размер</th>
                <th style={styles.th}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {ccLinks.map((cc) => {
                const asset = assetById.get(cc.creative_asset_id);
                return (
                  <tr key={cc.id} style={styles.row}>
                    <td style={styles.td}>
                      {asset?.name ?? cc.creative_asset_id}
                    </td>
                    <td style={styles.td}>{asset?.media_type ? mediaTypeLabel(asset.media_type) : "—"}</td>
                    <td style={styles.td}>
                      {asset
                        ? `${(asset.file_size_bytes / 1024).toFixed(0)} KB`
                        : "—"}
                    </td>
                    <td style={styles.td}>
                      {asset ? (
                        <span
                          style={{
                            ...styles.smallBadge,
                            background:
                              asset.status === "ready"
                                ? "#059669"
                                : asset.status === "metadata_only"
                                  ? "#d97706"
                                  : "#64748b",
                          }}
                        >
                          {statusLabel(asset.status)}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        {campaign.status === "draft" && !editing && (
          <div style={{ marginTop: "0.75rem" }}>
            <button
              type="button"
              onClick={() => { setAttachError(""); setShowAttachModal(true); }}
              style={{
                padding: "0.4rem 0.8rem",
                background: "#1e293b",
                color: "#fff",
                border: "none",
                borderRadius: 6,
                cursor: "pointer",
                fontSize: "0.8rem",
              }}
            >
              + Прикрепить креатив
            </button>
          </div>
        )}
      </Section>

      <Section title="Согласование">
        {approvals.length === 0 && statusHistory.length === 0 ? (
          <EmptyState text="Нет истории согласования" />
        ) : (
          <div>
            {approvals.length > 0 && (
              <div style={{ marginBottom: "1rem" }}>
                <h4 style={styles.subheading}>Заявки на согласование</h4>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Запрошено</th>
                      <th style={styles.th}>Рассмотрено</th>
                      <th style={styles.th}>Решение</th>
                      <th style={styles.th}>Комментарий</th>
                    </tr>
                  </thead>
                  <tbody>
                    {approvals.map((a) => (
                      <tr key={a.id} style={styles.row}>
                        <td style={styles.td}>
                          {formatDateTime(a.requested_at)}
                        </td>
                        <td style={styles.td}>
                          {a.reviewed_at ? formatDateTime(a.reviewed_at) : "—"}
                        </td>
                        <td style={styles.td}>
                          <span
                            style={{
                              ...styles.smallBadge,
                              background:
                                a.decision === "approved"
                                  ? "#059669"
                                  : a.decision === "rejected"
                                    ? "#dc2626"
                                    : "#64748b",
                            }}
                          >
                            {approvalLabel(a.decision)}
                          </span>
                        </td>
                        <td style={styles.td}>
                          {a.rejection_reason || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {statusHistory.length > 0 && (
              <div>
                <h4 style={styles.subheading}>История статусов</h4>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Дата</th>
                      <th style={styles.th}>Старый статус</th>
                      <th style={styles.th}>Новый статус</th>
                      <th style={styles.th}>Причина</th>
                    </tr>
                  </thead>
                  <tbody>
                    {statusHistory.map((h) => (
                      <tr key={h.id} style={styles.row}>
                        <td style={styles.td}>
                          {formatDateTime(h.changed_at)}
                        </td>
                        <td style={styles.td}>
                          {h.old_status ? statusLabel(h.old_status) : "—"}
                        </td>
                        <td style={styles.td}>
                          {statusLabel(h.new_status)}
                        </td>
                        <td style={styles.td}>{h.reason || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </Section>

      {/* ── PoP Reporting (S-023d) ── */}
      <PoPReportingSection campaignId={campaign.id} campaignCode={campaign.code} />

      {/* ── Attach Creative Modal ── */}
      {showAttachModal && (
        <AttachCreativeModal
          assets={creativeAssets}
          alreadyAttachedIds={new Set(ccLinks.map((cc) => cc.creative_asset_id))}
          onAttach={handleAttachCreative}
          onClose={() => setShowAttachModal(false)}
          attachingId={attachingAssetId}
          error={attachError}
        />
      )}

    </div>
  );
}

// ── Sub-components ──

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>{title}</h3>
      {children}
    </div>
  );
}

function KvList({ items }: { items: [string, string][] }) {
  return (
    <div style={styles.kvGrid}>
      {items.map(([k, v]) => (
        <div key={k} style={styles.kvRow}>
          <span style={styles.kvKey}>{k}</span>
          <span style={styles.kvValue}>{v}</span>
        </div>
      ))}
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div style={styles.emptyBox}>
      <p style={{ margin: 0, color: "#94a3b8", fontSize: "0.875rem" }}>
        {text}
      </p>
    </div>
  );
}

// ── PoP Reporting Section ──

function fmtDuration(ms: number): string {
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec} сек`;
  const min = Math.floor(sec / 60);
  const secRem = sec % 60;
  if (min < 60) return `${min} мин ${secRem} сек`;
  const hrs = Math.floor(min / 60);
  const minRem = min % 60;
  return `${hrs} ч ${minRem} мин`;
}

function fmtPopDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric", month: "short",
  });
}

function PoPReportingSection({ campaignId, campaignCode }: { campaignId: string; campaignCode: string }) {
  const [summary, setSummary] = useState<CampaignPopSummaryOut | null>(null);
  const [byDay, setByDay] = useState<CampaignPopByDayOut[]>([]);
  const [bySurface, setBySurface] = useState<CampaignPopBySurfaceOut[]>([]);
  const [popLoading, setPopLoading] = useState(true);
  const [popError, setPopError] = useState<string | null>(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [sum, day, surf] = await Promise.all([
          api.get<CampaignPopSummaryOut>(`/campaigns/${campaignId}/pop/summary`),
          api.get<CampaignPopByDayOut[]>(`/campaigns/${campaignId}/pop/by-day`),
          api.get<CampaignPopBySurfaceOut[]>(`/campaigns/${campaignId}/pop/by-surface`),
        ]);
        if (cancelled) return;
        setSummary(sum);
        setByDay(day);
        setBySurface(surf);
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof ApiError && (e.status === 403 || e.status === 404)) {
          setPopError("Нет доступа к отчётности");
          return;
        }
        setPopError(e instanceof Error ? e.message : "Ошибка загрузки отчётности");
      } finally {
        if (!cancelled) setPopLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [campaignId]);

  const handleExportCsv = async () => {
    setExportLoading(true);
    setExportError(null);
    try {
      const token = getToken();
      const resp = await fetch(
        `${IDENTITY_BASE_URL}/campaigns/${campaignId}/pop/export`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} },
      );
      if (!resp.ok) {
        if (resp.status === 403) throw new ApiError(403, { detail: "Нет прав на экспорт отчёта" });
        if (resp.status === 404) throw new ApiError(404, { detail: "Кампания не найдена" });
        throw new ApiError(resp.status, { detail: `Ошибка экспорта (${resp.status})` });
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${campaignCode}_pop_report.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 403) setExportError("Нет прав на экспорт отчёта");
      else if (e instanceof ApiError && e.status === 404) setExportError("Кампания не найдена");
      else setExportError(e instanceof Error ? e.message : "Ошибка экспорта");
    } finally {
      setExportLoading(false);
    }
  };

  if (popLoading) {
    return (
      <Section title="Отчётность">
        <p style={{ color: "#64748b", fontSize: "0.85rem" }}>
          Загрузка отчётности...
        </p>
      </Section>
    );
  }

  if (popError) {
    return (
      <Section title="Отчётность">
        <div style={styles.emptyBox}>
          <p style={{ margin: 0, color: "#94a3b8", fontSize: "0.875rem" }}>
            {popError}
          </p>
        </div>
      </Section>
    );
  }

  const isEmpty =
    (!summary || summary.impressions_count === 0) &&
    byDay.length === 0 &&
    bySurface.length === 0;

  if (isEmpty) {
    return (
      <Section title="Отчётность">
        <EmptyState text="Пока нет подтверждённых показов" />
      </Section>
    );
  }

  return (
    <Section title="Отчётность">
      <p style={{
        margin: "0 0 0.75rem", fontSize: "0.8rem", color: "#64748b",
        lineHeight: 1.4,
      }}>
        Подтверждённые показы (PoP) — фактические воспроизведения,
        зафиксированные устройствами. Не является отчётом по продажам
        или атрибуции.
      </p>

      {/* Summary cards */}
      {summary && (
        <div style={styles.popCards}>
          <PopCard label="Показов" value={summary.impressions_count.toLocaleString("ru-RU")} />
          <PopCard label="Время" value={fmtDuration(summary.total_duration_ms)} />
          <PopCard label="Устройств" value={String(summary.unique_devices)} />
          <PopCard label="Поверхностей" value={String(summary.unique_surfaces)} />
        </div>
      )}

      {/* By-day table */}
      {byDay.length > 0 && (
        <div style={{ marginBottom: "1rem" }}>
          <h4 style={styles.subheading}>По дням</h4>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Дата</th>
                <th style={styles.th}>Показов</th>
                <th style={styles.th}>Длительность</th>
              </tr>
            </thead>
            <tbody>
              {byDay.map((d, i) => (
                <tr key={d.date || i} style={styles.row}>
                  <td style={styles.td}>{fmtPopDate(d.date)}</td>
                  <td style={styles.td}>{d.impressions_count.toLocaleString("ru-RU")}</td>
                  <td style={styles.td}>{fmtDuration(d.total_duration_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* By-surface table */}
      {bySurface.length > 0 && (
        <div>
          <h4 style={styles.subheading}>По поверхностям</h4>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Поверхность</th>
                <th style={styles.th}>Показов</th>
                <th style={styles.th}>Длительность</th>
              </tr>
            </thead>
            <tbody>
              {bySurface.map((s, i) => (
                <tr key={s.surface_id || i} style={styles.row}>
                  <td style={styles.td}>{s.surface_id}</td>
                  <td style={styles.td}>{s.impressions_count.toLocaleString("ru-RU")}</td>
                  <td style={styles.td}>{fmtDuration(s.total_duration_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Export button */}
      <div style={{ marginTop: "1rem", borderTop: "1px solid #f1f5f9", paddingTop: "0.75rem", display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={handleExportCsv}
          disabled={exportLoading}
          style={{
            padding: "0.3rem 0.7rem",
            fontSize: "0.8rem",
            border: "1px solid #2563eb",
            borderRadius: 4,
            background: "#2563eb",
            color: "#fff",
            cursor: exportLoading ? "not-allowed" : "pointer",
            opacity: exportLoading ? 0.6 : 1,
          }}
        >
          {exportLoading ? "Экспорт..." : "Скачать CSV"}
        </button>
        <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>XLSX — в разработке</span>
        {exportError && (
          <span style={{ fontSize: "0.75rem", color: "#dc2626" }}>{exportError}</span>
        )}
      </div>
    </Section>
  );
}

function PopCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={styles.popCard}>
      <div style={styles.popCardValue}>{value}</div>
      <div style={styles.popCardLabel}>{label}</div>
    </div>
  );
}

// ── Styles ──

const styles: Record<string, React.CSSProperties> = {
  centered: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 200,
  },
  muted: { color: "#64748b", fontSize: "0.875rem" },
  inaccessibleBox: {
    background: "#f8fafc",
    border: "1px dashed #cbd5e1",
    borderRadius: 6,
    padding: "2rem",
    maxWidth: 480,
    textAlign: "center" as const,
  },
  backBtn: {
    marginTop: "1rem",
    padding: "0.4rem 0.8rem",
    background: "#f1f5f9",
    border: "1px solid #e2e8f0",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: "0.85rem",
    color: "#475569",
  },
  backLink: {
    background: "none",
    border: "none",
    color: "#2563eb",
    cursor: "pointer",
    fontSize: "0.85rem",
    padding: 0,
    marginBottom: "0.75rem",
    textDecoration: "underline",
    textUnderlineOffset: 2,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: "1.5rem",
  },
  badge: {
    display: "inline-block",
    padding: "0.2rem 0.6rem",
    borderRadius: 999,
    fontSize: "0.8rem",
    fontWeight: 500,
    color: "#fff",
    lineHeight: "1.4",
  },
  section: {
    marginBottom: "1.5rem",
  },
  sectionTitle: {
    margin: "0 0 0.75rem",
    fontSize: "1rem",
    fontWeight: 600,
    color: "#1e293b",
  },
  subheading: {
    margin: "0 0 0.5rem",
    fontSize: "0.85rem",
    fontWeight: 600,
    color: "#475569",
  },
  kvGrid: {
    display: "grid",
    gridTemplateColumns: "180px 1fr",
    gap: "0.4rem 0",
    fontSize: "0.875rem",
  },
  kvRow: {
    display: "contents" as "contents",
  },
  kvKey: {
    color: "#64748b",
    fontWeight: 500,
    padding: "0.25rem 0",
  },
  kvValue: {
    padding: "0.25rem 0",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse" as const,
    fontSize: "0.85rem",
    background: "#fff",
    borderRadius: 6,
    overflow: "hidden",
    boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
  },
  th: {
    textAlign: "left" as const,
    padding: "0.5rem 0.75rem",
    fontWeight: 600,
    color: "#475569",
    borderBottom: "1px solid #e2e8f0",
    fontSize: "0.75rem",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
  },
  td: {
    padding: "0.5rem 0.75rem",
    borderBottom: "1px solid #f1f5f9",
    verticalAlign: "middle" as const,
  },
  row: { transition: "background 0.1s" },
  smallBadge: {
    display: "inline-block",
    padding: "0.1rem 0.4rem",
    borderRadius: 999,
    fontSize: "0.7rem",
    fontWeight: 500,
    color: "#fff",
    lineHeight: "1.4",
  },
  emptyBox: {
    background: "#f8fafc",
    border: "1px dashed #cbd5e1",
    borderRadius: 6,
    padding: "1.5rem",
    textAlign: "center" as const,
  },
  popCards: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: "0.75rem",
    marginBottom: "1.25rem",
  },
  popCard: {
    background: "#f0f9ff",
    border: "1px solid #bae6fd",
    borderRadius: 6,
    padding: "0.75rem",
    textAlign: "center" as const,
  },
  popCardValue: {
    fontSize: "1.25rem",
    fontWeight: 700,
    color: "#0369a1",
  },
  popCardLabel: {
    fontSize: "0.7rem",
    color: "#64748b",
    marginTop: "0.25rem",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
  },
};

// ═══════════════════════════════════════════════
// Internal: EditCampaignForm (draft-only edit)
// ═══════════════════════════════════════════════

function EditCampaignForm({
  campaign,
  onSaved,
  onCancel,
}: {
  campaign: CampaignOut;
  onSaved: (updated: CampaignOut) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(campaign.name);
  const [code, setCode] = useState(campaign.code);
  const [description, setDescription] = useState(campaign.description ?? "");
  const [startAt, setStartAt] = useState(
    campaign.start_at ? campaign.start_at.slice(0, 16) : "",
  );
  const [endAt, setEndAt] = useState(
    campaign.end_at ? campaign.end_at.slice(0, 16) : "",
  );
  const [timezone, setTimezone] = useState(campaign.timezone);
  const [budgetStr, setBudgetStr] = useState(
    campaign.budget_limit_amount != null ? String(campaign.budget_limit_amount) : "",
  );
  const [budgetCurrency, setBudgetCurrency] = useState(campaign.budget_limit_currency);
  const [priority, setPriority] = useState(String(campaign.priority));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");

    const body: Record<string, unknown> = {};
    if (name !== campaign.name) body.name = name;
    if (code !== campaign.code) body.code = code;
    const desc = description || null;
    const origDesc = campaign.description;
    if (desc !== origDesc) body.description = desc;
    const st = startAt ? new Date(startAt).toISOString() : null;
    const origStart = campaign.start_at;
    if (st !== origStart) body.start_at = st;
    const et = endAt ? new Date(endAt).toISOString() : null;
    const origEnd = campaign.end_at;
    if (et !== origEnd) body.end_at = et;
    if (timezone !== campaign.timezone) body.timezone = timezone;
    const ba = budgetStr ? parseFloat(budgetStr) : null;
    if (ba !== campaign.budget_limit_amount) body.budget_limit_amount = ba;
    if (budgetCurrency !== campaign.budget_limit_currency)
      body.budget_limit_currency = budgetCurrency;
    const pr = parseInt(priority, 10) || 0;
    if (pr !== campaign.priority) body.priority = pr;

    if (Object.keys(body).length === 0) {
      onCancel();
      return;
    }

    try {
      const updated = await api.patch<CampaignOut>(
        `/campaigns/${campaign.id}`,
        body,
      );
      onSaved(updated);
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        if (e.status === 409)
          setError("Кампания не в черновике или не найдена");
        else if (e.status === 403)
          setError("Нет прав на редактирование");
        else setError(e.message || "Ошибка сохранения");
      } else {
        setError("Неизвестная ошибка");
      }
    } finally {
      setSaving(false);
    }
  }

  const ef: React.CSSProperties = {
    width: "100%",
    padding: "0.4rem",
    border: "1px solid #cbd5e1",
    borderRadius: 6,
    fontSize: "0.85rem",
    boxSizing: "border-box",
  };

  return (
    <div
      style={{
        background: "#fefce8",
        border: "1px solid #fde047",
        borderRadius: 8,
        padding: "1rem",
        marginBottom: "1rem",
      }}
    >
      <h3 style={{ fontSize: "0.95rem", fontWeight: 600, margin: "0 0 0.75rem" }}>
        Редактирование черновика
      </h3>
      <form onSubmit={handleSave}>
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.5rem" }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: "0.75rem", color: "#475569" }}>Название</label>
            <input style={ef} value={name} onChange={(e) => setName(e.target.value)} maxLength={255} />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: "0.75rem", color: "#475569" }}>Код</label>
            <input style={ef} value={code} onChange={(e) => setCode(e.target.value)} maxLength={64} />
          </div>
        </div>
        <div style={{ marginBottom: "0.5rem" }}>
          <label style={{ fontSize: "0.75rem", color: "#475569" }}>Описание</label>
          <textarea
            style={{ ...ef, minHeight: 50, resize: "vertical" }}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
          />
        </div>
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.5rem" }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: "0.75rem", color: "#475569" }}>Начало</label>
            <input style={ef} type="datetime-local" value={startAt} onChange={(e) => setStartAt(e.target.value)} />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: "0.75rem", color: "#475569" }}>Окончание</label>
            <input style={ef} type="datetime-local" value={endAt} onChange={(e) => setEndAt(e.target.value)} />
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.5rem" }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: "0.75rem", color: "#475569" }}>Бюджет</label>
            <input style={ef} type="number" min="0" step="0.01" value={budgetStr} onChange={(e) => setBudgetStr(e.target.value)} />
          </div>
          <div style={{ width: 80 }}>
            <label style={{ fontSize: "0.75rem", color: "#475569" }}>Вал.</label>
            <select style={ef} value={budgetCurrency} onChange={(e) => setBudgetCurrency(e.target.value)}>
              <option value="RUB">RUB</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: "0.75rem", color: "#475569" }}>Приоритет</label>
            <input style={ef} type="number" min="0" value={priority} onChange={(e) => setPriority(e.target.value)} />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: "0.75rem", color: "#475569" }}>Часовой пояс</label>
            <input style={ef} value={timezone} onChange={(e) => setTimezone(e.target.value)} />
          </div>
        </div>
        {error && <div style={{ color: "#dc2626", fontSize: "0.8rem", marginBottom: "0.5rem" }}>{error}</div>}
        <button type="submit" style={{ padding: "0.4rem 1rem", background: "#1e293b", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: "0.85rem" }} disabled={saving}>
          {saving ? "Сохранение..." : "Сохранить"}
        </button>
        <button type="button" onClick={onCancel} style={{ padding: "0.4rem 1rem", background: "transparent", color: "#475569", border: "1px solid #cbd5e1", borderRadius: 6, cursor: "pointer", fontSize: "0.85rem", marginLeft: "0.5rem" }}>
          Отмена
        </button>
      </form>
    </div>
  );
}

// ═══════════════════════════════════════════════
// Internal: ReadinessPanel (draft submit approval readiness)
// ═══════════════════════════════════════════════

function ReadinessPanel({
  flightsCount,
  placementsCount,
  attachedCreativesCount,
  attachedReadyCount,
  onSubmit,
  submitting,
  error,
}: {
  flightsCount: number;
  placementsCount: number;
  attachedCreativesCount: number;
  attachedReadyCount: number;
  onSubmit: () => void;
  submitting: boolean;
  error: string;
}) {
  const readyChecks = [
    { label: "Минимум один флайт", ok: flightsCount > 0 },
    { label: "Минимум одно размещение", ok: placementsCount > 0 },
    { label: "Минимум один привязанный креатив", ok: attachedCreativesCount > 0 },
    { label: "Все креативы загружены (ready)", ok: attachedCreativesCount > 0 && attachedReadyCount === attachedCreativesCount },
  ];
  const allReady = readyChecks.every((r) => r.ok);

  return (
    <div
      style={{
        background: allReady ? "#f0fdf4" : "#fffbeb",
        border: `1px solid ${allReady ? "#bbf7d0" : "#fde047"}`,
        borderRadius: 8,
        padding: "1rem",
        marginBottom: "1rem",
      }}
    >
      <h4 style={{ fontSize: "0.85rem", fontWeight: 600, margin: "0 0 0.5rem", color: "#1e293b" }}>
        Готовность к отправке
      </h4>
      <ul style={{ margin: "0 0 0.75rem", paddingLeft: "1.25rem", fontSize: "0.8rem", color: "#475569", listStyle: "none" }}>
        {readyChecks.map((r) => (
          <li key={r.label} style={{ marginBottom: "0.2rem" }}>
            <span style={{ marginRight: "0.4rem" }}>{r.ok ? "✅" : "❌"}</span>
            {r.label}
          </li>
        ))}
      </ul>
      {error && (
        <div style={{ color: "#dc2626", fontSize: "0.8rem", marginBottom: "0.5rem" }}>
          {error}
        </div>
      )}
      <button
        type="button"
        onClick={onSubmit}
        disabled={!allReady || submitting}
        style={{
          padding: "0.45rem 1rem",
          background: allReady ? "#059669" : "#94a3b8",
          color: "#fff",
          border: "none",
          borderRadius: 6,
          cursor: allReady ? "pointer" : "not-allowed",
          fontSize: "0.85rem",
          fontWeight: 500,
        }}
      >
        {submitting ? "Отправка..." : allReady ? "Отправить на согласование" : "Заполните все условия"}
      </button>
    </div>
  );
}

// ═══════════════════════════════════════════════
// Internal: AttachCreativeModal
// ═══════════════════════════════════════════════

function AttachCreativeModal({
  assets,
  alreadyAttachedIds,
  onAttach,
  onClose,
  attachingId,
  error,
}: {
  assets: CreativeAssetOut[];
  alreadyAttachedIds: Set<string>;
  onAttach: (assetId: string) => void;
  onClose: () => void;
  attachingId: string | null;
  error: string;
}) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 8,
          padding: "1.5rem",
          maxWidth: 560,
          width: "90%",
          maxHeight: "70vh",
          overflowY: "auto",
          boxShadow: "0 10px 30px rgba(0,0,0,0.15)",
        }}
      >
        <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 1rem" }}>
          Выберите креатив
        </h3>

        {error && (
          <div style={{ color: "#dc2626", fontSize: "0.8rem", marginBottom: "0.75rem", padding: "0.5rem", background: "#fef2f2", borderRadius: 4 }}>
            {error}
          </div>
        )}

        {assets.length === 0 ? (
          <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
            Нет доступных креативов. Загрузите креатив в библиотеке.
          </p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "0.4rem 0.5rem", borderBottom: "1px solid #e2e8f0", color: "#64748b", fontWeight: 600 }}>Название</th>
                <th style={{ textAlign: "left", padding: "0.4rem 0.5rem", borderBottom: "1px solid #e2e8f0", color: "#64748b", fontWeight: 600 }}>Тип</th>
                <th style={{ textAlign: "left", padding: "0.4rem 0.5rem", borderBottom: "1px solid #e2e8f0", color: "#64748b", fontWeight: 600 }}>Статус</th>
                <th style={{ textAlign: "center", padding: "0.4rem 0.5rem", borderBottom: "1px solid #e2e8f0", color: "#64748b", fontWeight: 600 }}></th>
              </tr>
            </thead>
            <tbody>
              {assets.map((asset) => {
                const isAttached = alreadyAttachedIds.has(asset.id);
                const isReady = asset.status === "ready";
                const isMetadata = asset.status === "metadata_only";
                return (
                  <tr key={asset.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "0.4rem 0.5rem" }}>
                      {asset.name}
                      {isAttached && (
                        <span style={{ fontSize: "0.7rem", color: "#64748b", marginLeft: "0.3rem" }}>
                          (уже привязан)
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "0.4rem 0.5rem", color: "#64748b" }}>
                      {mediaTypeLabel(asset.media_type)}
                    </td>
                    <td style={{ padding: "0.4rem 0.5rem" }}>
                      {isReady ? (
                        <span style={{ ...styles.smallBadge, background: "#059669" }}>Готов</span>
                      ) : isMetadata ? (
                        <span style={{ ...styles.smallBadge, background: "#d97706" }}>Ожидает загрузки</span>
                      ) : (
                        <span style={{ ...styles.smallBadge, background: "#64748b" }}>{statusLabel(asset.status)}</span>
                      )}
                    </td>
                    <td style={{ padding: "0.4rem 0.5rem", textAlign: "center" }}>
                      {isAttached ? (
                        <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>✓</span>
                      ) : isMetadata ? (
                        <span style={{ fontSize: "0.75rem", color: "#d97706" }}>
                          Загрузите файл
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => onAttach(asset.id)}
                          disabled={attachingId === asset.id}
                          style={{
                            padding: "0.25rem 0.6rem",
                            background: "#1e293b",
                            color: "#fff",
                            border: "none",
                            borderRadius: 4,
                            cursor: "pointer",
                            fontSize: "0.75rem",
                          }}
                        >
                          {attachingId === asset.id ? "..." : "Прикрепить"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        <div style={{ marginTop: "1rem", textAlign: "right" }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: "0.4rem 0.8rem",
              background: "transparent",
              color: "#475569",
              border: "1px solid #cbd5e1",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: "0.8rem",
            }}
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}
