// API response type definitions for Terra OS

export interface TenderListItem {
  id: string;
  title: string;
  buyer: string;
  cpv: string[];
  voivodeship: string;
  value_pln: number;
  deadline_at: string;
  status: string;
  match_score: number;
  match_reason: string;
}

export interface TenderDetail extends TenderListItem {
  source: string;
  external_id: string;
  published_at: string;
  url: string;
  raw: Record<string, unknown>;
}

export interface EstimateLine {
  description: string;
  unit: string;
  quantity: number;
  unit_price: number;
  total: number;
  knr_code: string;
  chapter: string;
}

export interface Estimate {
  id: string;
  tender_id: string;
  variant: 'doc' | 'owner';
  total_net_pln: number;
  overhead_pct: number;
  profit_pct: number;
  params: Record<string, unknown>;
  lines: EstimateLine[];
  created_at: string;
}

export interface TendersResponse {
  items: TenderListItem[];
  total: number;
}

export interface DashboardStats {
  total_tenders: number;
  by_status: Record<string, number>;
  total_value_pln: number;
  avg_match_score: number;
  estimates_count: number;
}
