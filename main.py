from src.pipelines.pipeline import run_research_pipeline
from src.tools.tools import web_search, scrape_url

def main():
    print("Hello from multi-agent!")
    run_research_pipeline("The impact of AI on healthcare")

if __name__ == "__main__":
    main()
