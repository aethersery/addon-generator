// Main Page - Addon Generator
'use client';

import { useState } from 'react';
import { api, type ResearchRequest, type GenerateResponse } from '@/lib/api';
import { ThemeForm } from '@/components/ThemeForm';
import { ProgressDisplay } from '@/components/ProgressDisplay';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AlertCircle, Info, Sparkles, Zap, Brain, Box, Github } from 'lucide-react';

export default function Home() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [generationResult, setGenerationResult] = useState<GenerateResponse | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState<'generate' | 'status' | 'about'>('generate');

  const handleGenerate = async (data: ResearchRequest) => {
    setIsGenerating(true);
    setJobId(null);
    setGenerationResult(null);
    setActiveTab('status');

    try {
      const result = await api.generateAddon(data);
      setJobId(result.job_id);
      setGenerationResult(result);
    } catch (error: any) {
      console.error('Generation failed:', error);
      alert(`Erro ao iniciar geração: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleResearchOnly = async (data: ResearchRequest) => {
    setIsGenerating(true);
    setJobId(null);
    setGenerationResult(null);
    setActiveTab('status');

    try {
      const result = await api.researchTheme(data);
      setJobId(result.job_id);
      setGenerationResult({ job_id: result.job_id, status: 'researching', message: result.message });
    } catch (error: any) {
      console.error('Research failed:', error);
      alert(`Erro ao iniciar pesquisa: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  if (jobId) {
    return (
      <div className="min-h-screen bg-background">
        {/* Header */}
        <header className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-50">
          <div className="container mx-auto px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🎮</span>
              <h1 className="text-xl font-bold">Addon Generator</h1>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => { setJobId(null); setActiveTab('generate'); }}>
                Nova Geração
              </Button>
            </div>
          </div>
        </header>

        {/* Progress Display */}
        <main className="container mx-auto px-4 py-6 max-w-4xl">
          <ProgressDisplay
            jobId={jobId}
            onComplete={(result) => {
              console.log('Generation completed:', result);
            }}
            onError={(error) => {
              console.error('Generation error:', error);
            }}
          />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🎮</span>
            <h1 className="text-xl font-bold">Addon Generator</h1>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <Github className="h-4 w-4" />
              GitHub
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="generate">
              <Sparkles className="h-4 w-4 mr-2" />
              Gerar Addon
            </TabsTrigger>
            <TabsTrigger value="status">
              <Zap className="h-4 w-4 mr-2" />
              Status
            </TabsTrigger>
            <TabsTrigger value="about">
              <Info className="h-4 w-4 mr-2" />
              Sobre
            </TabsTrigger>
          </TabsList>

          <TabsContent value="generate" className="space-y-6">
            <div className="text-center mb-4">
              <h2 className="text-2xl font-bold mb-2">Crie Addons Profissionais com IA</h2>
              <p className="text-muted-foreground max-w-2xl mx-auto">
                Transforme qualquer universo (animes, light novels, web novels, filmes, séries, jogos, livros) 
                em um addon completo para Minecraft Bedrock 26.40+ e Java Edition.
              </p>
            </div>

            <ThemeForm
              onSubmit={handleGenerate}
              isLoading={isGenerating}
            />

            <div className="flex gap-3 justify-center">
              <Button
                variant="outline"
                onClick={() => handleResearchOnly({
                  theme: '',
                  description: '',
                  mc_version: '26.40',
                  edition: 'bedrock',
                  style_preference: 'vanilla',
                  texture_resolution: 64,
                  include_pbr: true,
                  include_animations: true,
                  include_sounds: false,
                  include_scripts: true,
                })}
                disabled={isGenerating}
                size="lg"
              >
                <Brain className="h-4 w-4 mr-2" />
                Apenas Pesquisar Lore
              </Button>
            </div>

            {/* Features */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
              <FeatureCard
                icon={<Brain className="h-6 w-6" />}
                title="24 Agentes IA Especializados"
                description="Cada agente cuida de uma parte: entities, itens, blocos, scripts, modelos 3D, texturas, animações, sons, validação e empacotamento."
              />
              <FeatureCard
                icon={<Zap className="h-6 w-6" />}
                title="Orquestração Inteligente"
                description="LangGraph com roteamento dinâmico entre OpenRouter (GPT-4o, Claude, DeepSeek), Groq, Together AI, Google Gemini e modelos locais."
              />
              <FeatureCard
                icon={<Box className="h-6 w-6" />}
                title="100% Grátis (Free Tier)"
                description="Roda totalmente em free tiers: Groq, Together AI, Google AI Studio, OpenRouter (modelos grátis), Hunyuan3D, Tripo3D, FLUX."
              />
            </div>
          </TabsContent>

          <TabsContent value="status" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Monitorar Geração</CardTitle>
              </CardHeader>
              <CardContent className="text-center py-8">
                <p className="text-muted-foreground mb-4">
                  Inicie uma geração na aba "Gerar Addon" para acompanhar o progresso em tempo real aqui.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <StatCard label="Agentes" value="24" description="Especializados" />
                  <StatCard label="APIs Gratuitas" value="15+" description="Provedores" />
                  <StatCard label="Versão MC" value="26.40+" description="Bedrock/Java" />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="about" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Como Funciona</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <StepCard
                  number="1"
                  title="Pesquisa de Lore"
                  description="O Theme Researcher usa LLMs com grande contexto (Gemini 1.5 Pro, GPT-4o, Claude 3.5) para pesquisar profundamente o universo, extraindo entities, itens, blocos, biomas e mecânicas."
                />
                <StepCard
                  number="2"
                  title="Planejamento Arquitetural"
                  description="O Project Architect analisa a pesquisa e cria um plano mestre detalhado com dependências, ordem de geração, paralelos e estimativas de tokens/tempo."
                />
                <StepCard
                  number="3"
                  title="Geração Paralela (Fan-out)"
                  description="Behavior Pack (entities, itens, blocos, scripts, loot, spawn, recipes) e Resource Pack (modelos 3D via Hunyuan3D/Tripo3D, texturas via FLUX, animações, particles, sons) gerados em paralelo."
                />
                <StepCard
                  number="4"
                  title="Validação e Testes"
                  description="Validação contra bedrock-json-schemas, auto-correção de erros, teste no Bedrock Dedicated Server headless, empacotamento em .mcaddon/.mcpack."
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>APIs Gratuitas Utilizadas</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  <ProviderCard name="Groq" models="Llama 3.3 70B, 8B, Mixtral" free="14.4k req/dia" best="Código/JSON rápido" />
                  <ProviderCard name="Together AI" models="Llama 405B, DeepSeek-Coder, FLUX" free="Generoso" best="Modelos grandes, Imagens" />
                  <ProviderCard name="Google AI Studio" models="Gemini 1.5 Flash/Pro" free="1.5M tokens/dia" best="Contexto 1M tokens" />
                  <ProviderCard name="OpenRouter" models="GPT-4o, Claude 3.5, DeepSeek, +100" free="Créditos diários" best="Gateway universal" />
                  <ProviderCard name="Hunyuan3D" models="Text-to-3D, Image-to-3D" free="Free tier" best="Modelos 3D com PBR" />
                  <ProviderCard name="Tripo3D" models="Text-to-3D, Image-to-3D" free="Free tier" best="Modelos 3D rápidos" />
                </div>
              </CardContent>
            </Card>

            <Card className="border-yellow-500/50 bg-yellow-50 dark:bg-yellow-900/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-yellow-500" />
                  Aviso Legal (Importante)
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <p>Esta ferramenta gera addons para <strong>uso pessoal e educacional</strong>.</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Não distribuímos, hospedamos ou vendemos addons de IPs protegidos</li>
                  <li>Texturas/modelos são gerados por IA (derivados), não copiados</li>
                  <li>Use por sua conta e risco — respeite direitos autorais</li>
                  <li>Não publique em Marketplace, CurseForge, Modrinth sem permissão do detentor dos direitos</li>
                </ul>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="border-t py-6 mt-12">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>Addon Generator - Powered by AI Orchestration (LangGraph + Free LLMs)</p>
          <p className="mt-1">Para Minecraft Bedrock 26.40+ e Java Edition</p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-primary/10 rounded-lg text-primary">{icon}</div>
          <div>
            <h3 className="font-semibold">{title}</h3>
            <p className="text-sm text-muted-foreground mt-1">{description}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StatCard({ label, value, description }: { label: string; value: string; description: string }) {
  return (
    <div className="p-4 bg-muted/50 rounded-lg text-center">
      <div className="text-3xl font-bold">{value}</div>
      <div className="text-muted-foreground">{label}</div>
      <div className="text-xs text-muted-foreground">{description}</div>
    </div>
  );
}

function StepCard({ number, title, description }: { number: string; title: string; description: string }) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-sm">
        {number}
      </div>
      <div>
        <h4 className="font-semibold">{title}</h4>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

function ProviderCard({ name, models, free, best }: { name: string; models: string; free: string; best: string }) {
  return (
    <div className="p-4 bg-muted/50 rounded-lg border">
      <h4 className="font-semibold text-primary">{name}</h4>
      <p className="text-xs text-muted-foreground mt-1"><strong>Modelos:</strong> {models}</p>
      <p className="text-xs text-muted-foreground"><strong>Free Tier:</strong> {free}</p>
      <p className="text-xs text-green-600 dark:text-green-400"><strong>Melhor para:</strong> {best}</p>
    </div>
  );
}
