import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { CampaignBriefOut, CampaignBriefCreateRequest } from "../api/types";
import s from "./BriefForm.module.css";

export default function BriefCreatePage() {
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: "",
    objective: "",
    product_category: "",
    target_period_from: "",
    target_period_to: "",
    budget_amount: "",
    preferred_channels: "",
    comment: "",
  });

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent, action: "draft" | "submit") {
    e.preventDefault();
    if (!form.title.trim()) {
      setError("Название заявки обязательно");
      return;
    }
    setSaving(true);
    setError(null);

    const payload: CampaignBriefCreateRequest = {
      title: form.title.trim(),
      objective: form.objective.trim() || undefined,
      product_category: form.product_category.trim() || undefined,
      target_period_from: form.target_period_from || undefined,
      target_period_to: form.target_period_to || undefined,
      budget_amount: form.budget_amount ? parseFloat(form.budget_amount) : undefined,
      preferred_channels: form.preferred_channels.trim() || undefined,
      comment: form.comment.trim() || undefined,
    };

    try {
      const brief = await api.post<CampaignBriefOut>("/campaign-briefs", payload);
      if (action === "submit") {
        await api.post<CampaignBriefOut>(
          `/campaign-briefs/${brief.id}/submit`,
        );
      }
      navigate(action === "submit" ? `/briefs/${brief.id}` : "/briefs");
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.status === 422 ? "Проверьте заполненные поля" : e.message);
      } else {
        setError("Не удалось сохранить заявку");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={s.wrapper}>
      <h1 className={s.title}>Новая заявка на размещение</h1>

      {error && <div className={s.error}>{error}</div>}

      <form className={s.form} onSubmit={(e) => handleSubmit(e, "draft")}>
        <label className={s.field}>
          <span className={s.label}>Название *</span>
          <input
            className={s.input}
            value={form.title}
            onChange={(e) => update("title", e.target.value)}
            placeholder="Например: Продвижение молочной продукции"
            maxLength={255}
            disabled={saving}
          />
        </label>

        <label className={s.field}>
          <span className={s.label}>Цель</span>
          <textarea
            className={s.textarea}
            value={form.objective}
            onChange={(e) => update("objective", e.target.value)}
            placeholder="Что вы хотите достичь размещением?"
            rows={2}
            disabled={saving}
          />
        </label>

        <label className={s.field}>
          <span className={s.label}>Категория продукта</span>
          <input
            className={s.input}
            value={form.product_category}
            onChange={(e) => update("product_category", e.target.value)}
            placeholder="Например: Молочная продукция"
            disabled={saving}
          />
        </label>

        <div className={s.row}>
          <label className={s.field}>
            <span className={s.label}>Период с</span>
            <input
              className={s.input}
              type="date"
              value={form.target_period_from}
              onChange={(e) => update("target_period_from", e.target.value)}
              disabled={saving}
            />
          </label>
          <label className={s.field}>
            <span className={s.label}>Период по</span>
            <input
              className={s.input}
              type="date"
              value={form.target_period_to}
              onChange={(e) => update("target_period_to", e.target.value)}
              disabled={saving}
            />
          </label>
        </div>

        <label className={s.field}>
          <span className={s.label}>Бюджет (RUB)</span>
          <input
            className={s.input}
            type="number"
            value={form.budget_amount}
            onChange={(e) => update("budget_amount", e.target.value)}
            placeholder="Ожидаемый бюджет"
            min={0}
            disabled={saving}
          />
        </label>

        <label className={s.field}>
          <span className={s.label}>Предпочитаемые каналы / поверхности</span>
          <textarea
            className={s.textarea}
            value={form.preferred_channels}
            onChange={(e) => update("preferred_channels", e.target.value)}
            placeholder="Опишите, где вы хотели бы разместиться"
            rows={2}
            disabled={saving}
          />
        </label>

        <label className={s.field}>
          <span className={s.label}>Комментарий</span>
          <textarea
            className={s.textarea}
            value={form.comment}
            onChange={(e) => update("comment", e.target.value)}
            placeholder="Дополнительная информация"
            rows={3}
            disabled={saving}
          />
        </label>

        <div className={s.actions}>
          <button
            type="submit"
            className={s.btnDraft}
            disabled={saving}
          >
            {saving ? "Сохранение..." : "Сохранить черновик"}
          </button>
          <button
            type="button"
            className={s.btnSubmit}
            disabled={saving}
            onClick={(e) => handleSubmit(e, "submit")}
          >
            {saving ? "Отправка..." : "Отправить на рассмотрение"}
          </button>
          <Link to="/briefs" className={s.btnCancel}>
            Отмена
          </Link>
        </div>
      </form>
    </div>
  );
}
