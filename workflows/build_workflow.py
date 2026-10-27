"""Generate the n8n workflow JSON from the Python prompt and schema, so the two can't drift.

    python workflows/build_workflow.py --prompt v2 --model qwen3:8b > workflows/reqcheck.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent.prompts import PROMPTS  # noqa: E402
from agent.schema import ReviewV1  # noqa: E402

OLLAMA = "http://localhost:11434"
QDRANT = "http://localhost:6333"
COLLECTION = "requirements_v1"


def build(prompt_version, model, k, num_ctx):
    system, _ = PROMPTS[prompt_version]
    schema = ReviewV1.model_json_schema()

    build_prompt = f"""const body = $('Webhook').first().json.body;
const hits = $input.first().json.result.points
  .map(p => [p.payload.req_id, p.payload.text])
  .filter(([id]) => id !== body.req_id)
  .slice(0, {k});
const ctx = hits.map(([id, t]) => `- ${{id}}: ${{t}}`).join('\\n');
const user = `Related requirements for context:\\n${{ctx}}\\n\\nReview this requirement:\\n${{body.req_id}}: ${{body.text}}`;
return [{{ json: {{
  model: {json.dumps(model)},
  messages: [{{ role: 'system', content: {json.dumps(system)} }}, {{ role: 'user', content: user }}],
  format: {json.dumps(schema)},
  think: false,
  stream: false,
  options: {{ temperature: 0, seed: 0, num_ctx: {num_ctx} }},
}} }}];"""

    parse = """const body = $('Webhook').first().json.body;
const review = JSON.parse($input.first().json.message.content);
return [{ json: {
  req_id: body.req_id,
  analysis: review.analysis,
  findings: review.findings.map(f => ({ req_id: body.req_id, ...f })),
} }];"""

    def http(name, pos, url, body):
        return {"parameters": {"method": "POST", "url": url, "sendBody": True, "specifyBody": "json",
                               "jsonBody": body, "options": {"timeout": 300000}},
                "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": pos}

    nodes = [
        {"parameters": {"httpMethod": "POST", "path": "reqcheck", "responseMode": "responseNode", "options": {}},
         "name": "Webhook", "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 0],
         "webhookId": "reqcheck-webhook"},
        http("Embed query", [220, 0], f"{OLLAMA}/api/embed",
             '={{ JSON.stringify({ model: "nomic-embed-text", input: "search_query: " + $json.body.text }) }}'),
        http("Search Qdrant", [440, 0], f"{QDRANT}/collections/{COLLECTION}/points/query",
             f'={{{{ JSON.stringify({{ query: $json.embeddings[0], limit: {k + 1}, with_payload: true }}) }}}}'),
        {"parameters": {"jsCode": build_prompt}, "name": "Build prompt", "type": "n8n-nodes-base.code",
         "typeVersion": 2, "position": [660, 0]},
        http("Ollama review", [880, 0], f"{OLLAMA}/api/chat", "={{ JSON.stringify($json) }}"),
        {"parameters": {"jsCode": parse}, "name": "Parse findings", "type": "n8n-nodes-base.code",
         "typeVersion": 2, "position": [1100, 0]},
        {"parameters": {"respondWith": "firstIncomingItem", "options": {}}, "name": "Respond",
         "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1, "position": [1320, 0]},
    ]
    names = [n["name"] for n in nodes]
    connections = {a: {"main": [[{"node": b, "type": "main", "index": 0}]]} for a, b in zip(names, names[1:])}
    return {"name": "reqcheck", "nodes": nodes, "connections": connections, "settings": {"executionOrder": "v1"}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prompt", default="v2", choices=PROMPTS)
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--num-ctx", type=int, default=8192)
    a = ap.parse_args()
    print(json.dumps(build(a.prompt, a.model, a.k, a.num_ctx), indent=2))
