import { useParams } from "react-router-dom";

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <div>
      <h2 style={{ margin: "0 0 1rem", fontSize: "1.25rem" }}>
        Кампания {id}
      </h2>
      <p style={{ color: "#64748b", fontSize: "0.875rem" }}>
        Детали кампании появятся здесь (S-009c).
      </p>
    </div>
  );
}
