/** Честная заглушка: раздел документов появится после подключения договорного контура. */
export default function DocumentsPlaceholderPage() {
  return (
    <div style={{ maxWidth: 600 }}>
      <h1 style={{ fontSize: "1.25rem", fontWeight: 600, color: "#1e293b", marginBottom: "0.5rem" }}>
        Документы и договоры
      </h1>
      <p style={{ color: "#64748b", fontSize: "0.9rem", lineHeight: 1.6 }}>
        Документы появятся после подключения договорного контура. Сейчас вы можете
        ознакомиться с основными разделами кабинета.
      </p>
    </div>
  );
}
