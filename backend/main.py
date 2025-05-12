from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import arxiv
import json
from datetime import datetime
from config import SAVED_ARTICLES_DIR, MAX_RESULTS, get_today_folder
from pydantic import BaseModel
from typing import List
import os
import re

app = FastAPI()

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

def sanitize_filename(title):
    """Convert title to a valid filename"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Limit length
    return filename[:100]

@app.get("/search/{query}")
async def search_articles(query: str, max_results: int = 1):
    try:
        # Clean and format the query
        query = query.strip()
        
        # Create the search with proper parameters
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,  # Changed to Relevance for better results
            sort_order=arxiv.SortOrder.Descending
        )
        
        results = []
        for result in search.results():
            article = Article(
                title=result.title,
                description=result.summary,
                link=result.entry_id,
                published=str(result.published)
            )
            results.append(article)
            # Break if we've reached max_results
            if len(results) >= max_results:
                break
        
        return results
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