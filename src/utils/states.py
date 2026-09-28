from typing_extensions import NotRequired,TypedDict,Annotated
from typing import Optional,List
from src.utils.objects import Analyst
from langgraph.graph import MessagesState
import operator
from pydantic import BaseModel, Field

class GenerateAnalystsState(TypedDict):
    topic: str # Research topic
    max_analysts: int # Number of analysts
    human_analyst_feedback: NotRequired[Optional[str]] # Human feedback
    analysts: NotRequired[List[Analyst]] # Analyst asking questions


class InterviewState(MessagesState):
    max_num_turns: int # Number turns of conversation
    context: Annotated[list, operator.add] # Source docs
    analyst: Analyst # Analyst asking questions
    interview: str # Interview transcript
    sections: Annotated[list, operator.add]



class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Search query for retrieval.")    


class ResearchGraphState(TypedDict):
    topic: str # Research topic
    max_analysts: int # Number of analysts
    human_analyst_feedback: NotRequired[Optional[str]] # Human feedback
    analysts: List[Analyst] # Analyst asking questions
    sections: Annotated[list, operator.add] # Send() API key
    introduction: str # Introduction for the final report
    content: str # Content for the final report
    conclusion: str # Conclusion for the final report
    final_report: str # Final report