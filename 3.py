
from openai import OpenAI

client = OpenAI(api_key="sk-8f41d90f670e40dc99658b3ad2826e4f", base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-reasoner",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "你好啊"},
    ],
    stream=False
)

print(response.choices[0].message.content)