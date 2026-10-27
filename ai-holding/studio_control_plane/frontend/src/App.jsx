import React, { useState, useEffect } from 'react'
import { 
  Building2, 
  ShieldCheck, 
  Cpu, 
  Terminal, 
  Users, 
  Layers, 
  Play, 
  Pause, 
  RotateCcw, 
  AlertTriangle, 
  Flame, 
  CheckCircle2, 
  Send,
  Link,
  Unlink,
  Server
} from 'lucide-react'

export default function App() {
  const [activeTab, setActiveTab] = useState('topology')
  const [topology, setTopology] = useState({ nodes: [], edges: [] })
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [agentDetails, setAgentDetails] = useState(null)
  const [editSoul, setEditSoul] = useState('')
  const [editMemory, setEditMemory] = useState('')
  const [timeline, setTimeline] = useState([])
  const [resources, setResources] = useState([])
  const [chairmanPrompt, setChairmanPrompt] = useState('')
  const [toastMessage, setToastMessage] = useState('')
  const [loading, setLoading] = useState(false)

  // 1. Fetch Topology
  const fetchTopology = async () => {
    try {
      const res = await fetch('/api/topology')
      if (res.ok) {
        const data = await res.json()
        setTopology(data)
      }
    } catch (e) {
      console.error(e)
    }
  }

  // 2. Fetch Resources
  const fetchResources = async () => {
    try {
      const res = await fetch('/api/resources')
      if (res.ok) {
        const data = await res.json()
        setResources(data.service_accounts || [])
      }
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    fetchTopology()
    fetchResources()
    const timer = setInterval(() => {
      fetchTopology()
      fetchResources()
    }, 4000)
    return () => clearInterval(timer)
  }, [])

  // 3. Select Agent & Load Details
  const handleSelectAgent = async (agentPath) => {
    setSelectedAgent(agentPath)
    try {
      setLoading(true)
      const res = await fetch(`/api/agent/files?agent_path=${encodeURIComponent(agentPath)}`)
      if (res.ok) {
        const data = await res.json()
        setAgentDetails(data)
        setEditSoul(data.soul)
        setEditMemory(data.memory)
      }
      // Load timeline
      const tRes = await fetch(`/api/agent/timeline?agent_path=${encodeURIComponent(agentPath)}`)
      if (tRes.ok) {
        const tData = await tRes.json()
        setTimeline(tData)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  // 4. Save Hot-Edited File
  const handleSaveFile = async (type) => {
    if (!agentDetails) return
    const filename = type === 'soul' ? 'agent_soul.md' : 'agent_memory.md'
    const content = type === 'soul' ? editSoul : editMemory
    const path = `${agentDetails.agent_path}/${filename}`

    try {
      const res = await fetch('/api/agent/save-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, content })
      })
      if (res.ok) {
        setToastMessage(`Đã cập nhật ${filename} an toàn (Atomic Write)!`)
        setTimeout(() => setToastMessage(''), 3000)
      }
    } catch (e) {
      alert('Lỗi lưu file: ' + e)
    }
  }

  // 5. Unlink and Clone
  const handleUnlink = async () => {
    if (!selectedAgent) return
    try {
      const res = await fetch('/api/agent/unlink-and-clone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_path: selectedAgent })
      })
      if (res.ok) {
        setToastMessage('Đã Unlink & chuyển sang Clone độc lập!')
        handleSelectAgent(selectedAgent)
        fetchTopology()
        setTimeout(() => setToastMessage(''), 3000)
      }
    } catch (e) {
      alert('Lỗi: ' + e)
    }
  }

  // 6. Pause / Resume
  const handleTogglePause = async () => {
    if (!agentDetails) return
    const endpoint = agentDetails.is_paused ? '/api/agent/resume' : '/api/agent/pause'
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_path: selectedAgent })
      })
      if (res.ok) {
        handleSelectAgent(selectedAgent)
      }
    } catch (e) {
      console.error(e)
    }
  }

  // 7. Rollback Step
  const handleRollback = async (stepNum) => {
    if (!confirm(`Xác nhận Rollback về Step #${stepNum}? Các bước sau sẽ bị hủy bỏ!`)) return
    try {
      const res = await fetch('/api/agent/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_path: selectedAgent, step_num: stepNum })
      })
      if (res.ok) {
        setToastMessage(`Đã Rollback về Step #${stepNum} thành công!`)
        handleSelectAgent(selectedAgent)
        setTimeout(() => setToastMessage(''), 3000)
      }
    } catch (e) {
      alert('Lỗi: ' + e)
    }
  }

  // 8. Chairman Interceptor Command
  const handleSendChairmanCommand = async (e) => {
    e.preventDefault()
    if (!chairmanPrompt.trim()) return
    try {
      const res = await fetch('/api/chairman/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: chairmanPrompt })
      })
      if (res.ok) {
        const d = await res.json()
        setToastMessage(d.message || 'Chỉ thị của Chủ tịch đã được gửi!')
        setChairmanPrompt('')
        fetchTopology()
        setTimeout(() => setToastMessage(''), 4000)
      }
    } catch (e) {
      alert('Lỗi gửi lệnh: ' + e)
    }
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">
      {/* SIDEBAR NAVIGATION */}
      <aside className="w-64 border-r border-slate-800 bg-slate-900/60 p-4 flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2 mb-8">
            <Building2 className="w-8 h-8 text-indigo-400" />
            <div>
              <h1 className="font-bold text-lg leading-tight text-white">AI HOLDING</h1>
              <p className="text-xs text-indigo-400 font-mono tracking-wider">STUDIO CONTROL PLANE</p>
            </div>
          </div>

          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab('topology')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'topology' ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40' : 'text-slate-400 hover:bg-slate-800/60'
              }`}
            >
              <Layers className="w-4 h-4" />
              Sơ đồ Tổ chức (Topology)
            </button>

            <button
              onClick={() => setActiveTab('resources')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                activeTab === 'resources' ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40' : 'text-slate-400 hover:bg-slate-800/60'
              }`}
            >
              <Server className="w-4 h-4" />
              Tài nguyên & Key Pool ({resources.length})
            </button>
          </nav>
        </div>

        <div className="border-t border-slate-800 pt-4 text-xs text-slate-500">
          <div className="flex items-center gap-2 mb-1">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-300">Zero-Trust: Kích hoạt</span>
          </div>
          <div>Cổng LLM: OmniRoute (Port 20128)</div>
        </div>
      </aside>

      {/* MAIN VIEW AREA */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* TOP BAR / TOAST */}
        <header className="h-14 border-b border-slate-800 px-6 flex items-center justify-between bg-slate-900/30">
          <div className="text-sm font-medium text-slate-300">
            {activeTab === 'topology' && 'Sơ đồ Phân quyền & Quan hệ Nhân sự Tập đoàn'}
            {activeTab === 'resources' && 'Kho Tài nguyên & Hạn ngạch (resources.db / vault)'}
          </div>

          {toastMessage && (
            <div className="flex items-center gap-2 px-3 py-1 bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 rounded text-xs animate-pulse">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {toastMessage}
            </div>
          )}
        </header>

        {/* CONTENT */}
        <div className="flex-1 flex overflow-hidden">
          {activeTab === 'topology' && (
            <div className="flex-1 flex overflow-hidden">
              {/* TOPOLOGY CANVAS */}
              <div className="flex-1 p-6 overflow-auto bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px]">
                <div className="mb-4 flex items-center justify-between">
                  <div className="text-xs text-slate-400">
                    Bấm vào từng Agent để mở <b>Trình chỉnh sửa nóng (Hot-Editor)</b> và <b>Dòng thời gian (Timeline)</b>
                  </div>
                  <button 
                    onClick={fetchTopology} 
                    className="text-xs px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700"
                  >
                    Làm mới sơ đồ
                  </button>
                </div>

                {/* B2B ACTIVE CONTRACTS BANNER */}
                {topology.edges.filter(e => e.label).length > 0 && (
                  <div className="mb-4 p-3 bg-amber-950/30 border border-amber-500/40 rounded-lg flex items-center gap-3">
                    <span className="text-amber-400 text-sm font-semibold">🤝 Cầu nối B2B đang kích hoạt:</span>
                    {topology.edges.filter(e => e.label).map(e => (
                      <span key={e.id} className="text-xs bg-amber-900/60 text-amber-200 px-2 py-1 rounded border border-amber-600/40">
                        {e.label}
                      </span>
                    ))}
                  </div>
                )}

                {/* NODES GRID */}
                <div className="space-y-6">
                  {/* DEVOPS CLUSTER */}
                  <div className="p-4 rounded-xl border border-cyan-800/40 bg-cyan-950/10">
                    <div className="text-xs font-semibold text-cyan-400 mb-3 flex items-center gap-2">
                      <Cpu className="w-4 h-4" /> BỘ CHỈ HUY HẠ TẦNG (DEVOPS MINISTRY - ZERO TRUST)
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      {topology.nodes.filter(n => n.data.cluster === 'devops').map(node => (
                        <div
                          key={node.id}
                          onClick={() => handleSelectAgent(node.data.path)}
                          className={`p-3 rounded-lg border cursor-pointer transition ${
                            selectedAgent === node.data.path 
                              ? 'border-cyan-400 bg-cyan-900/40' 
                              : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="font-semibold text-cyan-300">{node.data.label}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                              node.data.mode === 'SHARED' ? 'bg-amber-900/60 text-amber-300' : 'bg-emerald-900/60 text-emerald-300'
                            }`}>
                              {node.data.mode}
                            </span>
                          </div>
                          <div className="text-[11px] text-slate-400">{node.data.role}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* COMPANIES CLUSTERS */}
                  {topology.nodes.filter(n => n.type === 'companyNode').map(compNode => {
                    const compName = compNode.data.label
                    const compSubNodes = topology.nodes.filter(n => n.data.path && n.data.path.startsWith(`companies/${compName}`))

                    return (
                      <div key={compNode.id} className="p-4 rounded-xl border border-indigo-800/40 bg-indigo-950/10">
                        <div className="text-xs font-semibold text-indigo-400 mb-3 flex items-center justify-between">
                          <span className="flex items-center gap-2">
                            <Building2 className="w-4 h-4" /> CÔNG TY THÀNH VIÊN: {compName.toUpperCase()}
                          </span>
                        </div>

                        <div className="grid grid-cols-3 gap-3">
                          {compSubNodes.map(node => (
                            <div
                              key={node.id}
                              onClick={() => handleSelectAgent(node.data.path)}
                              className={`p-3 rounded-lg border cursor-pointer transition ${
                                selectedAgent === node.data.path 
                                  ? 'border-indigo-400 bg-indigo-900/40' 
                                  : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                              }`}
                            >
                              <div className="flex items-center justify-between text-xs mb-1">
                                <span className="font-semibold text-indigo-200">{node.data.label}</span>
                                {node.data.mode && (
                                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                                    node.data.mode === 'SHARED' ? 'bg-amber-900/60 text-amber-300' : 'bg-emerald-900/60 text-emerald-300'
                                  }`}>
                                    {node.data.mode}
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] text-slate-400 font-mono truncate">{node.data.path}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* HOT-EDITOR & TIMELINE INSPECTOR PANEL (Right Sidebar) */}
              {selectedAgent && (
                <div className="w-96 border-l border-slate-800 bg-slate-900/90 flex flex-col justify-between p-4 overflow-y-auto">
                  <div>
                    {/* AGENT HEADER & CONTROL */}
                    <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-3">
                      <div>
                        <div className="text-xs font-bold text-slate-200 truncate">{selectedAgent}</div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {agentDetails?.is_shared ? '🔗 Symlink (Shared Archetype)' : '📦 Isolated (Cloned)'}
                        </div>
                      </div>

                      <button
                        onClick={handleTogglePause}
                        className={`p-1.5 rounded text-xs font-medium flex items-center gap-1 ${
                          agentDetails?.is_paused 
                            ? 'bg-amber-600/30 text-amber-300 border border-amber-500/50' 
                            : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                        }`}
                        title={agentDetails?.is_paused ? 'Resume execution' : 'Pause execution'}
                      >
                        {agentDetails?.is_paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
                        {agentDetails?.is_paused ? 'Tiếp tục' : 'Tạm dừng'}
                      </button>
                    </div>

                    {/* BLAST RADIUS ALERT */}
                    {agentDetails?.is_shared && agentDetails?.blast_radius?.length > 0 && (
                      <div className="mb-4 p-2.5 rounded bg-amber-950/40 border border-amber-500/50 text-xs">
                        <div className="flex items-center gap-1.5 text-amber-400 font-semibold mb-1">
                          <Flame className="w-3.5 h-3.5" /> Bán kính ảnh hưởng (Blast Radius): {agentDetails.blast_radius.length} Agent
                        </div>
                        <p className="text-[11px] text-amber-200/80 mb-2">
                          Agent này là Symlink. Sửa đổi sẽ ảnh hưởng đến các Agent khác cùng dùng Archetype!
                        </p>
                        <button
                          onClick={handleUnlink}
                          className="w-full flex items-center justify-center gap-1 text-[11px] bg-amber-800/50 hover:bg-amber-700/60 text-amber-200 py-1 rounded border border-amber-600/50"
                        >
                          <Unlink className="w-3 h-3" /> Unlink & Clone để sửa an toàn
                        </button>
                      </div>
                    )}

                    {/* SOUL.MD EDITOR */}
                    <div className="mb-4">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-slate-300">agent_soul.md (Nhân cách & Nhiệm vụ)</span>
                        <button
                          onClick={() => handleSaveFile('soul')}
                          className="text-[11px] text-indigo-400 hover:text-indigo-300"
                        >
                          Lưu
                        </button>
                      </div>
                      <textarea
                        value={editSoul}
                        onChange={(e) => setEditSoul(e.target.value)}
                        className="w-full h-32 bg-slate-950 border border-slate-800 rounded p-2 text-xs font-mono text-slate-300 focus:border-indigo-500 focus:outline-none"
                      />
                    </div>

                    {/* MEMORY.MD EDITOR */}
                    <div className="mb-4">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-slate-300">agent_memory.md (Bộ nhớ ngắn hạn)</span>
                        <button
                          onClick={() => handleSaveFile('memory')}
                          className="text-[11px] text-indigo-400 hover:text-indigo-300"
                        >
                          Lưu
                        </button>
                      </div>
                      <textarea
                        value={editMemory}
                        onChange={(e) => setEditMemory(e.target.value)}
                        className="w-full h-24 bg-slate-950 border border-slate-800 rounded p-2 text-xs font-mono text-slate-300 focus:border-indigo-500 focus:outline-none"
                      />
                    </div>

                    {/* EXECUTION TIMELINE & TIME-TRAVEL ROLLBACK */}
                    <div className="border-t border-slate-800 pt-3">
                      <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1">
                        <RotateCcw className="w-3.5 h-3.5 text-slate-400" /> Dòng thời gian & Rollback
                      </div>

                      {timeline.length === 0 ? (
                        <div className="text-[11px] text-slate-500 italic">Chưa có bước thực thi nào.</div>
                      ) : (
                        <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                          {timeline.map((step) => (
                            <div key={step.id} className="p-2 rounded bg-slate-950 border border-slate-800 text-[11px]">
                              <div className="flex items-center justify-between text-slate-400 mb-1">
                                <span className="font-semibold text-slate-300">Step #{step.step_num}</span>
                                <button
                                  onClick={() => handleRollback(step.step_num)}
                                  className="text-[10px] text-rose-400 hover:underline"
                                >
                                  Rollback về đây
                                </button>
                              </div>
                              <p className="text-slate-300 line-clamp-2">{step.thought || step.tool_call || 'Executing...'}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* RESOURCES TAB */}
          {activeTab === 'resources' && (
            <div className="flex-1 p-6 overflow-auto">
              <div className="max-w-4xl mx-auto space-y-4">
                <div className="text-sm font-semibold text-slate-300">
                  Danh sách Tài nguyên Hạ tầng Đăng ký (resources.db)
                </div>

                <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/60">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-800/80 text-slate-400">
                      <tr>
                        <th className="p-3">ID</th>
                        <th className="p-3">Nhà cung cấp</th>
                        <th className="p-3">Tài khoản / Email</th>
                        <th className="p-3">Vault Secret Ref</th>
                        <th className="p-3">Trạng thái</th>
                        <th className="p-3">Công ty sở hữu</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {resources.map((r) => (
                        <tr key={r.id} className="hover:bg-slate-800/40">
                          <td className="p-3 font-mono">{r.id}</td>
                          <td className="p-3 font-semibold text-cyan-400">{r.provider}</td>
                          <td className="p-3 font-mono">{r.account_email}</td>
                          <td className="p-3 font-mono text-slate-400">{r.vault_secret_ref}</td>
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] ${
                              r.status === 'AVAILABLE' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-amber-950 text-amber-300 border border-amber-800'
                            }`}>
                              {r.status}
                            </span>
                          </td>
                          <td className="p-3 text-slate-300">{r.locked_by_company || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* BOTTOM CHAIRMAN COMMAND INTERCEPTOR */}
        <footer className="h-16 border-t border-slate-800 px-6 flex items-center bg-slate-900/80">
          <form onSubmit={handleSendChairmanCommand} className="w-full flex items-center gap-3">
            <Terminal className="w-5 h-5 text-indigo-400" />
            <input
              type="text"
              value={chairmanPrompt}
              onChange={(e) => setChairmanPrompt(e.target.value)}
              placeholder="Chỉ thị của Chủ tịch: 'Tạo công ty Company_A_Bakery', 'Cho phép Company_A_Bakery hợp tác với Company_B_Soda', hoặc nhắn trực tiếp..."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <Send className="w-3.5 h-3.5" /> Phát lệnh
            </button>
          </form>
        </footer>
      </main>
    </div>
  )
}
