import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getCampaign,
  getFlightsByCampaign,
  getPlacementsByCampaign,
  getCreativesByCampaign,
  listAdvertisers,
  listBrands,
  listContracts,
  listCreativeAssets,
  getApprovalsByCampaign,
  createFlight,
  updateFlight,
  createPlacement,
  createCreative,
  requestApproval,
} from "../api/campaigns";
import type {
  CampaignOut,
  CampaignFlightOut,
  CampaignFlightCreateRequest,
  CampaignFlightUpdateRequest,
  CampaignPlacementOut,
  CampaignPlacementCreateRequest,
  CampaignCreativeOut,
  CampaignCreativeCreateRequest,
  CreativeAssetOut,
  AdvertiserOrganizationOut,
  AdvertiserBrandOut,
  AdvertiserContractOut,
  CampaignApprovalOut,
} from "../api/types";
import { statusLabel, statusColor } from "../api/types";
import { ApiError } from "../api/client";

// ── Delivered types for use in the component ──

type FlightWithForm = CampaignFlightOut & { _editing?: boolean };
type PlacementWithForm = CampaignPlacementOut & { _editing?: boolean };
type CreativeLink = CampaignCreativeOut & { asset: CreativeAssetOut | null };
type CreativeLinkWithForm = CreativeLink & { _editing?: boolean };

type Tab = "overview" | "flights" | "placements" | "creatives" | "reporting";

interface DetailData {
  campaign: CampaignOut;
  org: AdvertiserOrganizationOut | null;
  brand: AdvertiserBrandOut | null;
  contract: AdvertiserContractOut | null;
  approvals: CampaignApprovalOut[];
}

// ── Date helpers ──

function toISODateOnly(iso: string | null): string {
  if (!iso) return "";
  return iso.slice(0, 10);
}

function toISO(d: string): string {
  return new Date(d).toISOString();
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtAmount(amount: number | null, currency: string): string {
  if (amount == null) return "—";
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

// ── Component ──

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Core data
  const [data, setData] = useState<DetailData | null>(null);
  const [flights, setFlights] = useState<FlightWithForm[]>([]);
  const [placements, setPlacements] = useState<PlacementWithForm[]>([]);
  const [creatives, setCreatives] = useState<CreativeLinkWithForm[]>([]);
  const [allAssets, setAllAssets] = useState<CreativeAssetOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  // Form toggles
  const [showFlightAdd, setShowFlightAdd] = useState(false);
  const [showPlacementAdd, setShowPlacementAdd] = useState(false);
  const [showCreativeAdd, setShowCreativeAdd] = useState(false);

  // Form states
  const [flightName, setFlightName] = useState("");
  const [flightStart, setFlightStart] = useState("");
  const [flightEnd, setFlightEnd] = useState("");
  const [flightPriority, setFlightPriority] = useState("0");
  const [flightSubmitting, setFlightSubmitting] = useState(false);
  const [flightError, setFlightError] = useState<string | null>(null);

  const [placementSurface, setPlacementSurface] = useState("");
  const [placementStore, setPlacementStore] = useState("");
  const [placementCluster, setPlacementCluster] = useState("");
  const [placementBranch, setPlacementBranch] = useState("");
  const [placementSov, setPlacementSov] = useState("100");
  const [placementMaxImp, setPlacementMaxImp] = useState("");
  const [placementSubmitting, setPlacementSubmitting] = useState(false);
  const [placementError, setPlacementError] = useState<string | null>(null);

  const [creativeCode, setCreativeCode] = useState("");
  const [creativeName, setCreativeName] = useState("");
  const [creativeType, setCreativeType] = useState("image/jpeg");
  const [creativeSha, setCreativeSha] = useState("");
  const [creativeSize, setCreativeSize] = useState("");
  const [creativeW, setCreativeW] = useState("");
  const [creativeH, setCreativeH] = useState("");
  const [creativeDur, setCreativeDur] = useState("");
  const [creativeSubmitting, setCreativeSubmitting] = useState(false);
  const [creativeError, setCreativeError] = useState<string | null>(null);

  // Approval
  const [approvalSubmitting, setApprovalSubmitting] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);

  // ── Load all data ──

  const loadData = useCallback(async () => {
    if (!id) return;

    const campaign = await getCampaign(id);
    if (!campaign) {
      setError("Кампания не найдена");
      setLoading(false);
      return null;
    }

    const [
      flts,
      plcs,
      crs,
      assets,
      orgs,
      brands,
      contracts,
      apprs,
    ] = await Promise.all([
      getFlightsByCampaign(campaign.id),
      getPlacementsByCampaign(campaign.id),
      getCreativesByCampaign(campaign.id),
      listCreativeAssets(),
      listAdvertisers(),
      listBrands(),
      listContracts(),
      getApprovalsByCampaign(campaign.id),
    ]);

    const orgMap = new Map(orgs.map((o) => [o.id, o]));
    const brandMap = new Map(brands.map((b) => [b.id, b]));
    const contractMap = new Map(contracts.map((c) => [c.id, c]));

    setData({
      campaign,
      org: orgMap.get(campaign.advertiser_organization_id) ?? null,
      brand: campaign.advertiser_brand_id ? brandMap.get(campaign.advertiser_brand_id) ?? null : null,
      contract: contractMap.get(campaign.advertiser_contract_id) ?? null,
      approvals: apprs,
    });
    setFlights(flts);
    setPlacements(plcs);
    setCreatives(crs.sort((a, b) => a.sort_order - b.sort_order));
    setAllAssets(assets);
    return campaign;
  }, [id]);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const campaign = await loadData();
        if (cancelled) return;
        if (!campaign) return;
      } catch (e: unknown) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Ошибка загрузки");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [loadData]);

  const refreshFlights = async () => {
    if (!data) return;
    const f = await getFlightsByCampaign(data.campaign.id);
    setFlights(f);
  };

  const refreshPlacements = async () => {
    if (!data) return;
    const p = await getPlacementsByCampaign(data.campaign.id);
    setPlacements(p);
  };

  const refreshCreatives = async () => {
    if (!data) return;
    const c = await getCreativesByCampaign(data.campaign.id);
    const a = await listCreativeAssets();
    setCreatives(c.sort((x, y) => x.sort_order - y.sort_order));
    setAllAssets(a);
  };

  const refreshCampaign = async () => {
    if (!id) return;
    const campaign = await getCampaign(id);
    if (campaign && data) {
      setData({ ...data, campaign });
    }
  };

  // ── Render states ──

  if (loading) {
    return <div style={css.centered}><p style={css.muted}>Загрузка...</p></div>;
  }
  if (error) {
    return (
      <div style={css.centered}>
        <div style={css.errorBox}>
          <p style={{ margin: 0, fontWeight: 600 }}>Ошибка</p>
          <p style={{ margin: "0.25rem 0 0.5rem", fontSize: "0.875rem" }}>{error}</p>
          <button type="button" style={css.linkBtn} onClick={() => navigate("/campaigns")}>
            ← К списку кампаний
          </button>
        </div>
      </div>
    );
  }
  if (!data) {
    return (
      <div style={css.centered}>
        <div style={css.errorBox}>
          <p style={{ margin: 0, fontWeight: 600 }}>Кампания не найдена</p>
          <button type="button" style={css.linkBtn} onClick={() => navigate("/campaigns")}>
            ← К списку кампаний
          </button>
        </div>
      </div>
    );
  }

  const { campaign, org, brand, contract, approvals } = data;
  const isDraft = campaign.status === "draft";

  // ── Tab content ──

  function renderOverview() {
    const canApprove = flights.length > 0 && placements.length > 0 && creatives.length > 0;

    async function handleRequestApproval() {
      setApprovalError(null);
      setApprovalSubmitting(true);
      try {
        const res = await requestApproval(campaign.id);
        await Promise.all([refreshCampaign(), loadData()]);
        // Update local status
        if (data) {
          setData({
            ...data,
            campaign: { ...data.campaign, status: res.new_status },
          });
        }
      } catch (e: unknown) {
        if (e instanceof ApiError) {
          setApprovalError(formatApiError(e));
        } else {
          setApprovalError(e instanceof Error ? e.message : "Ошибка");
        }
      } finally {
        setApprovalSubmitting(false);
      }
    }

    return (
      <div style={css.section}>
        {/* Approval action */}
        {isDraft && (
          <div style={{ marginBottom: "1rem", padding: "0.75rem", background: "#f0f9ff", borderRadius: 6, border: "1px solid #bae6fd" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
              <div style={{ flex: 1, fontSize: "0.825rem", color: "#0c4a6e" }}>
                Кампания в черновике.
                {!canApprove && " Добавьте минимум один флайт, плейсмент и креатив для отправки на согласование."}
              </div>
              <button
                type="button"
                style={{
                  ...css.primaryBtn,
                  ...((!canApprove || approvalSubmitting) ? { background: "#9ca3af", cursor: "default" } : {}),
                }}
                disabled={!canApprove || approvalSubmitting}
                onClick={handleRequestApproval}
              >
                {approvalSubmitting ? "Отправка..." : "Отправить на согласование"}
              </button>
            </div>
            {approvalError && (
              <div style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "#dc2626" }}>{approvalError}</div>
            )}
          </div>
        )}

        {!isDraft && (
          <div style={{ marginBottom: "1rem", padding: "0.75rem", background: "#f8fafc", borderRadius: 6, border: "1px solid #e2e8f0", fontSize: "0.825rem", color: "#64748b" }}>
            Изменения доступны только в статусе «Черновик». Текущий статус: {statusLabel(campaign.status)}.
          </div>
        )}

        <div style={css.fieldGrid}>
          <F label="Код" value={campaign.code} />
          <F label="Название" value={campaign.name} />
          <F label="Статус" value={<Badge s={campaign.status} />} />
          <F label="Приоритет" value={String(campaign.priority)} />
          <F label="Бюджет" value={fmtAmount(campaign.budget_limit_amount, campaign.budget_limit_currency)} />
          <F label="Период" value={`${fmtDate(campaign.start_at)} – ${fmtDate(campaign.end_at)}`} />
          <F label="Часовой пояс" value={campaign.timezone} />
          {campaign.description && <FSpan label="Описание" value={campaign.description} />}
        </div>

        <h3 style={css.subheading}>Рекламодатель</h3>
        <div style={css.fieldGrid}>
          <F label="Организация" value={org?.display_name ?? org?.legal_name ?? campaign.advertiser_organization_id} />
          <F label="Бренд" value={brand?.name ?? "—"} />
          <F label="Договор" value={contract?.code ?? campaign.advertiser_contract_id} />
          <F label="Статус договора" value={contract?.status ? statusLabel(contract.status) : "—"} />
        </div>

        <h3 style={css.subheading}>Метаданные</h3>
        <div style={css.fieldGrid}>
          <F label="Создан" value={fmtDateTime(campaign.created_at)} />
          <F label="Обновлён" value={fmtDateTime(campaign.updated_at)} />
        </div>
      </div>
    );
  }

  // ── Flights tab ──

  function renderFlights() {
    async function handleAddFlight(e: FormEvent) {
      e.preventDefault();
      setFlightError(null);

      if (!flightStart || !flightEnd) {
        setFlightError("Даты начала и окончания обязательны");
        return;
      }
      if (flightStart >= flightEnd) {
        setFlightError("Дата начала должна быть раньше даты окончания");
        return;
      }

      setFlightSubmitting(true);
      try {
        const body: CampaignFlightCreateRequest = {
          name: flightName.trim() || null,
          start_at: toISO(flightStart),
          end_at: toISO(flightEnd),
          priority: parseInt(flightPriority, 10) || 0,
        };
        await createFlight(campaign.id, body);
        await refreshFlights();
        resetFlightForm();
      } catch (e: unknown) {
        setFlightError(formatApiError(e));
      } finally {
        setFlightSubmitting(false);
      }
    }

    function resetFlightForm() {
      setFlightName("");
      setFlightStart("");
      setFlightEnd("");
      setFlightPriority("0");
      setShowFlightAdd(false);
    }

    return (
      <div>
        {isDraft && (
          <div style={{ marginBottom: "0.75rem" }}>
            {!showFlightAdd ? (
              <button type="button" style={css.addBtn} onClick={() => setShowFlightAdd(true)}>
                + Добавить флайт
              </button>
            ) : (
              <form onSubmit={handleAddFlight} style={css.inlineForm}>
                <div style={css.inlineFields}>
                  <div>
                    <label htmlFor="f-name" style={css.miniLabel}>Название</label>
                    <input id="f-name" type="text" value={flightName} onChange={(e) => setFlightName(e.target.value)} style={css.miniInput} placeholder="Необязательно" />
                  </div>
                  <div>
                    <label htmlFor="f-start" style={css.miniLabel}>Начало *</label>
                    <input id="f-start" type="date" value={flightStart} onChange={(e) => setFlightStart(e.target.value)} style={css.miniInput} />
                  </div>
                  <div>
                    <label htmlFor="f-end" style={css.miniLabel}>Конец *</label>
                    <input id="f-end" type="date" value={flightEnd} onChange={(e) => setFlightEnd(e.target.value)} style={css.miniInput} />
                  </div>
                  <div>
                    <label htmlFor="f-prio" style={css.miniLabel}>Приоритет</label>
                    <input id="f-prio" type="number" value={flightPriority} onChange={(e) => setFlightPriority(e.target.value)} min={0} max={99} style={{ ...css.miniInput, width: 70 }} />
                  </div>
                  <div style={{ display: "flex", alignItems: "flex-end", gap: "0.25rem" }}>
                    <button type="submit" style={css.primaryBtn} disabled={flightSubmitting}>
                      {flightSubmitting ? "..." : "Добавить"}
                    </button>
                    <button type="button" style={css.cancelBtn} onClick={resetFlightForm}>Отмена</button>
                  </div>
                </div>
                {flightError && <div style={{ color: "#dc2626", fontSize: "0.8rem", marginTop: "0.5rem" }}>{flightError}</div>}
              </form>
            )}
          </div>
        )}

        {flights.length === 0 ? (
          <p style={css.muted}>У этой кампании пока нет флайтов.</p>
        ) : (
          <table style={css.miniTable}>
            <thead>
              <tr>
                <th style={css.miniTh}>Название</th>
                <th style={css.miniTh}>Начало</th>
                <th style={css.miniTh}>Конец</th>
                <th style={css.miniTh}>Приоритет</th>
              </tr>
            </thead>
            <tbody>
              {[...flights].sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime()).map((f) => (
                <tr key={f.id}>
                  <td style={css.miniTd}>{f.name ?? "—"}</td>
                  <td style={css.miniTd}>{fmtDate(f.start_at)}</td>
                  <td style={css.miniTd}>{fmtDate(f.end_at)}</td>
                  <td style={css.miniTd}>{f.priority}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    );
  }

  // ── Placements tab ──

  function renderPlacements() {
    async function handleAddPlacement(e: FormEvent) {
      e.preventDefault();
      setPlacementError(null);

      const surface = placementSurface.trim() || null;
      const store = placementStore.trim() || null;
      const cluster = placementCluster.trim() || null;
      const branch = placementBranch.trim() || null;

      if (!surface && !store && !cluster && !branch) {
        setPlacementError("Укажите хотя бы один идентификатор (surface, магазин, кластер или филиал)");
        return;
      }

      setPlacementSubmitting(true);
      try {
        const body: CampaignPlacementCreateRequest = {
          display_surface_id: surface,
          store_id: store,
          cluster_id: cluster,
          branch_id: branch,
          share_of_voice_pct: parseInt(placementSov, 10) || 100,
          max_impressions: placementMaxImp ? parseInt(placementMaxImp, 10) : null,
        };
        await createPlacement(campaign.id, body);
        await refreshPlacements();
        resetPlacementForm();
      } catch (e: unknown) {
        setPlacementError(formatApiError(e));
      } finally {
        setPlacementSubmitting(false);
      }
    }

    function resetPlacementForm() {
      setPlacementSurface("");
      setPlacementStore("");
      setPlacementCluster("");
      setPlacementBranch("");
      setPlacementSov("100");
      setPlacementMaxImp("");
      setShowPlacementAdd(false);
    }

    return (
      <div>
        <div style={{ marginBottom: "0.75rem", padding: "0.5rem", background: "#fffbeb", borderRadius: 4, border: "1px solid #fde68a", fontSize: "0.75rem", color: "#92400e" }}>
          Справочники поверхностей/магазинов пока не загружены через API. Вводите ID вручную. Поддерживается: display_surface_id, store_id, cluster_id, branch_id.
        </div>

        {isDraft && (
          <div style={{ marginBottom: "0.75rem" }}>
            {!showPlacementAdd ? (
              <button type="button" style={css.addBtn} onClick={() => setShowPlacementAdd(true)}>
                + Добавить плейсмент
              </button>
            ) : (
              <form onSubmit={handleAddPlacement} style={css.inlineForm}>
                <div style={css.inlineFields}>
                  <div>
                    <label style={css.miniLabel}>Surface ID</label>
                    <input type="text" value={placementSurface} onChange={(e) => setPlacementSurface(e.target.value)} style={css.miniInput} placeholder="UUID" />
                  </div>
                  <div>
                    <label style={css.miniLabel}>Store ID</label>
                    <input type="text" value={placementStore} onChange={(e) => setPlacementStore(e.target.value)} style={css.miniInput} placeholder="UUID" />
                  </div>
                  <div>
                    <label style={css.miniLabel}>Cluster ID</label>
                    <input type="text" value={placementCluster} onChange={(e) => setPlacementCluster(e.target.value)} style={css.miniInput} placeholder="UUID" />
                  </div>
                  <div>
                    <label style={css.miniLabel}>Branch ID</label>
                    <input type="text" value={placementBranch} onChange={(e) => setPlacementBranch(e.target.value)} style={css.miniInput} placeholder="UUID" />
                  </div>
                  <div>
                    <label style={css.miniLabel}>SOV %</label>
                    <input type="number" value={placementSov} onChange={(e) => setPlacementSov(e.target.value)} min={0} max={100} style={{ ...css.miniInput, width: 70 }} />
                  </div>
                  <div>
                    <label style={css.miniLabel}>Max показов</label>
                    <input type="number" value={placementMaxImp} onChange={(e) => setPlacementMaxImp(e.target.value)} min={0} style={{ ...css.miniInput, width: 90 }} />
                  </div>
                  <div style={{ display: "flex", alignItems: "flex-end", gap: "0.25rem" }}>
                    <button type="submit" style={css.primaryBtn} disabled={placementSubmitting}>
                      {placementSubmitting ? "..." : "Добавить"}
                    </button>
                    <button type="button" style={css.cancelBtn} onClick={resetPlacementForm}>Отмена</button>
                  </div>
                </div>
                {placementError && <div style={{ color: "#dc2626", fontSize: "0.8rem", marginTop: "0.5rem" }}>{placementError}</div>}
              </form>
            )}
          </div>
        )}

        {placements.length === 0 ? (
          <p style={css.muted}>У этой кампании пока нет плейсментов.</p>
        ) : (
          <table style={css.miniTable}>
            <thead>
              <tr>
                <th style={css.miniTh}>Surface</th>
                <th style={css.miniTh}>Store</th>
                <th style={css.miniTh}>SOV</th>
                <th style={css.miniTh}>Показы</th>
                <th style={css.miniTh}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {placements.map((p) => (
                <tr key={p.id}>
                  <td style={{ ...css.miniTd, fontFamily: "monospace", fontSize: "0.7rem" }}>{p.display_surface_id?.slice(0, 8) ?? "—"}</td>
                  <td style={{ ...css.miniTd, fontFamily: "monospace", fontSize: "0.7rem" }}>{p.store_id?.slice(0, 8) ?? "—"}</td>
                  <td style={css.miniTd}>{p.share_of_voice_pct}%</td>
                  <td style={css.miniTd}>{p.impressions_delivered}{p.max_impressions ? ` / ${p.max_impressions}` : ""}</td>
                  <td style={css.miniTd}><Badge s={p.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    );
  }

  // ── Creatives tab ──

  function renderCreatives() {
    async function handleAddCreative(e: FormEvent) {
      e.preventDefault();
      setCreativeError(null);

      if (!creativeCode.trim() || !creativeName.trim() || !creativeSize) {
        setCreativeError("Код, название и размер файла обязательны");
        return;
      }

      setCreativeSubmitting(true);
      try {
        const body: CampaignCreativeCreateRequest = {
          code: creativeCode.trim(),
          name: creativeName.trim(),
          media_type: creativeType,
          sha256_checksum: creativeSha.trim() || "0000000000000000000000000000000000000000000000000000000000000000",
          file_size_bytes: parseInt(creativeSize, 10),
          duration_ms: creativeDur ? parseInt(creativeDur, 10) : null,
          resolution_w: creativeW ? parseInt(creativeW, 10) : null,
          resolution_h: creativeH ? parseInt(creativeH, 10) : null,
          sort_order: creatives.length,
          duration_override_ms: null,
        };
        await createCreative(campaign.id, body);
        await refreshCreatives();
        resetCreativeForm();
      } catch (e: unknown) {
        setCreativeError(formatApiError(e));
      } finally {
        setCreativeSubmitting(false);
      }
    }

    function resetCreativeForm() {
      setCreativeCode("");
      setCreativeName("");
      setCreativeType("image/jpeg");
      setCreativeSha("");
      setCreativeSize("");
      setCreativeW("");
      setCreativeH("");
      setCreativeDur("");
      setShowCreativeAdd(false);
    }

    const MEDIA_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp", "video/mp4", "video/webm"];

    return (
      <div>
        <div style={{ marginBottom: "0.75rem", padding: "0.5rem", background: "#fffbeb", borderRadius: 4, border: "1px solid #fde68a", fontSize: "0.75rem", color: "#92400e" }}>
          Создание нового креатива (бэкенд не поддерживает привязку существующих). Загрузка файлов — в следующем срезе.
        </div>

        {allAssets.length > 0 && (
          <details style={{ marginBottom: "0.75rem", fontSize: "0.8rem" }}>
            <summary style={{ cursor: "pointer", color: "#475569", fontWeight: 500 }}>
              Существующие креативы ({allAssets.length})
            </summary>
            <table style={{ ...css.miniTable, marginTop: "0.5rem" }}>
              <thead>
                <tr>
                  <th style={css.miniTh}>Код</th>
                  <th style={css.miniTh}>Название</th>
                  <th style={css.miniTh}>Тип</th>
                  <th style={css.miniTh}>Размер</th>
                </tr>
              </thead>
              <tbody>
                {allAssets.map((a) => (
                  <tr key={a.id}>
                    <td style={css.miniTd}>{a.code}</td>
                    <td style={css.miniTd}>{a.name}</td>
                    <td style={css.miniTd}>{a.media_type}</td>
                    <td style={css.miniTd}>{a.resolution_w}×{a.resolution_h}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        )}

        {isDraft && (
          <div style={{ marginBottom: "0.75rem" }}>
            {!showCreativeAdd ? (
              <button type="button" style={css.addBtn} onClick={() => setShowCreativeAdd(true)}>
                + Создать креатив
              </button>
            ) : (
              <form onSubmit={handleAddCreative} style={css.inlineForm}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginBottom: "0.5rem" }}>
                  <div>
                    <label style={css.miniLabel}>Код *</label>
                    <input type="text" value={creativeCode} onChange={(e) => setCreativeCode(e.target.value)} style={css.miniInput} maxLength={64} required />
                  </div>
                  <div>
                    <label style={css.miniLabel}>Название *</label>
                    <input type="text" value={creativeName} onChange={(e) => setCreativeName(e.target.value)} style={css.miniInput} maxLength={255} required />
                  </div>
                  <div>
                    <label style={css.miniLabel}>Тип</label>
                    <select value={creativeType} onChange={(e) => setCreativeType(e.target.value)} style={css.miniSelect}>
                      {MEDIA_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={css.miniLabel}>Размер файла (байт) *</label>
                    <input type="number" value={creativeSize} onChange={(e) => setCreativeSize(e.target.value)} style={css.miniInput} min={0} required />
                  </div>
                  <div>
                    <label style={css.miniLabel}>Ширина</label>
                    <input type="number" value={creativeW} onChange={(e) => setCreativeW(e.target.value)} style={css.miniInput} min={1} />
                  </div>
                  <div>
                    <label style={css.miniLabel}>Высота</label>
                    <input type="number" value={creativeH} onChange={(e) => setCreativeH(e.target.value)} style={css.miniInput} min={1} />
                  </div>
                  <div>
                    <label style={css.miniLabel}>Длительность (мс)</label>
                    <input type="number" value={creativeDur} onChange={(e) => setCreativeDur(e.target.value)} style={css.miniInput} min={1} />
                  </div>
                  <div>
                    <label style={css.miniLabel}>SHA-256</label>
                    <input type="text" value={creativeSha} onChange={(e) => setCreativeSha(e.target.value)} style={css.miniInput} placeholder="Авто-заглушка" maxLength={64} />
                  </div>
                </div>
                <div style={{ display: "flex", gap: "0.25rem" }}>
                  <button type="submit" style={css.primaryBtn} disabled={creativeSubmitting}>
                    {creativeSubmitting ? "..." : "Создать"}
                  </button>
                  <button type="button" style={css.cancelBtn} onClick={resetCreativeForm}>Отмена</button>
                </div>
                {creativeError && <div style={{ color: "#dc2626", fontSize: "0.8rem", marginTop: "0.5rem" }}>{creativeError}</div>}
              </form>
            )}
          </div>
        )}

        {creatives.length === 0 ? (
          <p style={css.muted}>У этой кампании пока нет креативов.</p>
        ) : (
          <table style={css.miniTable}>
            <thead>
              <tr>
                <th style={css.miniTh}>#</th>
                <th style={css.miniTh}>Ассет</th>
                <th style={css.miniTh}>Тип</th>
                <th style={css.miniTh}>Разрешение</th>
                <th style={css.miniTh}>Длит.</th>
                <th style={css.miniTh}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {creatives.map((cc, i) => (
                <tr key={cc.id}>
                  <td style={css.miniTd}>{i + 1}</td>
                  <td style={css.miniTd}>{cc.asset ? cc.asset.name : cc.creative_asset_id}</td>
                  <td style={css.miniTd}>{cc.asset?.media_type ?? "—"}</td>
                  <td style={css.miniTd}>
                    {cc.asset?.resolution_w && cc.asset?.resolution_h
                      ? `${cc.asset.resolution_w}×${cc.asset.resolution_h}`
                      : "—"}
                  </td>
                  <td style={css.miniTd}>
                    {cc.asset?.duration_ms != null ? `${(cc.asset.duration_ms / 1000).toFixed(1)}с` : "—"}
                  </td>
                  <td style={css.miniTd}>{cc.asset ? statusLabel(cc.asset.status) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    );
  }

  function renderReporting() {
    return (
      <div style={css.section}>
        <p style={css.muted}>Отчётность PoP пока недоступна — эндпоинты в разработке (Phase 4.3b).</p>
      </div>
    );
  }

  // ── Main render ──

  const tabNames: Record<Tab, string> = { overview: "Обзор", flights: "Флайты", placements: "Плейсменты", creatives: "Креативы", reporting: "Отчётность" };
  const tabs: Tab[] = ["overview", "flights", "placements", "creatives", "reporting"];

  return (
    <div>
      <div style={{ marginBottom: "1rem" }}>
        <button type="button" style={css.linkBtn} onClick={() => navigate("/campaigns")}>← К списку кампаний</button>
      </div>
      <h2 style={css.heading}>
        {campaign.name}
        <span style={{ fontSize: "0.7rem", color: "#94a3b8", marginLeft: "0.5rem", fontWeight: 400 }}>{campaign.code}</span>
      </h2>
      <div style={css.tabBar}>
        {tabs.map((t) => (
          <button key={t} type="button" style={{ ...css.tab, ...(activeTab === t ? css.tabActive : {}) }} onClick={() => setActiveTab(t)}>
            {tabNames[t]}
            {t === "flights" && flights.length > 0 && <span style={css.tabCount}>{flights.length}</span>}
            {t === "placements" && placements.length > 0 && <span style={css.tabCount}>{placements.length}</span>}
            {t === "creatives" && creatives.length > 0 && <span style={css.tabCount}>{creatives.length}</span>}
          </button>
        ))}
      </div>
      {activeTab === "overview" && renderOverview()}
      {activeTab === "flights" && renderFlights()}
      {activeTab === "placements" && renderPlacements()}
      {activeTab === "creatives" && renderCreatives()}
      {activeTab === "reporting" && renderReporting()}
    </div>
  );
}

// ── Small helpers ──

function F({ label, value }: { label: string; value: React.ReactNode }) {
  return <div><div style={css.fieldLabel}>{label}</div><div style={css.fieldValue}>{value}</div></div>;
}
function FSpan({ label, value }: { label: string; value: string }) {
  return <div style={{ gridColumn: "1 / -1" }}><div style={css.fieldLabel}>{label}</div><div style={{ ...css.fieldValue, whiteSpace: "pre-wrap" }}>{value}</div></div>;
}
function Badge({ s }: { s: string }) {
  return <span style={{ display: "inline-block", padding: "0.15rem 0.5rem", borderRadius: 999, fontSize: "0.8rem", fontWeight: 500, color: "#fff", background: statusColor(s) }}>{statusLabel(s)}</span>;
}

function formatApiError(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 422) return `Ошибка данных: ${e.message}`;
    if (e.status === 403) return "Нет прав на это действие.";
    if (e.status === 409) return "Конфликт: кампания не в статусе черновика или данные конфликтуют.";
    return `Ошибка сервера (${e.status}): ${e.message}`;
  }
  return e instanceof Error ? e.message : "Неизвестная ошибка";
}

// ── Styles ──

const css: Record<string, React.CSSProperties> = {
  heading: { margin: "0 0 1rem", fontSize: "1.25rem", fontWeight: 600 },
  subheading: { margin: "1.25rem 0 0.5rem", fontSize: "0.9rem", fontWeight: 600, color: "#334155", borderBottom: "1px solid #e2e8f0", paddingBottom: "0.25rem" },
  centered: { display: "flex", alignItems: "center", justifyContent: "center", minHeight: 200, flexDirection: "column" },
  muted: { color: "#64748b", fontSize: "0.875rem" },
  errorBox: { background: "#fef2f2", color: "#991b1b", padding: "1rem", borderRadius: 6, maxWidth: 480 },
  linkBtn: { background: "none", border: "none", color: "#2563eb", cursor: "pointer", padding: 0, fontSize: "0.875rem", textDecoration: "underline" },
  tabBar: { display: "flex", gap: 0, borderBottom: "2px solid #e2e8f0", marginBottom: "1rem" },
  tab: { padding: "0.5rem 0.75rem", background: "none", border: "none", borderBottom: "2px solid transparent", marginBottom: -2, cursor: "pointer", fontSize: "0.825rem", color: "#64748b", fontWeight: 500, display: "flex", alignItems: "center", gap: "0.35rem" },
  tabActive: { color: "#1e293b", borderBottomColor: "#2563eb" },
  tabCount: { background: "#e2e8f0", color: "#475569", borderRadius: 999, padding: "0 0.4rem", fontSize: "0.7rem", fontWeight: 600, lineHeight: "1.4" },
  section: { background: "#fff", borderRadius: 6, padding: "1rem", boxShadow: "0 1px 2px rgba(0,0,0,0.06)" },
  fieldGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "0.75rem" },
  fieldLabel: { fontSize: "0.7rem", fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.15rem" },
  fieldValue: { fontSize: "0.875rem", color: "#1e293b" },
  miniTable: { width: "100%", borderCollapse: "collapse", fontSize: "0.825rem" },
  miniTh: { textAlign: "left", padding: "0.4rem 0.5rem", fontWeight: 600, color: "#475569", borderBottom: "1px solid #e2e8f0", fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.05em" },
  miniTd: { padding: "0.4rem 0.5rem", borderBottom: "1px solid #f1f5f9", verticalAlign: "middle" },
  addBtn: { padding: "0.35rem 0.75rem", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: "0.8rem", fontWeight: 500 },
  primaryBtn: { padding: "0.35rem 0.75rem", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: "0.8rem", fontWeight: 500 },
  cancelBtn: { padding: "0.35rem 0.75rem", background: "#fff", border: "1px solid #d1d5db", borderRadius: 4, cursor: "pointer", fontSize: "0.8rem", color: "#475569" },
  inlineForm: { background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 4, padding: "0.75rem" },
  inlineFields: { display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "flex-end" },
  miniLabel: { display: "block", fontSize: "0.65rem", fontWeight: 600, color: "#64748b", marginBottom: "0.1rem", textTransform: "uppercase" },
  miniInput: { padding: "0.3rem 0.5rem", border: "1px solid #d1d5db", borderRadius: 3, fontSize: "0.8rem", boxSizing: "border-box", fontFamily: "inherit" },
  miniSelect: { padding: "0.3rem 0.5rem", border: "1px solid #d1d5db", borderRadius: 3, fontSize: "0.8rem", background: "#fff", boxSizing: "border-box" },
};
