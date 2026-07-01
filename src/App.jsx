import React, { useState, useEffect } from 'react';
import { Send, Car, Sparkles, Plus, Trash2 } from 'lucide-react';

export default function App() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState([
    {
      sender: 'ai',
      text: "Hello! I am your CarDekho Assistant. Tell me what you're looking for! For example: *'Show me automatic cars under 8 Lakhs with high mileage'*."
    }
  ]);
  const [currentCars, setCurrentCars] = useState([]);
  const [shortlist, setShortlist] = useState([]);
  const [debugSql, setDebugSql] = useState('');

  // Active AI Provider state
  const [activeProvider, setActiveProvider] = useState('AI Matchmaker');

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        if (data.active_provider) {
          if (data.active_provider === 'Gemini' && data.gemini_model) {
            setActiveProvider(`Gemini (${data.gemini_model})`);
          } else if (data.active_provider === 'OpenAI' && data.openai_model) {
            setActiveProvider(`OpenAI (${data.openai_model})`);
          } else {
            setActiveProvider(data.active_provider);
          }
        }
      })
      .catch(() => {});
  }, []);

  // Explanation States for Top 3 suggestion breakdown
  const [explanations, setExplanations] = useState({});
  const [loadingExplanationIdx, setLoadingExplanationIdx] = useState(null);
  const [expandedExplanationIdx, setExpandedExplanationIdx] = useState(null);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userMessage = query;
    const currentHistory = [...chatHistory];
    
    setChatHistory(prev => [...prev, { sender: 'user', text: userMessage }]);
    setQuery('');
    setLoading(true);
    setExplanations({});
    setExpandedExplanationIdx(null);
    setLoadingExplanationIdx(null);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: userMessage,
          history: currentHistory
        })
      });
      const data = await res.json();
      
      setChatHistory(prev => [...prev, { sender: 'ai', text: data.message }]);
      if (data.cars) setCurrentCars(data.cars);
      if (data.sql) setDebugSql(data.sql);
    } catch (err) {
      setChatHistory(prev => [...prev, { sender: 'ai', text: "Error: Failed to fetch recommendations." }]);
    } finally {
      setLoading(false);
    }
  };

  const explainCarSuggestion = async (car, idx) => {
    if (expandedExplanationIdx === idx) {
      setExpandedExplanationIdx(null);
      return;
    }

    if (explanations[idx]) {
      setExpandedExplanationIdx(idx);
      return;
    }

    setLoadingExplanationIdx(idx);
    try {
      const lastUserMessage = chatHistory.filter(m => m.sender === 'user').slice(-1)[0]?.text || '';
      const res = await fetch('/api/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          car: car,
          rank: idx + 1,
          history: chatHistory,
          query: lastUserMessage
        })
      });
      const data = await res.json();
      setExplanations(prev => ({ ...prev, [idx]: data.explanation }));
      setExpandedExplanationIdx(idx);
    } catch (err) {
      setExplanations(prev => ({ ...prev, [idx]: "Failed to generate explanation. Please try again." }));
      setExpandedExplanationIdx(idx);
    } finally {
      setLoadingExplanationIdx(null);
    }
  };

  const addToShortlist = (car) => {
    if (shortlist.find(c => c.car_name === car.car_name && c.selling_price === car.selling_price)) return;
    setShortlist(prev => [...prev, car]);
  };

  const removeFromShortlist = (index) => {
    setShortlist(prev => prev.filter((_, i) => i !== index));
  };

  // Convert rupees format safely
  const formatPrice = (price) => {
    if (price === null || price === undefined) return 'N/A';
    if (price >= 100000) {
      return `₹ ${(price / 100000).toFixed(2)} Lakh`;
    }
    return `₹ ${price.toLocaleString()}`;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Navbar */}
      <nav className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <Car className="text-rose-500 w-8 h-8" />
          <span className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-rose-500 to-amber-500 bg-clip-text text-transparent">
            CarDekho Matchmaker
          </span>
        </div>
        <div className="text-xs text-slate-400 bg-slate-800 px-3 py-1 rounded-full flex items-center gap-1.5 border border-slate-700">
          <Sparkles className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
          Powered by {activeProvider}
        </div>
      </nav>

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-hidden">
        
        {/* Left Column: Chat Assistant & SQL Debugger */}
        <div className="lg:col-span-5 flex flex-col bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 overflow-hidden h-[75vh]">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-rose-500" />
            AI Car Consultant
          </h2>
          
          {/* Chat message display */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-2 mb-4 scrollbar-thin scrollbar-thumb-slate-800">
            {chatHistory.map((msg, i) => (
              <div key={i} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.sender === 'user' 
                    ? 'bg-rose-600 text-white rounded-br-none' 
                    : 'bg-slate-800/80 border border-slate-700/50 text-slate-200 rounded-bl-none'
                }`}>
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-800/80 border border-slate-700/50 rounded-2xl rounded-bl-none px-4 py-3 text-sm text-slate-400 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-bounce"></span>
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-bounce [animation-delay:0.2s]"></span>
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-bounce [animation-delay:0.4s]"></span>
                  Generating query & recommendations...
                </div>
              </div>
            )}
          </div>

          {/* Chat Form */}
          <form onSubmit={handleSend} className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask for models, price limits, transmission..."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20 text-white"
            />
            <button type="submit" className="bg-rose-600 hover:bg-rose-500 text-white p-3 rounded-xl transition shadow-lg shadow-rose-950/20">
              <Send className="w-4 h-4" />
            </button>
          </form>

          {/* Debug SQL Box */}
          {debugSql && (
            <div className="mt-4 p-3 bg-slate-950 border border-slate-800 rounded-xl">
              <div className="text-[10px] text-amber-500 font-semibold uppercase tracking-wider mb-1">Generated SQLite SQL Query</div>
              <code className="text-xs text-slate-400 font-mono break-all">{debugSql}</code>
            </div>
          )}
        </div>

        {/* Right Column: Search Results & Shortlist Comparison */}
        <div className="lg:col-span-7 flex flex-col gap-6 h-[75vh]">
          
          {/* Matches Section */}
          <div className="flex-1 bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 flex flex-col overflow-hidden">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center justify-between">
              <span>Matching Car Options ({currentCars.length})</span>
              <span className="text-xs text-slate-500 font-normal">Select matching cars to shortlist</span>
            </h2>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {currentCars.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-2 border-2 border-dashed border-slate-800/60 rounded-xl p-8">
                  <Car className="w-12 h-12 stroke-[1.5]" />
                  <p className="text-sm">No active matches. Chat with the Assistant on the left to run a search query!</p>
                </div>
              ) : (
                currentCars.map((car, idx) => {
                  const isTop3 = idx < 3;
                  const isExpanded = expandedExplanationIdx === idx;
                  const isLoading = loadingExplanationIdx === idx;
                  const explanation = explanations[idx];

                  return (
                    <div key={idx} className="p-4 bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-xl flex flex-col transition gap-3">
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-bold text-slate-200">{car.car_name || 'Unnamed Car'}</h3>
                            {isTop3 && (
                              <span className="bg-rose-500/10 text-rose-400 text-[10px] px-2 py-0.5 rounded border border-rose-500/20 font-extrabold tracking-wide uppercase">
                                #{idx + 1} Match
                              </span>
                            )}
                          </div>
                          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs text-slate-400">
                            <span className="text-amber-400 font-semibold">{formatPrice(car.selling_price)}</span>
                            <span>•</span>
                            <span>{car.transmission_type || 'N/A'}</span>
                            <span>•</span>
                            <span>{car.fuel_type || 'N/A'}</span>
                            <span>•</span>
                            <span>{car.km_driven !== null && car.km_driven !== undefined ? `${car.km_driven.toLocaleString()} km` : 'N/A'}</span>
                            <span>•</span>
                            <span>{car.mileage !== null && car.mileage !== undefined ? `${car.mileage} km/l` : 'N/A'}</span>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          {isTop3 && (
                            <button
                              onClick={() => explainCarSuggestion(car, idx)}
                              disabled={loadingExplanationIdx !== null && !isLoading}
                              className={`flex items-center gap-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                                isExpanded ? 'ring-2 ring-rose-500/50 bg-slate-700' : ''
                              }`}
                            >
                              <Sparkles className={`w-3.5 h-3.5 text-rose-400 ${isLoading ? 'animate-spin' : ''}`} />
                              {isLoading ? 'Thinking...' : isExpanded ? 'Hide Info' : 'Why this?'}
                            </button>
                          )}
                          <button
                            onClick={() => addToShortlist(car)}
                            className="flex items-center gap-1.5 bg-slate-800 hover:bg-rose-900/30 hover:text-rose-400 text-slate-300 border border-slate-700 px-3 py-1.5 rounded-lg text-xs font-semibold transition"
                          >
                            <Plus className="w-3.5 h-3.5" />
                            Shortlist
                          </button>
                        </div>
                      </div>

                      {/* Collapsible AI Explanation section for top 3 suggestion reasons */}
                      {isTop3 && (isExpanded || isLoading) && (
                        <div className="mt-1 p-3 bg-slate-950/60 border border-rose-500/10 rounded-lg text-xs leading-relaxed text-slate-300 flex items-start gap-2.5">
                          <Sparkles className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                          <div>
                            <div className="text-[10px] text-rose-400 font-bold uppercase tracking-wider mb-1">AI Recommendation Insight</div>
                            {isLoading ? (
                              <div className="flex items-center gap-2 text-slate-500 font-medium">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse [animation-delay:0.2s]"></span>
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse [animation-delay:0.4s]"></span>
                                Analyzing match attributes against your preferences...
                              </div>
                            ) : (
                              <p className="font-normal text-slate-300">{explanation}</p>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Shortlist Comparison Section */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 flex flex-col h-[280px]">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center justify-between">
              <span>Shortlist & Compare ({shortlist.length})</span>
              {shortlist.length > 0 && (
                <button onClick={() => setShortlist([])} className="text-xs text-rose-500 hover:underline flex items-center gap-1">
                  <Trash2 className="w-3.5 h-3.5" /> Clear All
                </button>
              )}
            </h2>

            <div className="flex-1 overflow-x-auto flex gap-4 pb-2">
              {shortlist.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-1 border border-dashed border-slate-800 rounded-xl p-4">
                  <p className="text-xs">Shortlist matches above to compare values side-by-side.</p>
                </div>
              ) : (
                shortlist.map((car, idx) => (
                  <div key={idx} className="min-w-[200px] bg-slate-950 border border-slate-800 rounded-xl p-3 flex flex-col justify-between relative group">
                    <button
                      onClick={() => removeFromShortlist(idx)}
                      className="absolute top-2 right-2 p-1 rounded bg-slate-900 hover:bg-rose-950 text-slate-400 hover:text-rose-500 border border-slate-800"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                    <div>
                      <h4 className="font-bold text-sm text-slate-200 pr-5 truncate">{car.car_name || 'Unnamed'}</h4>
                      <p className="text-rose-500 font-extrabold text-sm mt-1">{formatPrice(car.selling_price)}</p>
                      
                      <div className="mt-3 space-y-1.5 text-xs border-t border-slate-900 pt-3 text-slate-400">
                        <div className="flex justify-between"><span>Age:</span><span className="text-slate-200">{car.vehicle_age !== null && car.vehicle_age !== undefined ? `${car.vehicle_age} yrs` : 'N/A'}</span></div>
                        <div className="flex justify-between"><span>Driven:</span><span className="text-slate-200">{car.km_driven !== null && car.km_driven !== undefined ? `${car.km_driven.toLocaleString()} km` : 'N/A'}</span></div>
                        <div className="flex justify-between"><span>Engine:</span><span className="text-slate-200">{car.engine !== null && car.engine !== undefined ? `${car.engine} CC` : 'N/A'}</span></div>
                        <div className="flex justify-between"><span>Mileage:</span><span className="text-slate-200">{car.mileage !== null && car.mileage !== undefined ? `${car.mileage} km/l` : 'N/A'}</span></div>
                        <div className="flex justify-between"><span>Power:</span><span className="text-slate-200">{car.max_power !== null && car.max_power !== undefined ? `${car.max_power} BHP` : 'N/A'}</span></div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
