import { X, Users } from "lucide-react";
import { SentimentSegment, SENTIMENT_EMOJIS, SENTIMENT_COLORS } from "../types/sentiment";

interface SentimentSegmentModalProps {
  segment: SentimentSegment | null;
  isOpen: boolean;
  onClose: () => void;
}

export function SentimentSegmentModal({ segment, isOpen, onClose }: SentimentSegmentModalProps) {
  if (!isOpen || !segment) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-xl">
        {/* Header */}
        <div
          className="p-4 border-b flex items-center justify-between"
          style={{ backgroundColor: `${SENTIMENT_COLORS[segment.sentiment_label]}15` }}
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">{SENTIMENT_EMOJIS[segment.sentiment_label]}</span>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Segment {segment.segment_index + 1}</h2>
              <p className="text-sm text-gray-600">{segment.start_time}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded text-gray-600"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Sentiment Badge */}
          <div className="flex items-center gap-3">
            <div
              className="px-3 py-1 rounded-full text-white text-sm font-medium"
              style={{ backgroundColor: SENTIMENT_COLORS[segment.sentiment_label] }}
            >
              {segment.sentiment_label.charAt(0).toUpperCase() + segment.sentiment_label.slice(1)} (
              {(segment.sentiment_score * 100).toFixed(0)}%)
            </div>
          </div>

          {/* Segment Text */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-2">Transcript</h3>
            <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 leading-relaxed">
              {segment.segment_text}
            </div>
          </div>

          {/* Speaker Breakdown */}
          {segment.speaker_sentiments && segment.speaker_sentiments.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <Users className="w-4 h-4" />
                Speakers in This Segment
              </h3>
              <div className="space-y-2">
                {segment.speaker_sentiments.map((speaker, idx) => (
                  <div key={idx} className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-gray-900">{speaker.speaker}</span>
                      <span className="text-lg">{SENTIMENT_EMOJIS[speaker.sentiment_label]}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          backgroundColor: SENTIMENT_COLORS[speaker.sentiment_label],
                          width: `${Math.min(100, Math.max(10, (speaker.sentiment_score + 1) * 50))}%`,
                        }}
                      />
                      <span className="text-xs text-gray-600">
                        {speaker.sentiment_label.charAt(0).toUpperCase() + speaker.sentiment_label.slice(1)} (
                        {(speaker.sentiment_score * 100).toFixed(0)}%)
                      </span>
                    </div>
                    {speaker.snippet && (
                      <p className="text-xs text-gray-500 mt-2 italic">"{speaker.snippet.substring(0, 100)}"</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t p-4 bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border rounded-lg hover:bg-gray-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
