export type MockProviderStatus = 'operational' | 'degraded' | 'outage' | 'maintenance';
export type MockProviderTier = 'enterprise' | 'startup' | 'open-source';

export interface MockProviderEntity {
  id: string;
  name: string;
  description: string;
  status: MockProviderStatus;
  tier: MockProviderTier;
  modelsCount: number;
  averageLatencyMs: number;
  uptimePercentage: number;
  regions: string[];
  supportedModalities: string[];
  apiEndpoint: string;
  compliance: string[];
  updatedAt: string;
}

export const MOCK_PROVIDERS: MockProviderEntity[] = [
  {
    id: 'prov-001',
    name: 'OpenAI',
    description: 'Leading AI research and deployment company offering powerful foundation models.',
    status: 'operational',
    tier: 'enterprise',
    modelsCount: 12,
    averageLatencyMs: 450,
    uptimePercentage: 99.98,
    regions: ['us-east', 'us-west', 'eu-west', 'ap-northeast'],
    supportedModalities: ['text', 'vision', 'audio', 'embedding'],
    apiEndpoint: 'https://api.openai.com/v1',
    compliance: ['SOC2', 'HIPAA', 'GDPR'],
    updatedAt: new Date().toISOString()
  },
  {
    id: 'prov-002',
    name: 'Anthropic',
    description: 'AI safety and research company developing Constitutional AI models.',
    status: 'operational',
    tier: 'enterprise',
    modelsCount: 6,
    averageLatencyMs: 380,
    uptimePercentage: 99.95,
    regions: ['us-east', 'us-west', 'eu-central'],
    supportedModalities: ['text', 'vision'],
    apiEndpoint: 'https://api.anthropic.com/v1',
    compliance: ['SOC2', 'GDPR'],
    updatedAt: new Date().toISOString()
  },
  {
    id: 'prov-003',
    name: 'Google Cloud AI',
    description: 'Comprehensive suite of Gemini models tightly integrated with GCP.',
    status: 'operational',
    tier: 'enterprise',
    modelsCount: 15,
    averageLatencyMs: 250,
    uptimePercentage: 99.99,
    regions: ['global'],
    supportedModalities: ['text', 'vision', 'audio', 'video', 'code'],
    apiEndpoint: 'https://generativelanguage.googleapis.com',
    compliance: ['SOC2', 'HIPAA', 'GDPR', 'FedRAMP'],
    updatedAt: new Date().toISOString()
  },
  {
    id: 'prov-004',
    name: 'Cohere',
    description: 'Enterprise-focused NLP provider specializing in generation and RAG.',
    status: 'operational',
    tier: 'startup',
    modelsCount: 8,
    averageLatencyMs: 320,
    uptimePercentage: 99.9,
    regions: ['us-east', 'eu-west'],
    supportedModalities: ['text', 'embedding'],
    apiEndpoint: 'https://api.cohere.ai/v1',
    compliance: ['SOC2'],
    updatedAt: new Date().toISOString()
  },
  {
    id: 'prov-005',
    name: 'Hugging Face Inference',
    description: 'Managed inference endpoints for the largest open-source model hub.',
    status: 'degraded',
    tier: 'open-source',
    modelsCount: 100000,
    averageLatencyMs: 850,
    uptimePercentage: 98.5,
    regions: ['us-east', 'eu-west'],
    supportedModalities: ['text', 'vision', 'audio', 'embedding'],
    apiEndpoint: 'https://api-inference.huggingface.co',
    compliance: ['GDPR'],
    updatedAt: new Date().toISOString()
  }
];
