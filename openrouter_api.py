#!/usr/bin/env python
# -*- coding: utf-8 -*-

from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)


def summarize_text(text, len, model="meta-llama/llama-4-maverick:free"):
  completion = client.chat.completions.create(
    model=model,
    messages=[
        {
          "role": "user",
          "content": u"请把以下文本缩写为{0}字左右的摘要，保留关键信息，直接给出结果：\n\n{1}\n\n摘要：".format(len, text)
        }
      ]
    )
  try:
    response = completion.choices[0].message.content
  except Exception as e:
    print(e)
    return u"获取摘要失败"

  return response


if __name__ == "__main__":
  text = u"""二愣子睁大着双眼，直直望着茅草和烂泥糊成的黑屋顶，身上盖着的旧棉被，已呈深黄色，看不出原来的本来面目，还若有若无的散发着淡淡的霉味。"""
  print(summarize_text(text, 10, "meta-llama/llama-4-maverick:free"))