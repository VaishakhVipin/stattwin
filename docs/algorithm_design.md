# StatTwin Algorithm Design

## Overview
This document outlines the core algorithms and data processing pipeline for StatTwin, focusing on finding statistically similar soccer players using traditional ML approaches.

## Core Algorithm Components

### 1. Data Preprocessing Pipeline

#### 1.1 Feature Engineering
- **Per-90 Statistics**: Convert raw stats to per-90 minute basis for fair comparison
- **Position-Specific Features**: Group stats by category (passing, shooting, defending, possession)
- **Metadata Enrichment**: Age, league, continent, season as categorical features

#### 1.2 Normalization Strategy
- **Z-Score Normalization**: Standardize numerical features across the entire dataset
- **Robust Scaling**: Use median and IQR for outlier-resistant normalization
- **Feature Scaling**: Ensure all features are on similar scales (0-1 or -1 to 1)

### 2. Similarity Algorithms

#### 2.1 Cosine Similarity (Primary)
- **Formula**: `cos(θ) = (A·B) / (||A|| × ||B||)`
- **Use Case**: Measures playstyle similarity regardless of overall performance level
- **Advantage**: Angle-based, so magnitude differences don't affect similarity scores
- **Implementation**: Use scikit-learn's `cosine_similarity` function

#### 2.2 Euclidean Distance
- **Formula**: `√Σ(x₁-y₁)² + (x₂-y₂)² + ... + (xₙ-yₙ)²`
- **Use Case**: Overall statistical profile similarity
- **Advantage**: Intuitive distance metric
- **Note**: Requires normalized features to be meaningful

#### 2.3 Weighted Similarity
- **Position-Based Weights**: Different stat categories weighted by position importance
  - **Midfielders**: Passing > Shooting
  - **Forwards**: Shooting > Defending
  - **Defenders**: Defending > Shooting
- **Customizable Weights**: Allow users to adjust importance of different stat categories

### 3. Dimensionality Reduction

#### 3.1 Principal Component Analysis (PCA)
- **Purpose**: Reduce noise and identify most important statistical patterns
- **Components**: Start with 10-15 components explaining 90%+ variance
- **Application**: Run similarity algorithms on reduced feature space
- **Benefits**: Faster computation, less overfitting

#### 3.2 t-SNE (t-Distributed Stochastic Neighbor Embedding)
- **Purpose**: 2D visualization of player clusters
- **Use Case**: Interactive scatterplot showing player relationships
- **Parameters**: Perplexity = 30, learning rate = 200
- **Note**: Use for visualization only, not for similarity calculations

### 4. Clustering for Player Archetypes

#### 4.1 K-Means Clustering
- **Purpose**: Group players into statistical archetypes
- **K Selection**: Elbow method or silhouette analysis
- **Features**: Use PCA-reduced features
- **Output**: Player clusters for archetype identification

#### 4.2 DBSCAN (Alternative)
- **Purpose**: Density-based clustering for irregularly shaped clusters
- **Advantage**: No need to specify number of clusters
- **Parameters**: eps = 0.3, min_samples = 5
- **Use Case**: When K-means produces poor results

## Implementation Workflow

### Phase 1: Data Processing
1. **Load FBRef Data**: API calls or CSV imports
2. **Clean Data**: Handle missing values, outliers
3. **Feature Engineering**: Calculate per-90 stats, create position features
4. **Normalization**: Apply Z-score normalization
5. **Store Processed Data**: Save to `data/processed/` for fast loading

### Phase 2: Similarity Engine
1. **Player Selection**: Retrieve reference player's stat vector
2. **Filtering**: Apply user filters (age, league, position)
3. **Similarity Calculation**: Run cosine similarity on filtered dataset
4. **Ranking**: Sort by similarity score, return top N results

### Phase 3: Advanced Features
1. **PCA Implementation**: Reduce dimensions for faster similarity
2. **Clustering**: Identify player archetypes
3. **Visualization**: 2D scatterplot with t-SNE

## Performance Considerations

### Optimization Strategies
- **Vectorization**: Use numpy/pandas for bulk operations
- **Caching**: Store processed data and similarity matrices
- **Batch Processing**: Process multiple players simultaneously
- **Memory Management**: Use efficient data types (float32 vs float64)

### Scalability
- **Dataset Size**: Handle 10K+ players efficiently
- **Response Time**: Target <500ms for similarity queries
- **Memory Usage**: Keep under 2GB for typical deployment

## Data Structure

### Player Feature Vector
```python
{
    "player_id": "string",
    "name": "string",
    "position": "string",
    "age": "int",
    "league": "string",
    "continent": "string",
    "season": "string",
    "stats": {
        "passing": [0.85, 0.12, 0.92],  # Normalized values
        "shooting": [0.45, 0.78, 0.23],
        "defending": [0.12, 0.89, 0.67],
        "possession": [0.78, 0.34, 0.56]
    }
}
```

### Similarity Result
```python
{
    "reference_player": "string",
    "similar_players": [
        {
            "player_id": "string",
            "name": "string",
            "similarity_score": 0.89,
            "position": "string",
            "league": "string"
        }
    ],
    "filters_applied": {
        "age_range": [20, 25],
        "position": "midfielder",
        "league": "premier_league"
    }
}
```

## Testing Strategy

### Algorithm Validation
- **Synthetic Data**: Test with known similar/dissimilar player profiles
- **Cross-Validation**: Ensure similarity scores are consistent
- **Edge Cases**: Handle players with missing stats, extreme outliers
- **Performance Testing**: Measure response times with different dataset sizes

### Quality Metrics
- **Similarity Score Distribution**: Ensure scores are meaningful (not all 0.9+)
- **Position Consistency**: Similar players should generally play similar positions
- **League Distribution**: Results should respect user filters
- **User Feedback**: Collect feedback on result quality

## Future Enhancements

### Advanced Algorithms
- **Graph-Based Similarity**: Use player networks and graph embeddings
- **Time Series Analysis**: Consider player development over seasons
- **Ensemble Methods**: Combine multiple similarity metrics
- **Active Learning**: Improve similarity based on user feedback

### Performance Improvements
- **GPU Acceleration**: Use CUDA for large-scale similarity calculations
- **Distributed Computing**: Scale across multiple servers
- **Real-Time Updates**: Incremental similarity updates as new data arrives
- **Caching Strategies**: Redis for frequently accessed similarity scores
