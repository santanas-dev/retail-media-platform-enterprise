import { useCallback, useEffect, useState, useRef, type FormEvent } from "react";
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
  approveCampaign,
  rejectCampaign,
  attachCreative,
  createCreativeAsset,
  getCampaignPopSummary,
  getCampaignPopByDay,
  getCampaignPopBySurface,
  listBranches,
  listClusters,
  listStores,
  listDisplaySurfaces,
  createUploadIntent,
  completeUpload,
  uploadFileToPresignedUrl,
  simulateInventory,
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
  CampaignCreativeAttachRequest,
  CreativeAssetCreateRequest,
  CreativeAssetOut,
  AdvertiserOrganizationOut,
  AdvertiserBrandOut,
  AdvertiserContractOut,
  CampaignApprovalOut,
  CampaignPopSummaryOut,
  CampaignPopByDayOut,
  CampaignPopBySurfaceOut,
  BranchOut,
  StoreOut,
  DisplaySurfaceRefOut,
} from "../api/types";
import { statusLabel, statusColor } from "../api/types";
import type {
  InventoryAvailabilityResponse,
  InventorySlotAvailability,
  InventoryAlternativesResponse,
  InventorySimulationResponse,
} from "../api/types";
import { checkAvailability, suggestAlternatives } from "../api/campaigns";
import { ApiError, getToken, IDENTITY_BASE_URL } from "../api/client";
import { useAuth } from "../auth/AuthContext";

// ── Delivered types for use in the component ──

type FlightWithForm = CampaignFlightOut & { _editing?: boolean };
type PlacementWithForm = CampaignPlacementOut & { _editing?: boolean };
type CreativeLink = CampaignCreativeOut & { asset: CreativeAssetOut | null };
type CreativeLinkWithForm = CreativeLink & { _editing?: boolean };

type Tab = "overview" | "flights" | "placements" | "creatives" | "reporting" | "dashboard";

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
  const { user } = useAuth();

  const hasApprovePerm = user?.permissions?.includes("campaigns.approve") ?? false;

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

  // ── Availability forecast state ──
  const [availabilityResult, setAvailabilityResult] = useState<InventoryAvailabilityResponse | null>(null);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [availabilityError, setAvailabilityError] = useState<string | null>(null);
  const [placementAlternatives, setPlacementAlternatives] = useState<InventoryAlternativesResponse | null>(null);
  const [altLoading, setAltLoading] = useState(false);

  // ── S-089 Simulation state ──
  const [simulationResult, setSimulationResult] = useState<InventorySimulationResponse | null>(null);
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [simulationError, setSimulationError] = useState<string | null>(null);

  // S-009j: standalone creative asset intake (library)
  const [assetCode, setAssetCode] = useState("");
  const [assetName, setAssetName] = useState("");
  const [assetMediaType, setAssetMediaType] = useState("image");
  const [assetW, setAssetW] = useState("");
  const [assetH, setAssetH] = useState("");
  const [assetDur, setAssetDur] = useState("");
  const [assetSize, setAssetSize] = useState("");
  const [assetChecksum, setAssetChecksum] = useState("");
  const [assetSubmitting, setAssetSubmitting] = useState(false);
  const [assetError, setAssetError] = useState<string | null>(null);
  const [showAssetAdd, setShowAssetAdd] = useState(false);

  // Attach existing creative
  const [attachAssetId, setAttachAssetId] = useState("");
  const [attachSubmitting, setAttachSubmitting] = useState(false);
  const [attachError, setAttachError] = useState<string | null>(null);
  const [showAttach, setShowAttach] = useState(false);

  // S-017: Upload state
  const [uploadAssetId, setUploadAssetId] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState<
    "idle" | "requesting_url" | "uploading" | "finalizing" | "done" | "error"
  >("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const uploadInputRef = useRef<HTMLInputElement>(null);

  // Approval
  const [approvalSubmitting, setApprovalSubmitting] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);

  // Reject dialog
  const [showReject, setShowReject] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  // PoP reporting
  const [popSummary, setPopSummary] = useState<CampaignPopSummaryOut | null>(null);
  const [popByDay, setPopByDay] = useState<CampaignPopByDayOut[]>([]);
  const [popBySurface, setPopBySurface] = useState<CampaignPopBySurfaceOut[]>([]);
  const [popLoading, setPopLoading] = useState(false);
  const [popLoaded, setPopLoaded] = useState(false);
  const [popError, setPopError] = useState<string | null>(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // Reference data for placement pickers
  const [refSurfaces, setRefSurfaces] = useState<DisplaySurfaceRefOut[]>([]);
  const [refStores, setRefStores] = useState<StoreOut[]>([]);
  const [refLoading, setRefLoading] = useState(false);
  const [refLoaded, setRefLoaded] = useState(false);
  const [refError, setRefError] = useState<string | null>(null);

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

  // ── S-017: File upload handler ──

  const ALLOWED_MIME: Record<string, string> = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
  };
  const ALLOWED_TYPES_STR = Object.values(ALLOWED_MIME).join(", ");

  async function handleUpload(assetId: string, file: File) {
    const mime = file.type || "application/octet-stream";
    if (!(mime in ALLOWED_MIME)) {
      setUploadError(`Неподдерживаемый тип файла: ${mime}. Допустимы: ${ALLOWED_TYPES_STR}`);
      return;
    }

    setUploadAssetId(assetId);
    setUploadFile(file);
    setUploadProgress(0);
    setUploadStage("requesting_url");
    setUploadError(null);

    try {
      // 1. Create upload intent
      const intent = await createUploadIntent(assetId, {
        filename: file.name,
        content_type: mime,
        content_length: file.size,
      });

      // 2. PUT to presigned URL (no Authorization header)
      setUploadStage("uploading");
      await uploadFileToPresignedUrl(
        intent.upload_url,
        file,
        intent.headers,
        (loaded, total) => setUploadProgress(Math.round((loaded / total) * 100)),
      );

      // 3. Complete upload — server computes SHA-256
      setUploadStage("finalizing");
      await completeUpload(assetId, { upload_id: intent.upload_id });

      // 4. Refresh data
      setUploadStage("done");
      await refreshCreatives();
    } catch (e: unknown) {
      setUploadStage("error");
      if (e instanceof Error) setUploadError(e.message);
      else setUploadError("Неизвестная ошибка загрузки");
    }
  }

  function resetUpload() {
    setUploadAssetId(null);
    setUploadFile(null);
    setUploadProgress(0);
    setUploadStage("idle");
    setUploadError(null);
  }


  const refreshCampaign = async () => {
    if (!id) return;
    const campaign = await getCampaign(id);
    if (campaign && data) {
      setData({ ...data, campaign });
    }
  };

  const loadPopData = useCallback(async (campaignId: string) => {
    setPopLoading(true);
    setPopError(null);
    try {
      const [summary, byDay, bySurface] = await Promise.all([
        getCampaignPopSummary(campaignId),
        getCampaignPopByDay(campaignId),
        getCampaignPopBySurface(campaignId),
      ]);
      setPopSummary(summary);
      setPopByDay(byDay);
      setPopBySurface(bySurface);
      setPopLoaded(true);
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        if (e.status === 404) setPopError("Кампания не найдена.");
        else if (e.status === 403) setPopError("Нет прав на просмотр отчётности.");
        else setPopError(`Ошибка загрузки отчётности (${e.status})`);
      } else {
        setPopError(e instanceof Error ? e.message : "Ошибка загрузки отчётности");
      }
    } finally {
      setPopLoading(false);
    }
  }, []);

  // S-040: CSV export handler
  const handleExportCsv = useCallback(async () => {
    if (!data) return;
    setExportLoading(true);
    setExportError(null);
    try {
      const token = getToken();
      const resp = await fetch(
        `${IDENTITY_BASE_URL}/campaigns/${data.campaign.id}/pop/export`,
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
      a.download = `${data.campaign.code}_pop_report.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setExportError(e instanceof Error ? e.message : "Ошибка экспорта");
    } finally {
      setExportLoading(false);
    }
  }, [data]);

  // Lazy-load PoP data when reporting or dashboard tab is activated
  useEffect(() => {
    if ((activeTab === "reporting" || activeTab === "dashboard") && !popLoaded && !popLoading && data) {
      loadPopData(data.campaign.id);
    }
  }, [activeTab, popLoaded, popLoading, data, loadPopData]);

  // Lazy-load reference data when placements tab is activated
  useEffect(() => {
    if (activeTab === "placements" && !refLoaded && !refLoading && data) {
      setRefLoading(true);
      setRefError(null);
      Promise.all([
        listDisplaySurfaces(),
        listStores(),
      ])
        .then(([surfaces, stores]) => {
          setRefSurfaces(surfaces.filter((s) => s.is_active));
          setRefStores(stores.filter((s) => s.is_active));
          setRefLoaded(true);
        })
        .catch((e: unknown) => {
          setRefError(e instanceof Error ? e.message : "Ошибка загрузки справочников");
        })
        .finally(() => setRefLoading(false));
    }
  }, [activeTab, refLoaded, refLoading, data]);

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
  const isPendingApproval = campaign.status === "pending_approval";

  // ── Tab content ──

  function renderOverview() {
    const canApprove = flights.length > 0 && placements.length > 0 && creatives.length > 0;

    async function handleSimulate() {
      setSimulationError(null);
      setSimulationLoading(true);
      try {
        const res = await simulateInventory(campaign.id);
        setSimulationResult(res);
      } catch (e: unknown) {
        setSimulationError(e instanceof Error ? e.message : "Ошибка симуляции");
      } finally {
        setSimulationLoading(false);
      }
    }

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
        {/* ── Draft: submit for approval ── */}
        {isDraft && (
          <div style={{ marginBottom: "1rem", padding: "0.75rem", background: "#f0f9ff", borderRadius: 6, border: "1px solid #bae6fd" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
              <div style={{ flex: 1, fontSize: "0.825rem", color: "#0c4a6e" }}>
                Кампания в черновике.
                {!canApprove && " Добавьте минимум один флайт, плейсмент и креатив для отправки на согласование."}
              </div>
              {/* ── S-089 Simulation ── */}
              {canApprove && (
                <button type="button" style={{ ...css.secondaryBtn, fontSize: "0.75rem" }}
                  onClick={handleSimulate} disabled={simulationLoading}>
                  {simulationLoading ? "Симуляция..." : "🧪 Симуляция"}
                </button>
              )}
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

        {/* ── S-089 Simulation results ── */}
        {simulationResult && (
          <div style={{ marginBottom: "1rem", padding: "0.75rem", border: "1px solid var(--rmp-border-strong)", borderRadius: 6, fontSize: "0.8rem" }}>
            <strong style={{ color: simulationResult.overall_fit ? "var(--rmp-success-600)" : "var(--rmp-danger-600)" }}>
              {simulationResult.overall_fit ? "✅ Кампания помещается" : "❌ Кампания не помещается"}
            </strong>
            <span style={{ marginLeft: "0.5rem", color: "#64748b" }}>
              ({simulationResult.blocking_count} блок., {simulationResult.warning_count} пред.)
            </span>
            {simulationResult.placements.map((p, i) => (
              <div key={i} style={{ marginTop: "0.4rem", padding: "0.35rem", background: p.fit ? "#f0fdf4" : "#fef2f2", borderRadius: 4 }}>
                <span style={{ fontWeight: 600 }}>{p.surface_code || p.surface_id}</span>
                {" "}— fill {p.slot_fill_percent}% ({p.total_requested}/{p.total_available})
                {!p.fit && <span style={{ color: "var(--rmp-danger-600)", marginLeft: "0.5rem" }}>⚠ конфликт</span>}
                {p.conflicts.length > 0 && (
                  <ul style={{ margin: "0.15rem 0 0", paddingLeft: "1.2rem", fontSize: "0.75rem" }}>
                    {p.conflicts.slice(0, 3).map((c, j) => (
                      <li key={j} style={{ color: c.severity === "blocking" ? "var(--rmp-danger-600)" : "#92400e" }}>
                        {c.message}
                      </li>
                    ))}
                    {p.conflicts.length > 3 && <li style={{ color: "#64748b" }}>...и ещё {p.conflicts.length - 3}</li>}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
        {simulationError && (
          <div style={{ color: "#dc2626", fontSize: "0.8rem", marginBottom: "1rem" }}>{simulationError}</div>
        )}

        {/* ── Pending approval: approve / reject or read-only ── */}
        {isPendingApproval && (
          <div style={{ marginBottom: "1rem", padding: "0.75rem", background: hasApprovePerm ? "#fffbeb" : "#f8fafc", borderRadius: 6, border: hasApprovePerm ? "1px solid #fde68a" : "1px solid #e2e8f0" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
              <div style={{ flex: 1, fontSize: "0.825rem", color: hasApprovePerm ? "#92400e" : "#64748b" }}>
                Кампания ожидает согласования.
                {!hasApprovePerm && " У вас нет прав на согласование."}
              </div>
              {hasApprovePerm && (
                <>
                  <button
                    type="button"
                    style={{ ...css.primaryBtn, background: "#059669" }}
                    disabled={approvalSubmitting}
                    onClick={async () => {
                      setApprovalError(null);
                      setApprovalSubmitting(true);
                      try {
                        const res = await approveCampaign(campaign.id);
                        await refreshCampaign();
                        if (data) setData({ ...data, campaign: { ...data.campaign, status: res.new_status } });
                      } catch (e: unknown) {
                        setApprovalError(formatApiError(e));
                      } finally {
                        setApprovalSubmitting(false);
                      }
                    }}
                  >
                    {approvalSubmitting ? "..." : "Согласовать"}
                  </button>
                  <button
                    type="button"
                    style={{ ...css.cancelBtn, borderColor: "#dc2626", color: "#dc2626" }}
                    disabled={approvalSubmitting}
                    onClick={() => { setShowReject(true); setRejectReason(""); setApprovalError(null); }}
                  >
                    Отклонить
                  </button>
                </>
              )}
            </div>
            {approvalError && (
              <div style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "#dc2626" }}>{approvalError}</div>
            )}
            {/* Reject reason dialog */}
            {hasApprovePerm && showReject && (
              <div style={{ marginTop: "0.75rem", padding: "0.75rem", background: "#fff", borderRadius: 4, border: "1px solid #fecaca" }}>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 500, marginBottom: "0.25rem" }}>
                  Причина отклонения *
                </label>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  style={{ width: "100%", minHeight: 60, padding: "0.4rem", border: "1px solid #d1d5db", borderRadius: 3, fontSize: "0.825rem", boxSizing: "border-box" }}
                  placeholder="Укажите причину отклонения"
                  maxLength={1000}
                  rows={2}
                />
                <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                  <button
                    type="button"
                    style={{ ...css.primaryBtn, background: "#dc2626" }}
                    disabled={!rejectReason.trim() || approvalSubmitting}
                    onClick={async () => {
                      if (!rejectReason.trim()) return;
                      setApprovalError(null);
                      setApprovalSubmitting(true);
                      try {
                        const res = await rejectCampaign(campaign.id, { reason: rejectReason.trim() });
                        await refreshCampaign();
                        if (data) setData({ ...data, campaign: { ...data.campaign, status: res.new_status } });
                        setShowReject(false);
                      } catch (e: unknown) {
                        setApprovalError(formatApiError(e));
                      } finally {
                        setApprovalSubmitting(false);
                      }
                    }}
                  >
                    Подтвердить отклонение
                  </button>
                  <button
                    type="button"
                    style={css.cancelBtn}
                    onClick={() => setShowReject(false)}
                  >
                    Отмена
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {!isDraft && !isPendingApproval && (
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

    async function handleCheckAvailability() {
      if (!placementSurface || !data) return;
      setAvailabilityLoading(true);
      setAvailabilityError(null);
      setAvailabilityResult(null);
      setPlacementAlternatives(null);
      try {
        const startDt = data.campaign.start_at ? new Date(data.campaign.start_at) : new Date();
        const endDt = data.campaign.end_at ? new Date(data.campaign.end_at) : new Date(startDt.getTime() + 7 * 86400000);
        const result = await checkAvailability({
          surface_id: placementSurface,
          starts_at: startDt.toISOString(),
          ends_at: endDt.toISOString(),
          requested_sov_percent: parseInt(placementSov, 10) || null,
        });
        setAvailabilityResult(result);
        if (!result.all_available) {
          await handlePlacementAlternatives(startDt, endDt);
        }
      } catch (e: unknown) {
        setAvailabilityError(e instanceof ApiError ? e.message : "Ошибка проверки доступности");
      } finally {
        setAvailabilityLoading(false);
      }
    }

    async function handlePlacementAlternatives(startDt: Date, endDt: Date) {
      if (!placementSurface) return;
      setAltLoading(true);
      try {
        const altResult = await suggestAlternatives({
          surface_id: placementSurface,
          starts_at: startDt.toISOString(),
          ends_at: endDt.toISOString(),
          requested_sov_percent: parseInt(placementSov, 10) || null,
          max_results: 5,
        });
        setPlacementAlternatives(altResult);
      } catch {
        setPlacementAlternatives(null);
      } finally {
        setAltLoading(false);
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

    // Build helper maps for display
    const surfaceMap = new Map(refSurfaces.map((s) => [s.id, s]));
    const storeMap = new Map(refStores.map((s) => [s.id, s]));

    function surfaceLabel(id: string): string {
      const s = surfaceMap.get(id);
      return s ? `${s.code} (${s.resolution_w}×${s.resolution_h})` : id;
    }

    function storeLabel(id: string): string {
      const s = storeMap.get(id);
      return s ? `${s.name} [${s.code}]` : id;
    }

    const hasRefData = refSurfaces.length > 0;

    return (
      <div>
        {/* Reference loading/error */}
        {refLoading && <p style={css.muted}>Загрузка справочников...</p>}
        {!refLoading && refError && (
          <div style={{ marginBottom: "0.75rem", padding: "0.5rem", background: "#fef2f2", borderRadius: 4, border: "1px solid #fecaca", fontSize: "0.75rem", color: "#991b1b" }}>
            {refError}
          </div>
        )}

        {/* Add form */}
        {isDraft && (
          <div style={{ marginBottom: "0.75rem" }}>
            {!showPlacementAdd ? (
              <button type="button" style={css.addBtn} onClick={() => setShowPlacementAdd(true)}>
                + Добавить плейсмент
              </button>
            ) : (
              <form onSubmit={handleAddPlacement} style={css.inlineForm}>
                <div style={css.inlineFields}>
                  {hasRefData ? (
                    <>
                      <div>
                        <label style={css.miniLabel}>Поверхность</label>
                        <select value={placementSurface} onChange={(e) => setPlacementSurface(e.target.value)} style={{ ...css.miniSelect, minWidth: 200 }}>
                          <option value="">— не выбрана —</option>
                          {refSurfaces.map((s) => (
                            <option key={s.id} value={s.id}>{s.code} — {storeLabel(s.store_id)} ({s.resolution_w}×{s.resolution_h})</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label style={css.miniLabel}>Магазин</label>
                        <select value={placementStore} onChange={(e) => setPlacementStore(e.target.value)} style={{ ...css.miniSelect, minWidth: 160 }}>
                          <option value="">— не выбран —</option>
                          {refStores.map((s) => (
                            <option key={s.id} value={s.id}>{s.name} [{s.code}]</option>
                          ))}
                        </select>
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <label style={css.miniLabel}>Surface ID</label>
                        <input type="text" value={placementSurface} onChange={(e) => setPlacementSurface(e.target.value)} style={css.miniInput} placeholder="UUID" />
                      </div>
                      <div>
                        <label style={css.miniLabel}>Store ID</label>
                        <input type="text" value={placementStore} onChange={(e) => setPlacementStore(e.target.value)} style={css.miniInput} placeholder="UUID" />
                      </div>
                    </>
                  )}
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
                    {placementSurface && (
                      <button type="button" style={{ ...css.secondaryBtn, fontSize: "0.75rem" }}
                        onClick={handleCheckAvailability} disabled={availabilityLoading}>
                        {availabilityLoading ? "..." : "🔍 Доступность"}
                      </button>
                    )}
                  </div>
                </div>
                {!hasRefData && !refLoading && (
                  <p style={{ fontSize: "0.7rem", color: "#94a3b8", margin: "0.4rem 0 0" }}>
                    Нет доступных поверхностей для выбора. Справочники загружаются через API при наличии данных.
                  </p>
                )}
                {placementError && <div style={{ color: "#dc2626", fontSize: "0.8rem", marginTop: "0.5rem" }}>{placementError}</div>}
                {availabilityResult && (
                  <div style={{ marginTop: "0.75rem", padding: "0.5rem", border: "1px solid var(--rmp-border-strong)", borderRadius: "var(--rmp-radius-sm)", fontSize: "0.8rem" }}>
                    <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                      <span>Слотов: <strong>{availabilityResult.slots.length}</strong></span>
                      <span>Запрошено: <strong>{availabilityResult.total_requested}</strong></span>
                      <span>Доступно: <strong style={{ color: availabilityResult.all_available ? "var(--rmp-success-600)" : "var(--rmp-danger-600)" }}>{availabilityResult.total_available}</strong></span>
                      <span>Конфликтов: <strong style={{ color: availabilityResult.conflicts.length > 0 ? "var(--rmp-danger-600)" : "var(--rmp-success-600)" }}>{availabilityResult.conflicts.length}</strong></span>
                      <span>Итог: <strong style={{ color: availabilityResult.all_available ? "var(--rmp-success-600)" : "var(--rmp-danger-600)" }}>{availabilityResult.all_available ? "Доступно" : "Недоступно"}</strong></span>
                    </div>
                    {availabilityResult.conflicts.length > 0 && (
                      <div style={{ color: "var(--rmp-danger-600)", marginTop: "0.25rem" }}>
                        ⚠️ Конфликты: проверьте «Инвентарь → Конфликты».
                      </div>
                    )}
                  </div>
                )}
                {availabilityError && (
                  <div style={{ color: "#dc2626", fontSize: "0.8rem", marginTop: "0.5rem" }}>{availabilityError}</div>
                )}
                {/* S-087 — Placement alternatives */}
                {!availabilityResult?.all_available && placementAlternatives && (
                  <div style={{ marginTop: "0.5rem", padding: "0.4rem", border: "1px solid var(--rmp-border-strong)", borderRadius: "var(--rmp-radius-sm)", fontSize: "0.8rem" }}>
                    <strong>Возможные альтернативы ({placementAlternatives.total_found}):</strong>
                    {altLoading ? (
                      <p style={{ color: "#64748b", margin: "0.15rem 0 0" }}>Поиск альтернатив...</p>
                    ) : placementAlternatives.alternatives.length === 0 ? (
                      <p style={{ color: "#64748b", margin: "0.15rem 0 0" }}>Нет альтернатив. Попробуйте изменить период или SOV.</p>
                    ) : (
                      <ul style={{ margin: "0.25rem 0 0", paddingLeft: "1.2rem", display: "flex", flexDirection: "column", gap: "0.2rem" }}>
                        {placementAlternatives.alternatives.map((alt, i) => (
                          <li key={i}>
                            <strong>{alt.surface_code || alt.surface_id}</strong> — {alt.reason}{" "}
                            <span style={{ color: "var(--rmp-success-600)" }}>({alt.available_capacity} ед.)</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
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
                <th style={css.miniTh}>Поверхность</th>
                <th style={css.miniTh}>Магазин</th>
                <th style={css.miniTh}>SOV</th>
                <th style={css.miniTh}>Показы</th>
                <th style={css.miniTh}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {placements.map((p) => (
                <tr key={p.id}>
                  <td style={css.miniTd}>{p.display_surface_id ? surfaceLabel(p.display_surface_id) : "—"}</td>
                  <td style={css.miniTd}>{p.store_id ? storeLabel(p.store_id) : "—"}</td>
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
    // S-009j: standalone asset intake (library) — handle submit
    async function handleCreateAsset(e: FormEvent) {
      e.preventDefault();
      setAssetError(null);

      if (!assetCode.trim() || !assetName.trim()) {
        setAssetError("Код и название обязательны");
        return;
      }

      setAssetSubmitting(true);
      try {
        const body: CreativeAssetCreateRequest = {
          code: assetCode.trim(),
          name: assetName.trim(),
          media_type: assetMediaType,
          sha256_checksum: assetChecksum.trim() || undefined,
          file_size_bytes: assetSize ? parseInt(assetSize, 10) : null,
          resolution_w: assetW ? parseInt(assetW, 10) : null,
          resolution_h: assetH ? parseInt(assetH, 10) : null,
          duration_ms: assetDur ? parseInt(assetDur, 10) : null,
        };
        await createCreativeAsset(body);
        // Refresh the global asset list so the picker sees the new asset
        try { const fresh = await listCreativeAssets(); setAllAssets(fresh); } catch { /* non-critical */ }
        await refreshCreatives();
        resetAssetForm();
      } catch (e: unknown) {
        setAssetError(formatApiError(e));
      } finally {
        setAssetSubmitting(false);
      }
    }

    function resetAssetForm() {
      setAssetCode("");
      setAssetName("");
      setAssetMediaType("image");
      setAssetW("");
      setAssetH("");
      setAssetDur("");
      setAssetSize("");
      setAssetChecksum("");
      setShowAssetAdd(false);
    }

    const MEDIA_TYPE_LABELS = [
      { value: "image", label: "Изображение" },
      { value: "video", label: "Видео" },
      { value: "html", label: "HTML" },
      { value: "other", label: "Прочее" },
    ];

    // P1: helper — asset has real file (not metadata-only)
    function isDeliverable(a: CreativeAssetOut): boolean {
      return a.sha256_checksum != null && a.sha256_checksum.length === 64;
    }

    // Unattached assets (not yet linked to this campaign)
    const linkedIds = new Set(creatives.map((x) => x.creative_asset_id));
    const unattached = allAssets.filter((a) => !linkedIds.has(a.id));

    return (
      <div>
        {/* ── Attach existing creative ── */}
        {isDraft && (
          <div style={{ marginBottom: "0.75rem" }}>
            {!showAttach ? (
              <button type="button" style={css.addBtn} onClick={() => { setShowAttach(true); setAttachError(null); }}>
                + Прикрепить существующий креатив
              </button>
            ) : (
              <form onSubmit={async (e) => { e.preventDefault();
                if (!attachAssetId) { setAttachError("Выберите креатив"); return; }
                setAttachSubmitting(true); setAttachError(null);
                try {
                  await attachCreative(campaign.id, { creative_asset_id: attachAssetId, sort_order: creatives.length });
                  await refreshCreatives();
                  setAttachAssetId(""); setShowAttach(false);
                } catch (err: unknown) { setAttachError(formatApiError(err)); }
                finally { setAttachSubmitting(false); }
              }} style={css.inlineForm}>
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "flex-end" }}>
                  <div>
                    <label style={css.miniLabel}>Креатив</label>
                    {unattached.length > 0 ? (
                      <select value={attachAssetId} onChange={(e) => setAttachAssetId(e.target.value)}
                        style={{ ...css.miniSelect, minWidth: 260 }}>
                        <option value="">— выберите —</option>
                        {unattached.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name} [{a.code}] — {a.media_type}{a.resolution_w ? " " + a.resolution_w + "x" + a.resolution_h : ""}{!isDeliverable(a) ? " (ожидает загрузки)" : ""}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <p style={{ fontSize: "0.75rem", color: "#94a3b8", margin: 0 }}>
                        {allAssets.length === 0 ? "Нет доступных креативов для выбора." : "Все креативы уже прикреплены."}
                      </p>
                    )}
                  </div>
                  {attachAssetId && (() => {
                    const selected = unattached.find((a) => a.id === attachAssetId);
                    if (selected && !isDeliverable(selected)) {
                      return (
                        <div style={{ padding: "0.5rem", background: "#fff7ed", borderRadius: 4, border: "1px solid #fdba74", fontSize: "0.75rem", color: "#9a3412", marginBottom: "0.5rem" }}>
                          ⚠ Этот креатив ещё не загружен. Кампания с ним не пройдёт согласование — сначала загрузите файл.
                        </div>
                      );
                    }
                    return null;
                  })()}
                  {unattached.length > 0 && (
                    <div style={{ display: "flex", gap: "0.25rem", alignItems: "flex-end" }}>
                      <button type="submit" style={css.primaryBtn} disabled={attachSubmitting}>
                        {attachSubmitting ? "..." : "Прикрепить"}
                      </button>
                      <button type="button" style={css.cancelBtn} onClick={() => { setShowAttach(false); setAttachError(null); setAttachAssetId(""); }}>
                        Отмена
                      </button>
                    </div>
                  )}
                </div>
                {attachError && <div style={{ color: "#dc2626", fontSize: "0.8rem", marginTop: "0.5rem" }}>{attachError}</div>}
              </form>
            )}
          </div>
        )}

        {/* ── S-009j: Добавить креатив в библиотеку ── */}
        {isDraft && (
          <div style={{ marginBottom: "0.75rem" }}>
            {!showAssetAdd ? (
              <button type="button" style={css.addBtn} onClick={() => { setShowAssetAdd(true); setAssetError(null); }}>
                + Добавить креатив в библиотеку
              </button>
            ) : (
              <form onSubmit={handleCreateAsset} style={css.inlineForm}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginBottom: "0.5rem" }}>
                  <div>
                    <label htmlFor="ca-code" style={css.miniLabel}>Код *</label>
                    <input id="ca-code" type="text" value={assetCode} onChange={(e) => setAssetCode(e.target.value)} style={css.miniInput} maxLength={64} required />
                  </div>
                  <div>
                    <label htmlFor="ca-name" style={css.miniLabel}>Название *</label>
                    <input id="ca-name" type="text" value={assetName} onChange={(e) => setAssetName(e.target.value)} style={css.miniInput} maxLength={255} required />
                  </div>
                  <div>
                    <label htmlFor="ca-type" style={css.miniLabel}>Тип медиа</label>
                    <select id="ca-type" value={assetMediaType} onChange={(e) => setAssetMediaType(e.target.value)} style={css.miniSelect}>
                      {MEDIA_TYPE_LABELS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="ca-size" style={css.miniLabel}>Размер файла (байт)</label>
                    <input id="ca-size" type="number" value={assetSize} onChange={(e) => setAssetSize(e.target.value)} style={css.miniInput} min={0} placeholder="Опционально" />
                  </div>
                  <div>
                    <label htmlFor="ca-w" style={css.miniLabel}>Ширина</label>
                    <input id="ca-w" type="number" value={assetW} onChange={(e) => setAssetW(e.target.value)} style={css.miniInput} min={1} placeholder="Опционально" />
                  </div>
                  <div>
                    <label htmlFor="ca-h" style={css.miniLabel}>Высота</label>
                    <input id="ca-h" type="number" value={assetH} onChange={(e) => setAssetH(e.target.value)} style={css.miniInput} min={1} placeholder="Опционально" />
                  </div>
                  <div>
                    <label htmlFor="ca-dur" style={css.miniLabel}>Длительность (мс)</label>
                    <input id="ca-dur" type="number" value={assetDur} onChange={(e) => setAssetDur(e.target.value)} style={css.miniInput} min={1} placeholder="Опционально" />
                  </div>
                </div>

                {/* Technical params — collapsed */}
                <details style={{ marginBottom: "0.75rem", fontSize: "0.75rem" }}>
                  <summary style={{ cursor: "pointer", color: "#64748b" }}>
                    Технические параметры
                  </summary>
                  <div style={{ marginTop: "0.5rem" }}>
                    <label style={css.miniLabel}>SHA-256</label>
                    <input type="text" value={assetChecksum} onChange={(e) => setAssetChecksum(e.target.value)} style={css.miniInput} placeholder="Авто-заглушка" maxLength={64} />
                  </div>
                </details>

                {/* S-017: File upload is now active — use the "Загрузить файл" button on each asset */}

                <div style={{ display: "flex", gap: "0.25rem" }}>
                  <button type="submit" style={css.primaryBtn} disabled={assetSubmitting}>
                    {assetSubmitting ? "..." : "Добавить в библиотеку"}
                  </button>
                  <button type="button" style={css.cancelBtn} onClick={resetAssetForm}>Отмена</button>
                </div>
                {assetError && <div style={{ color: "#dc2626", fontSize: "0.8rem", marginTop: "0.5rem" }}>{assetError}</div>}
              </form>
            )}
          </div>
        )}

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
                  <th style={css.miniTh}>Статус</th>
                </tr>
              </thead>
              <tbody>
                {allAssets.map((a) => (
                  <tr key={a.id}>
                    <td style={css.miniTd}>{a.code}</td>
                    <td style={css.miniTd}>{a.name}</td>
                    <td style={css.miniTd}>{a.media_type}</td>
                    <td style={css.miniTd}>{a.resolution_w}×{a.resolution_h}</td>
                    <td style={css.miniTd}>
                      {isDeliverable(a)
                        ? statusLabel(a.status)
                        : <span style={{ color: "#d97706", fontWeight: 500 }}>⚠ Ожидает загрузки</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        )}

        {creatives.length === 0 ? (
          <p style={css.muted}>У этой кампании пока нет креативов.</p>
        ) : (
          <>
            {/* S-017: Hidden file input + inline upload progress */}
            <input
              ref={uploadInputRef}
              type="file"
              accept=".png,.jpg,.jpeg,.webp,.gif,.mp4"
              style={{ display: "none" }}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                // Find a metadata_only asset to upload to
                // Use the first metadata_only creative asset
                const metaCreative = creatives.find(
                  (c) => c.asset && !isDeliverable(c.asset),
                );
                if (metaCreative?.asset) {
                  handleUpload(metaCreative.asset.id, f);
                }
                // Reset input so same file can be re-selected
                e.target.value = "";
              }}
            />
            {uploadStage !== "idle" && uploadStage !== "done" && (
              <div style={{ padding: "0.5rem 0.75rem", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 4, marginBottom: "0.5rem", fontSize: "0.8rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
                  <span style={{ fontWeight: 600 }}>
                    {uploadStage === "requesting_url" && "Запрос адреса загрузки..."}
                    {uploadStage === "uploading" && `Загрузка ${uploadFile?.name ?? ""} — ${uploadProgress}%`}
                    {uploadStage === "finalizing" && "Проверка контрольной суммы на сервере..."}
                  </span>
                </div>
                {(uploadStage === "uploading" || uploadStage === "requesting_url") && (
                  <div style={{ width: "100%", height: 4, background: "#e2e8f0", borderRadius: 2, overflow: "hidden" }}>
                    <div style={{ width: `${uploadStage === "requesting_url" ? 10 : uploadProgress}%`, height: "100%", background: "#2563eb", transition: "width 0.2s" }} />
                  </div>
                )}
                {uploadStage === "error" && (
                  <div style={{ color: "#dc2626", marginTop: "0.35rem" }}>
                    Ошибка: {uploadError || "Не удалось загрузить файл"}
                  </div>
                )}
              </div>
            )}
            {uploadStage === "idle" && uploadError && (
              <div style={{ padding: "0.5rem 0.75rem", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 4, marginBottom: "0.5rem", fontSize: "0.8rem", color: "#991b1b" }}>
                {uploadError}
                <button type="button" onClick={resetUpload} style={{ marginLeft: "0.75rem", background: "none", border: "none", color: "#2563eb", cursor: "pointer", fontSize: "0.75rem", textDecoration: "underline" }}>
                  Сбросить
                </button>
              </div>
            )}
          <table style={css.miniTable}>
            <thead>
              <tr>
                <th style={css.miniTh}>#</th>
                <th style={css.miniTh}>Ассет</th>
                <th style={css.miniTh}>Тип</th>
                <th style={css.miniTh}>Разрешение</th>
                <th style={css.miniTh}>Длит.</th>
                <th style={css.miniTh}>Статус</th>
                {isDraft && <th style={css.miniTh}>Файл</th>}
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
                  <td style={css.miniTd}>
                    {cc.asset
                      ? isDeliverable(cc.asset)
                        ? statusLabel(cc.asset.status)
                        : <span style={{ color: "#d97706", fontWeight: 500 }}>⚠ Ожидает загрузки</span>
                      : "—"}
                  </td>
                  {isDraft && (
                    <td style={css.miniTd}>
                      {cc.asset && !isDeliverable(cc.asset) && (
                        <button
                          type="button"
                          data-upload={cc.asset.id}
                          style={{ background: "#2563eb", color: "#fff", border: "none", borderRadius: 3, padding: "0.2rem 0.4rem", fontSize: "0.72rem", cursor: "pointer" }}
                          onClick={() => uploadInputRef.current?.click()}
                        >
                          Загрузить файл
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          </>
        )}
      </div>
    );
  }

  function renderDashboard() {
    // Plan: sum of max_impressions across all placements
    const totalPlan = placements.reduce((sum, p) => sum + (p.max_impressions ?? 0), 0);
    const hasPlan = totalPlan > 0;

    // Fact: actual impressions from PoP
    const actual = popSummary?.impressions_count ?? 0;
    const hasPoP = popSummary !== null && popSummary.impressions_count > 0;

    // Deviation
    const deviationAbs = hasPlan ? actual - totalPlan : null;
    const deviationPct = hasPlan && totalPlan > 0
      ? Math.round(((actual - totalPlan) / totalPlan) * 100)
      : null;

    // Delivery status
    let deliveryLabel = "—";
    let deliveryColor = "#94a3b8";
    if (hasPlan && hasPoP) {
      if (deviationPct !== null && deviationPct >= -5) {
        deliveryLabel = deviationPct >= 0 ? "Перевыполнение" : "В норме";
        deliveryColor = "#16a34a";
      } else if (deviationPct !== null && deviationPct >= -30) {
        deliveryLabel = "Недопоказ";
        deliveryColor = "#d97706";
      } else {
        deliveryLabel = "Критичный недопоказ";
        deliveryColor = "#dc2626";
      }
    }

    // ── Card component ──
    function DCard({ label, value, color }: { label: string; value: string; color?: string }) {
      return (
        <div style={{ ...css.reportCard }}>
          <div style={css.reportCardLabel}>{label}</div>
          <div style={{ ...css.reportCardValue, color: color ?? "#0f172a" }}>{value}</div>
        </div>
      );
    }

    return (
      <div>

        {/* ── Loading ── */}
        {popLoading && (
          <div style={css.section}>
            <p style={css.muted}>Загрузка дашборда...</p>
          </div>
        )}

        {/* ── Error ── */}
        {!popLoading && popError && (
          <div style={css.section}>
            <div style={{ padding: "0.75rem", background: "#fef2f2", borderRadius: 4, border: "1px solid #fecaca", color: "#991b1b", fontSize: "0.875rem" }}>
              {popError}
            </div>
          </div>
        )}

        {/* ── Loaded ── */}
        {!popLoading && !popError && (
          <div>
            {/* ── Plan / Fact Cards ── */}
            <div style={{ ...css.section, marginBottom: "1rem" }}>
              <h3 style={{ ...css.subheading, marginTop: 0 }}>План / Факт</h3>
              <div style={css.reportGrid}>
                <DCard label={hasPlan ? "План (показы)" : "План"} value={hasPlan ? totalPlan.toLocaleString("ru-RU") : "Не задан"} />
                <DCard label={hasPoP ? "Факт (показы)" : "Факт"} value={hasPoP ? actual.toLocaleString("ru-RU") : "Нет данных"} color={hasPoP ? undefined : "#94a3b8"} />
                {deviationAbs !== null && (
                  <DCard label="Отклонение" value={`${deviationAbs >= 0 ? "+" : ""}${deviationAbs.toLocaleString("ru-RU")} (${deviationPct !== null && deviationPct >= 0 ? "+" : ""}${deviationPct}%)`}
                    color={deviationPct !== null && deviationPct >= -5 ? "#16a34a" : deviationPct !== null && deviationPct >= -30 ? "#d97706" : "#dc2626"} />
                )}
                <DCard label="Статус доставки" value={deliveryLabel} color={deliveryColor} />
              </div>

              {/* Underdelivery note */}
              {hasPlan && hasPoP && deviationPct !== null && deviationPct < -5 && (
                <div style={{ marginTop: "0.75rem", padding: "0.6rem 0.75rem", background: "#fffbeb", borderRadius: 4, border: "1px solid #fde68a", fontSize: "0.8rem", color: "#92400e" }}>
                  ⚠️ Недопоказ: план {totalPlan.toLocaleString("ru-RU")}, факт {actual.toLocaleString("ru-RU")} ({deviationPct}%).
                  Причины недопоказа — см. вкладку «Отчётность» (по дням / по поверхностям).
                  Автоматические компенсации — в плане (S-096).
                </div>
              )}
              {!hasPoP && (
                <div style={{ marginTop: "0.75rem", padding: "0.6rem 0.75rem", background: "#f8fafc", borderRadius: 4, border: "1px solid #e2e8f0", fontSize: "0.8rem", color: "#64748b" }}>
                  Пока нет подтверждённых показов. Данные появятся после поступления PoP-событий.
                </div>
              )}
              {hasPoP && !hasPlan && (
                <div style={{ marginTop: "0.75rem", padding: "0.6rem 0.75rem", background: "#f8fafc", borderRadius: 4, border: "1px solid #e2e8f0", fontSize: "0.8rem", color: "#64748b" }}>
                  План показов не задан в плейсментах. Добавьте max_impressions в плейсменты для расчёта план/факт.
                </div>
              )}
            </div>

            {/* ── By-Day breakdown ── */}
            {popByDay.length > 0 && (
              <div style={{ ...css.section, marginBottom: "1rem" }}>
                <h3 style={{ ...css.subheading, marginTop: 0 }}>По дням</h3>
                <table style={css.miniTable}>
                  <thead>
                    <tr>
                      <th style={css.miniTh}>Дата</th>
                      <th style={{ ...css.miniTh, textAlign: "right" }}>Показы</th>
                      <th style={{ ...css.miniTh, textAlign: "right" }}>Длительность</th>
                    </tr>
                  </thead>
                  <tbody>
                    {popByDay.map((row, i) => (
                      <tr key={i}>
                        <td style={css.miniTd}>{row.date}</td>
                        <td style={{ ...css.miniTd, textAlign: "right" }}>{row.impressions_count.toLocaleString("ru-RU")}</td>
                        <td style={{ ...css.miniTd, textAlign: "right" }}>{fmtDuration(row.total_duration_ms)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* ── By-Surface breakdown ── */}
            {popBySurface.length > 0 && (
              <div style={{ ...css.section, marginBottom: "1rem" }}>
                <h3 style={{ ...css.subheading, marginTop: 0 }}>По поверхностям / географии</h3>
                <table style={css.miniTable}>
                  <thead>
                    <tr>
                      <th style={css.miniTh}>Поверхность</th>
                      <th style={{ ...css.miniTh, textAlign: "right" }}>Показы</th>
                      <th style={{ ...css.miniTh, textAlign: "right" }}>Длительность</th>
                    </tr>
                  </thead>
                  <tbody>
                    {popBySurface.map((row, i) => (
                      <tr key={i}>
                        <td style={css.miniTd}>{row.surface_id}</td>
                        <td style={{ ...css.miniTd, textAlign: "right" }}>{row.impressions_count.toLocaleString("ru-RU")}</td>
                        <td style={{ ...css.miniTd, textAlign: "right" }}>{fmtDuration(row.total_duration_ms)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* ── Device Health ── */}
            <div style={{ ...css.section, marginBottom: "1rem" }}>
              <h3 style={{ ...css.subheading, marginTop: 0 }}>Здоровье устройств</h3>
              {popSummary && popSummary.unique_devices > 0 ? (
                <div>
                  <div style={css.reportGrid}>
                    <DCard label="Устройств с показами" value={popSummary.unique_devices.toLocaleString("ru-RU")} color="#2563eb" />
                    <DCard label="Поверхностей" value={popSummary.unique_surfaces.toLocaleString("ru-RU")} />
                  </div>
                  <div style={{ marginTop: "0.75rem", padding: "0.6rem 0.75rem", background: "#f8fafc", borderRadius: 4, border: "1px solid #e2e8f0", fontSize: "0.8rem", color: "#64748b" }}>
                    <strong>Ограничение:</strong> операционный центр здоровья устройств (online/offline, ошибки плеера, heartbeat, версии) — в плане (S-097).
                    Сейчас доступно только количество устройств, подтвердивших показы (PoP).
                  </div>
                </div>
              ) : (
                <div style={{ padding: "1.5rem 1rem", textAlign: "center" }}>
                  <p style={{ fontSize: "0.9rem", color: "#94a3b8", margin: "0 0 0.5rem" }}>
                    Нет данных об устройствах
                  </p>
                  <p style={{ fontSize: "0.75rem", color: "#cbd5e1" }}>
                    Данные появятся после поступления PoP-событий
                  </p>
                </div>
              )}
            </div>

            {/* ── No PoP at all ── */}
            {!hasPoP && popByDay.length === 0 && popBySurface.length === 0 && (
              <div style={{ ...css.section, padding: "2rem 1rem", textAlign: "center" }}>
                <p style={{ fontSize: "0.9rem", color: "#94a3b8", margin: "0 0 0.5rem" }}>
                  Пока нет подтверждённых показов
                </p>
                <p style={{ fontSize: "0.75rem", color: "#cbd5e1" }}>
                  Дашборд обновится после поступления PoP-событий от устройств
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  function renderReporting() {
    // ── Card component ──
    function Card({ label, value }: { label: string; value: string }) {
      return (
        <div style={css.reportCard}>
          <div style={css.reportCardLabel}>{label}</div>
          <div style={css.reportCardValue}>{value}</div>
        </div>
      );
    }

    const hasData = popSummary && popSummary.impressions_count > 0;

    return (
      <div style={css.section}>
        {/* ── Loading state ── */}
        {popLoading && <p style={css.muted}>Загрузка отчётности...</p>}

        {/* ── Error state ── */}
        {!popLoading && popError && (
          <div style={{ padding: "0.75rem", background: "#fef2f2", borderRadius: 4, border: "1px solid #fecaca", color: "#991b1b", fontSize: "0.875rem" }}>
            {popError}
          </div>
        )}

        {/* ── Empty state ── */}
        {!popLoading && !popError && !hasData && (
          <div style={{ padding: "2rem 1rem", textAlign: "center" }}>
            <p style={{ fontSize: "0.9rem", color: "#94a3b8", margin: "0 0 0.5rem" }}>
              Пока нет подтверждённых показов
            </p>
            <p style={{ fontSize: "0.75rem", color: "#cbd5e1" }}>
              Отчётность обновится после поступления PoP-событий от устройств
            </p>
          </div>
        )}

        {/* ── Data ── */}
        {!popLoading && !popError && hasData && popSummary && (
          <>
            {/* Summary cards */}
            <div style={css.reportGrid}>
              <Card label="Показы" value={popSummary.impressions_count.toLocaleString("ru-RU")} />
              <Card label="Общее время" value={fmtDuration(popSummary.total_duration_ms)} />
              <Card label="Устройств" value={popSummary.unique_devices.toLocaleString("ru-RU")} />
              <Card label="Поверхностей" value={popSummary.unique_surfaces.toLocaleString("ru-RU")} />
            </div>

            {/* By-Day table */}
            {popByDay.length > 0 && (
              <>
                <h3 style={{ ...css.subheading, marginTop: "1.5rem" }}>По дням</h3>
                <table style={css.miniTable}>
                  <thead>
                    <tr>
                      <th style={css.miniTh}>Дата</th>
                      <th style={{ ...css.miniTh, textAlign: "right" }}>Показы</th>
                      <th style={{ ...css.miniTh, textAlign: "right" }}>Длительность</th>
                    </tr>
                  </thead>
                  <tbody>
                    {popByDay.map((row, i) => (
                      <tr key={i}>
                        <td style={css.miniTd}>{row.date}</td>
                        <td style={{ ...css.miniTd, textAlign: "right" }}>{row.impressions_count.toLocaleString("ru-RU")}</td>
                        <td style={{ ...css.miniTd, textAlign: "right" }}>{fmtDuration(row.total_duration_ms)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}

            {/* By-Surface table */}
            {popBySurface.length > 0 && (
              <>
                <h3 style={{ ...css.subheading, marginTop: "1.5rem" }}>По поверхностям</h3>
                <table style={css.miniTable}>
                  <thead>
                    <tr>
                      <th style={css.miniTh}>Поверхность</th>
                      <th style={{ ...css.miniTh, textAlign: "right" }}>Показы</th>
                      <th style={{ ...css.miniTh, textAlign: "right" }}>Длительность</th>
                    </tr>
                  </thead>
                  <tbody>
                    {popBySurface.map((row, i) => (
                      <tr key={i}>
                        <td style={css.miniTd}>{row.surface_id}</td>
                        <td style={{ ...css.miniTd, textAlign: "right" }}>{row.impressions_count.toLocaleString("ru-RU")}</td>
                        <td style={{ ...css.miniTd, textAlign: "right" }}>{fmtDuration(row.total_duration_ms)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}

            {/* Limitation note + Export button */}
            <div style={{ marginTop: "1.5rem", borderTop: "1px solid #f1f5f9", paddingTop: "0.75rem", display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={handleExportCsv}
                disabled={exportLoading}
                style={{
                  padding: "0.35rem 0.75rem",
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
              <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                XLSX — в разработке
              </span>
              {exportError && (
                <span style={{ fontSize: "0.75rem", color: "#dc2626" }}>{exportError}</span>
              )}
            </div>
          </>
        )}
      </div>
    );
  }

  // ── Main render ──

  const tabNames: Record<Tab, string> = { overview: "Обзор", flights: "Флайты", placements: "Плейсменты", creatives: "Креативы", reporting: "Отчётность", dashboard: "Дашборд" };
  const tabs: Tab[] = ["overview", "flights", "placements", "creatives", "dashboard", "reporting"];

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
      {activeTab === "dashboard" && renderDashboard()}
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

function fmtDuration(ms: number): string {
  if (ms < 1000) return `${ms} мс`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} с`;
  return `${(ms / 60_000).toFixed(1)} мин`;
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
  reportGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "0.5rem", marginBottom: "0.5rem" },
  reportCard: { background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, padding: "0.75rem 1rem" },
  reportCardLabel: { fontSize: "0.65rem", fontWeight: 600, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.25rem" },
  reportCardValue: { fontSize: "1.25rem", fontWeight: 600, color: "#0f172a" },
};
