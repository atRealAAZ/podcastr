import React, { useState } from 'react';
import {
  Container,
  Typography,
  TextField,
  Button,
  Box,
  Card,
  CardContent,
  CardActions,
  Link,
  CircularProgress,
  IconButton,
  Collapse,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import axios from 'axios';

interface Article {
  title: string;
  description: string;
  link: string;
  published: string;
  score: number;
  reasoning: string;
}

interface SearchResponse {
  articles: Article[];
  llm_reasoning: string;
}

function App() {
  const [query, setQuery] = useState('');
  const [maxSearchResults, setMaxSearchResults] = useState(50);
  const [displayResults, setDisplayResults] = useState(10);
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [expandedCard, setExpandedCard] = useState<number | null>(null);
  const [showProfileEditor, setShowProfileEditor] = useState(false);
  const [profile, setProfile] = useState(localStorage.getItem('userProfile') || '');
  const [showLog, setShowLog] = useState(false);
  const [llmReasoning, setLlmReasoning] = useState('');

  const handleSearch = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setError('');
    
    try {
      const response = await axios.get<SearchResponse>(`http://localhost:8000/search/${encodeURIComponent(query)}`, {
        params: {
          max_results: maxSearchResults,
          display_results: displayResults,
          profile: profile
        }
      });
      setArticles(response.data.articles);
      setLlmReasoning(response.data.llm_reasoning);
    } catch (err) {
      setError('Failed to fetch articles. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.post('http://localhost:8000/save', articles);
      alert('Articles saved successfully!');
    } catch (err) {
      setError('Failed to save articles. Please try again.');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const truncateText = (text: string, lines: number) => {
    const words = text.split(' ');
    const truncated = words.slice(0, lines * 10).join(' ');
    return truncated + (words.length > lines * 10 ? '...' : '');
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h2" component="h1" align="center" gutterBottom>
        Podcastr
      </Typography>
      
      <Box sx={{ display: 'flex', gap: 4 }}>
        {/* Left Column */}
        <Box sx={{ width: '250px', minHeight: '600px' }}>
          <Button
            variant="outlined"
            onClick={() => setShowProfileEditor(!showProfileEditor)}
            sx={{ width: '100%', mb: 2 }}
          >
            Edit Profile
          </Button>
          
          {showProfileEditor && (
            <Box sx={{ mb: 2, height: 'calc(100vh - 250px)' }}>
              <TextField
                fullWidth
                multiline
                rows={12}
                variant="outlined"
                label="Your Research Profile"
                placeholder="Describe your research interests, expertise, and preferences..."
                value={profile}
                onChange={(e) => setProfile(e.target.value)}
                sx={{ 
                  height: 'calc(100% - 50px)',
                  '& .MuiInputBase-root': {
                    height: '100%'
                  },
                  '& .MuiInputBase-input': {
                    height: '100% !important'
                  }
                }}
              />
              <Button
                variant="contained"
                onClick={() => {
                  localStorage.setItem('userProfile', profile);
                  setShowProfileEditor(false);
                }}
                sx={{ mt: 1, width: '100%' }}
              >
                Save Profile
              </Button>
            </Box>
          )}
        </Box>

        {/* Center Column */}
        <Box sx={{ flex: 1 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                fullWidth
                variant="outlined"
                placeholder="Search for articles..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <TextField
                type="number"
                variant="outlined"
                label="Max Search Results"
                value={maxSearchResults}
                onChange={(e) => setMaxSearchResults(Math.max(1, parseInt(e.target.value) || 1))}
                inputProps={{ min: 1, max: 300 }}
                sx={{ width: '150px' }}
              />
              <TextField
                type="number"
                variant="outlined"
                label="Display Results"
                value={displayResults}
                onChange={(e) => setDisplayResults(Math.max(1, parseInt(e.target.value) || 1))}
                inputProps={{ min: 1, max: maxSearchResults }}
                sx={{ width: '150px' }}
              />
            </Box>
            <Button
              variant="contained"
              onClick={handleSearch}
              disabled={loading}
              sx={{ width: '100%', py: 1.5 }}
            >
              {loading ? 'Searching...' : 'Search'}
            </Button>
          </Box>

          {error && (
            <Typography color="error" align="center" gutterBottom sx={{ mt: 2 }}>
              {error}
            </Typography>
          )}

          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
              <CircularProgress />
            </Box>
          )}

          {articles.length > 0 && (
            <Box sx={{ mt: 4 }}>
              {articles.map((article, index) => (
                <Card 
                  key={index} 
                  sx={{ 
                    mb: 2,
                    cursor: 'pointer',
                    '&:hover': {
                      boxShadow: 3,
                    },
                  }}
                  onClick={() => setExpandedCard(expandedCard === index ? null : index)}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1 }}>
                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                      <Typography variant="caption" color="text.secondary">
                        Article #{index + 1}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Score: {article.score.toFixed(1)}
                      </Typography>
                    </Box>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        setArticles(articles.filter((_, i) => i !== index));
                      }}
                      sx={{ color: 'error.main' }}
                    >
                      <CloseIcon />
                    </IconButton>
                  </Box>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {article.title}
                    </Typography>
                    <Collapse in={expandedCard === index}>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        {article.description}
                      </Typography>
                      <Typography variant="body2" color="primary" paragraph>
                        Reasoning: {article.reasoning}
                      </Typography>
                    </Collapse>
                    <Collapse in={expandedCard !== index}>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        {truncateText(article.description, 5)}
                      </Typography>
                    </Collapse>
                    <Typography variant="caption" color="text.secondary">
                      Published: {new Date(article.published).toLocaleDateString()}
                    </Typography>
                  </CardContent>
                  <CardActions>
                    <Link href={article.link} target="_blank" rel="noopener noreferrer">
                      Read on arXiv
                    </Link>
                  </CardActions>
                </Card>
              ))}
              
              <Button
                variant="contained"
                color="secondary"
                onClick={handleSave}
                disabled={saving}
                sx={{ mt: 2, width: '100%', py: 1.5 }}
              >
                {saving ? 'Saving Articles...' : 'Save Articles'}
              </Button>
            </Box>
          )}
        </Box>

        {/* Right Column */}
        <Box sx={{ width: '250px' }}>
          <Button
            variant="outlined"
            onClick={() => setShowLog(!showLog)}
            sx={{ width: '100%', mb: 2 }}
          >
            Log
          </Button>
          
          {showLog && llmReasoning && (
            <Card sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                LLM Reasoning
              </Typography>
              <Typography variant="body2">
                {llmReasoning}
              </Typography>
            </Card>
          )}
        </Box>
      </Box>
    </Container>
  );
}

export default App; 