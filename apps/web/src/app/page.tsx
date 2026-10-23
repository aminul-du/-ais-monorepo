"use client";
import React, { useEffect, useState } from 'react';

export default function Home() {
  const [status, setStatus] = useState("CHECKING...");
  const [isOnline, setIsOnline] = useState(false);
  
  // Form State
  const [formData, setFormData] = useState({ name: '', email: '', scope: '' });
  const [formStatus, setFormStatus] = useState({ loading: false, error: '', success: false });

  useEffect(() => {
    fetch("http://127.0.0.1:8080/health")
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "CONNECTED") {
          setStatus("ONLINE");
          setIsOnline(true);
        }
      })
      .catch(() => {
        setStatus("OFFLINE");
        setIsOnline(false);
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormStatus({ loading: true, error: '', success: false });

    // Client-side validation
    if (!formData.name || !formData.email || !formData.scope) {
      setFormStatus({ loading: false, error: 'All fields are required.', success: false });
      return;
    }

    try {
      const res = await fetch("http://127.0.0.1:8080/api/inquiry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setFormStatus({ loading: false, error: '', success: true });
        setFormData({ name: '', email: '', scope: '' }); // Reset form
      } else {
        setFormStatus({ loading: false, error: data.error || 'Submission failed.', success: false });
      }
    } catch (err) {
      setFormStatus({ loading: false, error: 'Network error. Sandbox may be offline.', success: false });
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-cyan-500 selection:text-slate-950 scroll-smooth">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`h-3 w-3 rounded-full ${isOnline ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
            <span className="font-bold text-xl tracking-wider text-white">SHORBORNO<span className="text-cyan-400">AI</span></span>
          </div>
          <nav className="hidden md:flex space-x-8 text-sm font-medium text-slate-400">
            <a href="#features" className="hover:text-cyan-400 transition-colors">Features</a>
            <a href="#architecture" className="hover:text-cyan-400 transition-colors">Architecture</a>
            <a href="#contact" className="hover:text-cyan-400 transition-colors">Contact</a>
          </nav>
          <div className="flex items-center space-x-4">
             <div className={`px-3 py-1 text-xs font-mono font-bold border rounded ${isOnline ? 'border-green-500/50 text-green-400 bg-green-500/10' : 'border-red-500/50 text-red-400 bg-red-500/10'}`}>
               SANDBOX: {status}
             </div>
          </div>
        </div>
      </header>

      {/* Hero & Features omitted for brevity in prompt, assume standard rendering here... (Skipped to Contact section) */}

      <section id="contact" className="py-20 border-t border-slate-800 mt-20">
        <div className="max-w-3xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-2">Initiate Deployment Inquiry</h2>
            <p className="text-slate-400 text-sm">Connect with the engineering team to deploy ShorbornoAI instances.</p>
          </div>
          
          {formStatus.success ? (
            <div className="bg-green-500/10 border border-green-500/50 rounded-2xl p-8 text-center">
              <h3 className="text-xl font-bold text-green-400 mb-2">Inquiry Received</h3>
              <p className="text-slate-300">The engineering team will review your deployment request.</p>
              <button onClick={() => setFormStatus({ ...formStatus, success: false })} className="mt-6 px-6 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm transition-colors">Submit Another</button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6 bg-slate-900/50 p-8 rounded-2xl border border-slate-800">
              {formStatus.error && <div className="p-3 bg-red-500/10 border border-red-500/50 text-red-400 text-sm rounded-lg">{formStatus.error}</div>}
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Your Name</label>
                  <input type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition-colors" />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Email Address</label>
                  <input type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition-colors" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Project / Infrastructure Scope</label>
                <textarea rows={4} value={formData.scope} onChange={e => setFormData({...formData, scope: e.target.value})} className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition-colors"></textarea>
              </div>
              <button type="submit" disabled={formStatus.loading} className="w-full py-3.5 rounded-lg bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 disabled:opacity-50 transition-all shadow-lg shadow-cyan-500/20">
                {formStatus.loading ? 'Transmitting...' : 'Submit Launch Request'}
              </button>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}
