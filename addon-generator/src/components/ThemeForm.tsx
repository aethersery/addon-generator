// Theme Input Form Component
'use client';

import { useState } from 'react';
import type { ResearchRequest, Edition } from './types';
import { Card, CardContent, CardHeader, CardTitle, Button, Input, Textarea, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Label, Switch } from '@/components/ui';

interface ThemeFormProps {
  onSubmit: (data: ResearchRequest) => void;
  isLoading: boolean;
  defaultValues?: Partial<ResearchRequest>;
}

const EDITIONS: { value: Edition; label: string; description: string }[] = [
  { value: 'bedrock', label: 'Bedrock (26.40+)', description: 'MCPE, Windows 10, Console, Mobile' },
  { value: 'java', label: 'Java Edition', description: 'PC/Mac/Linux (Fabric/Forge)' },
  { value: 'both', label: 'Ambas', description: 'Gera para Bedrock e Java' },
];

const STYLES = [
  { value: 'vanilla', label: 'Vanilla', description: 'Estilo padrão do Minecraft' },
  { value: 'rtx', label: 'RTX/PBR', description: 'Texturas PBR completas (normal, roughness, metallic)' },
  { value: 'medieval', label: 'Medieval', description: 'Estilo medieval/fantasia' },
  { value: 'anime', label: 'Anime/Cel-shaded', description: 'Estilo anime com cel-shading' },
  { value: 'modern', label: 'Moderno', description: 'Estilo moderno/realista' },
];

const RESOLUTIONS = [16, 32, 64, 128, 256];

const POPULAR_THEMES = [
  'Shadow Slave',
  'Solo Leveling',
  'Naruto',
  'One Piece',
  'Attack on Titan',
  'Demon Slayer',
  'Jujutsu Kaisen',
  'Elden Ring',
  'The Witcher',
  'Lord of the Rings',
  'Harry Potter',
  'Game of Thrones',
  'Dragon Ball',
  'Bleach',
  'Chainsaw Man',
  'Overlord',
  'Re:Zero',
  'Mushoku Tensei',
  'The Beginning After The End',
  'Custom...',
];

export function ThemeForm({ onSubmit, isLoading, defaultValues }: ThemeFormProps) {
  const [formData, setFormData] = useState<ResearchRequest>({
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
    ...defaultValues,
  });

  const [selectedTheme, setSelectedTheme] = useState('');

  const handleChange = (field: keyof ResearchRequest, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleThemeSelect = (theme: string) => {
    setSelectedTheme(theme);
    if (theme !== 'Custom...') {
      handleChange('theme', theme);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.theme.trim()) {
      alert('Por favor, selecione ou digite um tema');
      return;
    }
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-2xl">🎮</span>
            Configurar Addon
          </CardTitle>
          <p className="text-muted-foreground">
            Descreva o universo que você quer transformar em addon Minecraft
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Theme Selection */}
          <div>
            <Label className="block text-sm font-medium mb-2">
              Universo / Tema <span className="text-red-500">*</span>
            </Label>
            <div className="flex flex-wrap gap-2 mb-3">
              {POPULAR_THEMES.map((theme) => (
                <button
                  key={theme}
                  type="button"
                  onClick={() => handleThemeSelect(theme)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                    selectedTheme === theme || formData.theme === theme
                      ? 'bg-primary text-primary-foreground shadow-md'
                      : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                  }`}
                >
                  {theme}
                </button>
              ))}
            </div>
            <Input
              placeholder="Ou digite seu próprio tema (ex: 'Minha Light Novel favorita')"
              value={formData.theme}
              onChange={(e) => {
                setSelectedTheme('Custom...');
                handleChange('theme', e.target.value);
              }}
              disabled={isLoading}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Exemplos: animes, mangás, light novels, web novels, filmes, séries, jogos, livros
            </p>
          </div>

          {/* Description */}
          <div>
            <Label className="block text-sm font-medium mb-2">
              Descrição Adicional (Opcional)
            </Label>
            <Textarea
              placeholder="Detalhes específicos: foque em certos personagens, arcs, mecânicas, itens especiais, etc."
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              rows={3}
              disabled={isLoading}
            />
          </div>

          {/* Configuration Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* MC Version */}
            <div>
              <Label className="block text-sm font-medium mb-1">Versão Minecraft</Label>
              <Input
                value={formData.mc_version}
                onChange={(e) => handleChange('mc_version', e.target.value)}
                placeholder="26.40"
                disabled={isLoading}
              />
            </div>

            {/* Edition */}
            <div>
              <Label className="block text-sm font-medium mb-1">Edição</Label>
              <Select value={formData.edition} onValueChange={(v) => handleChange('edition', v as Edition)} disabled={isLoading}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione" />
                </SelectTrigger>
                <SelectContent>
                  {EDITIONS.map((ed) => (
                    <SelectItem key={ed.value} value={ed.value}>
                      <div className="flex flex-col">
                        <span>{ed.label}</span>
                        <span className="text-xs text-muted-foreground">{ed.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Style */}
            <div>
              <Label className="block text-sm font-medium mb-1">Estilo Visual</Label>
              <Select value={formData.style_preference} onValueChange={(v) => handleChange('style_preference', v)} disabled={isLoading}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione" />
                </SelectTrigger>
                <SelectContent>
                  {STYLES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      <div className="flex flex-col">
                        <span>{s.label}</span>
                        <span className="text-xs text-muted-foreground">{s.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Resolution */}
            <div>
              <Label className="block text-sm font-medium mb-1">Resolução Texturas</Label>
              <Select value={formData.texture_resolution} onValueChange={(v) => handleChange('texture_resolution', Number(v))} disabled={isLoading}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione" />
                </SelectTrigger>
                <SelectContent>
                  {RESOLUTIONS.map((r) => (
                    <SelectItem key={r} value={r.toString()}>
                      {r}x{r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Feature Toggles */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-2 border-t">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="pbr"
                checked={formData.include_pbr}
                onChange={(e) => handleChange('include_pbr', e.target.checked)}
                disabled={isLoading}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <Label htmlFor="pbr" className="cursor-pointer text-sm">
                Texturas PBR (Normal, Roughness, Metallic)
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="animations"
                checked={formData.include_animations}
                onChange={(e) => handleChange('include_animations', e.target.checked)}
                disabled={isLoading}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <Label htmlFor="animations" className="cursor-pointer text-sm">
                Animações Completas
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="sounds"
                checked={formData.include_sounds}
                onChange={(e) => handleChange('include_sounds', e.target.checked)}
                disabled={isLoading}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <Label htmlFor="sounds" className="cursor-pointer text-sm">
                Sons Personalizados
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="scripts"
                checked={formData.include_scripts}
                onChange={(e) => handleChange('include_scripts', e.target.checked)}
                disabled={isLoading}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <Label htmlFor="scripts" className="cursor-pointer text-sm">
                Scripts TypeScript/JS
              </Label>
            </div>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full py-3 text-lg"
            disabled={isLoading || !formData.theme.trim()}
            size="lg"
          >
            {isLoading ? 'Iniciando...' : '🚀 Iniciar Geração do Addon'}
          </Button>
        </CardContent>
      </Card>
    </form>
  );
}
