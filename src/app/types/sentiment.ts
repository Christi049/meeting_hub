export type SentimentLabel = "positive" | "negative" | "neutral";

export interface SpeakerSentiment {
  speaker: string;
  sentiment_label: SentimentLabel;
  sentiment_score: number;
  snippet?: string;
}

export interface SentimentSegment {
  segment_index: number;
  start_time: string; // "0:00-5:00"
  segment_text: string;
  sentiment_label: SentimentLabel;
  sentiment_score: number; // -1 to +1
  speaker_sentiments: SpeakerSentiment[];
}

export interface SentimentBreakdown {
  speaker: string;
  average_score: number;
  segment_count: number;
  sentiment_label: SentimentLabel;
}

export interface SentimentSummary {
  overall_sentiment: SentimentLabel;
  sentiment_score: number;
  segments: SentimentSegment[];
  speaker_breakdown: Record<string, SentimentBreakdown>;
  positive_percentage: number;
  negative_percentage: number;
  neutral_percentage: number;
}

export const SENTIMENT_COLORS: Record<SentimentLabel, string> = {
  positive: "#10B981", // Green
  negative: "#EF4444", // Red
  neutral: "#F59E0B", // Yellow
};

export const SENTIMENT_EMOJIS: Record<SentimentLabel, string> = {
  positive: "😊",
  negative: "😟",
  neutral: "😐",
};
