"""API skill for Nanobricks.

Exposes nanobricks as REST API endpoints using FastAPI.
"""

from typing import Any

import uvicorn

from nanobricks.protocol import T_deps, T_in, T_out
from nanobricks.skill import NanobrickEnhanced, Skill, register_skill


def create_api_endpoint(brick, path: str, method: str = "POST"):
    """Create a FastAPI endpoint for a brick.

    This function is used at runtime when the API server is started.
    """
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel, create_model
    except ImportError:
        raise ImportError(
            "FastAPI is required for the API skill. "
            "Install it with: pip install fastapi uvicorn"
        )

    # Create input/output models dynamically
    # This is a simplified version - in production you'd want more sophisticated type mapping
    InputModel = create_model(
        f"{brick.name}Input",
        data=(Any, ...),  # Accept any data
    )

    OutputModel = create_model(
        f"{brick.name}Output",
        result=(Any, ...),  # Return any data
    )

    async def endpoint(request: InputModel) -> OutputModel:
        """API endpoint that invokes the brick."""
        try:
            result = await brick.invoke(request.data)
            return OutputModel(result=result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return endpoint, InputModel, OutputModel


@register_skill("api")
class SkillApi(Skill[T_in, T_out, T_deps]):
    """Exposes a nanobrick as a REST API endpoint.

    Config options:
        - path: API endpoint path (default: /{brick_name})
        - method: HTTP method (default: POST)
        - host: Host to bind to (default: 0.0.0.0)
        - port: Port to bind to (default: 8000)
        - auto_start: Start server immediately (default: False)
        - docs: Enable API docs (default: True)
    """

    def _create_enhanced_brick(self, brick):
        # Get config
        path = self.config.get("path", f"/{brick.name}")
        method = self.config.get("method", "POST")
        host = self.config.get("host", "0.0.0.0")
        port = self.config.get("port", 8000)
        auto_start = self.config.get("auto_start", False)
        enable_docs = self.config.get("docs", True)

        # Store API app reference
        api_app = None

        class ApiEnhanced(NanobrickEnhanced[T_in, T_out, T_deps]):
            def __init__(self, wrapped, skill):
                super().__init__(wrapped, skill)
                self._api_app = None
                self._server = None

            async def invoke(self, input: T_in, *, deps: T_deps | None = None) -> T_out:
                # Normal invocation - just pass through
                return await self._wrapped.invoke(input, deps=deps)

            def create_app(self) -> Any:
                """Create the FastAPI app."""
                try:
                    from fastapi import FastAPI
                except ImportError:
                    raise ImportError(
                        "FastAPI is required for the API skill. "
                        "Install it with: pip install fastapi uvicorn"
                    )

                # Create FastAPI app
                app = FastAPI(
                    title=f"{self._wrapped.name} API",
                    version=self._wrapped.version,
                    docs_url="/docs" if enable_docs else None,
                    redoc_url="/redoc" if enable_docs else None,
                )

                # Create endpoint
                endpoint, InputModel, OutputModel = create_api_endpoint(
                    self._wrapped, path, method
                )

                # Add route based on method
                if method.upper() == "GET":
                    app.get(path, response_model=OutputModel)(endpoint)
                elif method.upper() == "POST":
                    app.post(path, response_model=OutputModel)(endpoint)
                elif method.upper() == "PUT":
                    app.put(path, response_model=OutputModel)(endpoint)
                elif method.upper() == "DELETE":
                    app.delete(path, response_model=OutputModel)(endpoint)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Add health check
                @app.get("/health")
                async def health():
                    return {"status": "healthy", "brick": self._wrapped.name}

                # Add root endpoint with HTML interface
                from fastapi.responses import HTMLResponse

                @app.get("/", response_class=HTMLResponse)
                async def root():
                    html_content = f"""
                    <html>
                        <head>
                            <title>{self._wrapped.name} API</title>
                            <style>
                                body {{
                                    font-family: -apple-system, system-ui, sans-serif;
                                    max-width: 800px;
                                    margin: 0 auto;
                                    padding: 2rem;
                                    background: #f5f5f5;
                                }}
                                .container {{
                                    background: white;
                                    padding: 2rem;
                                    border-radius: 8px;
                                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                }}
                                h1 {{ color: #333; }}
                                .form-group {{
                                    margin-bottom: 1rem;
                                }}
                                label {{
                                    display: block;
                                    margin-bottom: 0.5rem;
                                    font-weight: 600;
                                }}
                                textarea {{
                                    width: 100%;
                                    padding: 0.5rem;
                                    border: 1px solid #ddd;
                                    border-radius: 4px;
                                    font-family: monospace;
                                    resize: vertical;
                                }}
                                button {{
                                    background: #007bff;
                                    color: white;
                                    border: none;
                                    padding: 0.5rem 1rem;
                                    border-radius: 4px;
                                    cursor: pointer;
                                    font-size: 16px;
                                }}
                                button:hover {{
                                    background: #0056b3;
                                }}
                                #result {{
                                    margin-top: 1rem;
                                    padding: 1rem;
                                    background: #f8f9fa;
                                    border-radius: 4px;
                                    font-family: monospace;
                                    white-space: pre-wrap;
                                }}
                                .links {{
                                    margin-top: 2rem;
                                    padding-top: 1rem;
                                    border-top: 1px solid #eee;
                                }}
                                a {{
                                    color: #007bff;
                                    text-decoration: none;
                                    margin-right: 1rem;
                                }}
                                a:hover {{
                                    text-decoration: underline;
                                }}
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <h1>🧱 {self._wrapped.name}</h1>
                                <p>Version: {self._wrapped.version}</p>
                                
                                <div class="form-group">
                                    <label for="input">Input:</label>
                                    <textarea id="input" rows="4" placeholder="Enter your input here...">Hello world!</textarea>
                                </div>
                                
                                <button onclick="sendRequest()">Analyze</button>
                                
                                <div id="result"></div>
                                
                                <div class="links">
                                    <a href="/docs">📚 API Documentation</a>
                                    <a href="/health">❤️ Health Check</a>
                                </div>
                            </div>
                            
                            <script>
                                async function sendRequest() {{
                                    const input = document.getElementById('input').value;
                                    const resultDiv = document.getElementById('result');
                                    
                                    resultDiv.textContent = 'Loading...';
                                    
                                    try {{
                                        const response = await fetch('{path}', {{
                                            method: '{method}',
                                            headers: {{
                                                'Content-Type': 'application/json'
                                            }},
                                            body: JSON.stringify({{ input: input }})
                                        }});
                                        
                                        const data = await response.json();
                                        resultDiv.textContent = JSON.stringify(data, null, 2);
                                    }} catch (error) {{
                                        resultDiv.textContent = 'Error: ' + error.message;
                                    }}
                                }}
                            </script>
                        </body>
                    </html>
                    """
                    return html_content

                self._api_app = app
                return app

            def start_server(self, host: str = None, port: int = None):
                """Start the API server."""
                if not self._api_app:
                    self.create_app()

                # Use provided or default host/port
                _host = host or self._skill.config.get("host", "0.0.0.0")
                _port = port or self._skill.config.get("port", 8000)

                print(f"🌐 Starting API server for {self._wrapped.name}")
                print(f"📍 Endpoint: http://{_host}:{_port}{path}")
                if enable_docs:
                    print(f"📚 Docs: http://{_host}:{_port}/docs")

                # Run the server
                uvicorn.run(self._api_app, host=_host, port=_port)

        # Create enhanced brick
        enhanced = ApiEnhanced(brick, self)

        # Auto-start if configured
        if auto_start:
            # Note: This would block, so typically you'd run in a thread
            # For now, we'll just print a message
            print("ℹ️  API skill configured. Call .start_server() to start the API")

        return enhanced
