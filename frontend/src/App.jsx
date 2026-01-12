import { useState, useRef, useEffect } from 'react'
import { Send, Radio, Square, CheckCircle, Download } from 'lucide-react'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [objective, setObjective] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [logs, setLogs] = useState('')
  const [screenshot, setScreenshot] = useState(null)
  const [status, setStatus] = useState('idle') // idle, active, completed
  const [isPolling, setIsPolling] = useState(false)
  const [finalUrl, setFinalUrl] = useState(null)
  const [extractedContent, setExtractedContent] = useState('')
  const pollingIntervalRef = useRef(null)
  const logsEndRef = useRef(null)
  const statusRef = useRef('idle')
  const sessionIdRef = useRef(null)

  // Keep refs in sync with state
  useEffect(() => {
    statusRef.current = status
  }, [status])

  useEffect(() => {
    sessionIdRef.current = sessionId
  }, [sessionId])

  // Auto-scroll logs to bottom
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const startSession = async () => {
    if (!objective.trim()) {
      alert('Please enter an objective')
      return
    }

    try {
      const response = await fetch(`${API_BASE_URL}/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ objective: objective.trim() }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to start session')
      }

      const data = await response.json()
      setSessionId(data.session_id)
      sessionIdRef.current = data.session_id
      setStatus('active')
      statusRef.current = 'active'
      setLogs('')
      setScreenshot(null)
      setIsPolling(true)

      // Start polling immediately
      executeStep(data.session_id)
    } catch (error) {
      alert(`Error: ${error.message}`)
      console.error('Start session error:', error)
    }
  }

  const executeStep = async (sid) => {
    if (!sid) return

    try {
      const response = await fetch(`${API_BASE_URL}/step`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: sid }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to execute step')
      }

      const data = await response.json()
      
      // Update screenshot
      if (data.screenshot) {
        setScreenshot(`data:image/png;base64,${data.screenshot}`)
      }

      // Update logs
      if (data.logs) {
        setLogs(data.logs)
      }

      // Update extracted content
      if (data.extracted_content) {
        setExtractedContent(data.extracted_content)
      }

      // Update status
      setStatus(data.status)
      statusRef.current = data.status
      
      // Store final URL when completed
      if (data.status === 'completed' && data.url) {
        setFinalUrl(data.url)
      }

      // Stop polling if completed
      if (data.status === 'completed') {
        stopPolling()
        setLogs(prev => prev + '\n\n[SYSTEM] ✅ Mission completed successfully!')
      }
    } catch (error) {
      console.error('Step execution error:', error)
      stopPolling()
      setLogs(prev => prev + `\n\n[ERROR] ${error.message}`)
      setStatus('idle')
      statusRef.current = 'idle'
    }
  }

  const startPolling = (sid) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
    }

    pollingIntervalRef.current = setInterval(() => {
      // Use refs to get current values
      if (statusRef.current !== 'completed' && isPolling && sessionIdRef.current) {
        executeStep(sessionIdRef.current)
      } else if (statusRef.current === 'completed') {
        stopPolling()
      }
    }, 1500) // Poll every 1.5 seconds (faster updates)
  }

  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }
    setIsPolling(false)
  }

  // Start/stop polling based on status
  useEffect(() => {
    if (isPolling && sessionId && status === 'active') {
      startPolling(sessionId)
    } else {
      stopPolling()
    }

    return () => {
      stopPolling()
    }
  }, [isPolling, sessionId, status])

  const handleStop = () => {
    stopPolling()
    setStatus('idle')
    if (sessionId) {
      // Optionally cleanup session on backend
      fetch(`${API_BASE_URL}/session/${sessionId}`, {
        method: 'DELETE',
      }).catch(console.error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <div className="container mx-auto px-4 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-4xl font-bold mb-2">ReasonOS</h1>
          <p className="text-gray-400">Autonomous Web Surfer Agent - Mission Control</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Panel - Mission Log */}
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
              <Radio className="w-6 h-6 text-blue-400" />
              Mission Log
            </h2>

            {/* Objective Input */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2 text-gray-300">
                Target Objective
              </label>
              <textarea
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                placeholder="e.g., Find the price of iPhone 15 on Amazon"
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows="3"
                disabled={status === 'active'}
              />
            </div>

            {/* Deploy Button */}
            <div className="mb-4">
              {status !== 'active' ? (
                <button
                  onClick={startSession}
                  disabled={!objective.trim()}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-lg flex items-center justify-center gap-2 transition-colors"
                >
                  <Send className="w-5 h-5" />
                  Run
                </button>
              ) : (
                <button
                  onClick={handleStop}
                  className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-lg flex items-center justify-center gap-2 transition-colors"
                >
                  <Square className="w-5 h-5" />
                  Stop Agent
                </button>
              )}
            </div>

            {/* Status Badge */}
            <div className="mb-4">
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                status === 'idle' ? 'bg-gray-600 text-gray-300' :
                status === 'active' ? 'bg-green-600 text-white' :
                'bg-blue-600 text-white'
              }`}>
                Status: {status === 'idle' ? 'Ready' : status === 'active' ? 'Active' : 'Completed'}
              </span>
            </div>

            {/* Mission Results - Show when completed or has content */}
            {(status === 'completed' || extractedContent) && (
              <div className="mb-4 p-4 bg-green-900/20 border border-green-600 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  <h3 className="text-lg font-semibold text-green-400">
                    {status === 'completed' ? 'Mission Completed!' : 'Extracted Content'}
                  </h3>
                </div>
                
                {/* Extracted Content Output */}
                {extractedContent && (
                  <div className="mb-3">
                    <label className="block text-sm font-medium mb-2 text-gray-300">Results:</label>
                    <div className="bg-gray-900 rounded-lg p-3 max-h-48 overflow-y-auto border border-gray-700">
                      <pre className="text-green-400 text-sm whitespace-pre-wrap font-mono">{extractedContent}</pre>
                    </div>
                  </div>
                )}
                
                <p className="text-sm text-gray-300 mb-2">
                  {status === 'completed' 
                    ? 'The agent has successfully completed the objective. View the final result above and in the Live Vision Feed panel.'
                    : 'Content extracted from the current page.'}
                </p>
                {finalUrl && (
                  <p className="text-xs text-gray-400 mb-3">
                    Final URL: <a href={finalUrl} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">{finalUrl}</a>
                  </p>
                )}
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      const data = `Mission: ${objective}\n\nFinal URL: ${finalUrl || 'N/A'}\n\nExtracted Content:\n${extractedContent || 'N/A'}\n\nReasoning Logs:\n${logs}`
                      const blob = new Blob([data], { type: 'text/plain' })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = `mission-${Date.now()}.txt`
                      a.click()
                      URL.revokeObjectURL(url)
                    }}
                    className="flex items-center gap-2 px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    Download Results
                  </button>
                </div>
              </div>
            )}

            {/* Terminal Logs */}
            <div className="mt-6">
              <label className="block text-sm font-medium mb-2 text-gray-300">
                Agent Reasoning Logs
              </label>
              <div className="bg-black rounded-lg p-4 h-96 overflow-y-auto font-mono text-sm border border-gray-700">
                {logs ? (
                  <pre className="text-green-400 whitespace-pre-wrap">{logs}</pre>
                ) : (
                  <div className="text-gray-500">Waiting for agent activity...</div>
                )}
                <div ref={logsEndRef} />
              </div>
            </div>
          </div>

          {/* Right Panel - Live Vision */}
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
              <Radio className="w-6 h-6 text-red-400" />
              Live Vision Feed
            </h2>

            <div className="relative bg-black rounded-lg border border-gray-700 overflow-hidden">
              {/* LIVE FEED Badge */}
              {status === 'active' && (
                <div className="absolute top-4 right-4 z-10">
                  <div className="bg-red-600 text-white px-4 py-2 rounded-lg font-bold text-sm flex items-center gap-2 animate-pulse">
                    <div className="w-2 h-2 bg-white rounded-full animate-ping" />
                    LIVE FEED
                  </div>
                </div>
              )}

              {/* Screenshot Display */}
              {screenshot ? (
                <img
                  src={screenshot}
                  alt="Agent view"
                  className="w-full h-auto max-h-[600px] object-contain"
                />
              ) : (
                <div className="flex items-center justify-center h-96 text-gray-500">
                  <div className="text-center">
                    <Radio className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                    <p>No feed available</p>
                    <p className="text-sm mt-2">Start a mission to see live vision</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
