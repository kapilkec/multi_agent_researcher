from src.agents.agents import build_search_agent, build_reader_agent, writer_chain, critic_chain

def run_research_pipeline(topic : str) -> dict:

    state = {}

    #search agent working 
    print( "\n"+" ="*50 )
    print("step 1 - search agent is working ...")
    print("="*50)

    search_agent = build_search_agent()
    search_result = search_agent.invoke(
        {
            "messages": [
                (
                    "user",
                    f"""
                    Search the internet for recent, publicly accessible information
                    about the topic: {topic}.

                    Use the available tools and return the results in a structured
                    format containing the title and URL for each result.
                    """,
                )
            ]
        }
    )
    state["search_results"] = search_result['messages'][-1].content

    print("\n search result ",state['search_results'])


    #step 2 - reader agent 
    print( "\n"+" ="*50 )
    print("step 2 - Reader agent is scraping top resources ...")
    print("="*50)
    reader_agent = build_reader_agent()
    reader_result = reader_agent.invoke({
        "messages": [
            (
                "user",
                f"Based on the following search results about '{topic}', "
                f"pick the most relevant URL and scrape it for deeper content.\n\n"
                f"Search Results:\n{state['search_results'][:800]}"
                f"Strictly use the url provided in the search results and do not return any information from other sources. Return the scraped content in a clean and readable format."
            )
        ]
    })

    def extract_text(msg) -> str:
        c = msg.content
        if isinstance(c, list):  # content-block form
            c = "".join(b.get("text", "") for b in c if isinstance(b, dict))
        c = (c or "").strip()
        if not c:  # reasoning-only turn
            c = (msg.additional_kwargs or {}).get("reasoning_content", "").strip()
        return c

    final_output = next(
        (t for m in reversed(reader_result["messages"])
        if m.type == "ai" and (t := extract_text(m))),
        None,
    )

    state['scraped_content'] = final_output if final_output else "No content could be scraped from the provided URLs."

    print("\nscraped content: \n", state["scraped_content"])

    #step 3 - writer chain 

    print("\n"+" ="*50)
    print("step 3 - Writer is drafting the report ...")
    print("="*50)

    research_combined = (
        f"SEARCH RESULTS : \n {state['search_results']} \n\n"
        f"DETAILED SCRAPED CONTENT : \n {state['scraped_content']}"
    )

    state["report"] = writer_chain.invoke({
        "topic" : topic,
        "research" : research_combined
    })

    print("\n Final Report\n",state['report'])

    #critic report 

    print("\n"+" ="*50)
    print("step 4 - critic is reviewing the report ")
    print("="*50)

    state["feedback"] = critic_chain.invoke({
        "report":state['report']
    })

    print("\n critic report \n", state['feedback'])

    return state