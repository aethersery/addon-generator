// API Client for Addon Generator Backend

import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  ResearchRequest,
  GenerationRequest,
  ResearchResponse,
  GenerateResponse,
  StatusResponse,
  ResultResponse,
  ProvidersResponse,
  LoreData,
} from './types';

// Get API base URL from environment or default to localhost
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 300000, // 5 minutes for long generations
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('[API Error]', error.response?.status, error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Health check
  async healthCheck(): Promise<{ status: string; version: string; providers: string[] }> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // List available LLM providers
  async getProviders(): Promise<ProvidersResponse> {
    const response = await this.client.get('/providers');
    return response.data;
  }

  // Start theme research only
  async researchTheme(request: ResearchRequest): Promise<ResearchResponse> {
    const response = await this.client.post<ResearchResponse>('/research', request);
    return response.data;
  }

  // Start full addon generation
  async generateAddon(request: GenerationRequest): Promise<GenerateResponse> {
    const response = await this.client.post<GenerateResponse>('/generate', request);
    return response.data;
  }

  // Get job status
  async getStatus(jobId: string): Promise<StatusResponse> {
    const response = await this.client.get<StatusResponse>(`/status/${jobId}`);
    return response.data;
  }

  // Get job result (when completed)
  async getResult(jobId: string): Promise<ResultResponse> {
    const response = await this.client.get<ResultResponse>(`/result/${jobId}`);
    return response.data;
  }

  // Get job logs
  async getLogs(jobId: string, limit = 100): Promise<{ logs: string[] }> {
    const response = await this.client.get(`/logs/${jobId}?limit=${limit}`);
    return response.data;
  }

  // Download generated file
  async downloadFile(jobId: string, fileType: 'bp' | 'rp' | 'mcaddon'): Promise<Blob> {
    const response = await this.client.get(`/download/${jobId}/${fileType}`, {
      responseType: 'blob',
    });
    return response.data;
  }

  // Trigger file download in browser
  async triggerDownload(jobId: string, fileType: 'bp' | 'rp' | 'mcaddon', filename: string): Promise<void> {
    const blob = await this.downloadFile(jobId, fileType);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  // Refine research with feedback
  async refineResearch(jobId: string, feedback: string, focusAreas: string[] = []): Promise<{ message: string; status: string }> {
    const response = await this.client.post(`/refine/${jobId}`, { feedback, focus_areas: focusAreas });
    return response.data;
  }

  // Delete job
  async deleteJob(jobId: string): Promise<{ message: string }> {
    const response = await this.client.delete(`/jobs/${jobId}`);
    return response.data;
  }
}

// Export singleton instance
export const api = new ApiClient();

// Helper function to format status for display
export function formatStatus(status: string): { label: string; color: string; icon: string } {
  const statusMap: Record<string, { label: string; color: string; icon: string }> = {
    pending: { label: 'Aguardando', color: 'gray', icon: '⏳' },
    researching: { label: 'Pesquisando Lore', color: 'blue', icon: '🔍' },
    planning: { label: 'Planejando', color: 'purple', icon: '📋' },
    generating_bp: { label: 'Gerando Behavior Pack', color: 'green', icon: '⚙️' },
    generating_rp: { label: 'Gerando Resource Pack', color: 'green', icon: '🎨' },
    generating_textures: { label: 'Gerando Texturas', color: 'orange', icon: '🖼️' },
    generating_models: { label: 'Gerando Modelos 3D', color: 'orange', icon: '📦' },
    validating: { label: 'Validando', color: 'yellow', icon: '✅' },
    packaging: { label: 'Empacotando', color: 'indigo', icon: '📦' },
    testing: { label: 'Testando', color: 'cyan', icon: '🧪' },
    completed: { label: 'Concluído', color: 'green', icon: '🎉' },
    failed: { label: 'Falhou', color: 'red', icon: '❌' },
  };
  return statusMap[status] || { label: status, color: 'gray', icon: '❓' };
}

// Helper to get status color class for Tailwind
export function getStatusColorClass(color: string): string {
  const colorClasses: Record<string, string> = {
    gray: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
    blue: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    purple: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    green: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    orange: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    yellow: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    indigo: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
    cyan: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
    red: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  };
  return colorClasses[color] || colorClasses.gray;
}
