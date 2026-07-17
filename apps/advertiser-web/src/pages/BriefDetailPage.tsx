import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { CampaignBriefOut } from "../api/types";
import { BRIEF_STATUS_LABELS } from "../api/types";
import s from "./BriefDetail.module.css";

export default function BriefDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [brief, setBrief] = useState<CampaignBriefOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.get<CampaignBriefOut>(`/campaign-briefs/${id}`);
        if (!cancelled) setBrief(data);
      } catch (e) {
        if (!cancelled) {
          if (e instanceof ApiError && e.status === 404) {
            setError("Заявка не найдена");
          } else if (e instanceof ApiError) {
            setError(e.message);
          } else {
            setError("Ошибка загрузки заявки");
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [id]);

  async function handleSubmit() {
    if (!brief || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const updated = await api.post<CampaignBriefOut>(
        `/campaign-briefs/${brief.id}/submit`,
      );
      setBrief(updated);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Не удалось отправить заявку");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className={s.loading}>Загрузка...</div>;
  if (error && !brief) return <div className={s.error}>{error}</div>;
  if (!brief) return <div className={s.error}>Заявка не найдена</div>;

  const isDraft = brief.status === "draft";
  const isSubmitted = brief.status === "submitted";

  return (
    <div className={s.wrapper}>
      <Link to="/briefs" className={s.backLink}>← К списку заявок</Link>

      <div className={s.header}>
        <h1 className={s.title}>{brief.title}</h1>
        <span className={`${s.badge} ${s[`status_${brief.status}`] ?? ""}`}>
          {BRIEF_STATUS_LABELS[brief.status] ?? brief.status}
        </span>
      </div>

      {error && <div className={s.error}>{error}</div>}

      <section className={s.section}>
        {brief.objective && (
          <div className={s.row}>
            <span className={s.label}>Цель</span>
            <span>{brief.objective}</span>
          </div>
        )}
        {brief.product_category && (
          <div className={s.row}>
            <span className={s.label}>Категория</span>
            <span>{brief.product_category}</span>
          </div>
        )}
      </section>

      <section className={s.section}>
        {(brief.target_period_from || brief.target_period_to) && (
          <div className={s.row}>
            <span className={s.label}>Период</span>
            <span>
              {brief.target_period_from
                ? new Date(brief.target_period_from).toLocaleDateString("ru-RU")
                : "…"}
              {" — "}
              {brief.target_period_to
                ? new Date(brief.target_period_to).toLocaleDateString("ru-RU")
                : "…"}
            </span>
          </div>
        )}
        {brief.budget_amount != null && (
          <div className={s.row}>
            <span className={s.label}>Бюджет</span>
            <span>
              {brief.budget_amount.toLocaleString()} {brief.budget_currency}
            </span>
          </div>
        )}
        {brief.preferred_channels && (
          <div className={s.row}>
            <span className={s.label}>Предпочитаемые каналы</span>
            <span>{brief.preferred_channels}</span>
          </div>
        )}
      </section>

      {brief.comment && (
        <section className={s.section}>
          <div className={s.row}>
            <span className={s.label}>Комментарий</span>
            <span style={{ whiteSpace: "pre-wrap" }}>{brief.comment}</span>
          </div>
        </section>
      )}

      <section className={`${s.section} ${s.meta}`}>
        <div className={s.row}>
          <span className={s.label}>Создана</span>
          <span>{new Date(brief.created_at).toLocaleString("ru-RU")}</span>
        </div>
        <div className={s.row}>
          <span className={s.label}>Обновлена</span>
          <span>{new Date(brief.updated_at).toLocaleString("ru-RU")}</span>
        </div>
      </section>

      {isDraft && (
        <div className={s.actions}>
          <Link to={`/briefs/${brief.id}/edit`} className={s.btnEdit}>
            Редактировать
          </Link>
          <button
            type="button"
            className={s.btnSubmit}
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? "Отправка..." : "Отправить на рассмотрение"}
          </button>
        </div>
      )}

      {isSubmitted && (
        <p className={s.submittedNote}>
          Заявка отправлена на рассмотрение. Редактирование недоступно.
        </p>
      )}
    </div>
  );
}
