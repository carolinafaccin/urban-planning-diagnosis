import { Card } from "@wri-brasil/design-system";
import ImageZoom from "./ImageZoom";
import type { ReportCard } from "../types";

export default function MapCard({ titulo, img, descricao }: ReportCard) {
  return (
    <Card className="overflow-hidden p-0 print:break-inside-avoid">
      <ImageZoom src={`${import.meta.env.BASE_URL}data/${img}`} alt={titulo} className="w-full" />
      <div className="p-4">
        <h3 className="text-base font-semibold text-wri-ink">{titulo}</h3>
        <p className="mt-1 text-sm text-wri-muted">{descricao}</p>
      </div>
    </Card>
  );
}
