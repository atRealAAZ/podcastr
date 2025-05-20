from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import arxiv
import json
from datetime import datetime
from config import SAVED_ARTICLES_DIR, MAX_RESULTS, get_today_folder
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Optional, Dict
import os
import re
from openai import OpenAI

app = FastAPI()

# Configure OpenAI
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Article(BaseModel):
    title: str
    description: str
    link: str
    published: str

class RankedArticle(Article):
    score: float
    reasoning: str

class SearchResponse(BaseModel):
    articles: List[RankedArticle]
    llm_reasoning: str

def sanitize_filename(title):
    """Convert title to a valid filename"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Limit length
    return filename[:100]

def rank_articles_by_profile(articles: List[Article], profile: str, num_results: int) -> SearchResponse:
    """Use LLM to rank articles based on user profile"""
    if not profile:
        return SearchResponse(
            articles=[RankedArticle(**article.dict(), score=0.0, reasoning="No profile provided") for article in articles[:num_results]],
            llm_reasoning="No profile was provided for ranking."
        )
    
    try:
        # Prepare the prompt for the LLM
        articles_text = "\n\n".join([
            f"Article {i+1}:\nTitle: {article.title}\nSummary: {article.description}"
            for i, article in enumerate(articles)
        ])
        
        prompt = f"""Given the following user profile and list of articles, analyze and rank the articles based on their relevance to the user's research profile, expertise, and interests.

User Profile:
{profile}

Articles:
{articles_text}

For each article, provide:
1. A relevance score (0-100)
2. A brief explanation of why this article matches or doesn't match the profile

Format your response as follows:
RANKINGS:
1: [article number], [score]
2: [article number], [score]
(etc.)

EXPLANATIONS:
[article number]: [explanation]
[article number]: [explanation]
(etc.)

SUMMARY:
[Brief overall explanation of your ranking decisions]"""

        # Get LLM response
        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[
                {"role": "system", "content": "You are a research paper recommendation system. Your task is to analyze articles and match them with a user's research profile. Provide detailed reasoning for your selections."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        # Parse the response
        response_text = response.choices[0].message.content
        sections = response_text.split('\n\n')
        
        # Parse rankings
        rankings_section = next(s for s in sections if s.startswith('RANKINGS:'))
        rankings = {}
        for line in rankings_section.split('\n')[1:]:  # Skip the "RANKINGS:" header
            if ':' in line:
                num, score = line.split(':')[1].split(',')
                rankings[int(num.strip())] = float(score.strip())

        # Parse explanations
        explanations_section = next(s for s in sections if s.startswith('EXPLANATIONS:'))
        explanations = {}
        for line in explanations_section.split('\n')[1:]:  # Skip the "EXPLANATIONS:" header
            if ':' in line:
                num, explanation = line.split(':', 1)
                explanations[int(num.strip())] = explanation.strip()

        # Get summary
        summary_section = next(s for s in sections if s.startswith('SUMMARY:'))
        summary = summary_section.replace('SUMMARY:', '').strip()

        # Create ranked articles
        ranked_articles = []
        for article_num, score in rankings.items():
            if article_num - 1 < len(articles):
                article = articles[article_num - 1]
                ranked_article = RankedArticle(
                    **article.dict(),
                    score=score,
                    reasoning=explanations.get(article_num, "No explanation provided")
                )
                ranked_articles.append(ranked_article)

        # Sort by score and take top num_results
        ranked_articles.sort(key=lambda x: x.score, reverse=True)
        ranked_articles = ranked_articles[:num_results]

        return SearchResponse(
            articles=ranked_articles,
            llm_reasoning=summary
        )

    except Exception as e:
        print(f"Error in LLM ranking: {str(e)}")
        return SearchResponse(
            articles=[RankedArticle(**article.dict(), score=0.0, reasoning="Ranking failed") for article in articles[:num_results]],
            llm_reasoning=f"Error during ranking: {str(e)}"
        )

@app.get("/search/{query}")
async def search_articles(
    query: str,
    max_results: int = 50,
    display_results: int = 10,
    profile: Optional[str] = None
):
    try:
        # Clean and format the query
        query = query.strip()
        
        # Create the search with proper parameters
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending
        )
        
        # Collect all results
        results = []
        for result in search.results():
            article = Article(
                title=result.title,
                description=result.summary,
                link=result.entry_id,
                published=str(result.published)
            )
            results.append(article)
            if len(results) >= max_results:
                break
        
        # Filter results based on profile if provided
        search_response = rank_articles_by_profile(results, profile, display_results)
        
        return search_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save")
async def save_articles(articles: List[Article]):
    try:
        # Get today's folder
        folder_path = get_today_folder()
        
        # Download PDFs for each article
        saved_files = []
        for article in articles:
            try:
                # Extract the arxiv ID from the link
                arxiv_id = article.link.split('/')[-1]
                
                # Create a search for this specific paper
                search = arxiv.Search(id_list=[arxiv_id])
                result = next(search.results())
                
                # Download the PDF
                safe_title = sanitize_filename(article.title)
                
                # Download to temp location
                result.download_pdf(folder_path, f"{arxiv_id}.pdf")
                
                
            except Exception as article_error:
                print(f"Error processing article {article.title}: {str(article_error)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing article {article.title}: {str(article_error)}"
                )
        
        return {
            "message": f"Articles saved as PDFs in {os.path.basename(folder_path)} folder",
            "saved_files": saved_files
        }
    except Exception as e:
        print(f"Error in save_articles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 