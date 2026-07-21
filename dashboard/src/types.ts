export interface ReportCard {
  id: string;
  titulo: string;
  img: string;
  descricao: string;
}

export interface Report {
  cidade: string;
  data: string;
  n_hex: number;
  n_pop: number | null;
  dist: Record<string, number>;
  cards: ReportCard[];
  analise_md: string;
}
