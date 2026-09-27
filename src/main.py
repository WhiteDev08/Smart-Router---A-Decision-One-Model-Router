from fastapi import FastAPI,HTTPException
import time
from pydantic import BaseModel
from typing import Optional
from src.jev import classify_question
from src.database import insert_state,get_state
from src.models import call_coding_model,call_general_query_model,call_summary_model
from fastapi.middleware.cors import CORSMiddleware

class UserState(BaseModel):
    user_id:str
    ques:str
    genre:Optional[str]=None
    jev_output:Optional[dict]=None
    answer:Optional[str]=None


app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health():
    return {"status":"running"}


@app.post("/route_state")
async def route_state(state:UserState):

    try:
        question=state.ques


        start_time = time.perf_counter()

        jev_output=classify_question(question)

        end_time = time.perf_counter()

        jev_time=end_time-start_time
        
        sorted_op = dict(sorted(jev_output.items(), key=lambda x: x[1], reverse=True))

        genre = next(iter(sorted_op.keys()))

        state.genre=genre
        state.jev_output=jev_output

        await insert_state(state)

        return {'genre':genre,'jev_output':jev_output,'jev_time': round(jev_time, 3)}

    
    except Exception as e:
        return {"error":str(e)}


@app.post("/generate")
async def generate(user_id:str):

    try:
        state=await get_state(user_id)
        
        if not state:
            raise HTTPException(status_code=404,detail="User state not found!")
        
        state.pop("_id")

        question=state["ques"]
        genre=state["genre"]

        if genre=="coding":
            answer=await call_coding_model(question)
        elif genre=="general_query":
            answer=await call_general_query_model(question)
        elif genre=="summary":
            answer=await call_summary_model(question)
        else:
            raise HTTPException(status_code=400,detail="Invalid genre!")
        
        state["answer"]=answer


        await insert_state(UserState(**state))

        return {'answer':answer,'message':'Answer inserted successfully!'}
    
    except HTTPException :
        raise 

    except Exception as e:
        return {"error":str(e)}
