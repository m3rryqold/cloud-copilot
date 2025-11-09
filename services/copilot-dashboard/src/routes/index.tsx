import { createFileRoute } from '@tanstack/react-router'
import { AGENT_CONFIGS, type AgentConfig } from '../config/agents'

export const Route = createFileRoute('/')({ component: Dashboard })

function Dashboard() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <section className="relative py-8 px-6 text-center overflow-hidden border-b border-slate-700">
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-purple-500/10"></div>
        <div className="relative max-w-5xl mx-auto">
          <div className="flex items-center justify-center mb-3">
            <img src="/logo.svg" alt="Cloud AI Copilots Logo" className="w-16 h-16" />
          </div>
          <h1 className="text-5xl md:text-6xl font-black text-white mb-4">
            <span className="bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              Cloud AI
            </span>{' '}
            <span className="text-gray-300">Copilots</span>
          </h1>
          <p className="text-xl text-gray-300 mb-2">
            Intelligent agents for Kubernetes management and cloud cost optimization
          </p>
          <p className="text-sm text-gray-400">
            Powered by Google Agent Development Kit (ADK) and A2A protocol
          </p>
        </div>
      </section>

      {/* Agents */}
      <section className="py-12 px-6 max-w-7xl mx-auto">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-white mb-2">Available Agents</h2>
          <p className="text-gray-400">{AGENT_CONFIGS.length} AI agents ready to assist</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {AGENT_CONFIGS.map((agent) => (
            <AgentCardStatic key={agent.id} agent={agent} />
          ))}
        </div>
      </section>

      {/* Quick Actions */}
      <section className="py-12 px-6 max-w-7xl mx-auto">
        <div className="bg-slate-800/30 border border-slate-700 rounded-lg p-8">
          <h3 className="text-2xl font-bold text-white mb-4">Quick Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <a
              href={AGENT_CONFIGS.find(a => a.id === 'k8s-copilot')?.webUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-4 bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/50 rounded-lg text-cyan-400 font-semibold transition-colors text-left block"
            >
              <div className="text-sm text-cyan-300 mb-1">Kubernetes</div>
              <div>Check Cluster Health</div>
            </a>
            <a
              href={AGENT_CONFIGS.find(a => a.id === 'cost-copilot')?.webUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-4 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/50 rounded-lg text-blue-400 font-semibold transition-colors text-left block"
            >
              <div className="text-sm text-blue-300 mb-1">Cost Analysis</div>
              <div>Find Idle Resources</div>
            </a>
            <a
              href="/agents/k8s-copilot"
              className="px-6 py-4 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/50 rounded-lg text-purple-400 font-semibold transition-colors text-left block"
            >
              <div className="text-sm text-purple-300 mb-1">Learn More</div>
              <div>View Agent Details</div>
            </a>
          </div>
        </div>
      </section>
    </div>
  )
}

interface AgentCardStaticProps {
  agent: AgentConfig
}

function AgentCardStatic({ agent }: AgentCardStaticProps) {
  return (
    <div className="border border-slate-700 rounded-lg p-6 hover:shadow-lg hover:border-cyan-500/50 transition-all bg-slate-800/50">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-2xl font-bold text-white mb-2">{agent.displayName}</h3>
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            <span>Available</span>
          </div>
        </div>
      </div>

      <p className="text-gray-300 mb-4 leading-relaxed">{agent.description}</p>

      <div className="mb-4">
        <h4 className="text-sm font-semibold text-gray-400 mb-2">Key Features</h4>
        <div className="flex flex-wrap gap-2">
          {agent.features.slice(0, 3).map((feature, i) => (
            <span
              key={i}
              className="px-3 py-1 bg-cyan-500/10 border border-cyan-500/30 rounded-full text-xs text-cyan-400"
            >
              {feature}
            </span>
          ))}
          {agent.features.length > 3 && (
            <span className="px-3 py-1 bg-slate-700 border border-slate-600 rounded-full text-xs text-gray-400">
              +{agent.features.length - 3} more
            </span>
          )}
        </div>
      </div>

      <div className="flex gap-2">
        <a
          href={`/agents/${agent.id}`}
          className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors text-center font-semibold"
        >
          View Details
        </a>
        <a
          href={agent.webUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 px-4 py-2 border border-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors text-center font-semibold"
        >
          Open Agent →
        </a>
      </div>
    </div>
  )
}
