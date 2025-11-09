/**
 * A2A Agent Types
 * Based on the A2A protocol specification
 */

export interface AgentSkill {
  id: string
  name: string
  description: string
  tags: string[]
}

export interface AgentCard {
  name: string
  description: string
  url: string
  version: string
  protocolVersion: string
  capabilities: Record<string, unknown>
  skills: AgentSkill[]
  defaultInputModes: string[]
  defaultOutputModes: string[]
  preferredTransport: string
  supportsAuthenticatedExtendedCard: boolean
}

export interface Agent {
  id: string
  name: string
  url: string  // A2A URL
  webUrl?: string  // Web UI URL (for user to visit)
  status: 'online' | 'offline' | 'unknown'
  card?: AgentCard
  error?: string
}

export interface AgentMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export interface ChatSession {
  id: string
  agentId?: string
  messages: AgentMessage[]
  createdAt: Date
}
