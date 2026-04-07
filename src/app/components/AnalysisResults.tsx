import { useState } from "react";
import { SentimentTimeline } from "./SentimentTimeline";
import { SpeakerSentimentBreakdown } from "./SpeakerSentimentBreakdown";
import { SentimentSegmentModal } from "./SentimentSegmentModal";
import { SENTIMENT_EMOJIS, SentimentSegment } from "../types/sentiment";

interface ActionItem {
  task: string;
  owner: string;
  due_by?: string;
}

interface AnalysisData {
  file_name: string;
  word_count: number;
  speakers: number;
  unique_speakers: string[];
  date: string;
  title: string;
  abstractive_summary: string;
  decisions: string[];
  action_items: ActionItem[];
  stored_path?: string;
  segments?: Array<{
    segment_index: number;
    start_time: string;
    sentiment_label: "positive" | "negative" | "neutral";
    sentiment_score: number;
  }>;
}

interface AnalysisResultsProps {
  data: AnalysisData;
}

function exportToCSV(data: AnalysisData) {
  const rows: string[] = [];
  rows.push(['Type', 'Owner', 'Item', 'Due By'].map((v) => `"${v}"`).join(','));
  
  (data.decisions || []).forEach((d) => {
    rows.push(['Decision', '', d, ''].map((v) => `"${v}"`).join(','));
  });
  
  (data.action_items || []).forEach((a) => {
    rows.push(
      [
        'Action Item',
        a.owner || 'Unknown',
        a.task || '',
        a.due_by || 'Unknown',
      ]
        .map((v) => `"${v}"`)
        .join(',')
    );
  });

  const csv = rows.join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  const baseName = (data.file_name || 'meeting').replace(/\.[^.]+$/, '');
  link.download = `${baseName}_decisions_actions.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

async function exportToPDF(data: AnalysisData) {
  // Dynamically import jsPDF
  const { jsPDF } = await import('jspdf');
  const doc = new jsPDF();
  
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 14;
  const maxWidth = pageWidth - margin * 2;
  let y = margin;

  function ensureSpace(required = 8) {
    if (y + required > pageHeight - margin) {
      doc.addPage();
      y = margin;
    }
  }

  function writeLine(text: string, size = 11, bold = false, gap = 6) {
    doc.setFont('helvetica', bold ? 'bold' : 'normal');
    doc.setFontSize(size);
    const lines = doc.splitTextToSize(text, maxWidth);
    for (const line of lines) {
      ensureSpace(gap + 2);
      doc.text(line, margin, y);
      y += gap;
    }
  }

  writeLine(`Meeting Report: ${data.file_name || 'meeting'}`, 14, true, 7);
  writeLine(`Project: ${data.title || 'Unknown'}`);
  writeLine(`Date: ${data.date || 'Unknown'}`);
  writeLine(`Speakers: ${data.speakers || 0}`);
  y += 2;

  writeLine('Detected Speakers', 12, true, 7);
  writeLine((data.unique_speakers || []).join(', ') || 'None');
  y += 4;

  writeLine('Decisions', 12, true, 7);
  if (data.decisions && data.decisions.length > 0) {
    data.decisions.forEach((d, i) => {
      writeLine(`${i + 1}. ${d}`, 10, false, 5);
    });
  } else {
    writeLine('None detected', 10);
  }
  y += 4;

  writeLine('Action Items', 12, true, 7);
  if (data.action_items && data.action_items.length > 0) {
    data.action_items.forEach((a, i) => {
      writeLine(
        `${i + 1}. ${a.task} (Owner: ${a.owner || 'Unknown'}, Due: ${a.due_by || 'Unknown'})`,
        10,
        false,
        5
      );
    });
  } else {
    writeLine('None detected', 10);
  }

  const baseName = (data.file_name || 'meeting').replace(/\.[^.]+$/, '');
  doc.save(`${baseName}_decisions_actions.pdf`);
}

export function AnalysisResults({ data }: AnalysisResultsProps) {
  const [selectedSegmentIndex, setSelectedSegmentIndex] = useState<number | null>(null);
  const [showSegmentModal, setShowSegmentModal] = useState(false);

  // Build sentiment segments with full data (currently we only have summary data)
  const sentimentSegments: SentimentSegment[] = (data.segments || []).map((seg) => ({
    segment_index: seg.segment_index,
    start_time: seg.start_time,
    sentiment_label: seg.sentiment_label,
    sentiment_score: seg.sentiment_score,
    segment_text: "", // Full text not available from API response
    speaker_sentiments: [],
  }));

  const selectedSegment = selectedSegmentIndex !== null ? sentimentSegments[selectedSegmentIndex] : null;

  // Calculate sentiment summary
  const sentimentCounts = {
    positive: sentimentSegments.filter((s) => s.sentiment_label === "positive").length,
    negative: sentimentSegments.filter((s) => s.sentiment_label === "negative").length,
    neutral: sentimentSegments.filter((s) => s.sentiment_label === "neutral").length,
  };
  const totalSegments = sentimentSegments.length;
  const sentimentPercentages = {
    positive: totalSegments > 0 ? Math.round((sentimentCounts.positive / totalSegments) * 100) : 0,
    negative: totalSegments > 0 ? Math.round((sentimentCounts.negative / totalSegments) * 100) : 0,
    neutral: totalSegments > 0 ? Math.round((sentimentCounts.neutral / totalSegments) * 100) : 0,
  };

  // Determine overall mood summary
  const getMoodSummary = () => {
    if (sentimentPercentages.positive > 60)
      return "😊 Predominantly positive - Great alignment and enthusiasm";
    if (sentimentPercentages.negative > 40)
      return "😟 Notable concerns and conflicts detected";
    if (sentimentPercentages.positive > sentimentPercentages.negative + 10)
      return "😊 Mostly positive with some concerns";
    return "😐 Balanced discussion";
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-4">
      <SentimentSegmentModal
        segment={selectedSegment}
        isOpen={showSegmentModal}
        onClose={() => setShowSegmentModal(false)}
      />
      {/* File Header */}
      <div className="flex items-center justify-between mb-6 pb-4 border-b">
        <div className="flex-1">
          <h3 className="font-semibold text-lg text-gray-900">{data.file_name}</h3>
          <p className="text-sm text-gray-500 mt-1">
            <strong>Meeting Date:</strong> {data.date}
          </p>
          <p className="text-sm text-gray-700 mt-2">
            <strong>Project Title:</strong> {data.title}
          </p>
        </div>
      </div>

      {/* Summary */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-900 mb-2">Summary</h4>
        <p className="text-gray-700">{data.abstractive_summary}</p>
      </div>

      {/* Sentiment Analysis Section */}
      {sentimentSegments.length > 0 && (
        <div className="mb-8 pb-8 border-b">
          <div className="mb-4">
            <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              {getMoodSummary()}
            </h4>
            <div className="grid grid-cols-3 gap-2 mb-4">
              <div className="bg-green-50 p-3 rounded-lg text-center">
                <p className="text-2xl font-bold text-green-600">{sentimentPercentages.positive}%</p>
                <p className="text-xs text-gray-600">Positive ({sentimentCounts.positive})</p>
              </div>
              <div className="bg-amber-50 p-3 rounded-lg text-center">
                <p className="text-2xl font-bold text-amber-600">{sentimentPercentages.neutral}%</p>
                <p className="text-xs text-gray-600">Neutral ({sentimentCounts.neutral})</p>
              </div>
              <div className="bg-red-50 p-3 rounded-lg text-center">
                <p className="text-2xl font-bold text-red-600">{sentimentPercentages.negative}%</p>
                <p className="text-xs text-gray-600">Negative ({sentimentCounts.negative})</p>
              </div>
            </div>
          </div>

          {/* Timeline */}
          <div className="mb-6">
            <SentimentTimeline
              segments={sentimentSegments}
              onSegmentClick={(idx) => {
                setSelectedSegmentIndex(idx);
                setShowSegmentModal(true);
              }}
            />
          </div>

          {/* Speaker Breakdown */}
          <SpeakerSentimentBreakdown segments={sentimentSegments} />
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-blue-50 p-4 rounded-lg">
          <p className="text-sm text-gray-600 mb-1">Total Words</p>
          <p className="text-2xl font-bold text-blue-600">{data.word_count}</p>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <p className="text-sm text-gray-600 mb-1">Number of Speakers</p>
          <p className="text-2xl font-bold text-green-600">{data.speakers}</p>
        </div>
      </div>

      {/* Storage Path */}
      {data.stored_path && (
        <div className="mb-6 p-3 bg-gray-100 rounded-lg text-xs text-gray-600 break-words">
          <strong>Stored at:</strong> {data.stored_path}
        </div>
      )}

      {/* Speakers List */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-900 mb-3">Speakers</h4>
        <div className="flex flex-wrap gap-2">
          {data.unique_speakers.map((speaker, idx) => (
            <span
              key={idx}
              className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium"
            >
              {speaker}
            </span>
          ))}
        </div>
      </div>

      {/* Decisions Table */}
      {data.decisions && data.decisions.length > 0 && (
        <div className="mb-6">
          <h4 className="font-semibold text-gray-900 mb-3">Decisions</h4>
          <div className="overflow-x-auto border rounded-lg">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">#</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Decision</th>
                </tr>
              </thead>
              <tbody>
                {data.decisions.map((decision, idx) => (
                  <tr key={idx} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-600 font-medium">{idx + 1}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{decision}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Action Items Table */}
      {data.action_items && data.action_items.length > 0 && (
        <div className="mb-6">
          <h4 className="font-semibold text-gray-900 mb-3">Action Items</h4>
          <div className="overflow-x-auto border rounded-lg">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Task</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Owner</th>
                </tr>
              </thead>
              <tbody>
                {data.action_items.map((item, idx) => (
                  <tr key={idx} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-700">{item.task}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded text-xs font-medium">
                        {item.owner}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Export Buttons */}
      <div className="flex gap-3 mt-6">
        <button
          onClick={() => exportToCSV(data)}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium"
        >
          Export CSV
        </button>
        <button
          onClick={() => exportToPDF(data)}
          className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition text-sm font-medium"
        >
          Export PDF
        </button>
      </div>
    </div>
  );
}
