from src.tools.tools import web_search, scrape_url

def main():
    print("Hello from multi-agent!")
    # result = web_search.invoke("What is life")
    result = scrape_url.invoke("https://en.wikipedia.org/wiki/Artificial_general_intelligence")
    print(result[:1000])  

if __name__ == "__main__":
    main()
