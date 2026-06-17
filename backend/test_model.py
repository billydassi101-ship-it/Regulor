from model_router import ask_mistral


response = ask_mistral([
    {"role": "user", "content": "Explique brièvement ce qu'est une banque."}
])

print("\n")
print(response)
print("\n")