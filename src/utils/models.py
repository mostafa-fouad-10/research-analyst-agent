from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from dotenv import load_dotenv
import os
from langchain_ollama import ChatOllama
load_dotenv()

llm=ChatOllama(model="qwen3:1.7b")


# llm=ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct",temperature=0)
# llm=ChatGoogleGenerativeAI(model="gemini-3.8-flash",temperature=0)



# chat_model = HuggingFaceEndpoint(
#     repo_id="meta-llama/Llama-3.3-70B-Instruct",
#     task="conversation",
#     max_new_tokens=512,
#     do_sample=False,
#     repetition_penalty=1.03,
#     provider="auto",  # let Hugging Face choose the best provider for you
#     huggingfacehub_api_token=os.environ['HF_TOKEN']
# )

# llm = ChatHuggingFace(llm=chat_model)