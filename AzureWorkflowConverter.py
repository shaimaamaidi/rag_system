import os
from dotenv import load_dotenv
from openai import AzureOpenAI


class AzureWorkflowConverter:

    def __init__(self):
        load_dotenv()
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION")
        )

    def convert_to_json_workflow(self, mermaid_text: str) -> str:
        system_prompt = """
        You're a BPMN / Workflow Extraction Professional. 
        Your task is to convert a flowchart in Arabic (in Mermaid / flowchart syntax) into a precise JSON representation. 

        ═══════════════════════════════════════
        Rules:
        ═══════════════════════════════════════

        1. Extract all nodes, subgraphs, and edges exactly as they appear.
        2. Preserve the hierarchy: subgraphs must be included.
        3. Nodes:
           - ID: unique identifier (use the label or S<number> if given)
           - Label: Arabic text inside the node
           - Type: "process" for rectangles, "decision" for diamonds, "start" or "end" for rounded nodes
           - Subgraph: name of the group/subgraph
        4. Edges:
           - From: source node ID
           - To: target node ID
           - Label: edge label if any (optional)
        5. Maintain the sequence, decisions, and all branches.
        6. Output must be valid JSON only, with keys: "nodes" and "edges".
        7. Do NOT add, remove, or change any step.
        8. Use only the information in the provided flowchart.

        ═══════════════════════════════════════
        OUTPUT FORMAT
        ═══════════════════════════════════════

        {
          "workflow_title": "string",
          "lanes": ["lane name 1", "lane name 2"],
          "nodes": [
            {
              "id": "<original_id>",
              "node_text": "البداية",
              "type": "start|end|process|decision|connector",
              "lane": "swimlane name"
            }
          ],
          "edges": [
            {
              "from": "node_id",
              "to": "node_id",
              "condition": "نعم | لا | null"
            }
          ]
        }
        """

        user_prompt = f"""
        Convert the following Arabic flowchart into JSON following the system rules:

        --- MERMAID INPUT ---
        {mermaid_text}
        """
        response = self.client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

