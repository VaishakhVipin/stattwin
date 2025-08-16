# StatTwin Implementation Plan

## 🎯 Implementation Priority Order

### Phase 1: Foundation & Data Connection (Week 1-2)
**Goal**: Get FBRef data flowing and basic data structures working

### Phase 2: Core Algorithms (Week 3-4)  
**Goal**: Implement similarity engine and get basic results

### Phase 3: API & Integration (Week 5-6)
**Goal**: Connect algorithms to FastAPI and test end-to-end

---

## 📊 Phase 1: Foundation & Data Connection

### 1.1 FBRef Data Connection Setup
**File**: `backend/app/core/fbref_client.py`
**Priority**: HIGH - Start here

**What to build**:
- FBRef API client class
- Basic authentication/rate limiting
- Player search endpoint
- Player stats endpoint
- Data caching to avoid repeated API calls

**Implementation steps**:
1. Research FBRef API endpoints (fbrapi.com)
2. Create client with session management
3. Implement player search by name
4. Fetch detailed stats for specific players
5. Add basic error handling and retries

**Dependencies**: `requests`, `python-dotenv`

### 1.2 Data Models & Structures
**File**: `backend/app/models/player.py`
**Priority**: HIGH

**What to build**:
- Player data model (Pydantic)
- Stats categories (passing, shooting, defending, possession)
- Metadata fields (age, position, league, continent)
- Data validation and type hints

**Implementation steps**:
1. Define Player model with all required fields
2. Create Stats sub-models for each category
3. Add validation rules (age ranges, valid positions)
4. Test with sample data

**Dependencies**: `pydantic`

### 1.3 Data Storage & Caching
**File**: `backend/app/core/data_manager.py`
**Priority**: MEDIUM

**What to build**:
- Local file storage for raw FBRef responses
- Processed data storage (JSON/Parquet)
- Basic caching layer to avoid re-fetching
- Data versioning and cleanup

**Implementation steps**:
1. Create data storage structure
2. Implement save/load functions for raw data
3. Add processed data storage
4. Basic cache invalidation logic

**Dependencies**: `pandas`, `json`, `pathlib`

---

## 🧮 Phase 2: Core Algorithms

### 2.1 Data Preprocessing Engine
**File**: `backend/app/algorithms/preprocessing.py`
**Priority**: HIGH - Core of the system

**What to build**:
- Raw data cleaning (handle missing values, outliers)
- Per-90 minute stat conversion
- Feature engineering (stat categories, ratios)
- Z-score normalization
- Data validation and quality checks

**Implementation steps**:
1. Create data cleaning functions
2. Implement per-90 conversion logic
3. Build feature engineering pipeline
4. Add normalization functions
5. Test with sample dataset

**Dependencies**: `pandas`, `numpy`, `scikit-learn`

### 2.2 Similarity Engine
**File**: `backend/app/algorithms/similarity.py`
**Priority**: HIGH - Main algorithm

**What to build**:
- Cosine similarity implementation
- Euclidean distance calculation
- Weighted similarity (position-based)
- Similarity score ranking and filtering
- Performance optimization for large datasets

**Implementation steps**:
1. Implement cosine similarity using scikit-learn
2. Add Euclidean distance calculation
3. Create position-based weighting system
4. Build similarity ranking function
5. Add performance optimizations

**Dependencies**: `scikit-learn`, `numpy`

### 2.3 Player Filtering System
**File**: `backend/app/algorithms/filtering.py`
**Priority**: MEDIUM

**What to build**:
- Age range filtering
- League/continent filtering
- Position filtering
- Season filtering
- Combined filter logic

**Implementation steps**:
1. Create individual filter functions
2. Build combined filter pipeline
3. Add filter validation
4. Test filter combinations

**Dependencies**: `pandas`

---

## 🔌 Phase 3: API & Integration

### 3.1 Similarity Service
**File**: `backend/app/services/similarity_service.py`
**Priority**: HIGH

**What to build**:
- Main similarity calculation service
- Orchestrate preprocessing + similarity + filtering
- Result formatting and ranking
- Error handling and validation

**Implementation steps**:
1. Create service class structure
2. Integrate preprocessing pipeline
3. Add similarity calculation
4. Implement filtering system
5. Format results for API response

**Dependencies**: All algorithm modules

### 3.2 FastAPI Endpoints
**File**: `backend/app/api/routes.py`
**Priority**: MEDIUM

**What to build**:
- Player search endpoint
- Similarity calculation endpoint
- Filter application endpoint
- Health check and status endpoints

**Implementation steps**:
1. Create basic FastAPI app structure
2. Add player search endpoint
3. Implement similarity endpoint
4. Add filtering support
5. Basic error handling

**Dependencies**: `fastapi`, similarity service

### 3.3 Main Application
**File**: `backend/app/main.py`
**Priority**: LOW

**What to build**:
- FastAPI app configuration
- Middleware setup
- Route registration
- Server startup configuration

**Implementation steps**:
1. Create FastAPI app instance
2. Add CORS and other middleware
3. Register API routes
4. Add startup/shutdown events

**Dependencies**: `fastapi`, `uvicorn`

---

## 🚀 Getting Started: Week 1 Action Plan

### Day 1-2: FBRef Connection
1. **Research FBRef API**:
   - Visit fbrapi.com
   - Understand authentication
   - Test basic endpoints
   - Document rate limits

2. **Create `fbref_client.py`**:
   - Basic client class
   - Player search function
   - Test with real API calls

### Day 3-4: Data Models
1. **Create `player.py`**:
   - Define Player model
   - Add stat categories
   - Test with sample data

2. **Create `data_manager.py`**:
   - Basic file storage
   - Save/load functions

### Day 5-7: First Algorithm
1. **Create `preprocessing.py`**:
   - Data cleaning functions
   - Per-90 conversion
   - Basic normalization

2. **Test with real data**:
   - Fetch 10-20 players from FBRef
   - Run through preprocessing
   - Verify data quality

---

## 🧪 Testing Strategy

### Algorithm Testing
- **Unit tests** for each function
- **Integration tests** for full pipeline
- **Performance tests** with increasing dataset sizes
- **Edge case testing** (missing data, outliers)

### Data Quality Checks
- **Stat ranges** (ensure per-90 stats are reasonable)
- **Missing data** handling
- **Outlier detection** and handling
- **Data consistency** across seasons/leagues

### API Testing
- **Endpoint functionality** with real data
- **Error handling** (invalid inputs, API failures)
- **Performance** under load
- **Response format** validation

---

## 📁 File Structure After Implementation

```
backend/
├── app/
│   ├── core/
│   │   ├── fbref_client.py      # FBRef API connection
│   │   ├── data_manager.py      # Data storage & caching
│   │   └── config.py            # Configuration settings
│   ├── algorithms/
│   │   ├── preprocessing.py     # Data cleaning & normalization
│   │   ├── similarity.py        # Core similarity algorithms
│   │   └── filtering.py         # Player filtering system
│   ├── models/
│   │   └── player.py            # Data models
│   ├── services/
│   │   └── similarity_service.py # Main business logic
│   ├── api/
│   │   └── routes.py            # API endpoints
│   └── main.py                  # FastAPI app
├── data/
│   ├── raw/                     # Raw FBRef responses
│   ├── processed/               # Clean, normalized data
│   └── metadata/                # Player context data
└── requirements.txt
```

---

## 🎯 Success Metrics

### Week 1-2 (Foundation)
- ✅ FBRef API connection working
- ✅ Can fetch player data
- ✅ Basic data models defined
- ✅ Data storage working

### Week 3-4 (Algorithms)
- ✅ Preprocessing pipeline complete
- ✅ Similarity calculations working
- ✅ Can find similar players
- ✅ Basic filtering working

### Week 5-6 (Integration)
- ✅ FastAPI endpoints working
- ✅ End-to-end similarity search
- ✅ Can handle real user queries
- ✅ Basic error handling

---

## 🚨 Risk Mitigation

### API Rate Limits
- **Solution**: Implement aggressive caching
- **Fallback**: Download CSV exports as backup

### Data Quality Issues
- **Solution**: Robust preprocessing with validation
- **Fallback**: Manual data cleaning scripts

### Performance Issues
- **Solution**: Vectorized operations, efficient data structures
- **Fallback**: Reduce dataset size, optimize algorithms

### Algorithm Accuracy
- **Solution**: Test with known similar players
- **Fallback**: Manual validation, user feedback collection
