'use client';

import { motion } from 'motion/react';
import { useState } from 'react';
import {
  Play, Pause, RotateCcw, CheckCircle2, XCircle,
  ArrowRight, Zap, Cpu, Clock, Activity,
} from 'lucide-react';

const pipelineSteps = [
  { id: 'ingest', label: 'Zwiad BZP', icon: Zap, tier: 1 },
  { id: 'analyze', label: 'Analiza dokumentów', icon: Cpu, tier: 1 },
  { id: 'engine_run', label: 'Silnik decyzyjny', icon: Activity, tier: 2 },
  { id: 'estimate', label: 'Kosztorys', icon: Cpu, tier: 2 },
  { id: 'decide', label: 'Go / No-go', icon: CheckCircle2, tier: 2 },
  { id: 'contract', label: 'Kontrakt', icon: CheckCircle2, tier: 3 },
  { id: 'optimize', label: 'Logistyka OR-Tools', icon: Cpu, tier: 3 },
  { id: 'plan', label: 'Plan dzienny', icon: Clock, tier: 3 },
  { id: 'dispatch', label: 'Dispatch (gated)', icon: Play, tier: 3 },
];

const mockRuns = [
  {
    id: 'run-001',
    agent: 'pipeline_supervisor',
    status: 'succeeded',
    started_at: '2026-07-01 09:00:23',
    finished_at: '2026-07-01 09:01:45',
    tokens_in: 2400,
    tokens_out: 890,
    cost_pln: 0.12,
    steps_completed: 9,
  },
  {
    id: 'run-002',
    agent: 'pipeline_supervisor',
    status: 'running',
    started_at: '2026-07-01 10:30:00',
    finished_at: null,
    tokens_in: 1200,
    tokens_out: 450,
    cost_pln: 0.06,
    steps_completed: 5,
  },
  {
    id: 'run-003',
    agent: 'pipeline_supervisor',
    status: 'failed',
    started_at: '2026-06-30 15:00:00',
    finished_at: '2026-06-30 15:00:34',
    tokens_in: 800,
    tokens_out: 100,
    cost_pln: 0.02,
    steps_completed: 2,
    error: 'ingest: BZP API timeout (30s)',
  },
];

export function PipelinePage() {
  const [activeRun, setActiveRun] = useState(mockRuns[0]);
  const currentStep = activeRun.steps_completed;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="p-8 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-earth-50">Pipeline Supervisor</h1>
          <p className="text-earth-400 mt-1">
            LangGraph — automatyczny pipeline M1→M2→M3
          </p>
        </div>
        <button className="px-4 py-2 rounded-lg bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 font-medium transition-colors flex items-center gap-2">
          <Play className="w-4 h-4" />
          Uruchom pipeline
        </button>
      </div>

      {/* Pipeline visualization */}
      <div className="p-6 rounded-xl bg-earth-900/60 border border-earth-800">
        <h2 className="text-earth-200 font-medium mb-4">Przebieg pipeline'u</h2>
        <div className="flex items-center gap-1 overflow-x-auto pb-2">
          {pipelineSteps.map((step, i) => {
            const Icon = step.icon;
            const isCompleted = i < currentStep;
            const isCurrent = i === currentStep;
            return (
              <div key={step.id} className="flex items-center">
                <div className={`flex flex-col items-center min-w-[80px] ${
                  isCompleted ? 'opacity-100' : isCurrent ? 'opacity-100' : 'opacity-40'
                }`}>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    isCompleted
                      ? 'bg-green-500/20 border-2 border-green-500'
                      : isCurrent
                      ? 'bg-amber-500/20 border-2 border-amber-500 animate-pulse'
                      : 'bg-earth-800 border-2 border-earth-700'
                  }`}>
                    {isCompleted ? (
                      <CheckCircle2 className="w-5 h-5 text-green-400" />
                    ) : (
                      <Icon className={`w-5 h-5 ${isCurrent ? 'text-amber-400' : 'text-earth-500'}`} />
                    )}
                  </div>
                  <span className={`text-[10px] mt-1.5 text-center leading-tight ${
                    isCompleted ? 'text-green-400' : isCurrent ? 'text-amber-400' : 'text-earth-500'
                  }`}>
                    {step.label}
                  </span>
                  <span className="text-[9px] text-earth-600 font-mono">T{step.tier}</span>
                </div>
                {i < pipelineSteps.length - 1 && (
                  <ArrowRight className={`w-3 h-3 mx-0.5 ${
                    isCompleted ? 'text-green-500' : 'text-earth-700'
                  }`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Agent runs */}
      <div className="space-y-3">
        <h2 className="text-earth-200 font-medium">Historia uruchomień</h2>
        {mockRuns.map(run => (
          <div
            key={run.id}
            onClick={() => setActiveRun(run)}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              activeRun.id === run.id
                ? 'bg-earth-900/80 border-amber-500/40'
                : 'bg-earth-900/40 border-earth-800 hover:border-earth-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {run.status === 'succeeded' && <CheckCircle2 className="w-5 h-5 text-green-400" />}
                {run.status === 'running' && <Play className="w-5 h-5 text-amber-400 animate-pulse" />}
                {run.status === 'failed' && <XCircle className="w-5 h-5 text-red-400" />}
                <div>
                  <p className="text-earth-100 font-mono text-sm">{run.id}</p>
                  <p className="text-earth-500 text-xs">{run.started_at}</p>
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <span className="text-earth-400">
                  {run.steps_completed}/{pipelineSteps.length} kroków
                </span>
                <span className="text-earth-400 font-mono">
                  {run.tokens_in + run.tokens_out} tok
                </span>
                <span className="text-amber-400 font-mono">
                  {run.cost_pln.toFixed(2)} PLN
                </span>
                {run.status === 'running' && (
                  <div className="flex gap-1">
                    <button className="p-1 rounded bg-earth-800 hover:bg-earth-700">
                      <Pause className="w-3.5 h-3.5 text-earth-300" />
                    </button>
                    <button className="p-1 rounded bg-earth-800 hover:bg-earth-700">
                      <RotateCcw className="w-3.5 h-3.5 text-earth-300" />
                    </button>
                  </div>
                )}
              </div>
            </div>
            {run.error && (
              <p className="mt-2 text-red-400 text-xs font-mono bg-red-500/10 px-2 py-1 rounded">
                {run.error}
              </p>
            )}
          </div>
        ))}
      </div>
    </motion.div>
  );
}
