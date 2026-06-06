import os
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


class DocumentAnalysis(BaseModel):
    summary: str
    key_points: list[str]
    next_actions: list[str]


def analyze_document(content: str) -> DocumentAnalysis:
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Analiza el documento y devuelve: "
                    "un resumen breve, los puntos más importantes, "
                    "y las próximas acciones o tareas que se mencionan."
                ),
            },
            {"role": "user", "content": content},
        ],
        response_format=DocumentAnalysis,
    )
    return response.choices[0].message.parsed