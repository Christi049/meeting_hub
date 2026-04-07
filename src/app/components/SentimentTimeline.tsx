import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { SentimentSegment, SENTIMENT_COLORS, SENTIMENT_EMOJIS } from "../types/sentiment";

interface SentimentTimelineProps {
  segments: SentimentSegment[];
  onSegmentClick: (index: number) => void;
}

export function SentimentTimeline({ segments, onSegmentClick }: SentimentTimelineProps) {
  if (!segments || segments.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <p className="text-sm">No sentiment data available</p>
      </div>
    );
  }

  const chartData = segments.map((segment) => ({
    timeRange: segment.start_time,
    score: segment.sentiment_score,
    sentiment: segment.sentiment_label,
    index: segment.segment_index,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-900 text-white px-3 py-2 rounded shadow-lg text-xs">
          <p className="font-semibold">{data.timeRange}</p>
          <p className="text-gray-300">
            {SENTIMENT_EMOJIS[data.sentiment]} {data.sentiment.charAt(0).toUpperCase() + data.sentiment.slice(1)}
          </p>
          <p className="text-gray-300">Score: {(data.score * 100).toFixed(0)}%</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full bg-white rounded-lg border p-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Sentiment Timeline</h3>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chartData} onClick={(data: any) => {
          if (data && data.activeTooltipIndex !== undefined) {
            onSegmentClick(data.activeTooltipIndex);
          }
        }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="timeRange" tick={{ fontSize: 12 }} />
          <YAxis domain={[-1, 1]} tick={{ fontSize: 12 }} />
          <Tooltip content={<CustomTooltip />} />
          <Bar
            dataKey="score"
            radius={[4, 4, 0, 0]}
            onClick={(data) => onSegmentClick(data.index)}
            cursor="pointer"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={SENTIMENT_COLORS[entry.sentiment]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-4 flex justify-center gap-4 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-green-500"></div>
          <span className="text-gray-600">Positive</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-amber-500"></div>
          <span className="text-gray-600">Neutral</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded bg-red-500"></div>
          <span className="text-gray-600">Negative</span>
        </div>
      </div>
    </div>
  );
}
