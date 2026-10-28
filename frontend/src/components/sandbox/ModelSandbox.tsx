import React, { useState } from 'react';
import {
  Sparkles,
  Zap,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Send,
  Copy,
  Check,
  ArrowRight,
  Globe,
  Gauge,
  Lock,
} from 'lucide-react';
import { API_BASE_URL } from '../../config/env';
import { SeverityBadge } from '../common/Badge';

interface ModelSandboxProps {
  onOpenAuth: () => void;
}

interface ModerationResult {
  isToxic: boolean;
  severity: 'SAFE' | 'LOW' | 'MEDIUM' | 'HIGH';
  detectedLanguage?: string;
  suggestion?: string;
  inferenceTimeMs?: number;
  categories: Record<string, number>;
}

const PRESET_PROMPTS = [
  {
    label: 'Hinglish Abuse',
    type: 'toxic',
    text: 'Bhai tu kitna bekaar insaan hai sharam kar',
  },
  {
    label: 'Hinglish Harassment',
    type: 'toxic',
    text: 'Teri aukaat nahi hai mere samne bolne ki chup baith',
  },
  {
    label: 'Safe English',
    type: 'safe',
    text: "Hey team, let's complete the final release deployment!",
  },
  {
    label: 'English Toxicity',
    type: 'toxic',
    text: 'You are completely useless and should be fired immediately',
  },
  {
    label: 'Safe Hinglish Praise',
    type: 'safe',
    text: 'Bhai project bohot badhiya lag raha hai, congratulations!',
  },
  {
    label: 'Hindi Safe',
    type: 'safe',
    text: 'आज का प्रोजेक्ट प्रेजेंटेशन बहुत अच्छा रहा, धन्यवाद',
  },
];

function getDisplayLanguage(code?: string): string {
  if (!code) return 'English';
  const c = code.toLowerCase();
  if (c === 'hi-en' || c === 'hinglish') return 'Hinglish';
  if (c === 'hi' || c === 'hindi') return 'Hindi';
  if (c === 'en' || c === 'english') return 'English';
  return code;
}

export default function ModelSandbox({ onOpenAuth }: ModelSandboxProps) {
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ModerationResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyzeText = async (textToAnalyze?: string) => {
    const text = (textToAnalyze !== undefined ? textToAnalyze : inputText).trim();
    if (!text) return;

    setIsLoading(true);
    setError(null);
    const startTime = performance.now();

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/moderate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          channel_id: 'sandbox',
          user_id: 'sandbox-guest',
        }),
      });

      const clientLatency = Math.round(performance.now() - startTime);

      if (!res.ok) {
        throw new Error('Analysis service returned an error. Please try again.');
      }

      const data = await res.json();
      setResult({
        isToxic: !!data.is_toxic,
        severity: data.severity || (data.is_toxic ? 'HIGH' : 'SAFE'),
        detectedLanguage: data.detected_language,
        suggestion: data.suggestion,
        inferenceTimeMs: data.inference_time_ms ? Math.round(data.inference_time_ms) : clientLatency,
        categories: data.categories || {},
      });
    } catch (e: any) {
      setError(e.message || 'Failed to analyze text. Please verify server connectivity.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePresetClick = (presetText: string) => {
    setInputText(presetText);
    analyzeText(presetText);
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex-1 h-full bg-slate-50 flex flex-col overflow-y-auto">
      {/* Sandbox Header */}
      <div className="px-6 py-4 bg-white border-b border-slate-200/80 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 bg-indigo-50 text-indigo-600 rounded-lg">
                <Sparkles className="w-5 h-5" />
              </span>
              <h2 className="text-base font-bold text-slate-800">
                Multi-Lingual Toxicity & Safety Sandbox
              </h2>
              <span className="text-[10px] px-2 py-0.5 bg-emerald-100 text-emerald-800 font-bold rounded-full">
                Public Tester
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Test code-mixed Hinglish, Hindi, and English toxicity detection & streaming intent detoxification.
            </p>
          </div>

          <button
            onClick={onOpenAuth}
            className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold border border-slate-200 transition-all"
          >
            <Lock className="w-3.5 h-3.5 text-slate-500" />
            Developer Access (Vineet)
          </button>
        </div>
      </div>

      <div className="p-4 sm:p-6 max-w-4xl w-full mx-auto space-y-6 flex-1">
        {/* Preset Chips */}
        <div>
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-amber-500" />
            Quick Test Prompts (Click to Evaluate)
          </div>
          <div className="flex flex-wrap gap-2">
            {PRESET_PROMPTS.map((preset) => (
              <button
                key={preset.label}
                onClick={() => handlePresetClick(preset.text)}
                className={`text-xs px-3 py-1.5 rounded-xl border transition-all text-left flex items-center gap-1.5 ${
                  preset.type === 'toxic'
                    ? 'bg-rose-50/70 border-rose-200 text-rose-800 hover:bg-rose-100'
                    : 'bg-emerald-50/70 border-emerald-200 text-emerald-800 hover:bg-emerald-100'
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    preset.type === 'toxic' ? 'bg-rose-500' : 'bg-emerald-500'
                  }`}
                />
                <span className="font-semibold">{preset.label}:</span>
                <span className="text-slate-600 truncate max-w-[200px]">{preset.text}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Input Box */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm space-y-3">
          <label className="block text-xs font-bold text-slate-700">
            Custom Message Inspector (Type in Hinglish, English, or Hindi)
          </label>
          <div className="relative">
            <textarea
              rows={3}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  analyzeText();
                }
              }}
              placeholder="e.g. Bhai tu kitna bekaar insaan hai, or Type anything in Hinglish or English..."
              className="w-full p-3.5 text-sm bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all resize-none"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-slate-400">
              Press <kbd className="px-1.5 py-0.5 bg-slate-100 border rounded text-[10px]">Enter</kbd> to analyze
            </span>
            <button
              onClick={() => analyzeText()}
              disabled={isLoading || !inputText.trim()}
              className="btn-primary flex items-center gap-2 py-2 px-4"
            >
              {isLoading ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Evaluating...
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  Analyze Safety
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-500 shrink-0" />
            {error}
          </div>
        )}

        {/* Results Display */}
        {result && (
          <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm space-y-4 animate-fade-in">
            {/* Status Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <SeverityBadge severity={result.severity} />
                <span className="text-xs px-2.5 py-0.5 bg-slate-100 text-slate-700 rounded-full font-medium flex items-center gap-1">
                  <Globe className="w-3 h-3 text-slate-400" />
                  {getDisplayLanguage(result.detectedLanguage)}
                </span>
                {result.inferenceTimeMs !== undefined && (
                  <span className="text-xs px-2.5 py-0.5 bg-indigo-50 text-indigo-700 rounded-full font-mono flex items-center gap-1">
                    <Gauge className="w-3 h-3 text-indigo-500" />
                    {result.inferenceTimeMs}ms
                  </span>
                )}
              </div>

              <div className="text-xs font-semibold">
                {result.isToxic ? (
                  <span className="text-rose-600 flex items-center gap-1">
                    <ShieldAlert className="w-3.5 h-3.5" /> Moderation Action Triggered
                  </span>
                ) : (
                  <span className="text-emerald-600 flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" /> Content Safe for Broadcast
                  </span>
                )}
              </div>
            </div>

            {/* Polite Alternative Card */}
            {result.suggestion && (
              <div className="p-4 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200/80 rounded-xl space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-emerald-800 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                    Intent-Preserving Polite Alternative
                  </span>
                  <button
                    onClick={() => handleCopy(result.suggestion!)}
                    className="flex items-center gap-1 text-[11px] text-emerald-700 hover:text-emerald-900 bg-emerald-100/60 px-2 py-0.5 rounded-lg transition-colors"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" /> Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" /> Copy
                      </>
                    )}
                  </button>
                </div>
                <p className="text-sm font-medium text-emerald-900 leading-relaxed">
                  "{result.suggestion}"
                </p>
              </div>
            )}

            {/* Category Breakdown */}
            {result.categories && Object.keys(result.categories).length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-slate-700 mb-2.5">
                  Multi-Label Toxicity Breakdown
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {Object.entries(result.categories).map(([cat, score]) => {
                    const pct = Math.min(100, Math.round(score * 100));
                    const isHigh = pct >= 40;
                    return (
                      <div
                        key={cat}
                        className="p-2.5 bg-slate-50 rounded-xl border border-slate-100 flex flex-col justify-between"
                      >
                        <div className="flex items-center justify-between text-xs mb-1.5">
                          <span className="capitalize font-medium text-slate-700">
                            {cat.replace(/_/g, ' ')}
                          </span>
                          <span
                            className={`font-mono text-[11px] font-bold ${
                              isHigh ? 'text-rose-600' : 'text-slate-500'
                            }`}
                          >
                            {pct}%
                          </span>
                        </div>
                        <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-300 ${
                              isHigh ? 'bg-rose-500' : 'bg-indigo-500'
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Developer Lock Info Banner */}
        <div className="p-4 bg-indigo-50/60 border border-indigo-100 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-indigo-950">
          <div className="flex items-start gap-2.5">
            <Lock className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-800">
                Are you looking for the Live Moderated Chat or Admin Dashboard?
              </p>
              <p className="text-slate-500 mt-0.5">
                The multi-user real-time chat room and system telemetry dashboard are restricted to developer <strong>Vineet</strong>.
              </p>
            </div>
          </div>
          <button
            onClick={onOpenAuth}
            className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-sm transition-all text-xs"
          >
            Unlock Developer Mode
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
