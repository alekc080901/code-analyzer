import requests
import uuid
import base64
import os
import urllib3
import json

# Отключаем предупреждения о самоподписанных сертификатах (для Sber API часто нужно)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GigaChatClient:
    def __init__(self):
        # Получаем данные из переменных окружения
        self.auth_key = os.getenv('GIGACHAT_AUTH_KEY')
        self.scope = os.getenv('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
        self.oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        self.api_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        self.access_token = None

        if not self.auth_key:
            print("Warning: GIGACHAT_AUTH_KEY not set in environment variables.")

    def get_token(self):
        if not self.auth_key:
            print("Cannot get token: GIGACHAT_AUTH_KEY is missing.")
            return

        rq_uid = str(uuid.uuid4())
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': rq_uid,
            'Authorization': f'Basic {self.auth_key}'
        }
        payload = {'scope': self.scope}

        try:
            response = requests.post(self.oauth_url, headers=headers, data=payload, verify=False)
            response.raise_for_status()
            self.access_token = response.json()['access_token']
            print("GigaChat token received successfully.")
        except Exception as e:
            print(f"Error getting GigaChat token: {e}")
            self.access_token = None

    def analyze_text(self, text: str) -> str:
        if not self.auth_key:
             return "GigaChat is not configured (missing auth key)."

        if not self.access_token:
            self.get_token()
        
        if not self.access_token:
            return "Failed to authenticate with GigaChat."

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }

        # Обрезаем текст, чтобы влезть в контекст
        truncated_text = text[:18000] # GigaChat держит большой контекст, но бережем токены

        payload = {
            "model": "GigaChat",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты эксперт по анализу кода и распределенных систем (микросервисов). Твоя задача - находить ошибки, проблемы с производительностью и давать рекомендации по изменению кода."
                },
                {
                    "role": "user",
                    "content": f"Проанализируй следующие данные (код и трейсы) и предложи изменения в коде в формате git diff. На выходе должен получиться краткий список проблем и предложенные исправления в коде.\n\n{truncated_text}"
                }
            ],
            "temperature": 0.7
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, verify=False)
            
            # Если токен протух (401), пробуем обновить один раз
            if response.status_code == 401:
                print("Token expired, refreshing...")
                self.get_token()
                headers['Authorization'] = f'Bearer {self.access_token}'
                response = requests.post(self.api_url, headers=headers, json=payload, verify=False)

            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"Error interacting with GigaChat: {str(e)}"

# Singleton instance
gigachat = GigaChatClient()

def analyze_code(content: str) -> str:
    return gigachat.analyze_text(content)
