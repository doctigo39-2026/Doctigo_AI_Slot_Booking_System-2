# voice_ui.py — auto-types mic transcript into the "Type your message..." box
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components

def mic_to_fixed_bar(lang_code: str = "en-IN", label: str = "🎙"):
    components.html(
        f"""
<div style="display:flex;gap:8px;align-items:center">
  <button id="micBtn" style="padding:10px 14px;border:0;border-radius:12px;cursor:pointer;
    background:linear-gradient(135deg,#4F46E5,#6366F1);color:#fff">{label}</button>
  <span id="micStat" style="font-size:12px;opacity:.75"></span>
</div>
<script>
(function() {{
  const ifrWin = window;
  const topWin = window.parent;
  const SCRIPT_ID = "doctigo-mic-controller";
  const LANG = {lang_code!r};

  // Install a single controller on parent
  if (!topWin.document.getElementById(SCRIPT_ID)) {{
    const s = topWin.document.createElement("script");
    s.id = SCRIPT_ID;
    s.type = "text/javascript";
    s.text = `
      (function() {{
        const W = window;
        const SR = W.SpeechRecognition || W.webkitSpeechRecognition;

        function findInputEl() {{
          // Prefer the fixed bar input
          const inBar = W.document.querySelector('.fixed-input-inner input, .fixed-input-inner textarea');
          if (inBar) return inBar;
          // Fallback: the placeholder "Type your message..." (case-insensitive)
          const nodes = Array.from(W.document.querySelectorAll('input[placeholder], textarea[placeholder]'));
          const match = nodes.find(n => (n.getAttribute('placeholder')||'').toLowerCase().includes('type your message'));
          return match || nodes[0] || null;
        }}

        function setCaretEnd(el) {{
          try {{
            const len = el.value.length;
            el.setSelectionRange(len, len);
          }} catch(e) {{}}
        }}

        function setVal(v) {{
          const el = findInputEl();
          if (!el) return;
          const proto = el.tagName==='TEXTAREA' ? W.HTMLTextAreaElement.prototype : W.HTMLInputElement.prototype;
          const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
          setter.call(el, v);
          el.dispatchEvent(new Event('input', {{ bubbles:true }}));
          el.dispatchEvent(new Event('change', {{ bubbles:true }}));
          setCaretEnd(el);
        }}

        function broadcast(msg) {{
          try {{
            const frames = Array.from(W.frames || []);
            for (let i=0;i<frames.length;i++) {{ try {{ frames[i].postMessage(msg, '*'); }} catch(e) {{}} }}
          }} catch(e) {{}}
        }}

        W.doctigoMic = {{
          ok: !!SR,
          rec: null,
          active: false,
          buf: "",
          start(lang) {{
            if (!this.ok) {{ broadcast({{source:'doctigoMic', type:'status', payload:'unsupported'}}); return; }}
            if (this.active) return;
            const Rec = W.SpeechRecognition || W.webkitSpeechRecognition;
            this.rec = new Rec();
            this.rec.lang = lang || 'en-IN';
            this.rec.interimResults = true;     // live typing
            this.rec.continuous = false;
            this.buf = "";

            this.rec.onstart = () => {{ this.active = true;  broadcast({{source:'doctigoMic', type:'status', payload:'listening'}}); }};
            this.rec.onend   = () => {{ this.active = false; broadcast({{source:'doctigoMic', type:'status', payload:'idle'}});     }};
            this.rec.onerror = () => {{ this.active = false; broadcast({{source:'doctigoMic', type:'status', payload:'error'}});    }};

            this.rec.onresult = (e) => {{
              let interim = "";
              for (let i=e.resultIndex; i<e.results.length; ++i) {{
                const t = e.results[i][0].transcript;
                if (e.results[i].isFinal) this.buf += t; else interim += t;
              }}
              const out = this.buf || interim;   // auto-type interim + final text
              setVal(out);
              broadcast({{source:'doctigoMic', type:'text', payload: out}});
            }};

            try {{ this.rec.start(); }} catch(err) {{ broadcast({{source:'doctigoMic', type:'status', payload:'error'}}); }}
          }},
          stop() {{ try {{ if (this.rec) this.rec.stop(); }} catch(e) {{}} }},
          toggle(lang) {{ if (this.active) this.stop(); else this.start(lang); }},
        }};
      }})();`;
    topWin.document.head.appendChild(s);
  }}

  // Button wiring inside iframe
  const btn  = document.getElementById('micBtn');
  const stat = document.getElementById('micStat');

  function setStat(s) {{
    stat.textContent = s === 'listening' ? 'Listening…'
                     : s === 'unsupported' ? 'Voice not supported'
                     : s === 'error' ? 'Mic error' : '';
    btn.style.background = s === 'listening' ? '#EF4444' : 'linear-gradient(135deg,#4F46E5,#6366F1)';
  }}

  btn.addEventListener('click', (ev) => {{
    ev.preventDefault();
    if (!topWin.doctigoMic || !topWin.doctigoMic.ok) {{ setStat('unsupported'); return; }}
    topWin.doctigoMic.toggle(LANG);
  }});

  function onMsg(e) {{
    if (!e || !e.data || e.data.source !== 'doctigoMic') return;
    if (e.data.type === 'status') setStat(e.data.payload);
  }}
  ifrWin.addEventListener('message', onMsg);
}})();
</script>
""",
        height=48,
        scrolling=False,
    )
