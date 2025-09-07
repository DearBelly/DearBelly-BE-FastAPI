from app.core.config import settings
from openai import OpenAI
import json

client = OpenAI(api_key=settings.OPENAI_KEY)

class PregnancySafetyChecker:
    def __init__(self, client: OpenAI):
        self.client = client

    """
    - isSafe: 안전하면 1, 안전하지 않으면 0
    - description: 복용 가능 여부 설명
    """
    def ask_chatgpt_about_pregnancy_safety(self, pill_name: str) -> tuple[str, int]:
        prompt = f"""
        약 이름: {pill_name}
        질문: 이 약은 임산부가 복용해도 안전한가요? 복용 가능 여부와 주의사항을 알려주세요.
        description 안에는 문장마다 \\n 을 적용하세요.
        결과를 JSON 형식으로 정확히 반환하세요. 설명이나 다른 텍스트를 절대 덧붙이지 마세요.
        스키마:
        {{
            "description": "복용 가능 여부 및 주의사항에 대한 설명",
            "isSafe": 1 또는 0
        }}
        """

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=600,
            response_format={"type": "json_object"}
        )
        print("GPT Asking 성공...")
        raw = response.choices[0].message.content.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and start < end:
                data = json.loads(raw[start:end+1])
            else:
                # 디버깅
                preview = raw[:200].replace("\n", "\\n")
                raise ValueError(f"응답이 유효한 JSON이 아닙니다. preview='{preview}'")

        description = data.get("description")
        isSafe = data.get("isSafe")

        if isinstance(isSafe, bool):
            isSafe = 1 if isSafe else 0
        elif isinstance(isSafe, str):
            isSafe = 1 if isSafe.strip() in {"1", "true", "True"} else 0
        elif not isinstance(isSafe, int):
            isSafe = 0

        if not isinstance(description, str):
            description = ""  # 안전장치

        return description, int(isSafe)


checker = PregnancySafetyChecker(client)