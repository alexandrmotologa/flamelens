"""Standalone interactive HTML/SVG FlameGraph exporter without external CDN dependencies."""

from __future__ import annotations

import json
from pathlib import Path

from flamelens.core.stack_tree import StackTree


def export_to_html(
    tree: StackTree,
    output_path: str | Path,
    title: str = "FlameLens Memory Allocation Profile",
) -> None:
    """Generate self-contained interactive HTML/SVG FlameGraph document."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tree_dict = tree.to_dict()
    tree_json = json.dumps(tree_dict)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: #121212;
      color: #e0e0e0;
      padding: 20px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 1px solid #333;
    }}
    h1 {{
      font-size: 20px;
      font-weight: 600;
      color: #ff9800;
    }}
    .stats {{
      font-size: 14px;
      color: #aaa;
    }}
    .controls {{
      display: flex;
      gap: 12px;
      align-items: center;
    }}
    input[type="text"] {{
      background: #222;
      border: 1px solid #444;
      color: #fff;
      padding: 6px 12px;
      border-radius: 4px;
      font-size: 14px;
      width: 250px;
    }}
    input[type="text"]:focus {{
      outline: none;
      border-color: #ff9800;
    }}
    button {{
      background: #333;
      color: #eee;
      border: 1px solid #555;
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
    }}
    button:hover {{
      background: #444;
    }}
    #flame-container {{
      width: 100%;
      overflow-x: auto;
      background: #181818;
      border: 1px solid #2a2a2a;
      border-radius: 6px;
      padding: 15px;
      min-height: 400px;
    }}
    .flame-row {{
      display: flex;
      height: 24px;
      margin-bottom: 2px;
      width: 100%;
    }}
    .flame-box {{
      height: 100%;
      display: flex;
      align-items: center;
      padding: 0 4px;
      font-size: 11px;
      color: #111;
      font-weight: 600;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
      cursor: pointer;
      border-right: 1px solid rgba(0,0,0,0.2);
      border-radius: 2px;
      transition: filter 0.15s ease;
    }}
    .flame-box:hover {{
      filter: brightness(1.25);
    }}
    .flame-box.highlight {{
      outline: 2px solid #e040fb;
    }}
    #tooltip {{
      position: absolute;
      display: none;
      background: #252525;
      color: #fff;
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 12px;
      pointer-events: none;
      border: 1px solid #444;
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
      z-index: 100;
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>FlameLens: {title}</h1>
      <div class="stats" id="stats-bar">Loading profile...</div>
    </div>
    <div class="controls">
      <input type="text" id="search-input" placeholder="Search function (e.g. Order)...">
      <button id="reset-zoom-btn">Reset Zoom</button>
    </div>
  </header>

  <div id="flame-container"></div>
  <div id="tooltip"></div>

  <script>
    const data = {tree_json};
    const container = document.getElementById("flame-container");
    const tooltip = document.getElementById("tooltip");
    const statsBar = document.getElementById("stats-bar");
    const searchInput = document.getElementById("search-input");
    const resetZoomBtn = document.getElementById("reset-zoom-btn");

    let currentRoot = data.root;
    let zoomHistory = [];

    function formatBytes(bytes) {{
      if (Math.abs(bytes) >= 1073741824) return (bytes / 1073741824).toFixed(2) + " GB";
      if (Math.abs(bytes) >= 1048576) return (bytes / 1048576).toFixed(2) + " MB";
      if (Math.abs(bytes) >= 1024) return (bytes / 1024).toFixed(2) + " KB";
      return bytes + " B";
    }}

    function getWarmColor(pct) {{
      const colors = [
        "#8B0000", "#B22222", "#D32F2F", "#E65100", "#F57C00",
        "#FF9800", "#FFA726", "#FFB74D", "#FFD54F", "#FFEE58"
      ];
      const idx = Math.min(colors.length - 1, Math.floor((pct / 100) * colors.length));
      return colors[idx];
    }}

    function renderTree(rootNode) {{
      container.innerHTML = "";
      const totalBytes = rootNode.inclusive_bytes || data.total_bytes;
      statsBar.textContent = `Total: ${{formatBytes(totalBytes)}} | Root: ${{rootNode.frame.name}}`;

      // Collect levels BFS
      const levels = [];
      function collect(node, depth) {{
        if (!levels[depth]) levels[depth] = [];
        levels[depth].push(node);
        const children = Object.values(node.children || {{}}).sort((a, b) => b.inclusive_bytes - a.inclusive_bytes);
        for (const child of children) {{
          collect(child, depth + 1);
        }}
      }}
      collect(rootNode, 0);

      // Render rows bottom-to-top (standard flamegraph order: root at bottom)
      for (let d = levels.length - 1; d >= 0; d--) {{
        const row = document.createElement("div");
        row.className = "flame-row";

        for (const node of levels[d]) {{
          const pct = (node.inclusive_bytes / totalBytes) * 100;
          if (pct < 0.1) continue;

          const box = document.createElement("div");
          box.className = "flame-box";
          box.style.width = pct + "%";
          box.style.backgroundColor = getWarmColor(pct);
          box.textContent = `${{node.frame.name}} (${{pct.toFixed(1)}}%)`;

          box.addEventListener("mouseenter", (e) => {{
            tooltip.style.display = "block";
            tooltip.innerHTML = `
              <strong>${{node.frame.name}}</strong><br>
              File: ${{node.frame.filename}}:${{node.frame.line_number}}<br>
              Inclusive: ${{formatBytes(node.inclusive_bytes)}} (${{pct.toFixed(1)}}%)<br>
              Self: ${{formatBytes(node.self_bytes)}}<br>
              Calls: ${{node.call_count}}
            `;
          }});

          box.addEventListener("mousemove", (e) => {{
            tooltip.style.left = (e.pageX + 12) + "px";
            tooltip.style.top = (e.pageY + 12) + "px";
          }});

          box.addEventListener("mouseleave", () => {{
            tooltip.style.display = "none";
          }});

          box.addEventListener("click", () => {{
            if (node !== currentRoot) {{
              zoomHistory.push(currentRoot);
              currentRoot = node;
              renderTree(currentRoot);
            }}
          }});

          row.appendChild(box);
        }}
        container.appendChild(row);
      }}
      applySearch();
    }}

    function applySearch() {{
      const query = searchInput.value.trim().toLowerCase();
      document.querySelectorAll(".flame-box").forEach(el => {{
        if (query && el.textContent.toLowerCase().includes(query)) {{
          el.classList.add("highlight");
        }} else {{
          el.classList.remove("highlight");
        }}
      }});
    }}

    searchInput.addEventListener("input", applySearch);

    resetZoomBtn.addEventListener("click", () => {{
      currentRoot = data.root;
      zoomHistory = [];
      renderTree(currentRoot);
    }});

    renderTree(currentRoot);
  </script>
</body>
</html>
"""

    path.write_text(html_content, encoding="utf-8")
