import type { Agent } from '../types/agent'
import { getAgentStats } from '../lib/a2a-client'

interface AgentCardProps {
  agent: Agent
}

export function AgentCard({ agent }: AgentCardProps) {
  const stats = getAgentStats(agent)
  const statusColor = {
    online: 'bg-green-500',
    offline: 'bg-red-500',
    unknown: 'bg-gray-500',
  }[agent.status]

  return (
    <a
      href={`/agents/${agent.id}`}
      className="block border rounded-lg p-6 hover:shadow-lg transition-shadow bg-white cursor-pointer"
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-xl font-bold mb-1">{agent.card?.name || agent.name}</h3>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span className={`w-2 h-2 rounded-full ${statusColor}`}></span>
            <span className="capitalize">{agent.status}</span>
          </div>
        </div>
        {agent.card && (
          <div className="text-right text-sm text-gray-600">
            <div>{stats.agents} agents</div>
            <div>{stats.tools} tools</div>
          </div>
        )}
      </div>

      {agent.card && (
        <>
          <p className="text-gray-700 mb-4 line-clamp-2">{agent.card.description}</p>
          <div className="flex gap-2">
            <span className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors">
              View Details
            </span>
            <a
              href={agent.webUrl || agent.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
            >
              Open Service
            </a>
          </div>
        </>
      )}

      {agent.error && (
        <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {agent.error}
        </div>
      )}
    </a>
  )
}
