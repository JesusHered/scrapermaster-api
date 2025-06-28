# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ScraperMaster API is a FastAPI-based web scraping service that uses Playwright to extract content from web pages and convert it to structured markdown. The API provides intelligent content extraction with automatic detection of amounts, dates, contact information, and structured data elements.

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Test the API
python test_api.py

# Test screenshots functionality
python test_screenshots.py
```

### Docker Development
```bash
# Build and run with Docker
docker build -t scrapermaster-api .
docker run -p 8000:8000 scrapermaster-api

# Or use Docker Compose
docker-compose up --build
```

### Production Deployment
```bash
# Start production server (used by start.sh)
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Architecture Overview

### Core Components

**main.py** - Main FastAPI application with three primary endpoints:
- `/scrape` - Main scraping endpoint that extracts content and converts to markdown
- `/screenshots` - Captures multiple screenshots of web pages in Base64 format
- `/health` - Health check endpoint

**ContentProcessor class** - Handles content processing with methods:
- `extract_amounts()` - Detects monetary amounts and quantities
- `extract_structured_data()` - Extracts tables, lists, headings, and contact info
- `clean_and_organize_content()` - Cleans HTML and prioritizes main content

**Playwright Integration** - Web scraping engine configured with:
- English locale (en-US) by default
- Cookie dialog handling via `handle_cookie_dialogs()`
- 5-second wait times for dynamic content loading
- Comprehensive error handling with detailed error types

### Data Models (Pydantic)

**UrlRequest** - Input validation for URL endpoints
**ScrapedContent** - Complete response model containing:
- Cleaned markdown content
- Extracted metadata (counts, flags)
- Images and links arrays
- Structured data (tables, lists, headings, contact info)
- Raw amounts and contact information

### Content Processing Pipeline

1. **Page Loading** - Playwright opens page with English locale
2. **Cookie Handling** - Automatic detection and acceptance of cookie dialogs
3. **Content Extraction** - JavaScript evaluation extracts images and links
4. **HTML Processing** - BeautifulSoup cleans and structures content
5. **Markdown Conversion** - Markdownify converts to clean markdown
6. **Data Extraction** - Regex patterns extract amounts, emails, phones, dates
7. **Structured Analysis** - Tables, lists, and headings are organized

## Key Implementation Details

### Error Handling Strategy
The application uses comprehensive error handling with specific error types:
- Browser/Playwright errors
- Network/Connection errors  
- SSL/Certificate errors
- Timeout errors (30s page load, 5s additional wait)

### Playwright Configuration
- Headless browser with optimized Chrome args
- English locale and US timezone for consistency
- User agent mimicking real browser
- Automatic cookie dialog handling for major sites

### Content Extraction Features
- **Smart Image Detection** - Handles lazy-loaded images via data-src attributes
- **Amount Recognition** - Multi-currency support (USD, EUR, GBP, etc.)
- **Contact Extraction** - Email and phone number patterns
- **Date Recognition** - Multiple date formats (DD/MM/YYYY, YYYY-MM-DD, natural language)
- **Structured Data** - Tables, lists, and heading hierarchy

### Response Optimization
- Images limited to all found (previously 20)
- Links limited to 50 most relevant
- Clean body HTML included for further processing
- Comprehensive metadata for quick analysis

## Testing and Debugging

The repository includes test files that demonstrate proper API usage:
- `test_api.py` - Tests scraping endpoint with example.com
- `test_screenshots.py` - Tests screenshot capture functionality

Both test files include proper error handling and response validation patterns.

## Docker Configuration

The Dockerfile is optimized for production deployment:
- Python 3.11 slim base image
- Playwright Chromium browser pre-installed
- System dependencies for browser operation
- Health check configuration in docker-compose.yml

## Important Notes

- The application is configured to prefer English content by default
- Cookie dialogs are automatically handled for better scraping success
- All URLs must start with http:// or https://
- The API includes CORS support and static file serving
- Screenshots are returned as Base64-encoded PNG images