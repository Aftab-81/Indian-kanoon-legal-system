from openai import OpenAI

client = OpenAI(
  base_url="https://api.openai.com/v1",
  api_key="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",
)

completion = client.chat.completions.create(
  extra_headers={
    "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
  },
  extra_body={},
  model="gpt-4-turbo",
  messages=[
    {
      "role": "user",
      "content": "What is the meaning of life?"
    }
  ]
)
print(completion.choices[0].message.content)