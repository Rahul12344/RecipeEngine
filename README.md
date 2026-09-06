# RecipeEngine

RecipeEngine is a comprehensive recipe management and recommendation platform that helps users discover, organize, and manage recipes based on their available ingredients and preferences. It supports text-based and image-based lookups of recipes.

## Features
Development in-progress

### 1. Recipe Hub
- Automated batch retrieval of recipes from various sources
- Integration with external recipe APIs
- Web scraping capabilities for recipe collection
- Centralized recipe database

### 2. Smart Recipe Recommendations
- Personalized recipe suggestions based on user preferences
- Machine learning-powered recommendation engine
- Consideration of dietary restrictions and preferences
- Seasonal and trending recipe highlights

### 3. Inventory-Based Filtering
- Filter recipes based on available ingredients
- Smart ingredient matching and substitution suggestions
- Shopping list generation for missing ingredients
- Inventory management system

### 4. Visual Recipe Search
- Image-based recipe search functionality
- Computer vision integration for ingredient recognition
- Visual recipe matching and suggestions
- Mobile-friendly image upload interface

## Technical Stack

- **Backend**: Python with FastAPI/Flask
- **Frontend**: React/Next.js
- **Database**: TBD
- **Machine Learning**: PyTorch for recommendation and image recognition
- **APIs**: Integration with various recipe and ingredient APIs
- **Web Scraping**: TBD

## Getting Started

1. Clone the repository
2. Install dependencies
3. Set up environment variables
4. Run the development server

## Ingestion pipeline

`scripts/run_ingestion.py` runs one full ingestion pass across the 4
supported recipe sources (AllRecipes, Delish, FoodNetwork, Food.com): it
crawls each site, archives every recipe page's raw HTML to S3, and parses +
persists structured `Recipe` data to Postgres. It does one pass and exits --
there is no long-running internal scheduler -- so it's meant to be triggered
by an OS-level scheduler.

Configuration: copy `.env.example` to `.env` and set `RECIPE_ENGINE_DATABASE_URL`
(a Postgres connection string) plus AWS credentials for the S3 archive step.

### Scheduling ingestion

**cron (primary, cross-platform):**

```
crontab -e
```

Add a line like the following to run it every 6 hours (adjust paths and
schedule as needed; cron doesn't source your shell profile, so the
environment variables need to be available to the command itself):

```
0 */6 * * * cd /path/to/RecipeEngine && export $(grep -v '^#' .env | xargs) && /path/to/miniforge3/envs/recipe_engine_env/bin/python scripts/run_ingestion.py >> /path/to/RecipeEngine/logs/ingestion.log 2>&1
```

**launchd (macOS-native alternative):** create a `~/Library/LaunchAgents/com.recipeengine.ingestion.plist`
that runs the same command via a `ProgramArguments` array with a
`StartCalendarInterval` (or `StartInterval`), then load it with
`launchctl load ~/Library/LaunchAgents/com.recipeengine.ingestion.plist`.
launchd plists don't source `.env` either, so either set `EnvironmentVariables`
in the plist or have `ProgramArguments` invoke a small wrapper shell script
that sources `.env` before calling `run_ingestion.py`.
