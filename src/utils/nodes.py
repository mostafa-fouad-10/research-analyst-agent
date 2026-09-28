from src.utils.states import GenerateAnalystsState, InterviewState, SearchQuery, ResearchGraphState
from src.utils.objects import Perspectives, Analyst
from src.utils.models import llm
from langchain.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from src.utils.prompts import analyst_instructions, search_instructions,question_instructions, answer_instructions, section_writer_instructions,intro_conclusion_instructions,report_writer_instructions
from langgraph.types import interrupt
from langchain_tavily import TavilySearch
from langchain_core.messages import get_buffer_string

load_dotenv()


# nodes
def create_analysts(state: GenerateAnalystsState):
    
    """ Create analysts """
    
    topic=state['topic']
    max_analysts=state['max_analysts']
    human_analyst_feedback=state.get('human_analyst_feedback', '')
        
    # Enforce structured output
    structured_llm = llm.with_structured_output(Perspectives)

    # System message
    system_message = analyst_instructions.format(topic=topic,
                                                            human_analyst_feedback=human_analyst_feedback, 
                                                            max_analysts=max_analysts)

    # Generate question 
    analysts = structured_llm.invoke([SystemMessage(content=system_message)]+[HumanMessage(content="Generate the set of analysts.")])
    
    # Write the list of analysis to state
    return {"analysts": analysts.analysts}


def human_feedback(state: GenerateAnalystsState):
    feedback = interrupt({
        "question": "Are these analysts okay?",
        "analysts": [
            analyst.model_dump() if hasattr(analyst, "model_dump") else analyst
            for analyst in state.get("analysts", [])
        ],
        "instructions": "Return feedback to regenerate analysts, or return empty/perfect/continue to approve."
    })

    if feedback is None:
        return {"human_analyst_feedback": None}

    if isinstance(feedback, str):
        feedback = feedback.strip()

        if feedback == "":
            return {"human_analyst_feedback": None}

        if feedback.lower() in {"perfect", "continue", "approved", "yes"}:
            return {"human_analyst_feedback": None}

        return {"human_analyst_feedback": feedback}

    return {"human_analyst_feedback": None}

def generate_question(state: InterviewState):
    """ Node to generate a question """

    # Get state
    analyst = state["analyst"]
    if isinstance(analyst, dict):
        analyst = Analyst.model_validate(analyst)
    messages = state["messages"]

    # Generate question 
    system_message = question_instructions.format(goals=analyst.persona)
    question = llm.invoke([SystemMessage(content=system_message)]+messages)
        
    # Write messages to state
    return {"messages": [question]}

def search_web(state: InterviewState):
    """ Retrieve docs from web search """
    print("BEFORE STRUCTURED INVOKE")

    # Search query
    structured_llm = llm.with_structured_output(SearchQuery)
    messages = [
        SystemMessage(content=search_instructions),
        *state["messages"],
        HumanMessage(content="Generate the search query.")
    ]
    
    search_query = structured_llm.invoke(messages)
    
    # Search
    tavily_search = TavilySearch(max_results=3)
    #search_docs = tavily_search.invoke(search_query.search_query) # updated 1.0
    data = tavily_search.invoke({"query": search_query.search_query})
    search_docs = data.get("results", data)
    

     # Format
    formatted_search_docs = "\n\n---\n\n".join(
        [
            f'<Document href="{doc["url"]}"/>\n{doc["content"]}\n</Document>'
            for doc in search_docs
        ]
    )

    return {"context": [formatted_search_docs]}

def search_web2(state: InterviewState):

    """ Retrieve docs from web search """
    print("BEFORE STRUCTURED INVOKE")

    # Search query
    structured_llm = llm.with_structured_output(SearchQuery)
    messages = [
    SystemMessage(content=search_instructions),
    *state["messages"],
    HumanMessage(content="Generate the search query.")
]

    search_query = structured_llm.invoke(messages)
    
    # Search
    tavily_search = TavilySearch(max_results=3)
    #search_docs = tavily_search.invoke(search_query.search_query) # updated 1.0
    data = tavily_search.invoke({"query": search_query.search_query})
    search_docs = data.get("results", data)
    

     # Format
    formatted_search_docs = "\n\n---\n\n".join(
        [
            f'<Document href="{doc["url"]}"/>\n{doc["content"]}\n</Document>'
            for doc in search_docs
        ]
    )

    return {"context": [formatted_search_docs]}


def generate_answer(state: InterviewState):
    
    """ Node to answer a question """

    # Get state
    analyst = state["analyst"]
    messages = state["messages"]
    context = state["context"]

    if isinstance(analyst, dict):
            analyst = Analyst.model_validate(analyst)

    # Answer question
    system_message = answer_instructions.format(goals=analyst.persona, context=context)
    answer = llm.invoke([SystemMessage(content=system_message)]+messages)
            
    # Name the message as coming from the expert
    answer.name = "expert"
    
    # Append it to state
    return {"messages": [answer]}



def save_interview(state: InterviewState):
    """ Save interviews """

    # Get messages
    messages = state["messages"]
    
    # Convert interview to a string
    interview = get_buffer_string(messages)
    
    # Save to interviews key
    return {"interview": interview}

def write_section(state: InterviewState):
    """ Node to answer a question """
    # Get state
    interview = state["interview"]
    context = state["context"]
    analyst = state["analyst"]

    if isinstance(analyst, dict):
            analyst = Analyst.model_validate(analyst)
    
    # Write section using either the gathered source docs from interview (context) or the interview itself (interview)
    system_message = section_writer_instructions.format(focus=analyst.description)
    section = llm.invoke([SystemMessage(content=system_message)]+[HumanMessage(content=f"Use this source to write your section: {context}")]) 
                
    # Append it to state
    return {"sections": [section.content]}

def write_report(state: ResearchGraphState):
    # Full set of sections
    sections = state["sections"]
    topic = state["topic"]

    # Concat all sections together
    formatted_str_sections = "\n\n".join([f"{section}" for section in sections])
    
    # Summarize the sections into a final report
    system_message = report_writer_instructions.format(topic=topic, context=formatted_str_sections)    
    report = llm.invoke([SystemMessage(content=system_message)]+[HumanMessage(content=f"Write a report based upon these memos.")]) 
    return {"content": report.content}

def write_introduction(state: ResearchGraphState):
    # Full set of sections
    sections = state["sections"]
    topic = state["topic"]

    # Concat all sections together
    formatted_str_sections = "\n\n".join([f"{section}" for section in sections])
    
    # Summarize the sections into a final report
    
    instructions = intro_conclusion_instructions.format(topic=topic, formatted_str_sections=formatted_str_sections)    
    intro = llm.invoke([SystemMessage(content=instructions)]+[HumanMessage(content=f"Write the report introduction")]) 
    return {"introduction": intro.content}

def write_conclusion(state: ResearchGraphState):

    # Full set of sections
    sections = state["sections"]
    topic = state["topic"]

    # Concat all sections together
    formatted_str_sections = "\n\n".join([f"{section}" for section in sections])
    
    # Summarize the sections into a final report
    
    instructions = intro_conclusion_instructions.format(topic=topic, formatted_str_sections=formatted_str_sections)    
    conclusion = llm.invoke([SystemMessage(content=instructions)]+[HumanMessage(content=f"Write the report conclusion")]) 
    return {"conclusion": conclusion.content}

# def finalize_report(state: ResearchGraphState):
#     """ The is the "reduce" step where we gather all the sections, combine them, and reflect on them to write the intro/conclusion """
#     # Save full final report
#     print("FINALIZE START")
#     content = state["content"]
#     if content.startswith("## Insights"):
#         content = content.strip("## Insights")
#     if "## Sources" in content:
#         try:
#             content, sources = content.split("\n## Sources\n")
#         except:
#             sources = None
#     else:
#         sources = None

#     final_report = state["introduction"] + "\n\n---\n\n" + content + "\n\n---\n\n" + state["conclusion"]
#     if sources is not None:
#         final_report += "\n\n## Sources\n" + sources
#     return {"final_report": final_report}

import re

def finalize_report(state: ResearchGraphState):
    """Combine introduction, body and conclusion into the final report."""
    content = state["content"].strip()

    # Remove a leading "## Insights" heading (the old .strip() removed characters, not a prefix)
    content = content.removeprefix("## Insights").lstrip()

    # Split off the Sources section (tolerates trailing spaces after the heading)
    parts = re.split(r"\n## Sources[ \t]*\n", content, maxsplit=1)
    content = parts[0].strip()
    sources = parts[1].strip() if len(parts) == 2 else None

    final_report = (
        state["introduction"].strip()
        + "\n\n---\n\n"
        + content
        + "\n\n---\n\n"
        + state["conclusion"].strip()
    )
    if sources:
        final_report += "\n\n## Sources\n" + sources

    return {"final_report": final_report}