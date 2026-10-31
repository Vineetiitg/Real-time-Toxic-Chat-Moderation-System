import React from 'react';
import { Lock, ShieldAlert, Sparkles, KeyRound, ArrowRight } from 'lucide-react';

interface DeveloperLockGateProps {
  featureName: string;
  onUnlock: () => void;
  onGoSandbox: () => void;
}

export default function DeveloperLockGate({
  featureName,
  onUnlock,
  onGoSandbox,
}: DeveloperLockGateProps) {
  return (
    <div className="flex-1 h-full bg-slate-50 flex items-center justify-center p-6 overflow-y-auto">
      <div className="max-w-md w-full bg-white rounded-3xl p-8 border border-slate-200/80 shadow-xl text-center animate-fade-in">
        {/* Animated Badge Icon */}
        <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-tr from-amber-500/20 via-rose-500/20 to-indigo-500/20 border border-amber-200/50 flex items-center justify-center mb-5 relative">
          <Lock className="w-8 h-8 text-amber-600" />
          <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-500 ring-4 ring-white flex items-center justify-center">
            <span className="w-1.5 h-1.5 rounded-full bg-white" />
          </div>
        </div>

        {/* Heading */}
        <span className="inline-block px-3 py-1 bg-amber-50 text-amber-800 border border-amber-200/60 rounded-full text-xs font-semibold mb-3">
          Restricted Area • Developer Only
        </span>
        <h2 className="text-xl font-bold text-slate-800 mb-2">
          {featureName} is Protected
        </h2>
        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          The <span className="font-semibold text-slate-800">{featureName}</span> involves live
          multi-user WebSocket channels and infrastructure controls, restricted exclusively to{' '}
          <span className="font-semibold text-indigo-600">Vineet (Developer)</span>.
        </p>

        {/* Action Buttons */}
        <div className="flex flex-col gap-3">
          <button
            onClick={onUnlock}
            className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-xl shadow-md shadow-indigo-600/20 flex items-center justify-center gap-2 transition-all active:scale-95"
          >
            <KeyRound className="w-4 h-4" />
            Enter Developer PIN to Unlock
          </button>

          <button
            onClick={onGoSandbox}
            className="w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-sm rounded-xl flex items-center justify-center gap-2 transition-all"
          >
            <Sparkles className="w-4 h-4 text-emerald-600" />
            Try Public Model Sandbox
            <ArrowRight className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {/* Information note for guests */}
        <div className="mt-6 pt-5 border-t border-slate-100 text-left">
          <div className="flex items-start gap-2.5 text-xs text-slate-500">
            <ShieldAlert className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <span>
              Recruiters and evaluators can freely test real-time Hinglish toxicity classification
              and Gemini streaming detoxification in the <strong>Model Sandbox</strong>.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

