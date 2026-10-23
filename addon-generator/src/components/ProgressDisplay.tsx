// Progress Display Component
'use client';

import { useEffect, useState } from 'react';
import { api, type StatusResponse, type ResultResponse, formatStatus, getStatusColorClass } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Download, X, RefreshCw, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';

interface ProgressDisplayProps {
  jobId: string;
  onComplete?: (result: ResultResponse) => void;
  onError?: (error: string) => void;
  pollInterval?: number;
}

const STEP_ORDER = [
  'theme_researcher',
  'project_architect',
  'entity_designer',
  'item_designer',
  'block_designer',
  'behavior_scripter',
  'loot_table_designer',
  'spawn_rule_designer',
  'recipe_designer',
  'manifest_builder_bp',
  'modeler',
  'texture_artist',
  'animator',
  'anim_controller',
  'render_controller',
  'particle_designer',
  'sound_designer',
  'ui_designer',
  'manifest_builder_rp',
  'schema_validator',
  'packager',
  'automated_tester',
  'doc_generator',
];

const STEP_LABELS: Record<string, string> = {
  theme_researcher: '🔍 Pesquisando Lore do Universo',
  project_architect: '📋 Criando Plano Mestre',
  entity_designer: '👾 Projetando Entities',
  item_designer: '⚔️ Projetando Itens',
  block_designer: '🧱 Projetando Blocos',
  behavior_scripter: '📝 Escrevendo Scripts Comportamento',
  loot_table_designer: '🎁 Criando Loot Tables',
  spawn_rule_designer: '🌍 Configurando Spawn Rules',
  recipe_designer: '🔨 Criando Receitas',
  manifest_builder_bp: '📦 Manifest Behavior Pack',
  modeler: '📐 Gerando Modelos 3D',
  texture_artist: '🎨 Gerando Texturas',
  animator: '🎬 Criando Animações',
  anim_controller: '🎮 Controllers de Animação',
  render_controller: '🖼️ Render Controllers',
  particle_designer: '✨ Partículas',
  sound_designer: '🔊 Sons',
  ui_designer: '🖥️ Interface/UI',
  manifest_builder_rp: '📦 Manifest Resource Pack',
  schema_validator: '✅ Validação de Schemas',
  packager: '📦 Empacotando .mcaddon',
  automated_tester: '🧪 Testando no BDS',
  doc_generator: '📚 Gerando Documentação',
};

export function ProgressDisplay({ jobId, onComplete, onError, pollInterval = 2000 }: ProgressDisplayProps) {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [result, setResult] = useState<ResultResponse | null>(null);
  const [isPolling, setIsPolling] = useState(true);
  const [showLogs, setShowLogs] = useState(false);

  // Poll for status updates
  useEffect(() => {
    let interval: NodeJS.Timeout;
    let mounted = true;

    const fetchStatus = async () => {
      try {
        const data = await api.getStatus(jobId);
        if (!mounted) return;
        setStatus(data);

        if (data.status === 'completed' && !result) {
          try {
            const resultData = await api.getResult(jobId);
            if (mounted) {
              setResult(resultData);
              setIsPolling(false);
              onComplete?.(resultData);
            }
          } catch (e) {
            console.error('Failed to get result:', e);
          }
        } else if (data.status === 'failed') {
          if (mounted) {
            setIsPolling(false);
            onError?.(data.error_message || 'Generation failed');
          }
        }
      } catch (e) {
        console.error('Status poll error:', e);
      }
    };

    fetchStatus();
    interval = setInterval(fetchStatus, pollInterval);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [jobId, pollInterval, result, onComplete, onError]);

  if (!status) {
    return (
      <Card className="w-full">
        <CardContent className="py-12 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Conectando ao servidor...</p>
        </CardContent>
      </Card>
    );
  }

  const { progress, current_step, step_details, logs, error_message } = status;
  const statusInfo = formatStatus(status.status);

  // Calculate step progress
  const currentStepIndex = STEP_ORDER.indexOf(current_step);
  const completedSteps = currentStepIndex >= 0 ? currentStepIndex : 0;

  return (
    <div className="space-y-4 w-full">
      {/* Status Header */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl">{statusInfo.icon}</span>
              <div>
                <h3 className="text-lg font-semibold">{statusInfo.label}</h3>
                <p className="text-sm text-muted-foreground">
                  {step_details || current_step ? STEP_LABELS[current_step] || current_step : 'Aguardando...'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={getStatusColorClass(statusInfo.color)} variant="secondary">
                {Math.round(progress * 100)}%
              </Badge>
              {status.status === 'failed' && (
                <Badge variant="destructive">Falhou</Badge>
              )}
              {status.status === 'completed' && (
                <Badge variant="default" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                  Concluído
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <Progress value={progress * 100} className="h-3" />
          
          {/* Step Progress Indicators */}
          <div className="mt-4 space-y-1">
            {STEP_ORDER.map((step, index) => {
              const isCompleted = index < completedSteps;
              const isCurrent = index === completedSteps && status.status !== 'completed' && status.status !== 'failed';
              const isUpcoming = index > completedSteps;
              
              return (
                <div
                  key={step}
                  className={`flex items-center gap-2 text-xs transition-colors ${
                    isCompleted ? 'text-green-600 dark:text-green-400' :
                    isCurrent ? 'text-primary font-medium' :
                    'text-muted-foreground'
                  }`}
                >
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                    isCompleted ? 'bg-green-500 text-white' :
                    isCurrent ? 'bg-primary text-white animate-pulse' :
                    'bg-muted'
                  }`}>
                    {isCompleted ? '✓' : index + 1}
                  </span>
                  <span className="flex-1 truncate">{STEP_LABELS[step] || step}</span>
                  {isCurrent && <Loader2 className="h-3 w-3 animate-spin text-primary" />}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Error Message */}
      {error_message && (
        <Card className="border-red-500/50 bg-red-50 dark:bg-red-900/20">
          <CardContent className="flex items-center gap-2 p-4">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <p className="text-red-700 dark:text-red-300 text-sm">{error_message}</p>
          </CardContent>
        </Card>
      )}

      {/* Logs */}
      <Card>
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <CardTitle className="text-base">Logs de Execução</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowLogs(!showLogs)}
            className="h-8"
          >
            {showLogs ? 'Ocultar' : 'Mostrar'} ({logs.length})
          </Button>
        </CardHeader>
        {showLogs && (
          <CardContent className="pt-0">
            <ScrollArea className="h-64">
              <div className="font-mono text-xs text-muted-foreground space-y-1 p-2">
                {logs.slice(-50).map((log, i) => (
                  <div key={i} className="border-l-2 border-muted pl-2 py-0.5">
                    {log}
                  </div>
                ))}
                {logs.length === 0 && (
                  <div className="text-center py-4 text-muted-foreground">Nenhum log ainda...</div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        )}
      </Card>

      {/* Download Buttons (when completed) */}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              Addon Gerado com Sucesso!
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {result.mcaddon_path && (
                <Button
                  onClick={() => api.triggerDownload(jobId, 'mcaddon', `${result.theme.replace(/\s+/g, '_')}.mcaddon`)}
                  className="h-14"
                >
                  <Download className="h-5 w-5 mr-2" />
                  <div className="text-left">
                    <div className="font-medium">.mcaddon (Completo)</div>
                    <div className="text-xs text-muted-foreground">Behavior + Resource Pack</div>
                  </div>
                </Button>
              )}
              {result.bp_zip_path && (
                <Button
                  variant="outline"
                  onClick={() => api.triggerDownload(jobId, 'bp', `${result.theme.replace(/\s+/g, '_')}_BP.mcpack`)}
                  className="h-14"
                >
                  <Download className="h-5 w-5 mr-2" />
                  <div className="text-left">
                    <div className="font-medium">Behavior Pack</div>
                    <div className="text-xs text-muted-foreground">.mcpack</div>
                  </div>
                </Button>
              )}
              {result.rp_zip_path && (
                <Button
                  variant="outline"
                  onClick={() => api.triggerDownload(jobId, 'rp', `${result.theme.replace(/\s+/g, '_')}_RP.mcpack`)}
                  className="h-14"
                >
                  <Download className="h-5 w-5 mr-2" />
                  <div className="text-left">
                    <div className="font-medium">Resource Pack</div>
                    <div className="text-xs text-muted-foreground">.mcpack</div>
                  </div>
                </Button>
              )}
            </div>

            <Separator />

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="p-3 bg-muted/50 rounded-lg">
                <div className="text-muted-foreground">Entities</div>
                <div className="font-bold text-xl">{result.assets_count.bp_entities}</div>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg">
                <div className="text-muted-foreground">Itens</div>
                <div className="font-bold text-xl">{result.assets_count.bp_items}</div>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg">
                <div className="text-muted-foreground">Blocos</div>
                <div className="font-bold text-xl">{result.assets_count.bp_blocks}</div>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg">
                <div className="text-muted-foreground">Scripts</div>
                <div className="font-bold text-xl">{result.assets_count.bp_scripts}</div>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg">
                <div className="text-muted-foreground">Modelos 3D</div>
                <div className="font-bold text-xl">{result.assets_count.rp_models}</div>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg">
                <div className="text-muted-foreground">Texturas</div>
                <div className="font-bold text-xl">{result.assets_count.rp_textures}</div>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg">
                <div className="text-muted-foreground">Animações</div>
                <div className="font-bold text-xl">{result.assets_count.rp_animations}</div>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg">
                <div className="text-muted-foreground">Tempo Total</div>
                <div className="font-bold text-xl">{formatTime(result.generation_time_seconds)}</div>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm pt-2 border-t">
              <div className="p-3 bg-muted/50 rounded-lg">
                <div className="text-muted-foreground">Tokens Usados</div>
                <div className="font-bold text-xl">{result.tokens_used.toLocaleString()}</div>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg">
                <div className="text-muted-foreground">Chamadas API</div>
                <div className="font-bold text-xl">{result.api_calls}</div>
              </div>
              <div className="p-3 bg-muted/50 rounded-lg">
                <div className="text-muted-foreground">Custo Estimado</div>
                <div className="font-bold text-xl">${result.estimated_cost_usd.toFixed(4)}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Retry Button (when failed) */}
      {status.status === 'failed' && !result && (
        <div className="text-center">
          <Button variant="outline" onClick={() => window.location.reload()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Tentar Novamente
          </Button>
        </div>
      )}
    </div>
  );
}
