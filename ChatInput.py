# ChatInput.py
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components

def chat_input(placeholder: str = "Type your message...", key: str = "chat_input"):
    """
    Fixed bottom input like ChatGPT with mic + send.
    Returns the submitted text (str) once, else None.
    """
    html = f"""
    <style>
      .chatbar-wrap {{
        position: fixed;
        left: 0; right: 0; bottom: 0;
        padding: 12px 16px;
        background: rgba(250,250,250,0.90);
        backdrop-filter: saturate(1.2) blur(6px);
        border-top: 1px solid rgba(0,0,0,0.08);
        z-index: 9999;
      }}
      .chatbar {{
        max-width: 920px; margin: 0 auto;
        display: grid; grid-template-columns: 44px 1fr 44px; gap: 8px;
        align-items: center;
      }}
      .btn {{
        height: 44px; width: 44px; border-radius: 12px; border: 1px solid #e5e7eb;
        background: white; cursor: pointer; font-size: 18px;
      }}
      .btn:active {{ transform: scale(0.98); }}
      .input {{
        width: 100%; height: 44px; border-radius: 12px; border: 1px solid #e5e7eb;
        padding: 0 12px; font-size: 14px; outline: none; background: white;
      }}
      .pill {{
        position: fixed; bottom: 72px; left: 50%; transform: translateX(-50%);
        background: #111827; color: #f9fafb; padding: 6px 10px; border-radius: 999px; font-size: 12px; display:none;
      }}
      @media (max-width: 640px) {{
        .chatbar {{ max-width: 100%; grid-template-columns: 44px 1fr 44px; }}
      }}
      /* Prevent Streamlit footer overlapping */
      footer {{ margin-bottom: 64px; }}
    </style>

    <div class="chatbar-wrap">
      <div class="chatbar">
        <button id="micBtn" class="btn" title="Voice input">🎤</button>
        <input id="msgInput" class="input" type="text" placeholder="{placeholder.replace('"','&quot;')}" />
        <button id="sendBtn" class="btn" title="Send">➤</button>
      </div>
    </div>
    <div id="micState" class="pill">Listening…</div>

    <script>
      const streamlitKey = "{key}";
      const input = document.getElementById("msgInput");
      const sendBtn = document.getElementById("sendBtn");
      const micBtn = document.getElementById("micBtn");
      const micState = document.getElementById("micState");

      // Focus the input on load
      setTimeout(() => input && input.focus(), 50);

      // Submit helper -> send value to Streamlit as this component's return value
      function submitValue(val) {{
        const payload = {{
          type: "streamlit:setComponentValue",
          value: val,
          key: streamlitKey,
        }};
        window.parent.postMessage(payload, "*");
      }}

      // Send on click
      sendBtn.addEventListener("click", () => {{
        const val = input.value.trim();
        if (val.length) {{
          submitValue(val);
          input.value = "";
        }}
      }});

      // Send on Enter
      input.addEventListener("keydown", (e) => {{
        if (e.key === "Enter" && !e.shiftKey) {{
          e.preventDefault();
          const val = input.value.trim();
          if (val.length) {{
            submitValue(val);
            input.value = "";
          }}
        }}
      }});

      // Voice input via Web Speech API
      let recognition = null;
      let listening = false;

      function showMic(state) {{
        micState.style.display = state ? "inline-block" : "none";
        micBtn.textContent = state ? "⏹" : "🎤";
        micBtn.title = state ? "Stop" : "Voice input";
      }}

      function initRecognition() {{
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {{
          alert("Voice input not supported in this browser.");
          return null;
        }}
        const r = new SR();
        r.lang = navigator.language || "en-US";
        r.interimResults = true;
        r.continuous = false;
        r.maxAlternatives = 1;
        r.onresult = (ev) => {{
          let txt = "";
          for (let i = ev.resultIndex; i < ev.results.length; i++) {{
            txt += ev.results[i][0].transcript;
          }}
          input.value = txt;
        }};
        r.onend = () => {{
          listening = false;
          showMic(false);
        }};
        r.onerror = () => {{
          listening = false;
          showMic(false);
        }};
        return r;
      }}

      micBtn.addEventListener("click", () => {{
        if (!recognition) recognition = initRecognition();
        if (!recognition) return;

        if (!listening) {{
          try {{
            recognition.start();
            listening = true;
            showMic(true);
          }} catch(e) {{}}
        }} else {{
          try {{
            recognition.stop();
          }} catch(e) {{}}
        }}
      }});

      // Announce component ready so Streamlit can mount it
      window.parent.postMessage({{
        type: "streamlit:componentReady",
        key: streamlitKey,
      }}, "*");
    </script>
    """
    # The components.html return value is captured from postMessage "streamlit:setComponentValue"
    val = components.html(html, height=84, scrolling=False)
    # components.html returns a DeltaGenerator; Streamlit captures the value via session_state
    # Retrieve and clear once
    ss_key = f"ComponentValue.{key}"
    if ss_key in st.session_state:
        out = st.session_state[ss_key]
        # clear after read
        del st.session_state[ss_key]
        return out
    return None
