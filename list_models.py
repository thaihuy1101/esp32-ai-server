import google.generativeai as genai
genai.configure(api_key="AQ.Ab8RN6J4LQwuQnZuGuT7TAUQc20Ql6aNY2Fg1--BTXw2NZr1PQ")
for m in genai.list_models():
    print(m.name)
