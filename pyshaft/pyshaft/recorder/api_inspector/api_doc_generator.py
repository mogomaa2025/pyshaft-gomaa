"""PyShaft API Inspector — HTML Documentation Generator."""

import json
from typing import Any
from pyshaft.recorder.api_inspector.api_models import ApiWorkflow, ApiFolder, ApiRequestStep, AssertionType

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - PyShaft API Docs</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/ajv/8.12.0/ajv7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/renderjson@1.4.0/renderjson.min.js"></script>
    <style>
        :root {{
            --bg-page: #0D1117;
            --bg-card: #161B22;
            --bg-hover: #21283B;
            --text-primary: #E6EDF3;
            --text-secondary: #8B949E;
            --border: #30363D;
            --accent-purple: #6C63FF;
            --method-get: #3FB950;
            --method-post: #58A6FF;
            --method-put: #D29922;
            --method-delete: #F85149;
            --method-patch: #E3B341;
            --btn-run: #238636;
            --btn-run-hover: #2EA043;
        }}
        
        @media (prefers-color-scheme: light) {{
            :root {{
                --bg-page: #F6F8FA;
                --bg-card: #FFFFFF;
                --bg-hover: #E1E4E8;
                --text-primary: #24292E;
                --text-secondary: #586069;
                --border: #E1E4E8;
            }}
        }}

        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            background-color: var(--bg-page);
            color: var(--text-primary);
            line-height: 1.5;
            margin: 0;
            padding: 0;
            display: flex;
        }}
        
        .sidebar {{
            width: 300px;
            background-color: var(--bg-card);
            border-right: 1px solid var(--border);
            height: 100vh;
            overflow-y: auto;
            position: fixed;
            padding: 20px;
        }}
        
        .content {{
            flex: 1;
            margin-left: 300px;
            padding: 40px;
            max-width: 1000px;
        }}
        
        h1, h2, h3, h4 {{ color: var(--text-primary); }}
        h1 {{ border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-top: 0; }}
        
        .nav-item {{ margin: 5px 0; }}
        .nav-link {{
            color: var(--text-secondary);
            text-decoration: none;
            display: block;
            padding: 5px 10px;
            border-radius: 6px;
        }}
        .nav-link:hover {{
            background-color: var(--bg-hover);
            color: var(--text-primary);
        }}
        
        .folder {{ font-weight: bold; margin-top: 15px; color: var(--text-primary); }}
        .folder-children {{ margin-left: 15px; border-left: 1px solid var(--border); padding-left: 10px; }}
        
        .request-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 30px;
        }}
        
        .method-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
            color: white;
            margin-right: 10px;
        }}
        .GET {{ background-color: var(--method-get); }}
        .POST {{ background-color: var(--method-post); }}
        .PUT {{ background-color: var(--method-put); }}
        .DELETE {{ background-color: var(--method-delete); }}
        .PATCH {{ background-color: var(--method-patch); }}
        
        .url {{
            font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
            color: var(--text-secondary);
            word-break: break-all;
        }}
        
        .section-title {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
            margin: 20px 0 10px 0;
            font-weight: 600;
        }}
        
        pre {{
            background-color: var(--bg-page);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 15px;
            overflow-x: auto;
            font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
            font-size: 13px;
            margin: 0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
        }}
        th, td {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background-color: var(--bg-page);
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
        }}
        
        /* Interactive UI */
        .try-it-out {{
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px dashed var(--border);
        }}
        
        input.edit-url {{
            width: 100%;
            padding: 8px;
            background: var(--bg-page);
            color: var(--text-primary);
            border: 1px solid var(--border);
            border-radius: 4px;
            font-family: monospace;
            margin-bottom: 10px;
        }}
        
        textarea.edit-body {{
            width: 100%;
            height: 100px;
            padding: 8px;
            background: var(--bg-page);
            color: var(--text-primary);
            border: 1px solid var(--border);
            border-radius: 4px;
            font-family: monospace;
            margin-bottom: 10px;
        }}
        
        button.btn-run {{
            background-color: var(--btn-run);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            cursor: pointer;
        }}
        button.btn-run:hover {{
            background-color: var(--btn-run-hover);
        }}
        
        .live-response-container {{
            display: none;
            margin-top: 15px;
            border: 1px solid var(--border);
            border-radius: 6px;
            overflow: hidden;
        }}
        .live-response-header {{
            background-color: var(--bg-page);
            padding: 8px 15px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .status-badge {{
            font-size: 12px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        .status-success {{ background-color: var(--method-get); color: white; }}
        .status-error {{ background-color: var(--method-delete); color: white; }}
        
        .schema-badge {{
            margin-left: 10px;
            font-size: 12px;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid currentColor;
        }}
        .schema-pass {{ color: var(--method-get); }}
        .schema-fail {{ color: var(--method-delete); }}
        
        .schema-block {{
            background: rgba(108, 99, 255, 0.1);
            border-left: 3px solid var(--accent-purple);
            padding: 10px;
            margin-bottom: 15px;
            border-radius: 0 4px 4px 0;
        }}
        
        /* renderjson styling */
        .renderjson a {{ text-decoration: none; cursor: pointer; }}
        .renderjson .disclosure {{ color: var(--accent-purple); font-size: 14px; margin-right: 5px; }}
        .renderjson .syntax {{ color: var(--text-secondary); }}
        .renderjson .string {{ color: #A5D6FF; }}
        .renderjson .number {{ color: #79C0FF; }}
        .renderjson .boolean {{ color: #56D364; }}
        .renderjson .key {{ color: #7EE787; font-weight: bold; }}
        .renderjson .keyword {{ color: #FF7B72; }}
        .renderjson .object.syntax {{ color: var(--text-secondary); }}
        .renderjson .array.syntax {{ color: var(--text-secondary); }}
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>{title}</h2>
        <div class="nav-tree">
            {nav_html}
        </div>
    </div>
    
    <div class="content">
        <h1>{title}</h1>
        {content_html}
    </div>

    <script>
        const ajv = new window.ajv7();
        renderjson.set_show_to_level(2);
        
        async function runRequest(reqId) {{
            const btn = document.getElementById(`btn_${{reqId}}`);
            const urlInput = document.getElementById(`url_${{reqId}}`);
            const corsToggle = document.getElementById(`cors_${{reqId}}`);
            const method = btn.getAttribute('data-method');
            const schemaStr = btn.getAttribute('data-schema');
            const bodyInput = document.getElementById(`body_${{reqId}}`);
            
            let url = urlInput.value;
            if (corsToggle && corsToggle.checked) {{
                url = "https://corsproxy.io/?" + encodeURIComponent(url);
            }}
            
            let options = {{ method: method, headers: {{}} }};
            
            // Extract headers from the table if they exist
            const headerTable = document.getElementById(`headers_${{reqId}}`);
            if (headerTable) {{
                const rows = headerTable.querySelectorAll('tr.header-row');
                rows.forEach(r => {{
                    const key = r.querySelector('.h-key').innerText;
                    const val = r.querySelector('.h-val').innerText;
                    options.headers[key] = val;
                }});
            }}
            
            if (bodyInput && bodyInput.value) {{
                options.body = bodyInput.value;
                if (!options.headers['Content-Type']) {{
                    options.headers['Content-Type'] = 'application/json';
                }}
            }}
            
            btn.innerText = "Running...";
            const respContainer = document.getElementById(`live_resp_container_${{reqId}}`);
            const respBody = document.getElementById(`live_resp_body_${{reqId}}`);
            const statusBadge = document.getElementById(`live_resp_status_${{reqId}}`);
            const schemaBadge = document.getElementById(`live_schema_status_${{reqId}}`);
            
            respContainer.style.display = "block";
            respBody.innerHTML = "Waiting for response...";
            statusBadge.className = "status-badge";
            statusBadge.innerText = "PENDING";
            schemaBadge.style.display = "none";
            
            try {{
                const response = await fetch(url, options);
                let dataText = await response.text();
                let parsedJson = null;
                
                try {{
                    parsedJson = JSON.parse(dataText);
                    respBody.innerHTML = "";
                    respBody.appendChild(renderjson(parsedJson));
                }} catch (e) {{
                    respBody.innerText = dataText;
                }}
                
                statusBadge.innerText = `${{response.status}} ${{response.statusText}}`;
                if (response.ok) {{
                    statusBadge.classList.add("status-success");
                }} else {{
                    statusBadge.classList.add("status-error");
                }}
                
                // Schema Validation
                if (schemaStr && parsedJson) {{
                    try {{
                        const schemaObj = JSON.parse(schemaStr);
                        const validate = ajv.compile(schemaObj);
                        const valid = validate(parsedJson);
                        schemaBadge.style.display = "inline-block";
                        if (valid) {{
                            schemaBadge.innerText = "Schema: PASSED ✓";
                            schemaBadge.className = "schema-badge schema-pass";
                        }} else {{
                            schemaBadge.innerText = "Schema: FAILED ✗";
                            schemaBadge.className = "schema-badge schema-fail";
                            console.error("Schema errors:", validate.errors);
                            respBody.innerText = "SCHEMA VALIDATION ERRORS:\\n" + JSON.stringify(validate.errors, null, 2) + "\\n\\nRESPONSE BODY:\\n" + dataText;
                        }}
                    }} catch (e) {{
                        console.error("Schema evaluation error", e);
                    }}
                }}
                
            }} catch (err) {{
                respBody.innerText = `Fetch Error: ${{err.message}}\\n\\nNote: If the API blocks CORS, requests from this HTML file will fail.`;
                statusBadge.innerText = "ERROR";
                statusBadge.classList.add("status-error");
            }} finally {{
                btn.innerText = "▶ Run Request";
            }}
        }}
        
        function renderStaticJson(containerId, jsonStr) {{
            try {{
                const parsed = JSON.parse(jsonStr);
                const container = document.getElementById(containerId);
                if (container) {{
                    container.innerHTML = "";
                    container.appendChild(renderjson(parsed));
                }}
            }} catch (e) {{}}
        }}
    </script>
</body>
</html>
"""

def _build_nav(items: list, prefix="") -> str:
    html = ""
    for idx, item in enumerate(items):
        if isinstance(item, ApiFolder):
            html += f'<div class="folder">{item.name}</div>'
            html += f'<div class="folder-children">{_build_nav(item.items, prefix + str(idx) + "_")}</div>'
        elif isinstance(item, ApiRequestStep):
            anchor = f"req_{prefix}{idx}"
            html += f'<div class="nav-item"><a href="#{anchor}" class="nav-link"><span style="font-size: 10px; font-weight: bold;" class="{item.method}">{item.method}</span> {item.name}</a></div>'
    return html

def _generate_shape(data: Any) -> Any:
    """Generate a Swagger-style type placeholder shape from a JSON object."""
    if isinstance(data, dict):
        return {k: _generate_shape(v) for k, v in data.items()}
    elif isinstance(data, list):
        if len(data) > 0:
            return [_generate_shape(data[0])]
        return []
    elif isinstance(data, bool):
        return False
    elif isinstance(data, int):
        return 0
    elif isinstance(data, float):
        return 0.0
    elif isinstance(data, str):
        return "string"
    elif data is None:
        return "null"
    return "unknown"

def _build_content(items: list, prefix="", variables: dict = None) -> str:
    if variables is None: variables = {}
    
    def resolve(val: str) -> str:
        for k, v in variables.items():
            val = val.replace(f"{{{{{k}}}}}", str(v))
        return val

    html = ""
    for idx, item in enumerate(items):
        if isinstance(item, ApiFolder):
            html += f'<div class="folder-content" style="margin-top: 40px;"><h2>📁 {item.name}</h2>'
            html += _build_content(item.items, prefix + str(idx) + "_", variables)
            html += '</div>'
        elif isinstance(item, ApiRequestStep):
            req_id = f"{prefix}{idx}"
            anchor = f"req_{req_id}"
            
            # Find Schema
            schema_str = ""
            if item.assertions:
                for a in item.assertions:
                    if a.type == AssertionType.JSON_SCHEMA:
                        try:
                            # Pre-validate it's valid JSON
                            json.loads(a.expected_value)
                            schema_str = a.expected_value
                            break
                        except:
                            pass
                            
            # Auto-generate schema shape if missing but we have a response
            if not schema_str and getattr(item, "last_response", None):
                try:
                    shape_dict = _generate_shape(item.last_response)
                    schema_str = json.dumps(shape_dict, indent=4)
                except:
                    pass
            
            html += f'<div id="{anchor}" class="request-card">'
            html += f'<h3><span class="method-badge {item.method}">{item.method}</span> {item.name}</h3>'
            
            # Request UI
            url = resolve(item.url or item.endpoint or "")
            
            html += '<div class="try-it-out">'
            html += f'<input type="text" id="url_{req_id}" class="edit-url" value="{url}" placeholder="https://api.example.com/endpoint" />'
            
            if item.headers:
                html += f'<table id="headers_{req_id}"><tr><th>Key</th><th>Value</th></tr>'
                for k, v in item.headers.items():
                    html += f'<tr class="header-row"><td class="h-key">{k}</td><td class="h-val">{resolve(str(v))}</td></tr>'
                html += '</table>'
            
            if item.payload:
                ps = resolve(str(item.payload))
                try:
                    payload_str = json.dumps(json.loads(ps), indent=2)
                except:
                    payload_str = ps
                html += f'<textarea id="body_{req_id}" class="edit-body">{payload_str}</textarea>'
                
            safe_schema_str = schema_str.replace('"', '&quot;').replace("'", "&#39;")
            html += f'''
            <div style="margin-bottom: 10px;">
                <label style="font-size: 13px; color: var(--text-secondary); cursor: pointer;">
                    <input type="checkbox" id="cors_{req_id}" /> Bypass CORS using public proxy (corsproxy.io)
                </label>
            </div>
            '''
            html += f'<button id="btn_{req_id}" class="btn-run" data-method="{item.method}" data-schema="{safe_schema_str}" onclick="runRequest(\'{req_id}\')">▶ Run Request</button>'
            html += '</div>'
            
            # Live Response View
            html += f'''
            <div id="live_resp_container_{req_id}" class="live-response-container">
                <div class="live-response-header">
                    <div>Live Response <span id="live_schema_status_{req_id}" class="schema-badge" style="display:none;"></span></div>
                    <span id="live_resp_status_{req_id}" class="status-badge"></span>
                </div>
                <div id="live_resp_body_{req_id}" style="padding: 15px; font-family: monospace; font-size: 13px; overflow-x: auto;"></div>
            </div>
            '''
            
            # Static example response
            if getattr(item, "last_response", None):
                html += '<div class="section-title" style="margin-top: 30px;">Example Response (Static)</div>'
                try:
                    resp_str = json.dumps(item.last_response, indent=2) if isinstance(item.last_response, (dict, list)) else str(item.last_response)
                except:
                    resp_str = str(item.last_response)
                
                safe_resp_str = resp_str.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                status_color = "var(--method-get)" if getattr(item, "last_status", 0) < 400 else "var(--method-delete)"
                html += f'<div style="font-size: 12px; font-weight: bold; margin-bottom: 5px; color: {status_color}">Status: {getattr(item, "last_status", "Unknown")}</div>'
                html += f'<div id="static_resp_{req_id}" style="background-color: var(--bg-page); border: 1px solid var(--border); border-radius: 6px; padding: 15px; overflow-x: auto; font-family: monospace; font-size: 13px;"><pre><code>{resp_str}</code></pre></div>'
                html += f'<script>renderStaticJson("static_resp_{req_id}", "{safe_resp_str}");</script>'
                
                if schema_str:
                    safe_schema_json = schema_str.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                    html += '<div class="section-title" style="margin-top: 15px;">Response Schema</div>'
                    html += f'<div id="static_schema_{req_id}" class="schema-block" style="padding: 15px; font-family: monospace; font-size: 13px; overflow-x: auto;"><pre><code>{schema_str}</code></pre></div>'
                    html += f'<script>renderStaticJson("static_schema_{req_id}", "{safe_schema_json}");</script>'
            elif schema_str:
                safe_schema_json = schema_str.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                html += '<div class="section-title" style="margin-top: 30px;">Expected JSON Schema</div>'
                html += f'<div id="static_schema_{req_id}" class="schema-block" style="padding: 15px; font-family: monospace; font-size: 13px; overflow-x: auto;"><pre><code>{schema_str}</code></pre></div>'
                html += f'<script>renderStaticJson("static_schema_{req_id}", "{safe_schema_json}");</script>'
                
            html += '</div>'
    return html

def generate_html_docs(item: ApiWorkflow | ApiFolder | ApiRequestStep, save_path: str, variables: dict = None) -> None:
    """Generate a standalone HTML documentation file for the given item."""
    
    if isinstance(item, ApiWorkflow):
        title = "API Workflow Documentation"
        items_list = item.items
    elif isinstance(item, ApiFolder):
        title = f"Folder: {item.name}"
        items_list = item.items
    elif isinstance(item, ApiRequestStep):
        title = f"Request: {item.name}"
        items_list = [item]
    else:
        title = "API Documentation"
        items_list = []
        
    nav_html = _build_nav(items_list)
    content_html = _build_content(items_list, variables=variables)
    
    final_html = _HTML_TEMPLATE.format(
        title=title,
        nav_html=nav_html,
        content_html=content_html
    )
    
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(final_html)
