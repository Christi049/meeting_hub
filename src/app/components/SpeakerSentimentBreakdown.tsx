import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { SentimentSegment, SENTIMENT_COLORS, SENTIMENT_EMOJIS } from "../types/sentiment";

interface SpeakerSentimentBreakdownProps {
  segments: SentimentSegment[];
}

export function SpeakerSentimentBreakdown({ segments }: SpeakerSentimentBreakdownProps) {
  if (!segments || segments.length === 0) {
    return null;
  }

  // Aggregate sentiment by speaker across all segments
  const speakerStats: Record<
    string,
    {
      scores: number[];
      segments: number;
      sentiment: "positive" | "negative" | "neutral";
    }
  > = {};

  segments.forEach((segment) => {
    segment.speaker_sentiments?.forEach((speaker_sentiment) => {
      if (!speakerStats[speaker_sentiment.speaker]) {
        speakerStats[speaker_sentiment.speaker] = {
          scores: [],
          segments: 0,
          sentiment: "neutral",
        };
      }
      speakerStats[speaker_sentiment.speaker].scores.push(speaker_sentiment.sentiment_score);
      speakerStats[speaker_sentiment.speaker].segments += 1;
    });
  });

  // Convert to chart data
  const chartData = Object.entries(speakerStats)
    .map(([speaker, stats]) => {
      const avgScore = stats.scores.length > 0 ? stats.scores.reduce((a, b) => a + b, 0) / stats.scores.length : 0;
      let sentiment: "positive" | "negative" | "neutral" = "neutral";
      if (avgScore > 0.03) sentiment = "positive";
      else if (avgScore < -0.03) sentiment = "negative";

      return {
        speaker,
        score: parseFloat(avgScore.toFixed(4)),
        segments: stats.segments,
        sentiment,
      };
    })
    .sort((a, b) => Math.abs(b.score) - Math.abs(a.score));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-900 text-white px-3 py-2 rounded shadow-lg text-xs">
          <p className="font-semibold">{data.speaker}</p>
          <p className="text-gray-300">
            {SENTIMENT_EMOJIS[data.sentiment]} {data.sentiment.charAt(0).toUpperCase() + data.sentiment.slice(1)}
          </p>
          <p className="text-gray-300">Score: {(data.score * 100).toFixed(0)}%</p>
          <p className="text-gray-300">Segments: {data.segments}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full bg-white rounded-lg border p-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Per-Speaker Sentiment</h3>
      <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 35)}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 150, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis type="number" domain={[-1, 1]} tick={{ fontSize: 12 }} />
          <YAxis dataKey="speaker" type="category" width={145} tick={{ fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="score" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={SENTIMENT_COLORS[entry.sentiment]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-4 text-xs text-gray-500">
        <p>
          Shows average sentiment score per speaker across all segments. Positive values indicate more favorable
          language, negative values indicate concerns or conflicts.
        </p>
      </div>
    </div>
  );
}
