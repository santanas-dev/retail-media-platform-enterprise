import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { CampaignBriefOut, PaginatedResponse } from "../api/types";
import { BRIEF_STATUS_LABELS } from "../api/types";
import s from "./BriefList.module.css";

export default function BriefListPage() {
  const [briefs, setBriefs] = useState<CampaignBriefOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBriefs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<PaginatedResponse<CampaignBriefOut>>("/campaign-briefs");
      setBriefs(data.items);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.status === 401 ? "Сессия истекла. Перезайдите." : `Ошибка загрузки: ${e.message}`);
      } else {
        setError("Не удалось загрузить заявки");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBriefs();
  }, [fetchBriefs]);

  if (loading) {
    return <div className={s.loading}>Загрузка...</div>;
  }

  if (error) {
    return <div className={s.error}>{error}</div>;
  }

  if (briefs.length === 0) {
    return (
      <div className={s.wrapper}>
        <h1 className={s.title}>Мои заявки</h1>
        <div className={s.empty}>
          <p className={s.emptyIcon}>📋</p>
          <p>У вас пока нет заявок на размещение.</p>
          <p className={s.muted}>
            Создайте первую заявку, чтобы отправить её на рассмотрение.
          </p>
          <Link to="/briefs/new" className={s.createBtn}>
            Создать заявку
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className={s.wrapper}>
      <div className={s.header}>
        <h1 className={s.title}>Мои заявки</h1>
        <Link to="/briefs/new" className={s.createBtn}>
          + Новая заявка
        </Link>
      </div>
      <div className={s.list}>
        {briefs.map((b) => (
          <Link to={`/briefs/${b.id}`} key={b.id} className={s.card}>
            <div className={s.cardHeader}>
              <span className={s.cardTitle}>{b.title}</span>
              <span className={`${s.badge} ${s[`status_${b.status}`] ?? ""}`}>
                {BRIEF_STATUS_LABELS[b.status] ?? b.status}
              </span>
            </div>
            <div className={s.cardMeta}>
              {b.product_category && <span>{b.product_category}</span>}
              {b.budget_amount != null && (
                <span>
                  {b.budget_amount.toLocaleString()} {b.budget_currency}
                </span>
              )}
              <span>{new Date(b.updated_at).toLocaleDateString("ru-RU")}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
