export interface ClaimItem {
  claim: string;
  verdict: string;
  explanation: string;
  sources: string[];
}

export interface SourceItem {
  title: string;
  url: string;
  description: string;
}

export interface DeepfakeData {
  is_deepfake: boolean;
  confidence: number;
  risk_level: string;
  analysis: string;
  indicators: string[];
}

export interface ReverseImageMatch {
  title: string;
  url: string;
  source: string;
  date: string;
  thumbnail: string;
}

export interface ReverseImageData {
  enabled: boolean;
  frame_url?: string | null;
  matches: ReverseImageMatch[];
  earliest_date?: string | null;
  note: string;
}

export interface FactCheckResult {
  id?: string;
  overall_verdict: string;
  confidence_score: number;
  summary: string;
  transcript: string;
  visual_description?: string | null;
  claims: ClaimItem[];
  sources: SourceItem[];
  deepfake: DeepfakeData;
  reverse_image?: ReverseImageData | null;
  video_url: string;
  created_at?: string;
}

export interface JobStatus {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  progress_message: string;
  result?: FactCheckResult;
  error?: string;
}
