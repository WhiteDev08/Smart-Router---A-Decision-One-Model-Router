from langchain.chat_models import init_chat_model
from src.prompts import coding_prompt,general_query_prompt,summary_prompt

llm=init_chat_model("google_genai:gemini-2.5-flash")


async def call_coding_model(question:str):
    prompt=coding_prompt.format(question=question)

    response=await llm.ainvoke(prompt)

    return response.content

async def call_general_query_model(question:str):
    prompt=general_query_prompt.format(question=question)

    response=await llm.ainvoke(prompt)

    return response.content

async def call_summary_model(question:str):
    prompt=summary_prompt.format(question=question)
    
    response=await llm.ainvoke(prompt)

    return response.content
