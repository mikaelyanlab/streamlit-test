# app.py — Insect–Microbe Systems Course Network (works w/ in-component passport)
# -------------------------------------------------------------------
# Zero fragile Streamlit↔PyVis bridge. The graph + passport render in one component.
# - Auto-loads /mnt/data/course_cleaned.csv (9 columns)
# - Uploads are self-healed to 9 fields, robust to stray commas/quotes
# - Edges by shared keywords (slider) + manual connect_with IDs
# - Clicking a node shows a "Session Passport" panel reliably
# -------------------------------------------------------------------

from __future__ import annotations
import io, csv, json, pathlib
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from typing import List, Dict, Any

DEFAULT_COLUMNS = [
    "session_id","date","title","instructor","module",
    "activity","keywords","notes","connect_with"
]

SAMPLE_ROWS=[{
    "session_id":"W1-Tu","date":"2026-01-13",
    "title":"Systems Bootcamp – Insects as Systems within Systems",
    "instructor":"You","module":"Systems Bootcamp",
    "activity":"Interactive lecture",
    "keywords":"systems thinking, feedback loops",
    "notes":"Define balancing and reinforcing loops.",
    "connect_with":""
}]

DEFAULT_DATA_PATH = "/mnt/data/course_cleaned.csv"

def _clean_keywords(s:str)->List[str]:
    if pd.isna(s) or not str(s).strip(): return []
    toks=[t.strip().lower() for t in str(s).replace(";",",").split(",")]
    return sorted({t for t in toks if t})

def _split_multi(s:str)->List[str]:
    if pd.isna(s) or not str(s).strip(): return []
    return [t.strip() for t in str(s).replace(";",",").split(",") if t.strip()]

def _load_csv_from_disk(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, header=0)
    # Ensure columns match expectations (they do for your cleaned file)
    missing = [c for c in DEFAULT_COLUMNS if c not in df.columns]
    if missing:
        # If anything missing, coerce to the expected shape
        df = df.reindex(columns=DEFAULT_COLUMNS, fill_value="")
    return df.fillna("")

def _load_csv_uploaded(file_obj) -> pd.DataFrame:
    """Self-heal to 9 columns. Accepts weird commas/quotes/whitespace."""
    raw=file_obj.read().decode("utf-8",errors="replace")
    raw=(raw.replace("\r\n","\n").replace("\r","\n")
            .replace("“",'"').replace("”",'"')
            .replace("‘","'").replace("’","'")
            .replace("\u00A0"," "))
    reader=csv.reader(io.StringIO(raw))
    rows=[r for r in reader if any(r)]
    clean=[]
    for r in rows:
        if len(r)<9: r+=['']*(9-len(r))
        elif len(r)>9: r=r[:9]
        clean.append(r)
    # Use header if first row looks like it; else inject defaults
    if clean and set(h.lower() for h in clean[0]) & {"session_id","title","keywords"}:
        header=clean[0]; data=clean[1:]
    else:
        header=DEFAULT_COLUMNS; data=clean
    df=pd.DataFrame(data,columns=header).fillna("")
    # Coerce to expected names/order if needed
    df = df.rename(columns={
        "session id":"session_id",
        "connect":"connect_with"
    })
    for col in DEFAULT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[DEFAULT_COLUMNS]

def _build_graph_data(df: pd.DataFrame, min_shared: int, include_manual: bool) -> Dict[str, Any]:
    """Prepare node & edge lists for vis.js, and lookup map for passports."""
    # Nodes + metadata
    nodes=[]
    lookup={}
    kw_map={}
    for _, r in df.iterrows():
        sid = str(r["session_id"]).strip()
        if not sid:
            continue
        node = {
            "id": sid,
            "label": sid,
            "title": f"{r['title']}<br>{r['module']}",
            # color by module in JS; here we just carry module through
            "module": r["module"] or "Unassigned",
        }
        nodes.append(node)
        lookup[sid] = {
            "session_id": sid,
            "date": r["date"],
            "title": r["title"],
            "instructor": r["instructor"],
            "module": r["module"] or "Unassigned",
            "activity": r["activity"],
            "keywords": r["keywords"],
            "notes": r["notes"],
        }
        kw_map[sid] = set(_clean_keywords(r["keywords"]))

    # Edges by shared keywords
    edges=[]
    sids=[n["id"] for n in nodes]
    for i in range(len(sids)):
        for j in range(i+1,len(sids)):
            a,b=sids[i],sids[j]
            shared=len(kw_map.get(a,set()) & kw_map.get(b,set()))
            if shared>=min_shared:
                edges.append({"from":a,"to":b,"width":1})

    # Manual edges
    if include_manual:
        for _, r in df.iterrows():
            a = str(r["session_id"]).strip()
            for b in _split_multi(r.get("connect_with","")):
                if a and b and a!=b and b in lookup:
                    edges.append({"from":a,"to":b,"width":1})

    # modules for coloring
    modules = sorted({n["module"] for n in lookup.values()})
    return {
        "nodes": nodes,
        "edges": edges,
        "lookup": lookup,
        "modules": modules
    }

# --------------------------- Streamlit UI ---------------------------

st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")
st.title("Insect–Microbe Systems — Course Network")

# Data state
if "sessions" not in st.session_state:
    # Try to boot with your cleaned file
    try:
        st.session_state.sessions = _load_csv_from_disk(DEFAULT_DATA_PATH)
        st.caption(f"Loaded default dataset from `{DEFAULT_DATA_PATH}`.")
    except Exception:
        st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)
        st.warning("Default dataset not found; using sample row.")

with st.sidebar.expander("📂 Data", expanded=True):
    # Download current sessions
    buf=io.StringIO()
    st.session_state.sessions.to_csv(buf, index=False)
    st.download_button("⬇️ Download sessions.csv", data=buf.getvalue(),
                       file_name="sessions.csv", mime="text/csv")

    up=st.file_uploader("Upload sessions.csv", type=["csv"])
    if up is not None:
        try:
            df=_load_csv_uploaded(up)
            st.session_state.sessions = df
            st.success(f"✅ CSV loaded ({len(df)} sessions).")
        except Exception as e:
            st.error(f"Upload failed: {e}")

with st.sidebar.expander("⚙️ Network Settings", expanded=True):
    min_shared = st.slider("Min shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)

# Build graph data
df = st.session_state.sessions.copy()
graph = _build_graph_data(df, min_shared=min_shared, include_manual=include_manual)

# Color palette (cycled in JS)
PALETTE = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
           "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]

# Render a single component that contains the graph + passport
html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="https://unpkg.com/vis-network@9.1.6/dist/vis-network.min.js"></script>
  <link href="https://unpkg.com/vis-network@9.1.6/styles/vis-network.min.css" rel="stylesheet" type="text/css" />
  <style>
    body {{ margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }}
    .wrap {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 16px;
      height: 720px;
      box-sizing: border-box;
      padding: 8px;
    }}
    #network {{
      width: 100%;
      height: 100%;
      border: 1px solid #ddd;
      border-radius: 10px;
    }}
    .passport {{
      height: 100%;
      border: 1px solid #ddd;
      border-radius: 10px;
      padding: 12px 14px;
      overflow:auto;
      background:#fafafa;
    }}
    .muted {{ color:#666; }}
    .chip {{
      display:inline-block; padding:2px 8px; margin:2px 4px 0 0; border-radius:999px; background:#eef; font-size:12px;
    }}
    h3 {{ margin-top:0; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div id="network"></div>
    <div class="passport" id="passport">
      <p class="muted">Click a node to view its Session Passport.</p>
    </div>
  </div>

  <script>
    // ----- data from Python -----
    const DATA = {json.dumps(graph)};
    const PALETTE = {json.dumps(PALETTE)};
    const modules = DATA.modules;
    const colorMap = {{}};
    modules.forEach((m,i)=> colorMap[m] = PALETTE[i % PALETTE.length]);

    // Build vis nodes/edges with colors
    const visNodes = DATA.nodes.map(n => {{
      const mod = DATA.lookup[n.id]?.module || "Unassigned";
      return {{
        id: n.id,
        label: n.label,
        title: n.title,
        color: colorMap[mod] || "#777",
        shape: "dot",
        size: 18
      }};
    }});
    const visEdges = DATA.edges;

    // ----- render network -----
    const container = document.getElementById('network');
    const network = new vis.Network(container, {{
      nodes: new vis.DataSet(visNodes),
      edges: new vis.DataSet(visEdges),
    }}, {{
      physics: {{
        enabled: true,
        forceAtlas2Based: {{
          gravitationalConstant: -50,
          centralGravity: 0.02,
          springLength: 120,
          avoidOverlap: 0.3
        }},
        solver: 'forceAtlas2Based',
        stabilization: true
      }},
      interaction: {{
        hover: true,
        tooltipDelay: 120
      }},
      edges: {{
        width: 1,
        smooth: {{ type: 'continuous' }}
      }},
      nodes: {{
        font: {{ color: '#111' }}
      }}
    }});

    // ----- passport panel -----
    const P = document.getElementById('passport');
    function renderPassport(id) {{
      const r = DATA.lookup[id];
      if(!r) {{
        P.innerHTML = '<p class="muted">No data found for '+id+'</p>';
        return;
      }}
      const chips = (r.keywords || '')
        .split(',')
        .map(s => s.trim())
        .filter(Boolean)
        .map(k => '<span class="chip">'+k+'</span>')
        .join(' ');
      P.innerHTML = `
        <h3>🪲 ${'{'}r.title{'}'}</h3>
        <p><strong>Date:</strong> ${'{'}r.date || '-'{'}'} &nbsp;|&nbsp;
           <strong>Module:</strong> ${'{'}r.module || 'Unassigned'{'}'} &nbsp;|&nbsp;
           <strong>Activity:</strong> ${'{'}r.activity || '-'{'}'}</p>
        <p><strong>Instructor:</strong> ${'{'}r.instructor || '-'{'}'}</p>
        <p><strong>Keywords:</strong><br>${'{'}chips || '<span class="muted">—</span>'{'}'}</p>
        <p><strong>Notes:</strong><br>${'{'}(r.notes || '').replace(/\\n/g,'<br>') || '<span class="muted">—</span>'{'}'}</p>
      `;
    }}

    network.on('selectNode', (params) => {{
      if (params.nodes && params.nodes.length) {{
        renderPassport(params.nodes[0]);
      }}
    }});
  </script>
</body>
</html>
"""

components.html(html, height=740, scrolling=False)
