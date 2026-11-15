"""Small official v2 components: viewport events and a working clipboard action."""

import streamlit as st

_viewport = st.components.v2.component("k50_viewport", js="""
export default function({setStateValue}) {
  let previous = '';
  function update() {
    const value = {mode: window.innerWidth >= 1280 ? 'desktop' :
      window.innerWidth >= 768 ? 'tablet' : 'mobile', height: Math.round(window.innerHeight / 50) * 50};
    const next = JSON.stringify(value);
    if (next !== previous) { previous = next; setStateValue('viewport', value); }
  }
  update(); window.addEventListener('resize', update);
  return () => window.removeEventListener('resize', update);
}
""")

_copy = st.components.v2.component("k50_copy", html="""
<button type="button">⧉ &nbsp;Sao chép</button><span role="status" aria-live="polite"></span>
<textarea aria-label="Sao chép thủ công" hidden readonly></textarea>
""", css="""
:host {font: 12px system-ui; color:var(--st-text-color);}
button {min-height:44px; padding:6px 12px; border-radius:9px; cursor:pointer;
border:1px solid var(--st-border-color, #94a3b8); background:var(--st-background-color); color:inherit; font:inherit;}
button:focus-visible {outline:3px solid var(--st-primary-color);outline-offset:2px;}
span {padding-left:10px;} textarea {width:95%;height:100px;}
""", js="""
export default function({parentElement, data}) {
 const button = parentElement.querySelector('button'), status = parentElement.querySelector('span');
 button.onclick = async () => {
   try {await navigator.clipboard.writeText(data.text); status.textContent = 'Đã sao chép';}
   catch (_) {const t = parentElement.querySelector('textarea'); t.hidden=false; t.value=data.text;
     t.focus(); t.select(); status.textContent='Nhấn ⌘C hoặc Ctrl+C để sao chép';}
 };
 return () => {button.onclick=null;};
}
""")


def viewport():
    result = _viewport(key="viewport", default={"viewport": {"mode": "desktop", "height": 900}},
                       height=0, on_viewport_change=lambda: None)
    return result.viewport or {"mode": "desktop", "height": 900}


def copy_answer(text, key):
    _copy(data={"text": text}, key=key, height="content")
