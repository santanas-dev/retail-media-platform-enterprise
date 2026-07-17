/** Честная заглушка: раздел поддержки будет доступен после запуска платформы. */
export default function SupportPlaceholderPage() {
  return (
    <div style={{ maxWidth: 600 }}>
      <h1 style={{ fontSize: "1.25rem", fontWeight: 600, color: "#1e293b", marginBottom: "0.5rem" }}>
        Поддержка
      </h1>
      <p style={{ color: "#64748b", fontSize: "0.9rem", lineHeight: 1.6 }}>
        Форма обратной связи и база знаний будут доступны после запуска платформы.
        По срочным вопросам обращайтесь к вашему менеджеру.
      </p>
    </div>
  );
}
