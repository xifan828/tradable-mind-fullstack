"""Custom authentication for the deployed LangGraph server.

Tradable Mind has no app-level user auth by design: the only secret is the
user's own Gemini key, which is held client-side and passed into the agent run
context per request. Locally (`langgraph dev`) there is no auth gate, so the
built-in run/stream endpoints and the custom `/api/*` + `/app` routes all work
from the browser with no headers.

On a managed Cloud deployment, however, the platform protects the built-in
LangGraph API routes (`/threads`, `/runs`, ...) with a LangSmith-API-key gate by
default. The browser sends no such key, so the chat run returns
`403 {"detail":"Missing authentication headers"}` while the custom chart routes
(which are not behind that gate) keep working.

Registering a custom auth handler here *replaces* that default gate with our own.
This handler accepts every request as an anonymous user, restoring the keyless
behavior we have locally. There are no `@auth.on` authorization handlers, so the
default is to accept — matching the "no app auth" design.
"""

from langgraph_sdk import Auth

auth = Auth()


@auth.authenticate
async def authenticate() -> Auth.types.MinimalUserDict:
    """Accept all requests as a single anonymous user.

    The app intentionally exposes no protected resources, so we do not inspect
    any headers or tokens.
    """
    return {"identity": "anonymous", "is_authenticated": True, "permissions": []}
